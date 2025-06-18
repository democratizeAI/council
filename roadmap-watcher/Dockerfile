FROM python:3.11-slim
WORKDIR /app
COPY services/roadmap-watcher/roadmap-watcher_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9101
CMD ["uvicorn", "roadmap-watcher_service:app", "--host", "0.0.0.0", "--port", "9101"]
