FROM python:3.11-slim
WORKDIR /app
COPY services/transcript-storage/transcript_storage_service.py ./
RUN pip install --no-cache-dir fastapi uvicorn aiohttp aiosqlite
EXPOSE 9100
CMD ["uvicorn", "transcript_storage_service:app", "--host", "0.0.0.0", "--port", "9100"] 