FROM python:3.11-slim

WORKDIR /app

COPY scripts/game_monitor_service.py .
RUN pip install --no-cache-dir fastapi uvicorn nats-py prometheus_client

EXPOSE 9301

CMD ["python", "-u", "game_monitor_service.py"]
