"""Stock content search -- images & templates, icons, videos. Confirmed
endpoints: docs.magnific.com/api-reference/resources/images-and-templates-api,
icons/icons-api, and the videos counterpart in the same Resources family.
These are synchronous search endpoints (not async tasks) -- no polling.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
from app import ext, chat
from accounts import _get_key
from models import SearchStockParams, StockItem, StockItemList

_STOCK_PATHS = {
    "images": "/v1/resources",
    "icons": "/v1/icons",
    "videos": "/v1/resources/videos",
}


@chat.function(
    name="search_stock_content", data_model=StockItemList,
    description=(
        "Search Magnific's stock content library -- 'images' (photos & "
        "templates), 'icons', or 'videos' -- by free-text query."
    ),
)
async def search_stock_content(ctx, params: SearchStockParams) -> ActionResult:
    """Search Magnific's stock library (images/icons/videos) by free text."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    content_type = params.content_type if params.content_type in _STOCK_PATHS else "images"
    path = _STOCK_PATHS[content_type]
    query = {"term": params.query, "limit": params.limit, "page": params.page}
    try:
        data = await mc.request(ctx, key, "GET", path, params=query)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific stock search failed: {exc.detail}")

    rows = data if isinstance(data, list) else data.get("data", data.get("items", []))
    items = []
    for row in rows[: params.limit]:
        if not isinstance(row, dict):
            continue
        items.append(StockItem(
            id=str(row.get("id", "")),
            title=str(row.get("title", row.get("name", ""))),
            thumbnail_url=str(row.get("thumbnail", row.get("preview", {}).get("url", "") if isinstance(row.get("preview"), dict) else row.get("thumbnail_url", ""))),
            preview_url=str(row.get("url", row.get("preview_url", ""))),
            content_type=content_type,
            author=str(row.get("author", {}).get("name", "") if isinstance(row.get("author"), dict) else row.get("author", "")),
            is_premium=bool(row.get("premium", row.get("is_premium", False))),
        ))
    return ActionResult.success(StockItemList(items=items), summary="Search stock content done.")
