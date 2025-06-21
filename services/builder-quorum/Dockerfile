FROM python:3.11-slim
WORKDIR /app
COPY services/builder-quorum/builder-quorum_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9251
CMD ["uvicorn", "builder-quorum_service:app", "--host", "0.0.0.0", "--port", "9251"]
