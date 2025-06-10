FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install fastapi uvicorn prometheus_client

# Copy guardian code
COPY guardian.py .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9004/health || exit 1

# Expose ports
EXPOSE 9004 9093

# Start guardian
CMD ["python", "guardian.py"] 