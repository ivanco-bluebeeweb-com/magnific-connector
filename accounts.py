"""Connect/disconnect Magnific, account balance -- same validate-before-save
pattern as Klaviyo Connector's connect_klaviyo: a bad key is rejected
immediately instead of failing silently on first real use later.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import magnific_client as mc
from app import ext, chat
from models import (
    NoParams,
    ConnectMagnificParams, ProviderConnection,
    CreditBalance,
)

_SECRET_NAME = "magnific_api_key"


async def _get_key(ctx) -> str:
    return (await ctx.secrets.get(_SECRET_NAME)) or ""


@chat.function(
    name="connect_magnific", data_model=ProviderConnection,
    description=(
        "Connect Magnific by saving your API key, after checking it "
        "actually works. Get a key from magnific.com: User menu -> "
        "Organization Settings -> API Keys."
    ),
)
async def connect_magnific(ctx, params: ConnectMagnificParams) -> ActionResult:
    """Validate the key against Magnific before saving it."""
    key = (params.api_key or "").strip()
    if not key:
        return ActionResult.error("API key is required.")
    try:
        # Cheapest real read available: team credit usage. Confirms the
        # key authenticates without spending any generation credits.
        await mc.request(ctx, key, "GET", "/v1/analytics/team-credit-usage")
    except mc.MagnificError as exc:
        return ActionResult.error(f"Magnific rejected this API key: {exc.detail}")
    except Exception as exc:  # network/timeout etc.
        return ActionResult.error(f"Could not reach Magnific to verify the key: {exc}")

    await ctx.secrets.set(_SECRET_NAME, key)
    return ActionResult.success(ProviderConnection(
        id="magnific", title="Magnific", connected=True,
        detail="Connected -- API key verified.",
    ), summary="Magnific connected.")


@chat.function(
    name="disconnect_magnific", data_model=ProviderConnection,
    description="Disconnect Magnific: deletes the saved API key. Existing generation history recorded here is kept.",
)
async def disconnect_magnific(ctx, params: NoParams) -> ActionResult:
    """Delete the saved API key. Existing local generation history stays."""
    await ctx.secrets.delete(_SECRET_NAME)
    return ActionResult.success(ProviderConnection(
        id="magnific", title="Magnific", connected=False,
        detail="Disconnected -- API key removed.",
    ), summary="Magnific disconnected.")


@chat.function(
    name="get_magnific_connection", data_model=ProviderConnection,
    description="Check whether Magnific is currently connected (does not reveal the saved API key).",
)
async def get_magnific_connection(ctx, params: NoParams) -> ActionResult:
    """Report whether an API key is currently saved for this user."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.success(ProviderConnection(
            id="magnific", title="Magnific", connected=False,
            detail="Not connected -- call connect_magnific with your API key.",
        ), summary="Magnific connection retrieved.")
    return ActionResult.success(ProviderConnection(
        id="magnific", title="Magnific", connected=True, detail="Connected.",
    ), summary="Magnific connection retrieved.")


@chat.function(
    name="get_account_balance", data_model=CreditBalance,
    description=(
        "Read your Magnific team's current credit usage/balance for the "
        "current billing period -- the first thing to check before a big "
        "generation batch."
    ),
)
async def get_account_balance(ctx, params: NoParams) -> ActionResult:
    """Read the team's current credit usage for the billing period."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Magnific is not connected. Call connect_magnific first.")
    try:
        data = await mc.request(ctx, key, "GET", "/v1/analytics/team-credit-usage")
    except mc.MagnificError as exc:
        return ActionResult.error(f"Could not read Magnific credit usage: {exc.detail}")

    return ActionResult.success(CreditBalance(
        id="magnific-balance", title="Magnific credit usage",
        credits_used=float(data.get("credits_used", data.get("total_credits_used", 0)) or 0),
        period_start=str(data.get("period_start", "")),
        period_end=str(data.get("period_end", "")),
        detail="Credit usage for the current billing period.",
    ), summary="Account balance retrieved.")
