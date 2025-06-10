#!/usr/bin/env python3
"""
Mission Validator Service (BC-120)
Monitors Council-API logs for GENESIS_MANDATE_001 acknowledgment
Exposes Prometheus metrics when mission is validated
"""

import os
import sys
import time
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import requests
from flask import Flask, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
import watchdog.events
import watchdog.observers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('mission-validator')

# Environment configuration
COUNCIL_API_URL = os.getenv('COUNCIL_API_URL', 'http://localhost:8000')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
VALIDATION_TIMEOUT = int(os.getenv('VALIDATION_TIMEOUT', '300'))  # 5 minutes
LOG_DIR = os.getenv('LOG_DIR', '/app/logs')
PORT = int(os.getenv('PORT', '8080'))

# Set log level
logging.getLogger().setLevel(getattr(logging, LOG_LEVEL.upper()))

# Prometheus metrics
mission_ingest_ok_total = Counter(
    'mission_ingest_ok_total',
    'Total number of successful mission ingestions',
    ['mission_type', 'source']
)

mission_validation_status = Gauge(
    'mission_validation_status',
    'Current mission validation status (1=validated, 0=pending)',
    ['mission_id']
)

mission_validator_health = Gauge(
    'mission_validator_health',
    'Health status of mission validator service (1=healthy, 0=unhealthy)'
)

log_lines_processed = Counter(
    'log_lines_processed_total',
    'Total number of log lines processed',
    ['log_file', 'status']
)

mission_ack_timestamp = Gauge(
    'mission_ack_timestamp',
    'Timestamp when mission acknowledgment was detected',
    ['mission_id']
)

# Global state
class ValidationState:
    def __init__(self):
        self.genesis_acknowledged = False
        self.ack_timestamp: Optional[float] = None
        self.validation_start_time = time.time()
        self.last_log_check = time.time()
        self.observer: Optional[watchdog.observers.Observer] = None
        self.running = True
        
    def mark_acknowledged(self, timestamp: Optional[float] = None):
        """Mark GENESIS_MANDATE_001 as acknowledged"""
        if not self.genesis_acknowledged:
            self.genesis_acknowledged = True
            self.ack_timestamp = timestamp or time.time()
            
            # Update metrics
            mission_ingest_ok_total.labels(
                mission_type='GENESIS_MANDATE_001',
                source='council_api'
            ).inc()
            
            mission_validation_status.labels(
                mission_id='GENESIS_MANDATE_001'
            ).set(1)
            
            mission_ack_timestamp.labels(
                mission_id='GENESIS_MANDATE_001'
            ).set(self.ack_timestamp)
            
            logger.info(f"🎉 GENESIS_MANDATE_001 acknowledged at {datetime.fromtimestamp(self.ack_timestamp)}")

# Global validation state
state = ValidationState()

class LogWatcher(watchdog.events.FileSystemEventHandler):
    """Watches log files for mission acknowledgment"""
    
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.processed_files = set()
        
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.suffix in ['.log', '.txt'] and 'council' in file_path.name.lower():
            self.check_log_file(file_path)
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.suffix in ['.log', '.txt'] and 'council' in file_path.name.lower():
            self.check_log_file(file_path)
    
    def check_log_file(self, file_path: Path):
        """Check a log file for GENESIS_MANDATE_001 acknowledgment"""
        try:
            if not file_path.exists():
                return
                
            logger.debug(f"Checking log file: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last 1000 lines to avoid processing entire file repeatedly
                lines = f.readlines()
                recent_lines = lines[-1000:] if len(lines) > 1000 else lines
                
                for line_num, line in enumerate(recent_lines, 1):
                    log_lines_processed.labels(
                        log_file=file_path.name,
                        status='processed'
                    ).inc()
                    
                    # Check for GENESIS_MANDATE_001 acknowledgment
                    if 'GENESIS_MANDATE_001' in line and 'acknowledged' in line.lower():
                        logger.info(f"Found acknowledgment in {file_path}:{line_num}")
                        logger.info(f"Line content: {line.strip()}")
                        
                        # Try to extract timestamp from log line
                        timestamp = self.extract_timestamp(line)
                        state.mark_acknowledged(timestamp)
                        return
                        
        except Exception as e:
            logger.error(f"Error checking log file {file_path}: {e}")
            log_lines_processed.labels(
                log_file=file_path.name,
                status='error'
            ).inc()
    
    def extract_timestamp(self, log_line: str) -> Optional[float]:
        """Extract timestamp from log line"""
        try:
            # Try to find ISO timestamp in log line
            import re
            timestamp_pattern = r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})'
            match = re.search(timestamp_pattern, log_line)
            
            if match:
                timestamp_str = match.group(1)
                # Handle both ISO format and space-separated format
                for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(timestamp_str, fmt)
                        return dt.timestamp()
                    except ValueError:
                        continue
        except Exception as e:
            logger.debug(f"Could not extract timestamp from log line: {e}")
        
        return None

def check_council_api_directly():
    """Check Council-API directly for GENESIS_MANDATE_001 status"""
    try:
        # Check health endpoint
        health_response = requests.get(
            f"{COUNCIL_API_URL}/health",
            timeout=10
        )
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            
            # Check if GENESIS_MANDATE_001 is mentioned in health response
            if 'GENESIS_MANDATE_001' in str(health_data):
                logger.info("Found GENESIS_MANDATE_001 in Council-API health response")
                state.mark_acknowledged()
                return True
                
        # Check logs endpoint if available
        try:
            logs_response = requests.get(
                f"{COUNCIL_API_URL}/logs",
                timeout=10
            )
            
            if logs_response.status_code == 200:
                logs_data = logs_response.text
                
                if 'GENESIS_MANDATE_001' in logs_data and 'acknowledged' in logs_data.lower():
                    logger.info("Found GENESIS_MANDATE_001 acknowledgment in Council-API logs endpoint")
                    state.mark_acknowledged()
                    return True
                    
        except requests.RequestException:
            # Logs endpoint might not exist, continue with file watching
            pass
            
    except requests.RequestException as e:
        logger.debug(f"Could not check Council-API directly: {e}")
    
    return False

def scan_existing_logs():
    """Scan existing log files for acknowledgment"""
    log_dir = Path(LOG_DIR)
    
    if not log_dir.exists():
        logger.warning(f"Log directory does not exist: {log_dir}")
        return
        
    logger.info(f"Scanning existing logs in: {log_dir}")
    
    watcher = LogWatcher(str(log_dir))
    
    for log_file in log_dir.glob("*.log"):
        if 'council' in log_file.name.lower():
            logger.info(f"Scanning existing log file: {log_file}")
            watcher.check_log_file(log_file)
            
            if state.genesis_acknowledged:
                return

def start_log_watcher():
    """Start the log file watcher"""
    log_dir = Path(LOG_DIR)
    
    if not log_dir.exists():
        logger.warning(f"Log directory does not exist: {log_dir}")
        return
        
    logger.info(f"Starting log watcher for: {log_dir}")
    
    event_handler = LogWatcher(str(log_dir))
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, str(log_dir), recursive=True)
    
    state.observer = observer
    observer.start()
    
    logger.info("Log watcher started successfully")

def validation_loop():
    """Main validation loop that runs in background"""
    logger.info("Starting mission validation loop")
    
    # Scan existing logs first
    scan_existing_logs()
    
    # Start file watcher
    start_log_watcher()
    
    # Check Council-API directly
    if not state.genesis_acknowledged:
        check_council_api_directly()
    
    # Periodic checks
    while state.running and not state.genesis_acknowledged:
        elapsed = time.time() - state.validation_start_time
        
        if elapsed > VALIDATION_TIMEOUT:
            logger.error(f"Mission validation timeout after {elapsed:.1f}s")
            mission_validator_health.set(0)
            break
            
        # Periodic API check
        if time.time() - state.last_log_check > 30:
            check_council_api_directly()
            state.last_log_check = time.time()
            
        time.sleep(5)
    
    logger.info("Validation loop completed")

# Flask app for metrics and health
app = Flask(__name__)

@app.route('/health')
def health():
    """Health check endpoint"""
    if state.genesis_acknowledged:
        return {
            "status": "healthy",
            "mission_validated": True,
            "mission_id": "GENESIS_MANDATE_001",
            "ack_timestamp": state.ack_timestamp,
            "uptime_seconds": time.time() - state.validation_start_time
        }, 200
    else:
        elapsed = time.time() - state.validation_start_time
        return {
            "status": "validating",
            "mission_validated": False,
            "elapsed_seconds": elapsed,
            "timeout_seconds": VALIDATION_TIMEOUT
        }, 200

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    # Update health metric
    mission_validator_health.set(1 if state.running else 0)
    
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST
    )

@app.route('/status')
def status():
    """Detailed status endpoint"""
    return {
        "mission_validator": {
            "version": "BC-120",
            "status": "running" if state.running else "stopped",
            "genesis_acknowledged": state.genesis_acknowledged,
            "ack_timestamp": state.ack_timestamp,
            "validation_start_time": state.validation_start_time,
            "elapsed_seconds": time.time() - state.validation_start_time,
            "timeout_seconds": VALIDATION_TIMEOUT,
            "council_api_url": COUNCIL_API_URL,
            "log_dir": LOG_DIR,
            "last_log_check": state.last_log_check
        }
    }

def main():
    """Main entry point"""
    logger.info("🚀 Mission Validator Service starting (BC-120)")
    logger.info(f"   Council API URL: {COUNCIL_API_URL}")
    logger.info(f"   Log directory: {LOG_DIR}")
    logger.info(f"   Validation timeout: {VALIDATION_TIMEOUT}s")
    logger.info(f"   Port: {PORT}")
    
    # Initialize health metric
    mission_validator_health.set(1)
    
    # Start validation in background thread
    validation_thread = threading.Thread(
        target=validation_loop,
        name="ValidationLoop",
        daemon=True
    )
    validation_thread.start()
    
    # Start Flask app
    try:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        logger.info("Shutting down mission validator")
    finally:
        state.running = False
        if state.observer:
            state.observer.stop()
            state.observer.join()

if __name__ == "__main__":
    main() 