#!/usr/bin/env python3
"""
Guardian - Prometheus monitoring service
Monitors Prometheus health and stops alerting when it's operational
"""

import time
import requests
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_prometheus_health():
    """Check if Prometheus is healthy and ready"""
    prom_url = os.getenv('PROM_URL', 'http://prometheus:9090')
    
    try:
        # Check if Prometheus is ready
        response = requests.get(f"{prom_url}/-/ready", timeout=5)
        if response.status_code == 200:
            logger.info("✅ Prometheus is UP and ready")
            return True
        else:
            logger.warning(f"⚠️ Prometheus returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Prometheus connection failed: {e}")
        return False

def main():
    """Main Guardian monitoring loop"""
    sleep_seconds = int(os.getenv('SLEEP_SECONDS', '15'))
    logger.info(f"🛡️ Guardian started - monitoring Prometheus every {sleep_seconds}s")
    
    consecutive_failures = 0
    
    while True:
        try:
            if check_prometheus_health():
                if consecutive_failures > 0:
                    logger.info(f"🎉 Prometheus recovered after {consecutive_failures} failures")
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.error(f"🚨 Prometheus has been down for {consecutive_failures} checks")
                
        except Exception as e:
            logger.error(f"Guardian error: {e}")
            
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    main() 