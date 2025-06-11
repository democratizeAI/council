#!/usr/bin/env python3
"""
Guide Loader Service - Monitors and manages guide loading processes
"""
import os
import time
import logging
import requests
from prometheus_client import start_http_server, Counter, Gauge

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
GUIDES_LOADED = Counter('guide_loader_guides_loaded_total', 'Total guides loaded')
GUIDES_IN_MEMORY = Gauge('guide_loader_guides_in_memory', 'Number of guides currently in memory')

def health_check():
    """Simple health check"""
    try:
        guides_dir = os.getenv('GUIDES_DIR', '/app/docs')
        return os.path.exists(guides_dir)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

def main():
    """Main entry point"""
    logger.info("🚀 Starting Guide Loader Service...")
    
    # Start Prometheus metrics server
    metrics_port = int(os.getenv('METRICS_PORT', '9108'))
    start_http_server(metrics_port)
    logger.info(f"📊 Metrics server started on port {metrics_port}")
    
    # Set initial metrics
    GUIDES_LOADED.inc()
    GUIDES_IN_MEMORY.set(1)
    
    # Main service loop
    try:
        while True:
            if health_check():
                logger.debug("Guide Loader service is healthy")
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Shutting down Guide Loader service...")

if __name__ == "__main__":
    main() 