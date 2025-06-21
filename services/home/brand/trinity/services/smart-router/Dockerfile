FROM python:3.11-slim
WORKDIR /app
COPY services/smart-router/smart-router_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9252
CMD ["uvicorn", "smart-router_service:app", "--host", "0.0.0.0", "--port", "9252"]
