#!/usr/bin/env python3
"""
Round Table Metrics Generator

Generates mock Round Table metrics and pushes them to Prometheus pushgateway
so the Grafana dashboard can display realistic data.
"""

import time
import random
import requests
import sys
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, push_to_gateway

def generate_roundtable_metrics():
    """Generate and push Round Table metrics to pushgateway"""
    
    # Create a custom registry for this push
    registry = CollectorRegistry()
    
    # Create metrics matching the Grafana dashboard expectations
    scratch_updates_total = Counter(
        'scratch_updates_total',
        'Number of scratch-pad updates by agent',
        ['agent'],
        registry=registry
    )
    
    roundtable_cloud_wins_total = Counter(
        'roundtable_cloud_wins_total',
        'Total cloud wins in round table',
        registry=registry
    )
    
    roundtable_local_wins_total = Counter(
        'roundtable_local_wins_total',
        'Total local agent wins',
        ['agent'],
        registry=registry
    )
    
    roundtable_latency_seconds = Histogram(
        'roundtable_latency_seconds',
        'Round table latency in seconds',
        buckets=[0.5, 1, 2, 4, 8, 16, 32, float('inf')],
        registry=registry
    )
    
    roundtable_quality_score = Histogram(
        'roundtable_quality_score',
        'Quality score distribution',
        ['source'],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        registry=registry
    )
    
    scratch_pad_file_size_bytes = Gauge(
        'scratch_pad_file_size_bytes',
        'Scratch-pad file sizes',
        ['agent'],
        registry=registry
    )
    
    # Generate realistic data
    agents = ['agent0', 'math', 'code', 'logic', 'knowledge']
    
    # Scratch updates (varied by agent activity)
    for agent in agents:
        updates = random.randint(10, 50)
        scratch_updates_total.labels(agent=agent)._value.set(updates)
    
    # Cloud wins
    roundtable_cloud_wins_total._value.set(random.randint(15, 25))
    
    # Local agent wins  
    for agent in agents:
        wins = random.randint(5, 15)
        roundtable_local_wins_total.labels(agent=agent)._value.set(wins)
    
    # Latency samples (some fast, some slow)
    for _ in range(50):
        latency = random.uniform(0.5, 8.0)
        roundtable_latency_seconds.observe(latency)
    
    # Quality scores
    for _ in range(30):
        # Cloud tends to be higher quality
        cloud_score = random.uniform(0.7, 1.0)
        roundtable_quality_score.labels(source='cloud').observe(cloud_score)
        
        # Local more varied
        local_score = random.uniform(0.4, 0.9)
        roundtable_quality_score.labels(source='local').observe(local_score)
    
    # File sizes (varying over time)
    base_time = time.time()
    for i, agent in enumerate(agents):
        size = int(1000 + (base_time % 10000) * (i + 1))
        scratch_pad_file_size_bytes.labels(agent=agent).set(size)
    
    # Push to gateway
    try:
        push_to_gateway('pushgateway:9091', job='roundtable', registry=registry)
        print(f"✅ Round Table metrics pushed successfully at {time.strftime('%H:%M:%S')}")
        return True
    except Exception as e:
        try:
            # Try localhost if container name fails
            push_to_gateway('localhost:9091', job='roundtable', registry=registry)
            print(f"✅ Round Table metrics pushed to localhost at {time.strftime('%H:%M:%S')}")
            return True
        except Exception as e2:
            print(f"❌ Failed to push metrics: {e}")
            print(f"❌ Localhost also failed: {e2}")
            return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        # Single push
        generate_roundtable_metrics()
    else:
        # Continuous mode
        print("🎯 Starting Round Table metrics generator...")
        print("📊 Pushing metrics every 30 seconds to Prometheus Pushgateway")
        print("🔄 Press Ctrl+C to stop")
        
        while True:
            try:
                generate_roundtable_metrics()
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n👋 Stopping metrics generator")
                break
            except Exception as e:
                print(f"⚠️ Error: {e}")
                time.sleep(10) 