"""Audio generation handlers -- music, sound effects, audio isolation.
Confirmed endpoints: docs.magnific.com music-generation/generate,
sound-effects/post-sound-effects, audio-isolation/isolate.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
from app import ext, chat
from accounts import _get_key
from models import (
    GenerateMusicParams, GenerateSoundEffectParams, IsolateAudioParams,
    AudioTaskRef, GetAudioTaskParams,
)

_AUDIO_PATHS = {
    "music": "/v1/ai/music-generation",
    "sound_effect": "/v1/ai/sound-effects",
    "audio_isolation": "/v1/ai/audio-isolation",
}


async def _record_history(ctx, *, model: str, task_id: str, prompt: str, status: str, result_urls: list[str] | None = None):
    try:
        await ctx.store.create("magnific_generations", {
            "kind": "audio", "model": model, "task_id": task_id,
            "prompt": prompt, "status": status, "result_urls": result_urls or [],
        })
    except Exception:
        pass


@chat.function(
    name="generate_music", data_model=AudioTaskRef,
    description="Generate a music track from a text description. Async -- poll with get_audio_task.",
)
async def generate_music(ctx, params: GenerateMusicParams) -> ActionResult:
    """Create an async music generation task."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    body = {"prompt": params.prompt, "duration": params.duration_seconds}
    try:
        task_id = await mc.create_task(ctx, key, _AUDIO_PATHS["music"], body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the music generation request: {exc.detail}")
    await _record_history(ctx, model="music", task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.success(AudioTaskRef(id=task_id, title="Music generation task", kind="music", status="pending"), summary="Generate music done.")


@chat.function(
    name="generate_sound_effect", data_model=AudioTaskRef,
    description="Generate a short sound effect from a text description. Async -- poll with get_audio_task.",
)
async def generate_sound_effect(ctx, params: GenerateSoundEffectParams) -> ActionResult:
    """Create an async sound-effect generation task."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    body = {"prompt": params.prompt, "duration": params.duration_seconds}
    try:
        task_id = await mc.create_task(ctx, key, _AUDIO_PATHS["sound_effect"], body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the sound effect request: {exc.detail}")
    await _record_history(ctx, model="sound_effect", task_id=task_id, prompt=params.prompt, status="pending")
    return ActionResult.success(AudioTaskRef(id=task_id, title="Sound effect task", kind="sound_effect", status="pending"), summary="Generate sound effect done.")


@chat.function(
    name="isolate_audio", data_model=AudioTaskRef,
    description="Isolate vocals/speech from background noise/music in an audio or video file. Async -- poll with get_audio_task.",
)
async def isolate_audio(ctx, params: IsolateAudioParams) -> ActionResult:
    """Create an async task to isolate vocals/speech from an audio/video file."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    body = {"audio_url": params.audio_url}
    try:
        task_id = await mc.create_task(ctx, key, _AUDIO_PATHS["audio_isolation"], body)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected the audio isolation request: {exc.detail}")
    await _record_history(ctx, model="audio_isolation", task_id=task_id, prompt="", status="pending")
    return ActionResult.success(AudioTaskRef(id=task_id, title="Audio isolation task", kind="audio_isolation", status="pending"), summary="Isolate audio done.")


@chat.function(
    name="get_audio_task", data_model=AudioTaskRef,
    description="Poll an audio generation/isolation task (music/sound_effect/audio_isolation). Returns result URLs once status is 'done'.",
)
async def get_audio_task(ctx, params: GetAudioTaskParams) -> ActionResult:
    """Poll an audio task and record the result in local history once done."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    if params.kind not in _AUDIO_PATHS:
        return ActionResult.error(f"Unknown audio kind '{params.kind}'. Valid: {', '.join(_AUDIO_PATHS)}")
    status_path = f"{_AUDIO_PATHS[params.kind]}/{params.task_id}"
    try:
        result = await mc.get_task(ctx, key, status_path)
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not read task status: {exc.detail}")
    if result["state"] == "done":
        await _record_history(ctx, model=params.kind, task_id=params.task_id, prompt="", status="done", result_urls=result["urls"])
    return ActionResult.success(AudioTaskRef(
        id=params.task_id, title=f"{params.kind} task", kind=params.kind,
        status=result["state"], result_urls=result["urls"],
    ), summary="Audio task retrieved.")
