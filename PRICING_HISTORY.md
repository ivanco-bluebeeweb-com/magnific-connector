# Pricing History — Magnific Connector

Обязательный журнал: каждое выставление или изменение цен на функции этого
приложения фиксируется здесь — что изменилось, почему, и на основании чего.
Не переписывать прошлые записи — только дописывать новые сверху.

---

## 2026-08-28 — первичный прайсинг (per_action, фиксированная шкала)

Прайсинг выставлен по канонической шкале из `PRICING_POLICY.md`
(`0, 8, 16, 20, 40, 60`), ПОСЛЕ чистого deploy (19/20 проверок, единственное
оставшееся — информационный warning про длину `models.py`), ДО
`submit_for_review` — порядок соблюдён.

**Тиры:**
- **0 (бесплатно, 5 функций):** `connect_magnific`, `disconnect_magnific`,
  `get_magnific_connection`, `list_image_models`, `list_video_models` —
  подключение и статический каталог моделей не тратят кредиты Magnific.
- **8 (лёгкое чтение/polling, 9 функций):** `get_account_balance`,
  `get_image_task`, `get_video_task`, `get_edit_task`, `get_audio_task`,
  `search_stock_content`, `list_team_members`, `list_api_keys`,
  `list_generation_results` — чтения и опрос статуса задачи, не создающие
  новую платную генерацию у Magnific.
- **16 (простая генерация, 3 функции):** `remove_background`,
  `generate_sound_effect`, `isolate_audio` — недорогие async-задачи.
- **20 (основная платная генерация, 6 функций):** `generate_image`,
  `upscale_image`, `relight_image`, `style_transfer_image`, `expand_image`,
  `generate_music` — большинство генеративных операций.
- **40 (самая дорогая, 1 функция):** `generate_video` — видео-генерация
  (Kling/Hailuo/WAN/Runway/и т.д.), объективно самая ресурсоёмкая операция
  во всём API.

`revenue_split_dev=70` (дефолт explorer-тира) передан явным параметром
`update_pricing`, как того требует §3 `PRICING_POLICY.md`.

**Известный платформенный баг воспроизведён повторно:** первый вызов
`update_pricing` вернул `success`, но фактически сохранил только 5 из 24
цен (все ненулевые — 19 полей — отчитались как "not stored", хотя API не
вернул ни одной ошибки). Немедленный повтор с идентичным payload —
сохранил все 24 цены полностью. Это тот же паттерн, что уже
задокументирован для MuleSoft (#2275), gitlab-cicd-connector (#2230),
pandadoc-connector (#2278), Losant Connector (#2347), node-red-connector
(#2380), servicenow-connector (#2449), bmc-helix-connector (#2467),
ivanti-connector (#2476), и общий баг-тикет #2620. Не создавал новый
дублирующий тикет — вместо этого добавил ссылку на это воспроизведение в
комментарий к задаче разработки #2626, чтобы паттерн был виден без
множения одинаковых задач.

После успешного сохранения — повторный `deploy_app`, чтобы зеркало цен в
`imperal.json["pricing"]` синхронизировалось с базой платформы.
