# Decomposition — Yandex Video Translation Project

## Level 1: Core Modules

### 1. Translation Engine (`vot`)
- `get_video_data()` — разрешение URL, извлечение video_id, host
- `VOTClient.translate_video()` — protobuf + HMAC запрос
- `polling` — цикл ожидания статуса (2, 5, 6)
- `audio download` — curl / httpx на S3 URL

### 2. Video Processing (`ffmpeg`)
- Извлечение длительности (ffprobe)
- Наложение переведённой аудиодорожки (`-map 0:v -map 1:a`)
- Генерация субтитров (если API возвращает)

### 3. API Service (`FastAPI`)
- `/translate` — POST с URL, запуск перевода
- `/status/{job_id}` — GET статус и результат
- `/download/{job_id}` — GET готовый mp3/mp4
- `/health` — проверка сервиса

### 4. Telegram Bot
- Команда `/start` — инструкция
- Приём ссылки → запуск перевода → отправка результата
- Обработка ошибок (timeout, кеш, прокси)

### 5. Web Frontend
- Локальный HTML с формой ввода URL
- Деплой на Cloudflare Pages (если нужен домен)

### 6. Documentation & Knowledge
- `docs/wiki/index.md` — индекс знаний
- `docs/api/openapi.md` — спецификация REST
- `logs/app.log` — структурированные логи

## Level 2: Tasks (per module)

### Translation Engine
1. Скопировать `vot` из `/tmp/yavot-py/src/` в проект.
2. Проверить импорт (`python -c "import vot"`).
3. Написать `test_video.py` с поллингом и `bypassCache`.
4. Добавить обработку `duration=None` для YouTube.
5. Тест на коротком видео (jNQXAC9IVRw) — подтверждено работает.

### API Service
1. Создать `src/backend/app.py` с FastAPI.
2. Добавить эндпоинты `/translate`, `/status`, `/download`.
3. Реализовать очередь задач (SQLite или in-memory dict).
4. Логирование через `logging` (файл + stdout).
5. Обработать исключения (session required, timeout, proxy).

### Bot
1. Создать `src/bot/bot.py` с `python-telegram-bot`.
2. Обработчик текста: если URL — запуск перевода.
3. Отправка прогресса (status, remaining_time) в чат.
4. Финальная отправка файла или ссылки на S3 (если <20 МБ).

### Web
1. `src/web/index.html` — простая форма.
2. `src/web/app.js` — вызов API через fetch.
3. `README.md` с инструкциями запуска.

### Deployment
1. `Dockerfile` для backend + bot.
2. `docker-compose.yml` (postgres, redis — опционально).
3. `.github/workflows/deploy.yml` — CI/CD на Cloudflare.
4. Домен: `video-trans.yourdomain.com` (после деплоя).

## Level 3: Verification Gates

- [ ] `python test_video.py` — проходит (подтверждено).
- [ ] `curl http://localhost:8000/health` — 200 OK.
- [ ] `python src/bot/bot.py` — отвечает на `/start`.
- [ ] Логи содержат `INFO` записи без ошибок.
- [ ] Документация содержит все разделы из `project-spec.md`.
