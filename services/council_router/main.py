#!/usr/bin/env python3
"""
Council Router Service - EXT-24B Latency Histogram Provider
Generates swarm_council_router_latency_seconds_bucket metrics for anomaly testing
"""

import os
import time
import random
import threading
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('council-router')

# Prometheus metrics
REQUEST_COUNT = Counter('council_router_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_LATENCY = Histogram(
    'swarm_council_router_latency_seconds',
    'Request latency histogram',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
)
ACTIVE_REQUESTS = Gauge('council_router_active_requests', 'Active requests')
HEALTH_STATUS = Gauge('council_router_health_status', 'Health status (1=healthy, 0=unhealthy)')

app = Flask(__name__)

class LatencySimulator:
    """Simulates realistic latency patterns for testing"""
    
    def __init__(self):
        self.base_latency = 0.050  # 50ms base
        self.spike_active = False
        self.spike_latency = 0.200  # 200ms spike
        self.spike_start = None
        self.spike_duration = 180  # 3 minutes
        
    def get_simulated_latency(self) -> float:
        """Get current simulated latency"""
        base = self.base_latency + random.uniform(0, 0.020)  # 0-20ms jitter
        
        if self.spike_active:
            # Check if spike should end
            if time.time() - self.spike_start > self.spike_duration:
                self.spike_active = False
                logger.info("🔻 Latency spike ended - returning to baseline")
                return base
            
            # Return spike latency with some variance
            return base + self.spike_latency + random.uniform(-0.010, 0.010)
        
        return base
    
    def trigger_spike(self, duration: int = 180, extra_latency: float = 0.200):
        """Trigger a latency spike for testing"""
        self.spike_active = True
        self.spike_start = time.time()
        self.spike_duration = duration
        self.spike_latency = extra_latency
        logger.info(f"🔥 Latency spike triggered: +{extra_latency*1000:.0f}ms for {duration}s")

# Global latency simulator
latency_sim = LatencySimulator()

@app.before_request
def before_request():
    """Start request timing"""
    request.start_time = time.time()
    ACTIVE_REQUESTS.inc()

@app.after_request
def after_request(response):
    """Record request metrics"""
    ACTIVE_REQUESTS.dec()
    
    # Calculate actual processing time
    processing_time = time.time() - request.start_time
    
    # Add simulated latency for testing
    simulated_latency = latency_sim.get_simulated_latency()
    total_latency = processing_time + simulated_latency
    
    # Record metrics
    method = request.method
    endpoint = request.endpoint or 'unknown'
    
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(total_latency)
    
    # Simulate the latency delay
    if simulated_latency > 0:
        time.sleep(simulated_latency)
    
    return response

@app.route('/health')
def health():
    """Health check endpoint"""
    HEALTH_STATUS.set(1)
    return jsonify({
        'status': 'healthy',
        'service': 'council-router',
        'version': '1.0.0',
        'timestamp': time.time(),
        'latency_spike_active': latency_sim.spike_active
    })

@app.route('/api/v1/route', methods=['POST'])
def route_request():
    """Main routing endpoint"""
    data = request.get_json() or {}
    
    # Simulate some processing
    time.sleep(random.uniform(0.001, 0.005))
    
    return jsonify({
        'routed': True,
        'destination': 'council-swarm',
        'request_id': f"req_{int(time.time())}",
        'data': data
    })

@app.route('/api/v1/status')
def status():
    """Service status endpoint"""
    return jsonify({
        'service': 'council-router',
        'active_requests': ACTIVE_REQUESTS._value._value,
        'total_requests': REQUEST_COUNT._value.sum(),
        'latency_spike_active': latency_sim.spike_active,
        'health': 'ok'
    })

@app.route('/debug/trigger-spike', methods=['POST'])
def trigger_spike():
    """Debug endpoint to trigger latency spike"""
    data = request.get_json() or {}
    duration = data.get('duration', 180)
    extra_latency = data.get('extra_latency', 0.200)
    
    latency_sim.trigger_spike(duration, extra_latency)
    
    return jsonify({
        'spike_triggered': True,
        'duration': duration,
        'extra_latency': extra_latency,
        'start_time': latency_sim.spike_start
    })

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def background_traffic():
    """Generate background traffic to create realistic metrics"""
    import requests
    
    while True:
        try:
            # Simulate background requests
            requests.post('http://localhost:8080/api/v1/route', 
                         json={'test': True}, timeout=5)
            time.sleep(random.uniform(0.5, 2.0))
        except:
            time.sleep(5)

if __name__ == '__main__':
    logger.info("🚀 Council Router Service Starting...")
    logger.info("📊 Prometheus metrics available at :9100/metrics")
    logger.info("🔍 Health check available at :8080/health")
    
    # Start background traffic in a separate thread
    traffic_thread = threading.Thread(target=background_traffic, daemon=True)
    traffic_thread.start()
    
    # Set initial health status
    HEALTH_STATUS.set(1)
    
    # Start the service on correct ports
    metrics_port = int(os.getenv('METRICS_PORT', 9100))
    api_port = 8080
    
    logger.info(f"🚀 Starting Council Router API on port {api_port}")
    logger.info(f"📊 Metrics available on port {metrics_port}")
    
    app.run(
        host='0.0.0.0',
        port=api_port,
        debug=False,
        threaded=True
    ) 