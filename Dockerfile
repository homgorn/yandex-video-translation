FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg curl git && rm -rf /var/lib/apt/lists/*

COPY specs/ docs/ logs/ src/ test_video.py .
COPY vot/ ./vot/

RUN pip install --no-cache-dir fastapi uvicorn httpx protobuf pydantic python-telegram-bot

# Установка yavot-py (если не скопирован vot напрямую)
# Но vot уже в папке — используем локальную копию
ENV PYTHONPATH="/app:/app/vot:$PYTHONPATH"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
