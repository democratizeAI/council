#!/usr/bin/env python3
"""
Council Router Metrics Simulator - EXT-24B Emergency Drill Support
Pushes simulated latency histogram metrics to enable immediate drill execution
"""

import time
import requests
import threading
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('council-metrics-sim')

class CouncilMetricsSimulator:
    """Simulates council router metrics for EXT-24B testing"""
    
    def __init__(self, pushgateway_url="http://localhost:9091"):
        self.pushgateway_url = pushgateway_url
        self.running = False
        self.spike_active = False
        self.base_latency = 0.050  # 50ms baseline
        self.spike_latency = 0.200  # 200ms spike
        
    def generate_histogram_metrics(self, latency_value: float) -> str:
        """Generate Prometheus histogram metrics for council router"""
        
        # Histogram buckets for latency
        buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, float('inf')]
        
        metrics = []
        
        # Generate bucket counts
        cumulative_count = 0
        for bucket in buckets:
            if latency_value <= bucket:
                cumulative_count += 1
            
            if bucket == float('inf'):
                bucket_label = '+Inf'
            else:
                bucket_label = str(bucket)
            
            metrics.append(f'swarm_council_router_latency_seconds_bucket{{method="POST",endpoint="route",le="{bucket_label}"}} {cumulative_count}')
        
        # Add sum and count
        metrics.append(f'swarm_council_router_latency_seconds_sum{{method="POST",endpoint="route"}} {latency_value}')
        metrics.append(f'swarm_council_router_latency_seconds_count{{method="POST",endpoint="route"}} 1')
        
        # Add some additional metrics
        metrics.append(f'council_router_requests_total{{method="POST",endpoint="route"}} 1')
        metrics.append(f'council_router_health_status 1')
        
        return '\n'.join(metrics)
    
    def push_metrics(self, latency_value: float) -> bool:
        """Push metrics to Pushgateway"""
        try:
            metrics_data = self.generate_histogram_metrics(latency_value)
            
            response = requests.post(
                f"{self.pushgateway_url}/metrics/job/council-router/instance/simulator",
                data=metrics_data,
                headers={'Content-Type': 'text/plain'},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.debug(f"📤 Metrics pushed: {latency_value:.3f}s latency")
                return True
            else:
                logger.warning(f"⚠️ Pushgateway returned {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to push metrics: {e}")
            return False
    
    def start_baseline_simulation(self):
        """Start generating baseline metrics"""
        logger.info("🚀 Starting council router metrics simulation")
        logger.info(f"📊 Baseline latency: {self.base_latency:.3f}s")
        logger.info(f"📤 Pushing to: {self.pushgateway_url}")
        
        self.running = True
        
        while self.running:
            # Calculate current latency
            if self.spike_active:
                current_latency = self.base_latency + self.spike_latency
            else:
                current_latency = self.base_latency
            
            # Push metrics
            success = self.push_metrics(current_latency)
            
            if success:
                status = "🔥 SPIKE" if self.spike_active else "📊 BASELINE"
                logger.info(f"{status} - Latency: {current_latency:.3f}s")
            
            time.sleep(2)  # Push every 2 seconds
    
    def trigger_spike(self, duration: int = 180):
        """Trigger latency spike for testing"""
        logger.info(f"🔥 TRIGGERING LATENCY SPIKE: +{self.spike_latency:.3f}s for {duration}s")
        
        self.spike_active = True
        
        # Schedule spike end
        def end_spike():
            time.sleep(duration)
            self.spike_active = False
            logger.info("🔻 Latency spike ended - returning to baseline")
        
        spike_thread = threading.Thread(target=end_spike, daemon=True)
        spike_thread.start()
    
    def stop(self):
        """Stop the simulation"""
        logger.info("🛑 Stopping metrics simulation")
        self.running = False

def main():
    """Run the simulator"""
    simulator = CouncilMetricsSimulator()
    
    try:
        # Start baseline simulation in background
        sim_thread = threading.Thread(target=simulator.start_baseline_simulation, daemon=True)
        sim_thread.start()
        
        # Wait a moment for baseline
        time.sleep(5)
        
        # Trigger spike for EXT-24B drill
        logger.info("⚡ EXT-24B DRILL: Triggering latency spike in 3 seconds...")
        time.sleep(3)
        
        simulator.trigger_spike(duration=180)
        
        # Keep running for the spike duration + margin
        time.sleep(200)
        
        simulator.stop()
        logger.info("✅ EXT-24B metrics simulation complete")
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        simulator.stop()
    
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")

if __name__ == "__main__":
    main() 