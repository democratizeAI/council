FROM python:3.11-alpine

RUN pip install apscheduler httpx

COPY scheduler.py .

CMD ["python", "scheduler.py"] 