---
name: yandex-video-translation
description: "Перевод видео с озвучкой через Yandex VOT API (yavot-py)."
category: media
---

# Yandex Video Translation (озвучка перевода)

Перевод видео на русский (и другие языки) с синтезированной озвучкой — та же технология, что Яндекс Браузер использует для «перевода видео». Работает без авторизации и кук: отправляешь URL видео, Яндекс переводит речь и возвращает mp3 озвучки.

## Репозитории

- **`yamixst/yavot-py`** — Python-порт vot.js, использовать его (pip-устанавливается)
- `FOSWLY/vot.js` — оригинал на TypeScript (60⭐), yavot-py — его порт

## Установка

```bash
cd /tmp && git clone --depth 1 https://github.com/yamixst/yavot-py.git
cd /tmp/yavot-py && python3 -m venv /tmp/vot-venv
/tmp/vot-venv/bin/pip install -q -e .
# проверка: /tmp/vot-venv/bin/python -c "import vot; print('OK')"
```

Зависимости: httpx, protobuf, pydantic. Python ≥3.10.

## Использование

```python
import asyncio, httpx
from vot import VOTClient, get_video_data

async def main():
    async with httpx.AsyncClient() as http_client:
        client = VOTClient(client=http_client)
        url = "https://www.youtube.com/watch?v=ID"
        video_data = await get_video_data(url, client=http_client)
        # video_data.duration == None для YouTube! → подставится DEFAULT_DURATION=310
        response = await client.translate_video(video_data, request_lang="en", response_lang="ru")
        # поллинг: status=2 → в процессе, translated=True → готов
        # response.url — mp3 озвучки, response.remaining_time — сек до готовности
asyncio.run(main())
```

**Сигнатура translate_video:** `request_lang` (язык оригинала) и `response_lang` (язык перевода). **НЕ `target_lang`!** — TypeError.

## КРИТИЧНО: лимит длительности ~10 минут — обходится через bypassCache

`get_video_data()` возвращает `duration=None` для YouTube → библиотека подставляет `DEFAULT_DURATION = 310` (config.py), и Яндекс озвучивает только **~600 сек (10 мин)** видео. Для полного перевода длинного видео:

```python
from vot.models import VideoData
video_data = VideoData(
    url="https://www.youtube.com/watch?v=ID",
    video_id="ID", host="youtube",
    duration=4095,  # реальная длительность в секундах
)
# + ОБЯЗАТЕЛЬНО bypassCache=True:
resp = await client.translate_video(
    video_data, request_lang="en", response_lang="ru",
    extra_opts={"bypassCache": True, "firstRequest": True},
)
```

✅ **ПРОВЕРЕНО:** duration=4095 + `bypassCache=True` → Яндекс вернул **полную озвучку 4095 сек**. Качество перевода в середине видео подтверждено распознаванием (связный текст, не мусор).

⚠️ **Без bypassCache** Яндекс отдаёт КЕШ: мгновенно (status=1, 0 сек) возвращает старый обрезанный 10-мин файл с тем же `translation_id`. Появление «DONE after 0s» = попал в кеш, а не получил полный перевод. Признак кеша: длительность mp3 = 600 сек при видео 4095 сек.

⚠️ Статусы сервера: 1=FINISHED, 2/3=WAITING, 5=PART_CONTENT, 6=AUDIO_REQUESTED, 7=SESSION_REQUIRED (нужен логин Яндекса — не обходится без авторизации).

## Поллинг

```python
for attempt in range(120):
    resp = await client.translate_video(video_data, request_lang="en", response_lang="ru")
    if resp.translated:
        print(resp.url)  # готово
        break
    await asyncio.sleep(getattr(resp, "remaining_time", 10) or 10)
```

- Статусы: 2 = в очереди/обработке, 5 = готово (translated=True), 6 = в процессе с remaining_time
- Полное 10-мин озвучивание заняло ~100 сек

## Скачивание озвучки и проверка

Скрипт `vot_translate.py` (полный код ниже) — поллинг + скачивание одной командой (сохрани как `vot_translate.py`):

```bash
env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY -u https_proxy -u http_proxy -u all_proxy \
  /tmp/vot-venv/bin/python vot_translate.py \
  "https://www.youtube.com/watch?v=ID" /tmp/voiceover.mp3 en ru
```

```python
#!/usr/bin/env python3
"""Translate a video via Yandex VOT API and download the Russian voiceover mp3.

Usage: env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY -u https_proxy -u http_proxy -u all_proxy \
       /tmp/vot-venv/bin/python vot_translate.py <youtube_url> [out.mp3] [request_lang] [response_lang] [duration_sec]

- Prints poll progress; on done downloads the mp3 (URL lives only 2h).
- ALWAYS passes bypassCache=True (otherwise Yandex returns the cached ~10-min file instantly).
- Pass duration_sec (from ffprobe) for videos >10 min — REQUIRED for full-length voiceover,
  otherwise DEFAULT_DURATION=310 -> only ~600s are translated. Verified: 68-min video -> full 4095s mp3.
"""
import asyncio, httpx, sys, subprocess, os

async def main():
    url = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/voiceover.mp3'
    req_lang = sys.argv[3] if len(sys.argv) > 3 else 'en'
    resp_lang = sys.argv[4] if len(sys.argv) > 4 else 'ru'
    duration = int(sys.argv[5]) if len(sys.argv) > 5 else None

    from vot import VOTClient, get_video_data
    from vot.models import VideoData

    async with httpx.AsyncClient() as http_client:
        client = VOTClient(client=http_client)
        vd = await get_video_data(url, client=http_client)
        print(f"Service: {vd.host}, Video ID: {vd.video_id}, duration: {getattr(vd, 'duration', None)}", flush=True)
        if duration and not vd.duration:
            vd = VideoData(url=vd.url, video_id=vd.video_id, host=vd.host, duration=duration)
            print(f"Duration overridden to {duration}s", flush=True)

        for attempt in range(180):
            resp = await client.translate_video(
                vd,
                request_lang=req_lang,
                response_lang=resp_lang,
                extra_opts={"bypassCache": True, "firstRequest": True},
            )
            if resp.translated:
                print(f"DONE after {attempt*5}s", flush=True)
                print(f"URL: {resp.url}", flush=True)
                subprocess.run(['curl', '-sL', '-o', out, resp.url, '--max-time', '300'], check=True)
                print(f"Downloaded: {out} ({os.path.getsize(out)} bytes)", flush=True)
                return
            wait = getattr(resp, 'remaining_time', 10) or 10
            print(f"[{attempt}] status={resp.status} wait={wait}s", flush=True)
            await asyncio.sleep(wait)
        print("TIMEOUT", flush=True)

asyncio.run(main())

```

```bash
curl -sL -o voiceover.mp3 "<response.url>" --max-time 300
```

- URL — S3 с **X-Amz-Expires=7200 (живёт 2 часа)** — качать сразу!
- Озвучка: mp3 ~32 kbps, 22 kHz, моно (~10 мин ≈ 9.6 МБ)
- **Проверка качества**: вырезать 30 сек (`ffmpeg -ss 0 -t 30 -i voiceover.mp3 /tmp/s.mp3`), распознать через любую STT (Whisper и т.п.) — убедиться, что это корректный перевод, а не мусор.

## Сборка финального видео (оригинал + русская озвучка)

```bash
ffmpeg -y -i video.mp4 -i voiceover.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -shortest out_ru.mp4
```

- `-map 0:v -map 1:a` — видео из файла 0, звук из файла 1; `-c:v copy` не перекодирует картинку (быстро)
- `-shortest` — обрезать по более короткому (озвучка = длительности видео при полном переводе)
- Проверка после сборки: `ffprobe` — аудио-поток aac, длительность ≈ видео
- Готовое видео 68 мин/720p ≈ 180 МБ — мессенджеры обычно не доставляют (>50 МБ), слать файловым хостингом

## Питфолы

- **Прокси-env ломает API** — если в окружении висят `HTTPS_PROXY/HTTP_PROXY/ALL_PROXY` (например, нерабочий локальный порт) → 502/туннель-ошибки. Всегда: `env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY -u https_proxy -u http_proxy -u all_proxy /tmp/vot-venv/bin/python script.py`
- **Скрипты запускать через venv** `/tmp/vot-venv/bin/python` — системный python не имеет `vot`
- **duration=None** — см. раздел выше, всегда проверять `getattr(video_data, 'duration', None)`
- **Поллинг в фоне** — озвучивание длинного видео может занять минуты
- Имя поля модели — `translation_id`, статус 5 = translated. Полезно печатать `response.model_dump()` для дебага.
