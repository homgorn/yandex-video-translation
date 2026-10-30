#!/usr/bin/env python3
"""Telegram bot for Yandex Video Translation Service."""

import asyncio, logging, sys, os
sys.path.insert(0, ".")
sys.path.insert(0, "/tmp/yavot-py/src")

# Очистка прокси
for k in ["HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "https_proxy", "http_proxy", "all_proxy"]:
    os.environ.pop(k, None)

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "your_token_here")
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.FileHandler("logs/app.log"), logging.StreamHandler()],
)
logger = logging.getLogger("bot")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я перевожу видео с озвучкой через Yandex VOT.\n"
        "Отправь ссылку на YouTube или другое видео.\n"
        "Поддерживается en→ru (и другие)."
    )

async def handle_video_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    url = text.strip()

    await update.message.reply_text(f"Начинаю перевод: {url}\nЭто может занять несколько минут.")

    # Здесь можно вызвать FastAPI `/translate` или напрямую vot
    # Для простоты — демонстрация с прямым вызовом (без блокировки чата)
    try:
        import httpx
        from vot import VOTClient, get_video_data
        from vot.models import VideoData

        async with httpx.AsyncClient(timeout=60.0) as client_http:
            client = VOTClient(client=client_http)
            video_data = await get_video_data(url, client=client_http)
            resp = await client.translate_video(
                video_data,
                request_lang="en",
                response_lang="ru",
                extra_opts={"bypassCache": True, "firstRequest": True},
            )

            if resp.translated:
                await update.message.reply_text(
                    f"Готово! Аудио доступно в течение 2 часов:\n{resp.url}\n"
                    f"Размер файла: проверь через curl."
                )
            else:
                await update.message.reply_text(
                    f"В процессе (статус={resp.status}). Ожидаем {getattr(resp, 'remaining_time', 10)} сек.\n"
                    f"Попробуйте позже или проверьте /status."
                )
    except Exception as exc:
        logger.error(f"Bot error: {exc}")
        await update.message.reply_text(f"Ошибка: {exc}\nПроверь прокси или повтори позже.")

if __name__ == "__main__":
    if TOKEN == "your_token_here":
        logger.warning("TELEGRAM_BOT_TOKEN not set! Set it via env var.")
        # Для теста можно запустить с фиктивным токеном (без сети)
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_url))
    logger.info("Bot started. Use /start and send a video URL.")
    app.run_polling()
