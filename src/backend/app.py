#!/usr/bin/env python3
"""FastAPI backend for Yandex Video Translation Service."""

import asyncio, uuid, logging, os
from datetime import datetime
from typing import Optional, Dict, Any

# Очистка прокси (критично для vot)
for key in ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"]:
    os.environ.pop(key, None)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Локальный vot (скопирован из /tmp/yavot-py/src)
import sys
sys.path.insert(0, "/tmp/yavot-py/src")  # fallback
sys.path.insert(0, ".")  # текущая папка с vot/

from vot import VOTClient, get_video_data
from vot.models import VideoData

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("backend")

app = FastAPI(title="Yandex Video Translation", version="0.1.0")

# In-memory store (для продакшена — SQLite или Redis)
jobs: Dict[str, Any] = {}

class TranslateRequest(BaseModel):
    url: str
    request_lang: str = "auto"
    response_lang: str = "ru"
    duration_sec: Optional[int] = None
    bypass_cache: bool = True
    first_request: bool = True

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0", "vot_available": True}

@app.post("/translate")
async def translate(req: TranslateRequest):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "translated": False,
        "audio_url": None,
        "request": req.dict(),
        "created_at": datetime.utcnow().isoformat(),
    }
    logger.info(f"Job {job_id} started: {req.url}")

    # Асинхронный запуск в фоне (без блокировки ответа)
    asyncio.create_task(_run_translation(job_id, req))

    return {"job_id": job_id, "status": "pending", "message": "Poll /status/{job_id}"}

@app.get("/status/{job_id}")
async def status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    data = jobs[job_id]
    return {
        "job_id": job_id,
        "status": data["status"],
        "translated": data["translated"],
        "audio_url": data.get("audio_url"),
        "message": "Done" if data["translated"] else "In progress",
    }

@app.get("/download/{job_id}")
async def download(job_id: str, format: str = "mp3", merge_video: bool = False):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    data = jobs[job_id]
    if not data["translated"] or not data.get("audio_url"):
        raise HTTPException(status_code=503, detail="Audio not ready yet")
    # В реальном сервисе — скачать с S3 и отдать через StreamingResponse
    # Или просто вернуть ссылку (если ещё жива)
    return {"download_url": data["audio_url"], "format": format, "merge_video": merge_video}

async def _run_translation(job_id: str, req: TranslateRequest):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            client = VOTClient(client=http_client)
            video_data = await get_video_data(req.url, client=http_client)
            logger.info(f"[{job_id}] Service: {video_data.host}, ID: {video_data.video_id}, duration: {getattr(video_data, 'duration', None)}")

            if req.duration_sec and not getattr(video_data, 'duration', None):
                video_data = VideoData(
                    url=video_data.url,
                    video_id=video_data.video_id,
                    host=video_data.host,
                    duration=req.duration_sec,
                )
                logger.info(f"[{job_id}] Duration overridden: {req.duration_sec}s")

            # Поллинг
            for attempt in range(120):
                resp = await client.translate_video(
                    video_data,
                    request_lang=req.request_lang,
                    response_lang=req.response_lang,
                    extra_opts={
                        "bypassCache": req.bypass_cache,
                        "firstRequest": req.first_request,
                    },
                )
                logger.info(f"[{job_id}] Attempt {attempt}: status={resp.status}, translated={resp.translated}, remaining_time={getattr(resp, 'remaining_time', None)}")

                if resp.translated:
                    jobs[job_id]["status"] = "finished"
                    jobs[job_id]["translated"] = True
                    jobs[job_id]["audio_url"] = resp.url
                    logger.info(f"[{job_id}] DONE. Audio URL available (2h lifetime).")
                    return

                wait = getattr(resp, 'remaining_time', 10) or 10
                await asyncio.sleep(min(wait, 20))

            jobs[job_id]["status"] = "timeout"
            logger.warning(f"[{job_id}] TIMEOUT after 120 attempts")
    except Exception as exc:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(exc)
        logger.error(f"[{job_id}] Translation error: {exc}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
