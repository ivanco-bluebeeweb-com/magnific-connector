"""Pydantic params models + SDL entity contracts for Magnific Connector.

All params models are module-scope (V17 federal invariant). Entities/
EntityLists follow the read-tool contract: a single record is an
sdl.Entity subclass, a list result is sdl.EntityList[T] -- never a bare
dict, same convention as every other connector in this portfolio.

WHY `model` IS A FREE STRING, NOT AN ENUM, ON GENERATION PARAMS.
The model catalog (see model_registry.py) is large (12+ image models, 15+
video models) and Magnific adds new ones over time. A pydantic enum would
force a code migration for every new model; a free string validated
against MODEL_REGISTRY at call time (clear error listing valid ids) keeps
the catalog data-driven, same reasoning as Media Studio's
model_registry.py.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection / account management.
# ──────────────────────────────────────────────────────────────────────────


class ConnectMagnificParams(BaseModel):
    api_key: str = Field(
        ..., description="Magnific API key to validate and save for this "
        "user. Get it from magnific.com > user menu > Organization "
        "Settings > API Keys.",
    )


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class CreditBalance(sdl.Entity):
    id: str = ""
    title: str = ""
    credits_used: float = 0.0
    period_start: str = ""
    period_end: str = ""
    detail: str = ""


# ──────────────────────────────────────────────────────────────────────────
# Image generation (generic multi-model path).
# ──────────────────────────────────────────────────────────────────────────


class GenerateImageParams(BaseModel):
    model: str = Field(
        "mystic", description="Which model to use: 'mystic' (default, most "
        "realistic), 'flux-2-pro', 'flux-2-turbo', 'flux-2-klein', "
        "'flux-pro-v1-1', 'flux-dev', 'hyperflux', 'flux-kontext-pro', "
        "'seedream-4', 'seedream-4-5', 'z-image', 'runway-t2i'. See "
        "list_image_models for the full catalog.",
    )
    prompt: str = Field(..., description="Text prompt describing the image to generate.")
    aspect_ratio: str = Field(
        "square_1_1", description="Aspect ratio hint, e.g. 'square_1_1', "
        "'classic_4_3', 'widescreen_16_9', 'social_story_9_16'. Ignored by "
        "models that use pixel width/height instead -- see "
        "list_image_models for which each model actually accepts.",
    )
    num_images: int = Field(1, ge=1, le=4, description="How many images to generate in one call (model-dependent, max 4).")
    reference_image_url: str = Field(
        "", description="Optional publicly reachable reference/input image "
        "URL, for models that support image-to-image or image references "
        "(e.g. Flux Kontext Pro, Flux 2 Klein).",
    )
    webhook_url: str = Field(
        "", description="Optional HTTPS callback URL Magnific POSTs the "
        "result to (HMAC-signed) instead of requiring you to poll "
        "get_image_task. Leave empty to poll manually.",
    )


class ImageTaskRef(sdl.Entity):
    id: str = ""
    title: str = ""
    model: str = ""
    status: str = ""
    image_urls: list[str] = Field(default_factory=list)


class GetImageTaskParams(BaseModel):
    model: str = Field(..., description="The model id the task was created with, e.g. 'mystic', 'flux-2-pro'.")
    task_id: str = Field(..., description="Task id returned by generate_image.")


class ModelInfo(sdl.Entity):
    id: str = ""
    title: str = ""
    kind: str = ""  # image | video | edit | audio
    provider: str = ""
    supports_image_input: bool = False
    notes: str = ""


class ModelInfoList(sdl.EntityList[ModelInfo]):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Image editing (upscale / relight / style transfer / bg removal / expand).
# ──────────────────────────────────────────────────────────────────────────


class UpscaleImageParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable URL of the image to upscale.")
    mode: str = Field(
        "creative", description="'creative' (Magnific's exclusive engine -- "
        "can add/infer new detail, supports prompt+style) or 'precision' "
        "(faithful super-resolution, no hallucination -- best for logos, "
        "UI, text, product photos).",
    )
    scale: int = Field(2, description="Upscale factor: 2, 4, 8, or 16 (model-dependent ceiling).")
    prompt: str = Field("", description="Optional creative-mode prompt to guide added detail/style.")


class RelightImageParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable URL of the image to relight.")
    prompt: str = Field("", description="Optional description of the desired lighting (e.g. 'golden hour, warm rim light').")
    light_direction: str = Field("", description="Optional light direction hint, e.g. 'top_left', 'front', 'back'.")


class StyleTransferParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable URL of the source image.")
    style_reference_url: str = Field(..., description="Publicly reachable URL of the style reference image.")
    strength: float = Field(0.7, ge=0.0, le=1.0, description="How strongly to apply the reference style (0=subtle, 1=full).")


class RemoveBackgroundParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable URL of the image to remove the background from.")


class ExpandImageParams(BaseModel):
    image_url: str = Field(..., description="Publicly reachable URL of the image to expand (outpaint).")
    prompt: str = Field("", description="Optional description of what should appear in the newly expanded area.")
    target_aspect_ratio: str = Field(
        "widescreen_16_9", description="Target aspect ratio after expansion, e.g. 'widescreen_16_9', 'classic_4_3'.",
    )


class EditTaskRef(sdl.Entity):
    id: str = ""
    title: str = ""
    operation: str = ""  # upscale | relight | style_transfer | remove_background | expand
    status: str = ""
    image_urls: list[str] = Field(default_factory=list)


class GetEditTaskParams(BaseModel):
    operation: str = Field(..., description="The edit operation the task was created with, e.g. 'upscale', 'relight'.")
    task_id: str = Field(..., description="Task id returned by the edit call.")


# ──────────────────────────────────────────────────────────────────────────
# Video generation (generic multi-model path).
# ──────────────────────────────────────────────────────────────────────────


class GenerateVideoParams(BaseModel):
    model: str = Field(
        "kling-2.5-pro", description="Which video model to use, e.g. "
        "'kling-2.5-pro', 'kling-2.1-master', 'hailuo-2.3', 'wan-2.6', "
        "'runway-gen4-turbo', 'runway-gen4-aleph', 'ltx-2', "
        "'seedance-v1-pro', 'pixverse-v5', 'omnihuman', 'vfx-1'. See "
        "list_video_models for the full catalog.",
    )
    prompt: str = Field("", description="Text prompt describing the video/motion to generate. Required unless image_url alone drives an image-to-video model.")
    image_url: str = Field(
        "", description="Publicly reachable source image URL, required by "
        "image-to-video models (e.g. 'kling-2.5-pro', 'wan-2.5-i2v') and "
        "optional first-frame guidance for others.",
    )
    duration_seconds: int = Field(5, ge=1, le=60, description="Requested clip duration in seconds. Each model has its own supported range/step -- an out-of-range value is rejected by Magnific with a clear error.")
    aspect_ratio: str = Field("widescreen_16_9", description="Aspect ratio for the output video, e.g. 'widescreen_16_9', 'social_story_9_16', 'square_1_1'.")
    webhook_url: str = Field("", description="Optional HTTPS callback URL for async completion instead of polling get_video_task. Recommended for video -- jobs can take minutes.")


class VideoTaskRef(sdl.Entity):
    id: str = ""
    title: str = ""
    model: str = ""
    status: str = ""
    video_urls: list[str] = Field(default_factory=list)


class GetVideoTaskParams(BaseModel):
    model: str = Field(..., description="The model id the task was created with, e.g. 'kling-2.5-pro'.")
    task_id: str = Field(..., description="Task id returned by generate_video.")


# ──────────────────────────────────────────────────────────────────────────
# Audio generation.
# ──────────────────────────────────────────────────────────────────────────


class GenerateMusicParams(BaseModel):
    prompt: str = Field(..., description="Description of the music to generate, e.g. 'upbeat corporate background track, 30s'.")
    duration_seconds: int = Field(30, description="Target track length in seconds.")


class GenerateSoundEffectParams(BaseModel):
    prompt: str = Field(..., description="Description of the sound effect, e.g. 'glass shattering on concrete'.")
    duration_seconds: float = Field(3.0, description="Target effect length in seconds.")


class IsolateAudioParams(BaseModel):
    audio_url: str = Field(..., description="Publicly reachable URL of the audio/video file to isolate vocals/speech from background noise/music.")


class AudioTaskRef(sdl.Entity):
    id: str = ""
    title: str = ""
    operation: str = ""  # music | sound_effect | isolate
    status: str = ""
    audio_urls: list[str] = Field(default_factory=list)


class GetAudioTaskParams(BaseModel):
    operation: str = Field(..., description="The audio operation the task was created with: 'music', 'sound_effect', or 'isolate'.")
    task_id: str = Field(..., description="Task id returned by the audio generation call.")


# ──────────────────────────────────────────────────────────────────────────
# Stock content search.
# ──────────────────────────────────────────────────────────────────────────


class SearchStockParams(BaseModel):
    query: str = Field(..., description="Search term, e.g. 'business meeting', 'summer sale banner'.")
    content_type: str = Field(
        "images", description="'images' (photos & templates), 'icons', or 'videos'.",
    )
    limit: int = Field(20, ge=1, le=100, description="Max number of results.")
    page: int = Field(1, ge=1, description="Page number for pagination.")


class StockItem(sdl.Entity):
    id: str = ""
    title: str = ""
    thumbnail_url: str = ""
    preview_url: str = ""
    content_type: str = ""
    author: str = ""
    is_premium: bool = False


class StockItemList(sdl.EntityList[StockItem]):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Team analytics.
# ──────────────────────────────────────────────────────────────────────────


class TeamMember(sdl.Entity):
    id: str = ""
    title: str = ""
    email: str = ""
    role: str = ""


class TeamMemberList(sdl.EntityList[TeamMember]):
    pass


class ApiKeyInfo(sdl.Entity):
    id: str = ""
    title: str = ""
    created_at: str = ""
    last_used_at: str = ""
    active: bool = True


class ApiKeyInfoList(sdl.EntityList[ApiKeyInfo]):
    pass


# ──────────────────────────────────────────────────────────────────────────
# Generation history (this connector's own local record, via ctx.store).
# ──────────────────────────────────────────────────────────────────────────


class GenerationRecord(sdl.Entity):
    """One locally-tracked generation call, so `list_generation_results`
    can show a real history even though Magnific itself does not expose a
    'list all my past tasks' endpoint across every model."""
    id: str = ""
    title: str = ""
    kind: str = ""  # image | video | edit | audio
    model: str = ""
    task_id: str = ""
    prompt: str = ""
    status: str = ""
    result_urls: list[str] = Field(default_factory=list)
    created_at: str = ""


class GenerationRecordList(sdl.EntityList[GenerationRecord]):
    pass


class ListGenerationResultsParams(BaseModel):
    kind: str = Field("", description="Optional filter: 'image', 'video', 'edit', or 'audio'. Empty = all kinds.")
    limit: int = Field(20, ge=1, le=100, description="Max number of records to return, most recent first.")
