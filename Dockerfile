FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Firejail for sandbox execution
RUN apt-get update && apt-get install -y \
    curl \
    firejail \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs and memory directories
RUN mkdir -p logs memory

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "autogen_api_shim:app", "--host", "0.0.0.0", "--port", "9000"] 