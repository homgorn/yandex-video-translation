# Wiki Index — Yandex Video Translation Service

## Навигация

- [Проектная спецификация](../../specs/requirements/project-spec.md)
- [Декомпозиция](../../specs/decomposition/decomposition.md)
- [API Спецификация](../api/openapi.md)
- [Инструкция по установке](../../README.md)
- [Тест любого видео](../../test_video.py)
- [Логи](../../logs/)

## Знания (Knowledge Base)

### Как работает Yandex VOT API?

- `get_video_data(url)` — извлекает `video_id`, `host`, `duration` (для YouTube часто `None`).
- `translate_video()` — отправляет protobuf с HMAC-подписью. Требуется `request_lang` и `response_lang` (НЕ `target_lang`).
- `bypassCache=True` — обязательно для видео >10 минут, иначе возвращает кеш (600 сек).
- `duration` нужно передавать вручную для длинных видео (из `ffprobe`).

### Что делать, если API не отвечает?

1. Проверить прокси: `env -u HTTPS_PROXY ... python script.py`
2. Увеличить `timeout` в `httpx.AsyncClient`.
3. Проверить `session required` (статус 7) — без авторизации Яндекса не обойти.
4. Перезапустить с другим `video_id` — возможно, кеш или временная блокировка.

### Как проверить качество перевода?

- Вырезать 30 сек (`ffmpeg -ss 0 -t 30 -i ...`)
- Распознать через Whisper или любую STT.
- Убедиться, что текст связный, не мусор.
- Для длинных видео проверять середину (не только начало).

### Архитектура сервиса

```
Frontend (HTML/JS) / Telegram Bot
    ↓
FastAPI (REST API, Async)
    ↓
Yandex VOT (protobuf, HMAC)
    ↓
S3 (mp3, 2h lifetime)
    ↓
FFmpeg (merge video + audio)
```

### Ограничения и риски

- Яндекс может изменить API или заблокировать доступ в любой момент.
- Без авторизации работает, но `session required` (статус 7) — не обходится.
- Прокси-переменные (`HTTPS_PROXY`, `HTTP_PROXY`, `ALL_PROXY`) ломают соединение.
- URL аудио живёт 2 часа — нужно качать сразу или сохранять в хранилище.

### Полезные ссылки

- [yavot-py](https://github.com/yamixst/yavot-py)
- [vot.js (оригинал)](https://github.com/FOSWLY/vot.js)
- [yavot-api](https://github.com/VolcharaVasiliy/yavot-api)
- [vot-cli](https://github.com/FOSWLY/vot-cli)
- [KtuvitBot (Telegram bot пример)](https://github.com/shlomota/KtuvitBot)
