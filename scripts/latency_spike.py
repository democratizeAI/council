#!/usr/bin/env python3
"""
Council Latency Spike Generator (M-310)
Synthetic drift script that adds configurable delay to test anomaly detection
"""

import os
import sys
import time
import requests
import threading
import signal
import argparse
from datetime import datetime, timedelta
from typing import Optional
import logging

# Add project root to path for A2A integration
sys.path.append('.')

try:
    from common.a2a_bus import A2ABus
except ImportError:
    A2ABus = None
    print("Warning: A2A bus not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('latency-spike')

# Configuration
COUNCIL_URL = os.getenv('COUNCIL_URL', 'http://council-api:8080')
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus:9090')
DEFAULT_SPIKE_DURATION = 180  # 3 minutes
DEFAULT_SPIKE_LATENCY = 0.150  # 150ms


class LatencySpiker:
    """Generates synthetic latency spikes to test anomaly detection"""
    
    def __init__(self, spike_latency: float = DEFAULT_SPIKE_LATENCY, 
                 duration: int = DEFAULT_SPIKE_DURATION):
        self.spike_latency = spike_latency
        self.duration = duration
        self.active = False
        self.start_time = None
        self.end_time = None
        self.spike_thread = None
        self.stop_event = threading.Event()
        
        # A2A integration
        self.a2a_bus = None
        if A2ABus:
            try:
                self.a2a_bus = A2ABus('latency-spiker')
                logger.info("🔌 A2A bus initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize A2A bus: {e}")
        
        logger.info(f"🏗️ Latency Spiker initialized")
        logger.info(f"   Spike latency: {spike_latency*1000:.0f}ms")
        logger.info(f"   Duration: {duration}s")
    
    def publish_spike_event(self, event_type: str, details: dict = None):
        """Publish latency spike events to A2A bus"""
        if not self.a2a_bus:
            return
        
        try:
            payload = {
                "event_type": event_type,
                "timestamp": time.time(),
                "spike_latency_ms": self.spike_latency * 1000,
                "duration_seconds": self.duration,
                "rule_target": "M-310",
                **(details or {})
            }
            
            stream_id = self.a2a_bus.pub(
                row_id=f"LATENCY_SPIKE_{event_type}",
                payload=payload,
                event_type=event_type
            )
            
            logger.info(f"📤 Published {event_type} event: {stream_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish {event_type} event: {e}")
    
    def make_slow_request(self, delay: float) -> Optional[float]:
        """Make a request to Council API with artificial delay"""
        try:
            # Add artificial delay before request
            time.sleep(delay)
            
            start_time = time.time()
            
            # Make a simple health check request
            response = requests.get(
                f"{COUNCIL_URL}/health",
                timeout=10,
                headers={"User-Agent": "latency-spiker/M-310"}
            )
            
            duration = time.time() - start_time
            
            if response.status_code == 200:
                logger.debug(f"Request completed in {duration:.3f}s (+ {delay:.3f}s artificial)")
                return duration + delay
            else:
                logger.warning(f"Request failed with status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def spike_worker(self):
        """Worker thread that generates continuous slow requests"""
        logger.info(f"🔥 Starting latency spike: +{self.spike_latency*1000:.0f}ms for {self.duration}s")
        
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=self.duration)
        
        # Publish spike start event
        self.publish_spike_event("LATENCY_SPIKE_START", {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        })
        
        request_count = 0
        total_latency = 0
        
        while not self.stop_event.is_set() and datetime.now() < self.end_time:
            # Make slow request
            latency = self.make_slow_request(self.spike_latency)
            
            if latency:
                request_count += 1
                total_latency += latency
                
                if request_count % 10 == 0:
                    avg_latency = total_latency / request_count
                    remaining = (self.end_time - datetime.now()).total_seconds()
                    logger.info(f"📊 Spike progress: {request_count} requests, "
                               f"avg {avg_latency:.3f}s, {remaining:.0f}s remaining")
            
            # Wait between requests (1 request per second)
            if not self.stop_event.wait(1.0):
                continue
        
        # Calculate final stats
        if request_count > 0:
            avg_latency = total_latency / request_count
            actual_duration = (datetime.now() - self.start_time).total_seconds()
            
            logger.info(f"✅ Spike completed:")
            logger.info(f"   Requests: {request_count}")
            logger.info(f"   Average latency: {avg_latency:.3f}s")
            logger.info(f"   Actual duration: {actual_duration:.1f}s")
            
            # Publish spike completion event
            self.publish_spike_event("LATENCY_SPIKE_COMPLETE", {
                "request_count": request_count,
                "average_latency": avg_latency,
                "actual_duration": actual_duration
            })
        
        self.active = False
    
    def start_spike(self):
        """Start the latency spike in background thread"""
        if self.active:
            logger.warning("⚠️ Spike already active")
            return False
        
        logger.info(f"🚀 Starting {self.duration}s latency spike (+{self.spike_latency*1000:.0f}ms)")
        
        self.active = True
        self.stop_event.clear()
        
        self.spike_thread = threading.Thread(target=self.spike_worker, daemon=True)
        self.spike_thread.start()
        
        return True
    
    def stop_spike(self):
        """Stop the latency spike"""
        if not self.active:
            logger.warning("⚠️ No active spike to stop")
            return False
        
        logger.info("🛑 Stopping latency spike")
        
        self.stop_event.set()
        
        if self.spike_thread and self.spike_thread.is_alive():
            self.spike_thread.join(timeout=5.0)
        
        # Publish spike stop event
        self.publish_spike_event("LATENCY_SPIKE_STOPPED", {
            "stopped_at": datetime.now().isoformat(),
            "was_manual": True
        })
        
        self.active = False
        return True
    
    def wait_for_completion(self):
        """Wait for spike to complete naturally"""
        if not self.active:
            logger.warning("⚠️ No active spike")
            return
        
        if self.spike_thread:
            self.spike_thread.join()
            logger.info("✅ Spike completed")
    
    def check_prometheus_alert(self, alert_name: str = "CouncilLatencyAnomaly") -> bool:
        """Check if the target alert is firing in Prometheus"""
        try:
            url = f"{PROMETHEUS_URL}/api/v1/alerts"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("status") == "success":
                alerts = data.get("data", {}).get("alerts", [])
                
                for alert in alerts:
                    if alert.get("labels", {}).get("alertname") == alert_name:
                        state = alert.get("state", "")
                        logger.info(f"🚨 Alert {alert_name}: {state}")
                        return state in ["pending", "firing"]
                
                logger.info(f"📊 Alert {alert_name}: not found (inactive)")
                return False
            else:
                logger.error(f"Prometheus API error: {data}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to check alert status: {e}")
            return False
    
    def get_current_latency(self) -> Optional[float]:
        """Get current P95 latency from Prometheus"""
        try:
            query = 'histogram_quantile(0.95, rate(council_router_latency_seconds_bucket[5m]))'
            url = f"{PROMETHEUS_URL}/api/v1/query"
            
            response = requests.get(url, params={"query": query}, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if (data.get("status") == "success" and 
                data.get("data", {}).get("result")):
                
                result = data["data"]["result"][0]
                value = float(result["value"][1])
                
                logger.debug(f"Current P95 latency: {value:.3f}s")
                return value
            else:
                logger.warning("No latency data available")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get current latency: {e}")
            return None


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global spiker
    logger.info("🛑 Received interrupt signal")
    if spiker and spiker.active:
        spiker.stop_spike()
    sys.exit(0)


def main():
    """Main entry point"""
    global spiker
    
    parser = argparse.ArgumentParser(description="Council Latency Spike Generator (M-310)")
    parser.add_argument("--latency", type=float, default=DEFAULT_SPIKE_LATENCY,
                        help=f"Spike latency in seconds (default: {DEFAULT_SPIKE_LATENCY})")
    parser.add_argument("--duration", type=int, default=DEFAULT_SPIKE_DURATION,
                        help=f"Spike duration in seconds (default: {DEFAULT_SPIKE_DURATION})")
    parser.add_argument("--check-alert", action="store_true",
                        help="Check if CouncilLatencyAnomaly alert is firing")
    parser.add_argument("--get-latency", action="store_true",
                        help="Get current P95 latency")
    parser.add_argument("--wait", action="store_true",
                        help="Wait for spike completion")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🔥 Council Latency Spike Generator (M-310)")
    logger.info(f"   Target: +{args.latency*1000:.0f}ms for {args.duration}s")
    
    # Handle utility commands
    if args.check_alert:
        spiker = LatencySpiker()
        is_firing = spiker.check_prometheus_alert()
        print(f"CouncilLatencyAnomaly alert: {'FIRING' if is_firing else 'INACTIVE'}")
        exit(0 if is_firing else 1)
    
    if args.get_latency:
        spiker = LatencySpiker()
        latency = spiker.get_current_latency()
        if latency:
            print(f"Current P95 latency: {latency:.3f}s ({latency*1000:.0f}ms)")
            exit(0)
        else:
            print("Failed to get latency data")
            exit(1)
    
    # Main spike execution
    spiker = LatencySpiker(spike_latency=args.latency, duration=args.duration)
    
    try:
        # Get baseline latency
        baseline = spiker.get_current_latency()
        if baseline:
            logger.info(f"📊 Baseline P95 latency: {baseline:.3f}s ({baseline*1000:.0f}ms)")
        
        # Start spike
        if spiker.start_spike():
            logger.info(f"⏱️ Spike running for {args.duration}s...")
            
            # Monitor progress
            check_interval = 30  # Check every 30 seconds
            next_check = time.time() + check_interval
            
            while spiker.active:
                current_time = time.time()
                
                if current_time >= next_check:
                    # Check alert status
                    is_firing = spiker.check_prometheus_alert()
                    
                    # Get current latency
                    current_latency = spiker.get_current_latency()
                    if current_latency:
                        logger.info(f"📊 Current P95: {current_latency:.3f}s "
                                   f"(+{(current_latency-baseline)*1000:.0f}ms from baseline)")
                    
                    if is_firing:
                        logger.info("🚨 SUCCESS: CouncilLatencyAnomaly alert is FIRING")
                    
                    next_check = current_time + check_interval
                
                time.sleep(1)
            
            if args.wait:
                spiker.wait_for_completion()
            
            logger.info("✅ Latency spike completed")
            
            # Final alert check
            time.sleep(5)  # Allow alerts to update
            final_alert_status = spiker.check_prometheus_alert()
            logger.info(f"🔍 Final alert status: {'FIRING' if final_alert_status else 'INACTIVE'}")
            
        else:
            logger.error("❌ Failed to start spike")
            exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Spike interrupted by user")
        if spiker.active:
            spiker.stop_spike()
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        if spiker.active:
            spiker.stop_spike()
        exit(1)


if __name__ == "__main__":
    main() 