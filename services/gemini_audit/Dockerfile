FROM python:3.11-slim

LABEL maintainer="QA-302 Team"
LABEL description="Gemini Streaming Auditor - Real-time PR policy enforcement"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user for security
RUN groupadd -r gemini && useradd -r -g gemini gemini
RUN chown -R gemini:gemini /app
USER gemini

# Expose port
EXPOSE 8091

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8091/health || exit 1

# Start command
CMD ["python", "main.py"] 