"""Panel UI -- connect form + generation dashboard.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per UI_INTERFACE_STANDARD.md's "left
sidebar, no decorated cards" rule (same convention as Klaviyo Connector's /
MuleSoft Connector's panels.py). Every section is a plain ui.Stack,
left-aligned, sections separated by ui.Divider().

FORM CONTAINER STRETCHED FULL WIDTH, per the standing UI rule: the connect
form's own Stack uses align="stretch" at every nesting level, and its
Form/Button use full_width=True -- never a narrow, centered form floating
in a wide sidebar.

NO DUPLICATED INSTRUCTIONS BETWEEN SIDEBAR AND SETTINGS MODAL: the sidebar
shows only the connect form + a short one-line hint; the full walkthrough
(where to get a key, what it unlocks) lives once, in panels_settings.py's
help copy -- not repeated here.

CENTER SLOT -- a real post-connect dashboard (credit balance + recent
generations + an image-generation form), not the canonical "Nothing to
show here" placeholder, per POST_CONNECT_EXPERIENCE.md for this app.
"""
from __future__ import annotations

from imperal_sdk import ui

import magnific_client as mc
import model_registry as mr
from app import ext
from accounts import _get_key


def _field(label: str, node: ui.UINode) -> ui.UINode:
    """A labeled input: a caption Text above the raw component -- ui.Input/
    ui.Select/ui.Textarea don't accept a `label` kwarg themselves, per the
    confirmed pattern used across every other connector's panels.py."""
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"),
        node,
    ])


def _settings_button() -> ui.UINode:
    return ui.Button("App settings", variant="secondary", size="sm", full_width=True,
                      on_click=ui.Call("__panel__magnific_settings"))


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=2, align="stretch", children=[
        ui.Text("Connect Magnific", variant="subtitle"),
        ui.Text(
            "Paste your API key to start generating.",
            variant="caption",
        ),
        ui.Form(
            action="connect_magnific",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    _field("API key", ui.Input(
                        param_name="api_key",
                        placeholder="mgn_live_••••••••••••••••",
                    )),
                ]),
            ],
        ),
    ])


@ext.panel("magnific_overview", slot="left", title="Magnific", icon="🎨")
async def magnific_overview_panel(ctx, **kwargs) -> object:
    key = await _get_key(ctx)
    connected = bool(key)
    balance_line = ""
    if connected:
        try:
            data = await mc.request(ctx, key, "GET", "/v1/analytics/team-credit-usage")
            row = data.get("data", data) if isinstance(data, dict) else {}
            used = row.get("credits_used", row.get("total_used", None))
            if used is not None:
                balance_line = f"{used} credits used this period"
        except Exception:
            connected = False

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            _connect_form(),
            ui.Divider(),
            _settings_button(),
        ])

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        ui.Text("Magnific", variant="subtitle"),
        ui.Text(balance_line or "Connected.", variant="caption"),
        ui.Divider(),
        ui.ListItem(title="Generate image", icon="Image",
                    on_click=ui.Call("__panel__magnific_center", screen="image")),
        ui.ListItem(title="Generate video", icon="Video",
                    on_click=ui.Call("__panel__magnific_center", screen="video")),
        ui.ListItem(title="Edit image", icon="Wand",
                    on_click=ui.Call("__panel__magnific_center", screen="edit")),
        ui.ListItem(title="Audio", icon="Music",
                    on_click=ui.Call("__panel__magnific_center", screen="audio")),
        ui.ListItem(title="Stock content", icon="Search",
                    on_click=ui.Call("__panel__magnific_center", screen="stock")),
        ui.ListItem(title="History", icon="Clock",
                    on_click=ui.Call("__panel__magnific_center", screen="history")),
        ui.Divider(),
        _settings_button(),
    ])
