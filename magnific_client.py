"""Thin async HTTP client for the Magnific API (api.magnific.com).

WHY A NEW CLIENT, NOT REUSE OF `Apps/Media Studio/magnific_client.py`.
Different extensions cannot share a Python module across app boundaries on
this platform (each app is deployed as its own isolated bundle) -- and even
if they could, Media Studio's client is scoped to its own `ctx`/error
conventions (MEDIA_PROVIDER_ERROR) tied to its own ActionResult usage. This
client follows the SAME confirmed API contract (task lifecycle, headers,
`{"data": {...}}` envelope) but raises this connector's own `MagnificError`
so handlers.py can turn failures into ActionResult.error() uniformly, same
pattern as klaviyo_client.py's `KlaviyoError`.

WHY POLLING IN v1, NOT WEBHOOKS.
Same reasoning as Media Studio: webhooks need a publicly reachable callback
URL and there is a live, confirmed platform bug in a *different* extension
(Asana Connector) where the webhook layer does not proxy a handler's HTTP
headers/status code back onto the wire -- unverified whether Magnific's
HMAC-signed-body webhook model is affected, so polling (zero dependency on
that unverified path) is what v1 ships. `webhook_url` params exist on the
generate_* calls for a future dev pass once verified safe.
"""
from __future__ import annotations

import asyncio

BASE_URL = "https://api.magnific.com"

# Confirmed via docs.magnific.com/authentication.
_AUTH_HEADER = "x-magnific-api-key"

DONE_STATUSES = {"completed", "complete", "done", "success", "succeeded"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}

DEFAULT_POLL_INTERVAL_S = 3.0
DEFAULT_MAX_POLLS = 100  # ~5 minutes at 3s -- enough for slower video models


class MagnificError(Exception):
    """Raised for any Magnific API failure -- HTTP error, malformed
    response, or a reported task failure. `code` is a short machine-stable
    tag handlers.py can use to decide retry/user-messaging behaviour."""

    def __init__(self, message: str, code: str = "MAGNIFIC_ERROR"):
        super().__init__(message)
        self.detail = message
        self.code = code


def _headers(api_key: str) -> dict:
    return {_AUTH_HEADER: api_key, "Content-Type": "application/json"}


async def request(ctx, api_key: str, method: str, path: str, *, json: dict | None = None, params: dict | None = None) -> dict:
    """One raw call against api.magnific.com. Unwraps the `{"data": {...}}`
    envelope Magnific uses on every documented endpoint -- confirmed
    identical across Mystic/Flux/Seedream/analytics/stock in
    docs.magnific.com/api-reference/*."""
    resp = await ctx.http.request(
        method, f"{BASE_URL}{path}", headers=_headers(api_key),
        json=json, params=params, timeout=30,
    )
    if resp.status_code == 401:
        raise MagnificError("Magnific rejected this API key (401 Unauthorized).", "MAGNIFIC_AUTH_ERROR")
    if resp.status_code == 429:
        raise MagnificError("Magnific rate limit hit -- try again shortly.", "MAGNIFIC_RATE_LIMITED")
    if resp.status_code == 402:
        raise MagnificError("Magnific reports insufficient credits for this request.", "MAGNIFIC_INSUFFICIENT_CREDITS")
    if not (200 <= resp.status_code < 300):
        raise MagnificError(f"Magnific API error (HTTP {resp.status_code}): {resp.text[:300]}", "MAGNIFIC_HTTP_ERROR")
    if not resp.text:
        return {}
    body = resp.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def _extract_status(body: dict) -> str:
    """Defensive: Magnific's task-status field name is confirmed as
    `status` on every documented async endpoint, but the exact casing/
    value set (e.g. 'COMPLETED' vs 'completed') is not guaranteed
    identical everywhere, so this normalizes to lowercase and also checks
    a `task_status` fallback some SDKs alias it to."""
    raw = body.get("status") or body.get("task_status") or ""
    return str(raw).lower()


def _extract_result_urls(body: dict) -> list[str]:
    """Result payloads across Magnific's endpoints use one of a few
    documented-plausible shapes: `generated[]` (image URLs list), `url`
    (single string), or `output` (list or single). Tries each rather than
    assuming one, so a real completed task never silently returns []."""
    for key in ("generated", "output", "urls", "images", "videos"):
        val = body.get(key)
        if isinstance(val, list) and val:
            urls = []
            for item in val:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict):
                    u = item.get("url") or item.get("image") or item.get("video")
                    if u:
                        urls.append(u)
            if urls:
                return urls
    single = body.get("url")
    if isinstance(single, str) and single:
        return [single]
    return []


async def create_task(ctx, api_key: str, create_path: str, body: dict) -> str:
    """POST to a model's create endpoint. Returns the task_id."""
    data = await request(ctx, api_key, "POST", create_path, json=body)
    task_id = data.get("task_id") or data.get("id") or ""
    if not task_id:
        raise MagnificError(
            "Magnific accepted the request but returned no task_id -- "
            "cannot poll for the result.", "MAGNIFIC_NO_TASK_ID",
        )
    return task_id


async def get_task(ctx, api_key: str, status_path: str) -> dict:
    """GET a task's current status. Returns a normalized dict:
    {state: pending|done|failed, urls: [...], raw_status: str}."""
    body = await request(ctx, api_key, "GET", status_path)
    status = _extract_status(body)
    if status in DONE_STATUSES:
        urls = _extract_result_urls(body)
        return {"state": "done", "urls": urls, "raw_status": status}
    if status in FAILED_STATUSES:
        return {"state": "failed", "urls": [], "raw_status": status}
    return {"state": "pending", "urls": [], "raw_status": status or "unknown"}


async def poll_task(
    ctx, api_key: str, status_path: str, *,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    max_polls: int = DEFAULT_MAX_POLLS,
    on_progress=None,
) -> list[str]:
    """Poll a task to completion. Returns the list of result URLs.
    Raises MagnificError on failure or timeout."""
    for attempt in range(1, max_polls + 1):
        if on_progress:
            await on_progress(attempt, max_polls)
        await asyncio.sleep(poll_interval_s)
        result = await get_task(ctx, api_key, status_path)
        if result["state"] == "done":
            if not result["urls"]:
                raise MagnificError(
                    "Magnific reported the task as done but returned no "
                    "result URLs.", "MAGNIFIC_EMPTY_RESULT",
                )
            return result["urls"]
        if result["state"] == "failed":
            raise MagnificError(
                f"Magnific reported the task as failed (status={result['raw_status']}).",
                "MAGNIFIC_TASK_FAILED",
            )
    raise MagnificError(
        f"Magnific task did not finish within {max_polls * poll_interval_s:.0f}s.",
        "MAGNIFIC_TIMEOUT",
    )
