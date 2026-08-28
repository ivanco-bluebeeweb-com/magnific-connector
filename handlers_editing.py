"""Image editing handlers -- upscale (Creative/Precision), relight, style
transfer, background removal, expand (outpaint). Each is its own confirmed
endpoint (docs.magnific.com/api-reference/image-*), not a model_registry
row, because these take an existing image + edit-specific params rather
than a text-prompt-driven generation body.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
from app import ext, chat
from accounts import _get_key
from models import (
    UpscaleImageParams, RelightImageParams, StyleTransferParams,
    RemoveBackgroundParams, ExpandImageParams, EditTaskRef, GetEditTaskParams,
)

# path per edit "kind" -- confirmed via docs.magnific.com/api-reference/
# image-upscaler-creative, image-relight, image-style-transfer,
# remove-background, image-expand.
_EDIT_PATHS = {
    "upscale_creative": "/v1/ai/image-upscaler-creative",
    "upscale_precision": "/v1/ai/image-upscaler-precision",
    "relight": "/v1/ai/image-relight",
    "style_transfer": "/v1/ai/image-style-transfer",
    "remove_background": "/v1/ai/beta/remove-background",
    "expand": "/v1/ai/image-expand",
}


async def _record_history(ctx, *, model: str, task_id: str, prompt: str, status: str, result_urls: list[str] | None = None):
    try:
        await ctx.store.create("magnific_generations", {
            "kind": "edit", "model": model, "task_id": task_id,
            "prompt": prompt, "status": status, "result_urls": result_urls or [],
        })
    except Exception:
        pass


async def _start_edit(ctx, kind: str, body: dict) -> str:
    key = await _get_key(ctx)
    if not key:
        raise mc.MagnificError("Magnific is not connected. Call connect_magnific first.", "MAGNIFIC_NOT_CONNECTED")
    path = _EDIT_PATHS[kind]
    return await mc.create_task(ctx, key, path, body)


@chat.function(
    name="upscale_image", data_model=EditTaskRef,
    description=(
        "Upscale an image 2x/4x/8x/16x with Magnific's exclusive Creative "
        "engine (can add/infer new detail, supports a guiding prompt) or "
        "Precision engine (faithful super-resolution, no hallucination -- "
        "best for logos, UI, text, product photos). Async -- poll with "
        "get_edit_task."
    ),
)
async def upscale_image(ctx, params: UpscaleImageParams) -> ActionResult:
    """Upscale an image with the Creative or Precision engine."""
    kind = "upscale_creative" if params.mode == "creative" else "upscale_precision"
    body = {"image_url": params.image_url, "scale_factor": params.scale}
    if params.mode == "creative" and params.prompt:
        body["prompt"] = params.prompt
    try:
        task_id = await _start_edit(ctx, kind, body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the upscale request: {exc.detail}")
    await _record_history(ctx, model=kind, task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.ok(EditTaskRef(id=task_id, title="Upscale task", kind=kind, status="pending"))


@chat.function(
    name="relight_image", data_model=EditTaskRef,
    description="Change an image's lighting (direction/mood) with Magnific's relighting model. Async -- poll with get_edit_task.",
)
async def relight_image(ctx, params: RelightImageParams) -> ActionResult:
    """Create an async relighting task for an image."""
    body = {"image_url": params.image_url}
    if params.prompt:
        body["prompt"] = params.prompt
    if params.light_direction:
        body["light_direction"] = params.light_direction
    try:
        task_id = await _start_edit(ctx, "relight", body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the relight request: {exc.detail}")
    await _record_history(ctx, model="relight", task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.ok(EditTaskRef(id=task_id, title="Relight task", kind="relight", status="pending"))


@chat.function(
    name="style_transfer_image", data_model=EditTaskRef,
    description="Apply a reference image's visual style to a source image. Async -- poll with get_edit_task.",
)
async def style_transfer_image(ctx, params: StyleTransferParams) -> ActionResult:
    """Create an async style-transfer task between a source and reference image."""
    body = {
        "image_url": params.image_url,
        "style_reference_url": params.style_reference_url,
        "strength": params.strength,
    }
    try:
        task_id = await _start_edit(ctx, "style_transfer", body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the style transfer request: {exc.detail}")
    await _record_history(ctx, model="style_transfer", task_id=task_id, prompt="", status="pending")
    return ActionResult.ok(EditTaskRef(id=task_id, title="Style transfer task", kind="style_transfer", status="pending"))


@chat.function(
    name="remove_background", data_model=EditTaskRef,
    description="Remove the background from an image, leaving a transparent PNG. Async -- poll with get_edit_task.",
)
async def remove_background(ctx, params: RemoveBackgroundParams) -> ActionResult:
    """Create an async background-removal task for an image."""
    body = {"image_url": params.image_url}
    try:
        task_id = await _start_edit(ctx, "remove_background", body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the background removal request: {exc.detail}")
    await _record_history(ctx, model="remove_background", task_id=task_id, prompt="", status="pending")
    return ActionResult.ok(EditTaskRef(id=task_id, title="Remove background task", kind="remove_background", status="pending"))


@chat.function(
    name="expand_image", data_model=EditTaskRef,
    description="Expand (outpaint) an image's canvas in any direction, optionally guided by a prompt for the new area. Async -- poll with get_edit_task.",
)
async def expand_image(ctx, params: ExpandImageParams) -> ActionResult:
    """Create an async outpaint (canvas expansion) task for an image."""
    body = {
        "image_url": params.image_url,
        "top": params.top, "bottom": params.bottom,
        "left": params.left, "right": params.right,
    }
    if params.prompt:
        body["prompt"] = params.prompt
    try:
        task_id = await _start_edit(ctx, "expand", body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the expand request: {exc.detail}")
    await _record_history(ctx, model="expand", task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.ok(EditTaskRef(id=task_id, title="Expand task", kind="expand", status="pending"))


@chat.function(
    name="get_edit_task", data_model=EditTaskRef,
    description="Poll an image editing task (upscale/relight/style transfer/remove background/expand). Returns result URLs once status is 'done'.",
)
async def get_edit_task(ctx, params: GetEditTaskParams) -> ActionResult:
    """Poll an image editing task and record the result once done."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    if params.kind not in _EDIT_PATHS:
        return ActionResult.error(f"Unknown edit kind '{params.kind}'. Valid: {', '.join(_EDIT_PATHS)}")
    status_path = f"{_EDIT_PATHS[params.kind]}/{params.task_id}"
    try:
        result = await mc.get_task(ctx, key, status_path)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not read task status: {exc.detail}")
    if result["state"] == "done":
        await _record_history(ctx, model=params.kind, task_id=params.task_id, prompt="", status="done", result_urls=result["urls"])
    return ActionResult.ok(EditTaskRef(
        id=params.task_id, title=f"{params.kind} task", kind=params.kind,
        status=result["state"], result_urls=result["urls"],
    ))
