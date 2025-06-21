FROM python:3.11-slim
WORKDIR /app
# Copy core welder logic and thin wrapper
COPY phoenix_auto_welder.py ./phoenix_auto_welder.py
COPY services/auto-welder/auto_welder_service.py ./auto_welder_service.py
RUN pip install --no-cache-dir docker aiohttp PyYAML
CMD ["python3", "auto_welder_service.py"] 