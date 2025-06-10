#!/usr/bin/env python3
"""
Guardian Service - Health monitoring and alerting
Monitors system health and provides health check endpoints
"""

from fastapi import FastAPI
from prometheus_client import Counter, Histogram, start_http_server
import uvicorn
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Guardian Service", version="1.0.0")

# Prometheus metrics
guardian_requests = Counter('guardian_requests_total', 'Total Guardian requests')
guardian_health_checks = Histogram('guardian_health_check_duration_seconds', 'Health check duration')

@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    guardian_requests.inc()
    logger.info("Health check requested")
    return {"status": "ok", "service": "guardian"}

@app.get("/-/healthy")
async def prometheus_health():
    """Prometheus-style health check"""
    guardian_requests.inc()
    return {"status": "healthy"}

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(9093)
    logger.info("Guardian service starting on port 9004")
    
    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=9004) 