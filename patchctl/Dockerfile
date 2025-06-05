FROM python:3.12-slim
RUN pip install fastapi uvicorn pydantic PyYAML
COPY . /app
WORKDIR /app
CMD ["uvicorn","patchctl.app:app","--host","0.0.0.0","--port","9000"] 