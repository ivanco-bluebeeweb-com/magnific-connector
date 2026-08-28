# Magnific Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`, `concepts/panels.md`. Основано на функционале `magnific-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Прогресс-индикатор с точной оценкой оставшегося времени для видео-задач НЕДОСТУПЕН — Magnific не отдаёт ETA. Реализация: обычный статус "Обрабатывается" + периодический ручной/авто-рефреш через `ui.Call`. Все остальные пункты идеального флоу реализуемы штатным словарём примитивов.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="stretch") + `ui.Text`(баланс credits) + `ui.Divider` + navigation `ui.ListItem`(Generate Image/Generate Video/Edit Image/Audio/Stock/History) + `ui.Button`("App settings", secondary, единственная) | Без карточек по стандарту; форма подключения (когда не подключено) занимает всю ширину сайдбара, `align="stretch"` на каждом уровне контейнера. |
| Generate Image (center, default) | `ui.Select`(param_name="model", лейбл "Модель", options: Mystic/Flux 2 Pro/Flux 2 Turbo/Seedream 4.5/Z-Image Turbo/Runway T2I) + `ui.Textarea`(param_name="prompt", лейбл "Промпт", placeholder="Продуктовое фото керамической кружки на деревянном столе, мягкий дневной свет") + `ui.Select`(param_name="aspect_ratio", лейбл "Соотношение сторон") + `ui.Button`("Сгенерировать", primary) | `Select` для модели — конечный список, не свободный текст; `Textarea` — промпт часто длиннее одной строки. |
| Generation Result | `ui.Image`(результат) + `ui.KeyValue`(model/aspect_ratio/task_id/status) + `ui.Row`(`ui.Button`("Апскейлить")+`ui.Button`("Ещё вариант")) | Показ результата с прямыми действиями "что дальше" — апскейл сразу логичный next-step. |
| Generate Video | `ui.Select`(model: Kling 2.6 Pro/Hailuo 2.3/WAN 2.6/Runway Gen4 Turbo/...) + `ui.Textarea`(param_name="prompt", лейбл "Описание сцены", placeholder="Камера медленно приближается к чашке кофе, пар поднимается вверх") + `ui.ImageUpload`(param_name="source_image", лейбл "Исходное изображение (для image-to-video)", опционально) + `ui.Button`("Создать видео", primary) | `ImageUpload` — многие video-модели именно image-to-video, не text-to-video. |
| Video Result | `ui.Video`(результат) + `ui.KeyValue`(model/duration/status) | Прямое воспроизведение готового видео. |
| Edit Image (Upscaler/Relight/Style/BG/Expand) | `ui.Button`-таббар(вручную, без `ui.Tabs` — BUG-001) переключает `ui.ImageUpload`(лейбл "Изображение для обработки") + операция-специфичные поля (Upscaler: `ui.Select`(scale_factor 2x/4x/8x/16x); Relight: `ui.Textarea`(лейбл "Описание нового освещения", placeholder="Тёплый закатный свет сбоку"); Style Transfer: `ui.ImageUpload`(лейбл "Референс стиля")) + `ui.Button`("Применить", primary) | Разные операции редактирования не взаимозаменяемы — ручной таббар обходит известный баг `ui.Tabs`. |
| Audio (Music/SFX/Isolation) | `ui.Select`(param_name="audio_mode", лейбл "Тип", Music/Sound Effects/Audio Isolation) + `ui.Textarea`(param_name="description", лейбл "Описание звука", placeholder="Спокойная лаунж-музыка с саксофоном, 30 секунд") + `ui.Button`("Сгенерировать", primary) | Три audio-операции достаточно похожи (текст → аудио-задача), чтобы жить в одном экране с переключателем режима, не в трёх отдельных вкладках. |
| Stock Content | `ui.Input`(param_name="query", лейбл "Поиск", placeholder="кофейная чашка минимализм", on_submit=Call) + `ui.Select`(param_name="content_type", лейбл "Тип", Images/Icons/Videos) + `ui.DataTable`(результаты: thumb via `ui.Image`, title, license, Button "Скачать") | Каталоговый поиск — DataTable со встроенным действием на строку. |
| History | `ui.DataTable`(task_id, type, model, status Badge, created_at; sortable) | Единая история всех задач генерации — value-add поверх Analytics/list_generation_results. |
| App Settings | `ui.Accordion`([Подключение+Disconnect, Баланс credits+команда, Webhooks]) | Централизованные настройки по стандарту, единая кнопка в сайдбаре ведёт сюда. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__magnific_sidebar` рендерит баланс + разделы; `auto_action` открывает Generate Image, если `not active_view`.
2. Generate Image: заполнил форму → `ui.Button("Сгенерировать")` → `create_action`(via generate_product_photo-подобный generic handler) → poll → `refresh_panels=["magnific_result"]` → Generation Result.
3. Generation Result → "Апскейлить" → `ui.Call("__panel__magnific_upscale", task_id=...)` → Edit Image (Upscaler таб предзаполнен исходным изображением).
4. Раздел "История" → DataTable → клик на строку → тот же Generation Result экран с данными этой задачи (`ui.Call(task_id=...)`).
5. Раздел "Stock" → Input(поиск, on_submit=Call) → DataTable результатов → Button("Скачать") на строке → `download_result`.
6. "App settings" → отдельный center overlay с Accordion-секциями; сайдбар НЕ дублирует инструкцию по получению ключа (она только в Empty-состоянии до подключения) и НЕ дублирует пояснения про credits (они только в самом Accordion).

## 3. Конкретные экраны (screens)

### Screen: Generate Image (`magnific_center`, default)
- `ui.Select`(лейбл "Модель") + `ui.Textarea`(лейбл "Промпт", контекстный placeholder) + `ui.Select`(лейбл "Соотношение сторон") — форма растянута на всю ширину сайдбара/центра (`align="stretch"` на всех уровнях).
- `ui.Button`("Сгенерировать", primary, единственная primary в группе).

### Screen: Generation Result (`magnific_center` + `task_id`)
- `ui.Image` + `ui.KeyValue` + `ui.Row`(две secondary-кнопки следующего действия).

### Screen: Generate Video (`magnific_video`)
- Аналогично Generate Image, плюс опциональный `ui.ImageUpload`.

### Screen: Edit Image (`magnific_edit` + `mode`)
- Ручной таббар (`ui.Row` из `ui.Button`) переключает `mode`; под ним операция-специфичная форма.

### Screen: Audio (`magnific_audio`)
- `ui.Select`(режим) + `ui.Textarea`(описание) + `ui.Button`("Сгенерировать").

### Screen: Stock Content (`magnific_stock`)
- `ui.Input`(поиск) + `ui.Select`(тип) + `ui.DataTable`.

### Screen: History (`magnific_history`)
- `ui.DataTable` с sortable колонками, row-click → Generation Result.

### Screen: App settings (`magnific_settings`)
- `ui.Accordion`: "Подключение" (API key info + Disconnect с Dialog-подтверждением — единственное место с этой инструкцией), "Баланс и команда" (credits, team members), "Webhooks" (List + Button "Добавить").
