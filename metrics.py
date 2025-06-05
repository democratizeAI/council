#!/usr/bin/env python3
"""
Metrics Registry - Prometheus metrics for Swarm Operations
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server
import time

# Pattern-Miner metrics
PATTERN_GAUGE = Counter("pattern_clusters_total", "clusters mined")

# Router metrics  
ROUTER_REQUESTS = Counter("swarm_router_requests_total", "Total router requests")
ROUTER_ERRORS = Counter("swarm_router_errors_total", "Router errors", ["error_type"])

# Execution metrics
EXECUTION_SUCCESS = Counter("swarm_execution_success_total", "Successful executions")
EXECUTION_FAILURES = Counter("swarm_execution_failures_total", "Failed executions", ["reason"])

# Cost tracking
COST_USD_TOTAL = Counter("cost_usd_total", "Total cost in USD", ["agent"])

# Performance metrics
RESPONSE_TIME = Histogram("response_time_seconds", "Response time in seconds")
MERGE_EFFICIENCY = Gauge("merge_efficiency", "Merge efficiency ratio")

# Registry singleton to prevent duplicate pushes
class RegistrySingleton:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance
    
    def __init__(self):
        if not self.initialized:
            self.metrics = {
                'pattern_clusters_total': PATTERN_GAUGE,
                'swarm_router_requests_total': ROUTER_REQUESTS,
                'swarm_execution_success_total': EXECUTION_SUCCESS,
                'cost_usd_total': COST_USD_TOTAL,
                'merge_efficiency': MERGE_EFFICIENCY
            }
            self.initialized = True

# Global registry instance
registry = RegistrySingleton()

def start_metrics_server(port=8000):
    """Start Prometheus metrics HTTP server"""
    start_http_server(port)
    print(f"📊 Metrics server started on port {port}")

if __name__ == "__main__":
    start_metrics_server() 