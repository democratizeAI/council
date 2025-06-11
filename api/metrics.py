"""
Metrics module for Agent-0 API
Provides Prometheus metrics collection and canary recording
"""

import os
from prometheus_client import Counter, Histogram, Gauge
import time

# Determine if this is a canary instance
IS_CANARY = os.getenv("IS_CANARY", "false").lower() == "true"

# Prometheus metrics
canary_requests_total = Counter(
    'canary_requests_total',
    'Total number of canary requests',
    ['endpoint', 'status', 'canary']
)

request_duration_seconds = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['endpoint', 'canary']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections',
    ['canary']
)

# Health check metrics
health_check_total = Counter(
    'health_check_total',
    'Total number of health checks',
    ['canary']
)

def record_canary(endpoint: str, success: bool):
    """
    Record a canary request metric
    
    Args:
        endpoint: The endpoint that was called
        success: Whether the request was successful
    """
    status = "success" if success else "error"
    canary_requests_total.labels(
        endpoint=endpoint,
        status=status,
        canary=str(IS_CANARY).lower()
    ).inc()

def record_request_duration(endpoint: str, duration: float):
    """
    Record request duration metric
    
    Args:
        endpoint: The endpoint that was called
        duration: Request duration in seconds
    """
    request_duration_seconds.labels(
        endpoint=endpoint,
        canary=str(IS_CANARY).lower()
    ).observe(duration)

def update_active_connections(count: int):
    """
    Update active connections gauge
    
    Args:
        count: Current number of active connections
    """
    active_connections.labels(canary=str(IS_CANARY).lower()).set(count)

def record_health_check():
    """Record a health check request"""
    health_check_total.labels(canary=str(IS_CANARY).lower()).inc()
