"""Model registry -- one row per Magnific model = {endpoint paths, body
builder, kind}. This is the seam that lets 4 generic handlers
(generate_image/generate_video/get_image_task/get_video_task) cover the
entire Magnific model catalog instead of one handler per model.

WHY THIS EXISTS (same reasoning as Media Studio's model_registry.py).
Confirmed via docs.magnific.com/api-reference: every model is its own REST
path with its own request-body shape (Imagen4-style models want
aspect_ratio, some want raw width/height, Kontext/Klein want reference
images, etc.). One row = {create_path, status_path, body builder}.
Response *parsing* (status/urls) is identical across every async task
endpoint (`magnific_client._extract_status/_extract_result_urls`), so only
request-building differs per row.

WHY NOT EVERY DOCUMENTED MODEL IS LISTED HERE YET.
Some model pages (e.g. a few Flux/Seedream variants, several video models)
sit behind bot-protected rendering that this Discovery pass could not open
field-by-field. Rather than guess a body shape and ship a silently-wrong
request, only models with a CONFIRMED field-by-field body from llms.txt +
opened pages are listed. `check_new_models` in handlers_catalog.py points
back to this file as the place to add a confirmed model later -- adding a
row here never requires touching handlers.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class ModelSpec:
    id: str
    title: str
    kind: str  # image | video
    create_path: str
    status_path_tmpl: str  # "{task_id}" placeholder
    build_body: Callable[..., dict]
    supports_image_input: bool = False
    tags: list[str] = field(default_factory=list)


def _img_body(prompt: str, *, aspect_ratio: str = "", reference_image_url: str = "", **_) -> dict:
    body: dict = {"prompt": prompt}
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if reference_image_url:
        body["reference_images"] = [reference_image_url]
    return body


def _img_wh_body(prompt: str, *, reference_image_url: str = "", **_) -> dict:
    # Pixel-based models (no aspect_ratio enum) -- default to a common
    # 4:3 landscape size, confirmed acceptable range 512-2048 per model docs.
    body: dict = {"prompt": prompt, "width": 1024, "height": 768}
    if reference_image_url:
        body["reference_images"] = [reference_image_url]
    return body


def _mystic_body(prompt: str, *, aspect_ratio: str = "", **_) -> dict:
    body = {"prompt": prompt}
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    return body


def _video_body(prompt: str, *, image_url: str = "", duration_seconds: int = 5, aspect_ratio: str = "", **_) -> dict:
    body: dict = {"duration": duration_seconds}
    if prompt:
        body["prompt"] = prompt
    if image_url:
        body["image"] = image_url
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    return body


IMAGE_MODELS: dict[str, ModelSpec] = {
    "mystic": ModelSpec(
        "mystic", "Mystic", "image",
        "/v1/ai/mystic", "/v1/ai/mystic/{task_id}", _mystic_body,
        tags=["recommended", "photorealistic"],
    ),
    "flux-2-pro": ModelSpec(
        "flux-2-pro", "Flux 2 Pro", "image",
        "/v1/ai/text-to-image/flux-2-pro", "/v1/ai/text-to-image/flux-2-pro/{task_id}", _img_body,
        supports_image_input=True, tags=["professional"],
    ),
    "flux-2-turbo": ModelSpec(
        "flux-2-turbo", "Flux 2 Turbo", "image",
        "/v1/ai/text-to-image/flux-2-turbo", "/v1/ai/text-to-image/flux-2-turbo/{task_id}", _img_wh_body,
        tags=["fast", "cheap"],
    ),
    "flux-2-klein": ModelSpec(
        "flux-2-klein", "Flux 2 Klein", "image",
        "/v1/ai/text-to-image/flux-2-klein", "/v1/ai/text-to-image/flux-2-klein/{task_id}", _img_body,
        supports_image_input=True, tags=["fast", "multi-reference"],
    ),
    "flux-pro-v1-1": ModelSpec(
        "flux-pro-v1-1", "Flux Pro 1.1", "image",
        "/v1/ai/text-to-image/flux-pro-v1-1", "/v1/ai/text-to-image/flux-pro-v1-1/{task_id}", _img_body,
        tags=["premium"],
    ),
    "flux-dev": ModelSpec(
        "flux-dev", "Flux Dev", "image",
        "/v1/ai/text-to-image/flux-dev", "/v1/ai/text-to-image/flux-dev/{task_id}", _img_body,
        tags=["detailed"],
    ),
    "hyperflux": ModelSpec(
        "hyperflux", "Hyperflux", "image",
        "/v1/ai/text-to-image/hyperflux", "/v1/ai/text-to-image/hyperflux/{task_id}", _img_body,
        tags=["ultra-fast"],
    ),
    "flux-kontext-pro": ModelSpec(
        "flux-kontext-pro", "Flux Kontext Pro", "image",
        "/v1/ai/text-to-image/flux-kontext-pro", "/v1/ai/text-to-image/flux-kontext-pro/{task_id}", _img_body,
        supports_image_input=True, tags=["context-aware"],
    ),
    "seedream-4": ModelSpec(
        "seedream-4", "Seedream 4", "image",
        "/v1/ai/text-to-image/seedream-4", "/v1/ai/text-to-image/seedream-4/{task_id}", _img_body,
        tags=["fast"],
    ),
    "seedream-4-5": ModelSpec(
        "seedream-4-5", "Seedream 4.5", "image",
        "/v1/ai/text-to-image/seedream-4-5", "/v1/ai/text-to-image/seedream-4-5/{task_id}", _img_body,
        tags=["fast", "high-quality"],
    ),
    "z-image": ModelSpec(
        "z-image", "Z-Image", "image",
        "/v1/ai/text-to-image/z-image", "/v1/ai/text-to-image/z-image/{task_id}", _img_body,
        tags=["fast"],
    ),
    "runway-t2i": ModelSpec(
        "runway-t2i", "RunWay Text-to-Image", "image",
        "/v1/ai/text-to-image/runway-t2i", "/v1/ai/text-to-image/runway-t2i/{task_id}", _img_body,
        tags=["cinematic"],
    ),
}

VIDEO_MODELS: dict[str, ModelSpec] = {
    "kling-2.5-pro": ModelSpec(
        "kling-2.5-pro", "Kling 2.5 Pro", "video",
        "/v1/ai/image-to-video/kling-v2.5-pro", "/v1/ai/image-to-video/kling-v2.5-pro/{task_id}", _video_body,
        supports_image_input=True, tags=["recommended"],
    ),
    "kling-2.1": ModelSpec(
        "kling-2.1", "Kling 2.1", "video",
        "/v1/ai/image-to-video/kling-v2.1", "/v1/ai/image-to-video/kling-v2.1/{task_id}", _video_body,
        supports_image_input=True, tags=[],
    ),
    "hailuo-2.3": ModelSpec(
        "hailuo-2.3", "Hailuo 2.3", "video",
        "/v1/ai/image-to-video/minimax-hailuo-02-768p", "/v1/ai/image-to-video/minimax-hailuo-02-768p/{task_id}", _video_body,
        supports_image_input=True, tags=["fast"],
    ),
    "wan-2.5-i2v": ModelSpec(
        "wan-2.5-i2v", "WAN 2.5 Image-to-Video", "video",
        "/v1/ai/image-to-video/wan-2.5", "/v1/ai/image-to-video/wan-2.5/{task_id}", _video_body,
        supports_image_input=True, tags=[],
    ),
    "runway-gen4-turbo": ModelSpec(
        "runway-gen4-turbo", "RunWay Gen-4 Turbo", "video",
        "/v1/ai/image-to-video/runway-gen4-turbo", "/v1/ai/image-to-video/runway-gen4-turbo/{task_id}", _video_body,
        supports_image_input=True, tags=["cinematic"],
    ),
    "seedance-pro": ModelSpec(
        "seedance-pro", "Seedance 1.0 Pro", "video",
        "/v1/ai/image-to-video/seedance-pro", "/v1/ai/image-to-video/seedance-pro/{task_id}", _video_body,
        supports_image_input=True, tags=[],
    ),
    "pixverse-v5": ModelSpec(
        "pixverse-v5", "PixVerse V5", "video",
        "/v1/ai/image-to-video/pixverse-v5", "/v1/ai/image-to-video/pixverse-v5/{task_id}", _video_body,
        supports_image_input=True, tags=[],
    ),
}


def get_image_model(model_id: str) -> ModelSpec:
    spec = IMAGE_MODELS.get(model_id)
    if not spec:
        valid = ", ".join(sorted(IMAGE_MODELS))
        raise ValueError(f"Unknown image model '{model_id}'. Valid ids: {valid}")
    return spec


def get_video_model(model_id: str) -> ModelSpec:
    spec = VIDEO_MODELS.get(model_id)
    if not spec:
        valid = ", ".join(sorted(VIDEO_MODELS))
        raise ValueError(f"Unknown video model '{model_id}'. Valid ids: {valid}")
    return spec
