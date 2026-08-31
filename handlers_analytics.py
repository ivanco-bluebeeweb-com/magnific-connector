"""Analytics (team members, API keys), model catalog listing, and local
generation history. Analytics endpoints confirmed via
docs.magnific.com/api-reference/analytics/overview (team-credit-usage used
already in accounts.py; members/api-keys are siblings in the same family).
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
import model_registry as mr
from app import ext, chat
from accounts import _get_key
from models import (
    NoParams, TeamMember, TeamMemberList, ApiKeyInfo, ApiKeyInfoList,
    ModelInfo, ModelInfoList, GenerationRecord, GenerationRecordList,
    ListGenerationResultsParams,
)


@chat.function(
    name="list_team_members", data_model=TeamMemberList,
    description="List the members of your Magnific organization/team.",
)
async def list_team_members(ctx, params: NoParams) -> ActionResult:
    """List the members of the connected Magnific organization."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        data = await mc.request(ctx, key, "GET", "/v1/analytics/members")
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not list team members: {exc.detail}")
    rows = data if isinstance(data, list) else data.get("data", data.get("members", []))
    members = [
        TeamMember(
            id=str(r.get("id", "")), title=str(r.get("name", r.get("email", ""))),
            email=str(r.get("email", "")), role=str(r.get("role", "")),
        )
        for r in rows if isinstance(r, dict)
    ]
    return ActionResult.success(TeamMemberList(items=members), summary="Team members listed.")


@chat.function(
    name="list_api_keys", data_model=ApiKeyInfoList,
    description="List the API keys registered on your Magnific organization (never reveals key secret values).",
)
async def list_api_keys(ctx, params: NoParams) -> ActionResult:
    """List the API keys registered on the connected Magnific organization."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        data = await mc.request(ctx, key, "GET", "/v1/analytics/api-keys")
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not list API keys: {exc.detail}")
    rows = data if isinstance(data, list) else data.get("data", data.get("api_keys", []))
    keys = [
        ApiKeyInfo(
            id=str(r.get("id", "")), title=str(r.get("name", r.get("label", ""))),
            created_at=str(r.get("created_at", "")), last_used_at=str(r.get("last_used_at", "")),
            active=bool(r.get("active", True)),
        )
        for r in rows if isinstance(r, dict)
    ]
    return ActionResult.success(ApiKeyInfoList(items=keys), summary="Api keys listed.")


@chat.function(
    name="list_image_models", data_model=ModelInfoList,
    description="List every image generation model this connector supports, with its id and notes -- use the id in generate_image's model field.",
)
async def list_image_models(ctx, params: NoParams) -> ActionResult:
    """List every image model this connector's registry supports."""
    items = [
        ModelInfo(id=s.id, title=s.title, kind=s.kind, supports_image_input=s.supports_image_input, notes=", ".join(s.tags))
        for s in mr.IMAGE_MODELS.values()
    ]
    return ActionResult.success(ModelInfoList(items=items), summary="Image models listed.")


@chat.function(
    name="list_video_models", data_model=ModelInfoList,
    description="List every video generation model this connector supports, with its id and notes -- use the id in generate_video's model field.",
)
async def list_video_models(ctx, params: NoParams) -> ActionResult:
    """List every video model this connector's registry supports."""
    items = [
        ModelInfo(id=s.id, title=s.title, kind=s.kind, supports_image_input=s.supports_image_input, notes=", ".join(s.tags))
        for s in mr.VIDEO_MODELS.values()
    ]
    return ActionResult.success(ModelInfoList(items=items), summary="Video models listed.")


@chat.function(
    name="list_generation_results", data_model=GenerationRecordList,
    description="List your past generation/edit/video actions with filters by type, status, date range -- this connector's own locally-tracked history (Magnific has no cross-model 'list all my tasks' endpoint).",
)
async def list_generation_results(ctx, params: ListGenerationResultsParams) -> ActionResult:
    """List this connector's own locally-tracked generation history."""
    where = {"kind": params.kind} if params.kind else None
    page = await ctx.store.query("magnific_generations", where=where, limit=params.limit, order_by="-created_at")
    items = [
        GenerationRecord(
            id=str(row.id), title=f"{row.data.get('kind', '')}: {row.data.get('model', '')}",
            kind=str(row.data.get("kind", "")), model=str(row.data.get("model", "")),
            task_id=str(row.data.get("task_id", "")), prompt=str(row.data.get("prompt", "")),
            status=str(row.data.get("status", "")), result_urls=list(row.data.get("result_urls", []) or []),
            created_at=str(getattr(row, "created_at", "")),
        )
        for row in page.data
    ]
    return ActionResult.success(GenerationRecordList(items=items), summary="Generation results listed.")
