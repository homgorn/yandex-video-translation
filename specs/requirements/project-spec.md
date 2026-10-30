# Project Specification — Yandex Video Translation Service

## Overview

Онлайн-сервис перевода видео с озвучкой через Yandex VOT API. Поддерживает YouTube, Vimeo, TikTok и прямые ссылки. Выдаёт переведённую аудиодорожку (mp3), субтитры и готовое видео с наложенным звуком.

## Goals

1. Перевод любого видео до 68 минут с полной озвучкой (`bypassCache=True`).
2. Онлайн-сервис с REST API (FastAPI) для автоматизации.
3. Телеграм-бот для быстрого доступа без регистрации.
4. Локальный сайт с возможностью деплоя на домен.

## Non-Goals

- Авторизация через Яндекс (API не поддерживает без кук, но работает с `bypassCache`).
- Коммерческая монетизация (только исследовательский/образовательный проект).
- Поддержка всех языков — начинаем с en→ru, ru→en, авто-детект.

## Key Metrics

- Успешность перевода: >95% для видео <10 минут, >80% для длинных (>30 мин).
- Время ответа API: <2 сек на запрос, поллинг отдельно.
- Качество: связный текст в середине видео (проверено STT).

## Constraints & Risks

- Яндекс может изменить или заблокировать API в любой момент.
- Прокси-переменные (`HTTPS_PROXY`) ломают соединение — всегда очищать.
- Длительность >10 мин требует ручного `duration` и `bypassCache`.
- URL аудио живёт 2 часа (`X-Amz-Expires=7200`) — качать сразу.

## Technology Stack

- **Backend**: Python 3.12, FastAPI, asyncio, httpx
- **Translation Engine**: yavot-py (`vot` модуль)
- **Video Processing**: ffmpeg
- **Bot**: python-telegram-bot (v20+), async
- **Frontend**: HTML + vanilla JS (локально) или Astro (деплой)
- **Database**: SQLite (локально), PostgreSQL (деплой)
- **Deployment**: Docker + Docker Compose → Cloudflare Pages / Vercel

## Architecture

```
User / Telegram Bot
    ↓
FastAPI Service (REST + Async Queue)
    ↓
Yandex VOT API (protobuf + HMAC signing)
    ↓
S3 Audio URL (2h lifetime)
    ↓
FFmpeg (merge audio + video)
    ↓
Response (mp3 / mp4 / subtitle URL)
```

## Acceptance Criteria

- [ ] Тест любого YouTube-видео проходит успешно (`test_video.py`).
- [ ] Сервис отвечает на `/translate` с JSON `{url, status, audio_url, duration}`.
- [ ] Бот принимает ссылку и возвращает mp3 или ссылку на готовое видео.
- [ ] Все операции логируются в `logs/app.log` с уровнем INFO.
- [ ] Документация в `docs/` содержит API-спецификацию и инструкции по деплою.

## Security & Legal

- Не использовать для коммерческих целей или спама.
- Не хранить личные данные пользователей.
- Уважать Terms of Service Яндекса.
- Самоограничение: не более 10 запросов в минуту на IP.

## References

- [yavot-py GitHub](https://github.com/yamixst/yavot-py)
- [vot.js (original)](https://github.com/FOSWLY/vot.js)
- [yavot-api (proxy wrapper)](https://github.com/VolcharaVasiliy/yavot-api)
