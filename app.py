"""Extension declaration, secrets, lifecycle hooks -- Magnific Connector.

WHY BYOK (bring-your-own-key), same reasoning as Klaviyo/DataForSEO/n8n.
Magnific (the renamed Freepik API, api.magnific.com) is a paid third-party
generative-AI platform the USER has their own account and credit balance
with. The user pastes their own Magnific API key once, Vault-encrypted via
`ctx.secrets`, and every call spends THEIR OWN credits against THEIR OWN
account.

WHY A SINGLE SECRET (api_key), NOT client_id/client_secret.
Confirmed via docs.magnific.com/authentication: "Currently, private API
keys are the only way to authenticate with the Magnific API ... only
server-to-server calls can be made". There is a separate OAuth/MCP path for
AI assistants (Claude/ChatGPT/Cursor) connecting directly, but that is not
this connector's model -- this is a server-to-server BYOK connector, same
shape as every other API-key connector in the portfolio.

WHY THIS IS A SEPARATE APP FROM MEDIA STUDIO.
Media Studio already uses Magnific internally as one image-generation
provider (`Apps/Media Studio/magnific_client.py` + `model_registry.py`),
but only exposes a narrow slice (mostly Mystic + upscaler) scoped to
article-brief image packages. This connector exposes Magnific's FULL public
surface directly to the user: every image/video/edit/audio model, plus
team analytics and stock content search -- independent of Media Studio,
with its own API key and its own connection lifecycle.

WHY `write_mode="both"`, SAME REASONING AS KLAVIYO/DATAFORSEO CONNECTOR.
Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write this -- leaving a first-time user with no
in-app screen explaining what a Magnific API key is, where to get one, or
whether what they pasted actually works. `write_mode="both"` keeps the
platform Secrets screen working AND lets `connect_magnific` validate the
key against Magnific's own API before writing it.
"""

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "magnific-connector",
    version="0.1.0",
    display_name="Magnific Connector",
    description=(
        "Full access to your own Magnific (formerly Freepik API) account: "
        "AI image generation (Mystic, Flux family, Seedream, Z-Image, "
        "RunWay), video generation (Kling, Hailuo, WAN, RunWay, LTX, "
        "Seedance, PixVerse, OmniHuman, VFX), image editing (Creative/"
        "Precision upscaling, relight, style transfer, background removal, "
        "expand), audio (music generation, sound effects, audio "
        "isolation), team credit/usage analytics, and stock content search "
        "(images, icons, videos). Bring-your-own-account (BYOK): connect "
        "your own Magnific API key, every call spends your own credits."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["magnific:read", "magnific:write"],
)

chat = ChatExtension(
    ext,
    tool_name="magnific-connector",
    description="Image/video/audio generation, image editing, analytics and stock content via your own Magnific account",
)

ext.secret(
    name="magnific_api_key",
    description=(
        "Your Magnific API key, from magnific.com > user menu > "
        "Organization Settings > API Keys. Spent against your own credit "
        "balance on every generation call."
    ),
    write_mode="both",
)


@ext.health_check
async def health_check(ctx) -> bool:
    """Basic liveness check -- confirms the secrets surface is reachable.

    Deliberately does NOT call out to Magnific itself: a health check
    should verify OUR OWN plumbing works, not spend the user's rate-limit
    budget on every kernel liveness probe. Whether the saved key is still
    valid is what connect_magnific / get_magnific_connection are for.
    """
    await ctx.secrets.get("magnific_api_key")


@ext.on_install
async def on_install(ctx):
    """Make the first step traceable -- and knowable.

    A Magnific API key cannot be provisioned for the user, so a fresh
    install is inert by design until one is pasted via connect_magnific.
    Recording that at install time means "nothing works yet" shows up as
    an expected state in the audit log rather than looking like a broken
    deployment -- same reasoning as Klaviyo Connector's on_install.
    """
    await ctx.log(
        "Magnific Connector installed -- awaiting an API key; "
        "call connect_magnific to activate."
    )
