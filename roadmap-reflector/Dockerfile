FROM python:3.11-slim
WORKDIR /app
COPY services/roadmap-reflector/reflector_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py prometheus-client docker
EXPOSE 9103 9902
CMD ["uvicorn","reflector_service:app","--host","0.0.0.0","--port","9103"] 