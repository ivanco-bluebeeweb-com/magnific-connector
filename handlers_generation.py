"""Image + video generation handlers -- the generic multi-model path.

WHY GENERIC, NOT ONE HANDLER PER MODEL.
model_registry.py holds {create_path, status_path, body builder} per model
id. generate_image/generate_video look up the spec, build the body, POST,
and return a task ref for polling via get_image_task/get_video_task -- the
SAME four handlers work across all 12 image models and 7 video models.
Adding a model later is a model_registry.py row, never a new handler.

WHY THESE RETURN A PENDING TASK, NOT A BLOCKING WAIT-FOR-RESULT.
Media Studio's magnific_client.generate_image() blocks and polls inline
because it's called from a background job queue. Here the caller is a
live chat turn -- blocking for up to several minutes (video models) would
stall the conversation. So generate_image/generate_video return
immediately with a task_id; get_image_task/get_video_task are the
explicit follow-up poll, and history is recorded via ctx.store so
list_generation_results shows it even if the user never polls again.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
import model_registry as mr
from app import ext, chat
from accounts import _get_key
from models import (
    GenerateImageParams, ImageTaskRef, GetImageTaskParams,
    GenerateVideoParams, VideoTaskRef, GetVideoTaskParams,
)


async def _record_history(ctx, *, kind: str, model: str, task_id: str, prompt: str, status: str, result_urls: list[str] | None = None):
    """Best-effort local history row so list_generation_results has real
    data -- Magnific itself has no cross-model 'list my past tasks' endpoint."""
    try:
        await ctx.store.create("magnific_generations", {
            "kind": kind, "model": model, "task_id": task_id,
            "prompt": prompt, "status": status,
            "result_urls": result_urls or [],
        })
    except Exception:
        pass  # history is a convenience, never block the real action on it


@chat.function(
    name="generate_image", data_model=ImageTaskRef,
    description=(
        "Generate styled image(s) with a chosen Magnific model (Mystic, "
        "Flux family, Seedream, Z-Image, RunWay T2I). Async -- returns a "
        "task_id; poll with get_image_task until status is 'done'."
    ),
)
async def generate_image(ctx, params: GenerateImageParams) -> ActionResult:
    """Create an async image generation task on the chosen model."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        spec = mr.get_image_model(params.model)
    except ValueError as exc:
        return ActionResult.error(str(exc))

    body = spec.build_body(
        params.prompt, aspect_ratio=params.aspect_ratio,
        reference_image_url=params.reference_image_url,
    )
    if params.webhook_url:
        body["webhook_url"] = params.webhook_url

    try:
        task_id = await mc.create_task(ctx, key, spec.create_path, body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the image generation request: {exc.detail}")

    await _record_history(ctx, kind="image", model=spec.id, task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.ok(ImageTaskRef(
        id=task_id, title=f"{spec.title} image task", model=spec.id, status="pending",
    ))


@chat.function(
    name="get_image_task", data_model=ImageTaskRef,
    description="Poll an image generation task's status. Returns image URLs once status is 'done'.",
)
async def get_image_task(ctx, params: GetImageTaskParams) -> ActionResult:
    """Poll an image task and record the result in local history once done."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        spec = mr.get_image_model(params.model)
    except ValueError as exc:
        return ActionResult.error(str(exc))

    status_path = spec.status_path_tmpl.format(task_id=params.task_id)
    try:
        result = await mc.get_task(ctx, key, status_path)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not read task status: {exc.detail}")

    if result["state"] == "done":
        await _record_history(ctx, kind="image", model=spec.id, task_id=params.task_id, prompt="", status="done", result_urls=result["urls"])
    return ActionResult.ok(ImageTaskRef(
        id=params.task_id, title=f"{spec.title} image task", model=spec.id,
        status=result["state"], image_urls=result["urls"],
    ))


@chat.function(
    name="generate_video", data_model=VideoTaskRef,
    description=(
        "Generate a video with a chosen Magnific model (Kling, Hailuo, "
        "WAN, RunWay, Seedance, PixVerse). Async and often slow (minutes) "
        "-- returns a task_id; poll with get_video_task, or pass "
        "webhook_url for a callback instead."
    ),
)
async def generate_video(ctx, params: GenerateVideoParams) -> ActionResult:
    """Create an async video generation task on the chosen model."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        spec = mr.get_video_model(params.model)
    except ValueError as exc:
        return ActionResult.error(str(exc))
    if spec.supports_image_input and not params.image_url and not params.prompt:
        return ActionResult.error(f"{spec.title} needs either image_url or prompt (or both).")

    body = spec.build_body(
        params.prompt, image_url=params.image_url,
        duration_seconds=params.duration_seconds,
    )
    if params.webhook_url:
        body["webhook_url"] = params.webhook_url

    try:
        task_id = await mc.create_task(ctx, key, spec.create_path, body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the video generation request: {exc.detail}")

    await _record_history(ctx, kind="video", model=spec.id, task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.ok(VideoTaskRef(
        id=task_id, title=f"{spec.title} video task", model=spec.id, status="pending",
    ))


@chat.function(
    name="get_video_task", data_model=VideoTaskRef,
    description="Poll a video generation task's status. Returns video URLs once status is 'done'.",
)
async def get_video_task(ctx, params: GetVideoTaskParams) -> ActionResult:
    """Poll a video task and record the result in local history once done."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        spec = mr.get_video_model(params.model)
    except ValueError as exc:
        return ActionResult.error(str(exc))

    status_path = spec.status_path_tmpl.format(task_id=params.task_id)
    try:
        result = await mc.get_task(ctx, key, status_path)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not read task status: {exc.detail}")

    if result["state"] == "done":
        await _record_history(ctx, kind="video", model=spec.id, task_id=params.task_id, prompt="", status="done", result_urls=result["urls"])
    return ActionResult.ok(VideoTaskRef(
        id=params.task_id, title=f"{spec.title} video task", model=spec.id,
        status=result["state"], video_urls=result["urls"],
    ))
