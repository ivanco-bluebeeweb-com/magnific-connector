"""The single 'App settings' screen (center slot) -- key management for
Magnific Connector. Per UI_INTERFACE_STANDARD.md: the left sidebar never
wraps the connect form in a Card, and disconnect (never exposed in the
sidebar itself) lives here. The one secondary "App settings" button sits
LAST at the bottom of the sidebar.

This screen also carries the ONE full walkthrough of what a Magnific API
key unlocks and where to get it -- the sidebar's connect form only shows a
one-line hint, per the standing "no duplicated instructions between
sidebar and modal" rule.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from accounts import _get_key


@ext.panel("magnific_settings", slot="center", title="Magnific settings", center_overlay=True)
async def magnific_settings_panel(ctx, **kwargs) -> object:
    key = await _get_key(ctx)
    if not key:
        return ui.Stack(direction="v", gap=3, align="start", children=[
            ui.Text("Подключения", variant="heading"),
            ui.Text("Magnific ещё не подключен.", variant="caption"),
            ui.Text(
                "Ключ можно получить на magnific.com: меню профиля -> "
                "Organization Settings -> API Keys. Ключ проверяется перед "
                "сохранением и используется для генерации изображений, "
                "видео, аудио и поиска стокового контента через ваш "
                "собственный баланс кредитов.",
                variant="caption",
            ),
            ui.Link(label="Open magnific.com", href="https://www.magnific.com/"),
        ])
    return ui.Stack(direction="v", gap=3, align="start", children=[
        ui.Text("Подключения", variant="heading"),
        ui.Stack(direction="v", gap=1, align="start", children=[
            ui.Text("Аккаунт Magnific", variant="body"),
            ui.Text("API-ключ сохранён и проверен.", variant="caption"),
            ui.Button(
                "Отключить", variant="danger", size="sm",
                on_click=ui.Call("disconnect_magnific"),
            ),
        ]),
    ])
