"""
API Metrics Module
Provides monitoring and canary deployment tracking
"""

import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Mock Prometheus metrics for compatibility
class MockMetric:
    """Mock Prometheus metric for environments without prometheus_client"""
    def __init__(self, name: str):
        self.name = name
        self._value = 0
        
    def inc(self, amount: float = 1):
        self._value += amount
        
    def observe(self, value: float):
        logger.debug(f"📊 {self.name}: {value}")
        
    def labels(self, **kwargs):
        return self

# Canary deployment tracking
IS_CANARY = False
_canary_metrics = {
    "start_time": time.time(),
    "requests_count": 0,
    "errors_count": 0,
    "last_activity": time.time()
}

def record_canary(request_path: str, status_code: int, response_time_ms: float):
    """Record canary deployment metrics"""
    global _canary_metrics
    
    _canary_metrics["requests_count"] += 1
    _canary_metrics["last_activity"] = time.time()
    
    if status_code >= 400:
        _canary_metrics["errors_count"] += 1
    
    logger.debug(f"📊 Canary metric: {request_path} → {status_code} ({response_time_ms:.1f}ms)")

def get_canary_metrics() -> Dict[str, Any]:
    """Get current canary metrics"""
    return _canary_metrics.copy()

# Adapter selection tracking (for ensemble routing)
adapter_select_total = MockMetric("adapter_select_total")

# Ensemble metrics
ensemble_mappings_total = MockMetric("ensemble_mappings_total")
ensemble_cache_size = MockMetric("ensemble_cache_size")

# Streaming metrics
stream_requests_total = MockMetric("stream_requests_total")
stream_chunk_duration_seconds = MockMetric("stream_chunk_duration_seconds")
stream_total_duration_seconds = MockMetric("stream_total_duration_seconds")

# Lineage security tracking
lineage_last_push_timestamp = time.time()

def update_lineage_timestamp():
    """Update lineage push timestamp"""
    global lineage_last_push_timestamp
    lineage_last_push_timestamp = time.time()
