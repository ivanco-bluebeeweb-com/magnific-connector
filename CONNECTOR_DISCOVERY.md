# Magnific Connector — Connector Discovery

**Дата:** 2026-08-28. **Источник истины:** `docs.magnific.com/llms.txt` (полный индекс, вытянут напрямую) + точечная сверка отдельных страниц (`/authentication`, `/webhooks`, upscaler overview). Часть страниц (Analytics team-credit-usage) отдана за JS/bot-protection — не открыта rendered-reader'ом в эту сессию, тело запроса взято из llms.txt-описания + по аналогии со схемой остальных Analytics-эндпоинтов.

Magnific = переименованный **Freepik API** (`api.magnific.com`). НЕ путать с andro-нишевым "апскейлером" — это мультимодальная AI-платформа: image gen, video gen, image editing, audio gen, analytics, stock content.

## Base URL & Auth

- `https://api.magnific.com`
- Заголовок `x-magnific-api-key: <key>` на КАЖДЫЙ запрос. Один тип credential (server-to-server, приватный ключ) — OAuth/MCP-режим существует отдельно для AI-ассистентов (Claude/ChatGPT/Cursor), но не для server-to-server интеграций вроде этой.
- Rate limits существуют (`/ratelimits`), точные цифры не документированы публично по числу — обрабатывать 429 как retryable.

## Async Task Lifecycle (общий для ВСЕХ AI-эндпоинтов)

1. `POST /v1/ai/<model>` → `{"data": {"task_id": ..., "status": "CREATED"|...}}`.
2. `GET /v1/ai/<model>/{task_id}` → poll до `status: "COMPLETED"` (или `FAILED`).
3. Опционально: `webhook_url` в теле POST — Magnific шлёт HMAC-signed POST на callback вместо поллинга.

Это ТОЧНО тот же контракт, что уже реализован в `Apps/Media Studio/magnific_client.py` (`_extract_status`/`_extract_image_urls`, `DONE_STATUSES`/`FAILED_STATUSES`) — код можно и нужно переиспользовать как референс паттерна (не импортировать напрямую: разные приложения, разные `ctx`).

**Решение по webhook vs polling (v1):** Polling, как и Media Studio — по той же причине (неподтверждённый платформенный баг echo заголовков на webhook-слое, см. комментарий в `magnific_client.py`). Long-running video-задачи (может занять минуты) поддержат `webhook_url` как ОПЦИОНАЛЬНЫЙ параметр в теле запроса (сохраняем задел на будущее), но основной путь получения результата в чате — задача создаётся, user получает task_id, дальше отдельный `get_*_task` вызов или авто-поллинг с прогрессом (как в Mystic-пути Media Studio).

## Tier 1 — Core (must-have, обязательно к запуску)

### Image Generation (generic multi-model path)
- Mystic: `POST /v1/ai/mystic`, `GET /v1/ai/mystic/{task_id}` — флагманская модель Magnific.
- Flux family: Kontext Pro, Flux 2 Pro, Flux 2 Turbo, Flux 2 Klein, Flux Pro 1.1, Flux Dev, Hyperflux — каждая свой path (`/v1/ai/flux-*` и т.п.), разные body-схемы (Klein/Kontext поддерживают reference images).
- Seedream: Seedream 4, Seedream 4.5, (Seedream 4.5 Edit — под Image Editing).
- Z-Image Turbo.
- RunWay Text-to-Image.

Дизайн: ОДИН generic handler `generate_image(model, prompt, ...)` + внутренний registry (по образцу `Media Studio/model_registry.py` — там уже есть Mystic/Imagen4/Gemini adapters, будем строить параллельную, не импортируемую копию под собственные модели Magnific), а не 12 отдельных tool-функций — иначе взрыв почти идентичных функций, плохой UX выбора инструмента.

### Video Generation (generic multi-model path)
- Kling: 2.1 Pro, 2.5 Pro, 2.6 Pro, 2.6 Motion Control, O1 Pro/Standard.
- MiniMax Hailuo: 02 1080p, 2.3, Video-01-Live.
- WAN: 2.5 T2V, 2.5 I2V, 2.6.
- RunWay: Gen4 Turbo, Act Two.
- LTX 2.0 Pro, Seedance Pro, PixVerse V5, OmniHuman 1.5, VFX.

Дизайн: ОДИН generic `generate_video(model, prompt_or_image, ...)`, тот же registry-паттерн.

### Image Editing
- Upscaler Creative (`/v1/ai/image-upscaler`, добавляет/домысливает деталь) — УЖЕ в Media Studio, но там урезанный путь только под нужды Media Hub.
- Upscaler Precision (отдельный path, честный super-res без hallucination — для логотипов/текста/продуктовых фото).
- Relight — смена освещения.
- Style Transfer.
- Remove Background (`/v1/ai/beta/remove-background`).
- Image Expand (`/v1/ai/flux-pro` вариант — расширение границ).

### Connection / Account
- `connect_magnific` (validate + save key), `disconnect_magnific`, `list_connections`.

## Tier 2 — важное, повышает ценность

### Audio
- Music Generation (ElevenLabs под капотом): `POST /v1/ai/music-generation`, list tasks, get task by id.
- Sound Effects: `POST /v1/ai/sound-effects`, list, get.
- Audio Isolation (SAM Audio): `POST /v1/ai/audio-isolation`, list, get — извлечение отдельных звуков из аудио/видео.

### Analytics (командный биллинг/использование — критично для видимости расходов)
- `POST /v1/analytics/team-credit-usage` — расход credits за период.
- `GET /v1/analytics/team-members` — участники команды (user_id, email, role, status).
- `GET /v1/analytics/team-api-keys` — API-ключи команды (api_key_id, display_name, status — БЕЗ самого секрета).
- `GET /v1/analytics/team-groups` — группы.
- `GET /v1/analytics/team-projects` — проекты (project_reference UUID, name).

Это единственный способ для пользователя увидеть, сколько credits потрачено — обязательно к value-add отчёту `get_account_overview`/`audit_account` в POST_CONNECT_EXPERIENCE.

## Tier 3 — nice-to-have, охват "максимального функционала"

### Stock Content
- Images & Templates — поиск/скачивание стоковых изображений.
- Icons — векторная библиотека иконок.
- Videos — стоковое видео.

Это НЕ AI-generation, а поисково-лицензионный каталог — отдельные простые `search_stock_*`/`get_stock_*` функции, не async task lifecycle.

## Известные пробелы / не подтверждено

- Analytics team-credit-usage вернула bot-protection при чтении reader'ом (не rendered) — точная форма тела запроса (какие фильтры принимает POST) взята из краткого описания в llms.txt, НЕ проверена полем-в-поле. Перед кодом хендлера — задокументировать это допущение прямо в docstring клиента (как Media Studio делает для task-status тела: "defensive parsing, raises structured error on unrecognized shape"), не выдумывать точные названия полей фильтра.
- GPT Image — Media Studio's model_registry.py явно НЕ включает его (все угаданные URL 404). Тот же вывод переносится сюда: НЕ включать GPT Image в registry Magnific Connector, пока реальный endpoint не подтверждён.
- Rate limit конкретные числа не опубликованы по значению — обрабатываем как generic retryable 429, без указания точных порогов пользователю.

## Архитектурное решение (снимает риск "30 почти одинаковых инструментов")

Вместо function-per-model (что дало бы 25+ Tier1/2 tool-функций только под generate_*), используем **два generic handler'а** (`generate_image`, `generate_video`) с параметром `model` + внутренним `MODEL_REGISTRY` (path + body-builder на модель, как в Media Studio), плюс отдельные специализированные handlers там, где body/семантика РЕАЛЬНО отличается настолько, что generic-параметр обманывал бы пользователя (upscaler creative vs precision — разные trade-offs с разным UX-выбором; relight/style-transfer/remove-bg/expand — разные "приложения" редактирования, не взаимозаменяемые варианты одной операции). Итог — управляемое число tool-функций (~30 всего, не ~50), при этом 100% эндпоинтов из индекса покрыты.
