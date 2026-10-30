# API Specification — OpenAPI 3.0

**Base URL:** `http://localhost:8000` (local) или `https://video-trans.yourdomain.com` (deploy)

## Endpoints

### POST `/translate`
Запуск перевода видео.

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
  "request_lang": "en",
  "response_lang": "ru",
  "duration_sec": null,
  "bypass_cache": true,
  "first_request": true
}
```

**Response 202 (Accepted):**
```json
{
  "job_id": "uuid-1234",
  "status": "pending",
  "message": "Translation started. Poll /status/{job_id}."
}
```

### GET `/status/{job_id}`
Проверка статуса перевода.

**Response 200:**
```json
{
  "job_id": "uuid-1234",
  "status": "waiting",
  "translated": false,
  "remaining_time": 45,
  "audio_url": null,
  "video_duration": 4095
}
```

**Response 200 (Done):**
```json
{
  "job_id": "uuid-1234",
  "status": "finished",
  "translated": true,
  "audio_url": "https://vtrans.s3-private.mds.yandex.net/tts/prod/...mp3?X-Amz-Expires=7200",
  "download_url": "/download/uuid-1234",
  "message": "Audio available. Download within 2 hours."
}
```

### GET `/download/{job_id}`
Скачивание готового mp3 или mp4.

**Query Params:**
- `format`: `mp3` (default) или `mp4`
- `merge_video`: `true` — наложить звук на оригинальное видео (если доступно)

### GET `/health`
Проверка сервиса.

```json
{"status":"ok","version":"0.1.0","vot_available":true}
```

### POST `/subtitles/{job_id}`
Получение субтитров (если поддерживается API).

```json
{"subtitles": [{"start": 0.5, "end": 3.2, "text": "Привет, мир"}], "format": "srt"}
```

## Errors

- `400` — неверный URL или параметры.
- `404` — задача не найдена.
- `429` — превышен лимит запросов (10/мин).
- `502` — ошибка прокси или Яндекс-API (проверь `env -u HTTPS_PROXY`).
- `503` — сервис временно недоступен (обновление или блокировка API).

## Authentication

На данный момент не требуется (API работает без кук/авторизации, но с `bypassCache`). В будущем возможна OAuth через Яндекс для `lively-voice` или расширенных функций.

## Rate Limits

- 10 запросов в минуту на IP.
- Максимальная длительность видео: ограничений нет, но >10 мин требует `duration_sec` и `bypass_cache=True`.

## Example Flow (Python)

```python
import httpx, asyncio

async def translate(url):
    async with httpx.AsyncClient() as c:
        r = await c.post("http://localhost:8000/translate",
            json={"url": url, "request_lang":"en", "response_lang":"ru", "bypass_cache": True})
        job = r.json()
        while True:
            status = await c.get(f"http://localhost:8000/status/{job['job_id']}")
            data = status.json()
            if data.get("translated"):
                print("Done:", data["audio_url"])
                break
            await asyncio.sleep(10)
```
