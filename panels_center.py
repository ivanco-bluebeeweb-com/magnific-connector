"""Center panel -- generation dashboard with screen dispatch (image, video,
edit, audio, stock, history), one panel_id per UI_COMPONENT_VOCABULARY.md's
master-detail pattern (kwargs pick the screen instead of a separate panel
per screen).
"""
from __future__ import annotations

from imperal_sdk import ui

import model_registry as mr
from app import ext
from accounts import _get_key


IMAGE_MODEL_OPTIONS = [{"value": mid, "label": spec.title} for mid, spec in mr.IMAGE_MODELS.items()]
VIDEO_MODEL_OPTIONS = [{"value": mid, "label": spec.title} for mid, spec in mr.VIDEO_MODELS.items()]
ASPECT_RATIO_OPTIONS = [
    {"value": "square_1_1", "label": "Квадрат 1:1"},
    {"value": "classic_4_3", "label": "Классика 4:3"},
    {"value": "widescreen_16_9", "label": "Широкий 16:9"},
    {"value": "social_story_9_16", "label": "Сторис 9:16"},
]


def _image_screen() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Сгенерировать изображение", variant="subtitle"),
        ui.Form(
            action="generate_image", submit_label="Сгенерировать", full_width=True,
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    ui.Select(param_name="model", label="Модель", options=IMAGE_MODEL_OPTIONS,
                              placeholder="Выберите модель генерации"),
                    ui.Textarea(param_name="prompt", label="Промпт",
                                placeholder="Продуктовое фото керамической кружки на деревянном столе, мягкий дневной свет"),
                    ui.Select(param_name="aspect_ratio", label="Соотношение сторон",
                              options=ASPECT_RATIO_OPTIONS, placeholder="Выберите соотношение сторон"),
                ]),
            ],
        ),
    ])


def _video_screen() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Сгенерировать видео", variant="subtitle"),
        ui.Form(
            action="generate_video", submit_label="Сгенерировать", full_width=True,
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    ui.Select(param_name="model", label="Модель", options=VIDEO_MODEL_OPTIONS,
                              placeholder="Выберите модель видео"),
                    ui.Textarea(param_name="prompt", label="Описание сцены",
                                placeholder="Камера медленно приближается к чашке кофе на столе у окна, пар поднимается вверх"),
                    ui.Input(param_name="image_url", label="Референс-изображение (необязательно)",
                             placeholder="https://example.com/reference.jpg"),
                ]),
            ],
        ),
    ])


def _edit_screen() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Редактировать изображение", variant="subtitle"),
        ui.Text("Апскейл, релайт, перенос стиля, удаление фона, расширение холста.", variant="caption"),
        ui.Form(
            action="upscale_image", submit_label="Апскейлить (Creative)", full_width=True,
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    ui.Input(param_name="image_url", label="URL изображения",
                             placeholder="https://example.com/photo.jpg"),
                    ui.Select(param_name="scale_factor", label="Множитель увеличения",
                              options=[{"value": "2x", "label": "2x"}, {"value": "4x", "label": "4x"},
                                       {"value": "8x", "label": "8x"}, {"value": "16x", "label": "16x"}],
                              placeholder="Выберите множитель"),
                ]),
            ],
        ),
    ])


def _audio_screen() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Сгенерировать музыку", variant="subtitle"),
        ui.Form(
            action="generate_music", submit_label="Сгенерировать", full_width=True,
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    ui.Textarea(param_name="prompt", label="Описание трека",
                                placeholder="Спокойный лоу-фай бит для видео о кофейне, 90 BPM"),
                    ui.Input(param_name="duration_seconds", label="Длительность (сек)",
                             placeholder="30"),
                ]),
            ],
        ),
    ])


def _stock_screen() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Поиск стокового контента", variant="subtitle"),
        ui.Form(
            action="search_stock_content", submit_label="Искать", full_width=True,
            children=[
                ui.Stack(direction="v", gap=2, align="stretch", children=[
                    ui.Input(param_name="query", label="Поисковый запрос",
                             placeholder="кофейная чашка на столе"),
                    ui.Select(param_name="content_type", label="Тип контента",
                              options=[{"value": "images", "label": "Изображения"},
                                       {"value": "icons", "label": "Иконки"},
                                       {"value": "videos", "label": "Видео"}],
                              placeholder="Выберите тип контента"),
                ]),
            ],
        ),
    ])


async def _history_screen(ctx) -> ui.UINode:
    page = await ctx.store.query("magnific_generations", limit=50, order_by="-created_at")
    rows = [
        {"model": r.get("model", ""), "kind": r.get("kind", ""),
         "status": r.get("status", ""), "task_id": r.get("task_id", "")}
        for r in (page.data if hasattr(page, "data") else [])
    ]
    if not rows:
        return ui.Empty(message="Пока нет истории генераций.", icon="Clock")
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("История генераций", variant="subtitle"),
        ui.DataTable(
            columns=[
                ui.DataColumn("kind", "Тип", sortable=True),
                ui.DataColumn("model", "Модель", sortable=True),
                ui.DataColumn("status", "Статус", sortable=True),
                ui.DataColumn("task_id", "ID задачи"),
            ],
            rows=rows,
        ),
    ])


@ext.panel("magnific_center", slot="center", title="Magnific", icon="🎨", center_overlay=True)
async def magnific_center_panel(ctx, screen: str = "image", **kwargs) -> object:
    key = await _get_key(ctx)
    if not key:
        return ui.Empty(message="Подключите Magnific из левой панели, чтобы начать генерацию.", icon="🎨")
    if screen == "video":
        return _video_screen()
    if screen == "edit":
        return _edit_screen()
    if screen == "audio":
        return _audio_screen()
    if screen == "stock":
        return _stock_screen()
    if screen == "history":
        return await _history_screen(ctx)
    return _image_screen()
