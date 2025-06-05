FROM python:3.11-slim

# Install NVIDIA ML Python bindings
RUN pip install --no-cache-dir pynvml

# Create app directory
WORKDIR /app

# Copy application
COPY main.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash exporter && \
    chown -R exporter:exporter /app
USER exporter

# Expose metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the metrics exporter
CMD ["python", "main.py"] 