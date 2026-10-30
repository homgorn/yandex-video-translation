#!/usr/bin/env python3
"""Тест перевода любого видео через Yandex VOT API.

Запуск:
    python test_video.py "https://www.youtube.com/watch?v=..." [duration_sec]

Обязательно очищать прокси перед запуском:
    env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY python test_video.py ...
"""
import asyncio, httpx, sys, subprocess, os, time

async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # тестовое короткое видео
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else None
    out_path = "/tmp/test_voiceover.mp3"

    # Очистка прокси-переменных (как требует скилл)
    for k in ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"]:
        os.environ.pop(k, None)

    print(f"[TEST] URL: {url}", flush=True)
    print(f"[TEST] Duration override: {duration}", flush=True)

    from vot import VOTClient, get_video_data
    from vot.models import VideoData

    async with httpx.AsyncClient(timeout=30.0) as client_http:
        client = VOTClient(client=client_http)
        try:
            video_data = await get_video_data(url, client=client_http)
            print(f"[TEST] Service: {video_data.host}, Video ID: {video_data.video_id}, duration={getattr(video_data, 'duration', None)}", flush=True)
        except Exception as e:
            print(f"[TEST] get_video_data error: {e}", flush=True)
            return

        if duration and not getattr(video_data, 'duration', None):
            video_data = VideoData(
                url=video_data.url,
                video_id=video_data.video_id,
                host=video_data.host,
                duration=duration,
            )
            print(f"[TEST] Duration overridden to {duration}s", flush=True)

        # Поллинг с bypassCache
        for attempt in range(60):
            try:
                resp = await client.translate_video(
                    video_data,
                    request_lang="en",
                    response_lang="ru",
                    extra_opts={"bypassCache": True, "firstRequest": True},
                )
                print(f"[TEST] Attempt {attempt}: status={resp.status}, translated={resp.translated}, remaining_time={getattr(resp, 'remaining_time', None)}", flush=True)

                if resp.translated:
                    print(f"[TEST] DONE! URL: {resp.url}", flush=True)
                    # Скачиваем MP3
                    try:
                        subprocess.run(
                            ["curl", "-sL", "-o", out_path, resp.url, "--max-time", "300"],
                            check=True,
                            capture_output=True,
                        )
                        size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
                        print(f"[TEST] Downloaded: {out_path} ({size} bytes)", flush=True)
                    except Exception as download_err:
                        print(f"[TEST] Download error: {download_err}", flush=True)
                    return

                wait = getattr(resp, 'remaining_time', 10) or 10
                await asyncio.sleep(min(wait, 15))
            except Exception as e:
                print(f"[TEST] Attempt {attempt} error: {e}", flush=True)
                await asyncio.sleep(10)

        print("[TEST] TIMEOUT after 60 attempts", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
