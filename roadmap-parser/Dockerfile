FROM python:3.11-slim
WORKDIR /app
COPY services/roadmap-parser/parser_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn nats-py
EXPOSE 9102
CMD ["uvicorn","parser_service:app","--host","0.0.0.0","--port","9102"] 