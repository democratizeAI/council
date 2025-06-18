#!/usr/bin/env python3
"""
Standalone Prometheus metrics exporter for Agent-0
Runs as a separate service to ensure metrics availability even if main service crashes
"""

import os
import time
import psutil
import requests
from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Initialize FastAPI app
app = FastAPI(
    title="Agent-0 Metrics Exporter",
    description="Standalone Prometheus metrics exporter for Agent-0",
    version="1.0.0"
)

# Prometheus metrics
EXPORTER_REQUESTS = Counter('agent0_exporter_requests_total', 'Total requests to metrics exporter')
EXPORTER_ERRORS = Counter('agent0_exporter_errors_total', 'Total errors in metrics collection')

# System metrics
SYSTEM_CPU_PERCENT = Gauge('agent0_system_cpu_percent', 'System CPU utilization')
SYSTEM_MEMORY_PERCENT = Gauge('agent0_system_memory_percent', 'System memory utilization')
SYSTEM_DISK_PERCENT = Gauge('agent0_system_disk_percent', 'System disk utilization')

# Agent-0 service metrics
AGENT0_SERVICE_UP = Gauge('agent0_service_up', 'Agent-0 service availability (1=up, 0=down)')
AGENT0_SERVICE_RESTARTS = Counter('agent0_service_restarts_total', 'Total Agent-0 service restarts')
AGENT0_RESPONSE_TIME = Histogram('agent0_response_time_seconds', 'Agent-0 API response time')

# GPU metrics (if available)
GPU_UTILIZATION = Gauge('agent0_gpu_utilization_percent', 'GPU utilization percentage')
GPU_MEMORY_USED = Gauge('agent0_gpu_memory_used_mb', 'GPU memory used in MB')
GPU_TEMPERATURE = Gauge('agent0_gpu_temperature_celsius', 'GPU temperature in Celsius')

def collect_system_metrics():
    """Collect basic system metrics"""
    try:
        # CPU utilization
        cpu_percent = psutil.cpu_percent(interval=1)
        SYSTEM_CPU_PERCENT.set(cpu_percent)
        
        # Memory utilization
        memory = psutil.virtual_memory()
        SYSTEM_MEMORY_PERCENT.set(memory.percent)
        
        # Disk utilization
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        SYSTEM_DISK_PERCENT.set(disk_percent)
        
    except Exception as e:
        EXPORTER_ERRORS.inc()
        print(f"Error collecting system metrics: {e}")

def collect_agent0_metrics():
    """Collect Agent-0 specific metrics"""
    try:
        # Check if Agent-0 service is responding
        start_time = time.time()
        
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                AGENT0_SERVICE_UP.set(1)
                AGENT0_RESPONSE_TIME.observe(response_time)
                
                # Extract metrics from health response
                health_data = response.json()
                
                # GPU metrics if available
                monitoring = health_data.get("monitoring", {})
                gpu_util = monitoring.get("gpu_utilization", 0)
                if gpu_util > 0:
                    GPU_UTILIZATION.set(gpu_util)
                
                # Service restart count
                service_info = health_data.get("service", {})
                restarts = service_info.get("startups_total", 0)
                AGENT0_SERVICE_RESTARTS._value._value = restarts
                
            else:
                AGENT0_SERVICE_UP.set(0)
                AGENT0_RESPONSE_TIME.observe(response_time)
                
        except requests.RequestException:
            AGENT0_SERVICE_UP.set(0)
            
    except Exception as e:
        EXPORTER_ERRORS.inc()
        print(f"Error collecting Agent-0 metrics: {e}")

def collect_gpu_metrics():
    """Collect GPU metrics using nvidia-ml-py if available"""
    try:
        import pynvml
        
        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        
        if device_count > 0:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # First GPU
            
            # GPU utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            GPU_UTILIZATION.set(util.gpu)
            
            # GPU memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            GPU_MEMORY_USED.set(mem_info.used // (1024 * 1024))  # Convert to MB
            
            # GPU temperature
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            GPU_TEMPERATURE.set(temp)
            
    except ImportError:
        # pynvml not available, skip GPU metrics
        pass
    except Exception as e:
        EXPORTER_ERRORS.inc()
        print(f"Error collecting GPU metrics: {e}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    EXPORTER_REQUESTS.inc()
    
    try:
        # Collect all metrics
        collect_system_metrics()
        collect_agent0_metrics()
        collect_gpu_metrics()
        
        # Return Prometheus format
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
        
    except Exception as e:
        EXPORTER_ERRORS.inc()
        return Response(f"# Error generating metrics: {e}\n", media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
async def health():
    """Health check for the exporter itself"""
    return {
        "status": "healthy",
        "service": "agent0-metrics-exporter",
        "timestamp": time.time()
    }

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "service": "Agent-0 Metrics Exporter",
        "endpoints": {
            "metrics": "/metrics",
            "health": "/health"
        },
        "description": "Standalone Prometheus metrics exporter for Agent-0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9091) 