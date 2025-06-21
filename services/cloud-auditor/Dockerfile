FROM python:3.11-slim
WORKDIR /app
COPY services/cloud-auditor/cloud-auditor_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9250
CMD ["uvicorn", "cloud-auditor_service:app", "--host", "0.0.0.0", "--port", "9250"]
