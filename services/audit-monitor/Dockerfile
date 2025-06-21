FROM python:3.11-slim
WORKDIR /app
COPY services/audit-monitor/audit-monitor_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9400
CMD ["uvicorn", "audit-monitor_service:app", "--host", "0.0.0.0", "--port", "9400"]
