#!/usr/bin/env python3
"""
EXT-24C Load Ramp Generator
Increases QPS from 200 → 600 over 10 minutes to test autoscaler response
"""

import time
import threading
import requests
import random
from datetime import datetime, timedelta
from typing import List
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [LOAD-RAMP] %(message)s')
logger = logging.getLogger('load-ramp')

class LoadRampGenerator:
    """Generates increasing load for autoscaler testing"""
    
    def __init__(self, target_url="http://localhost:8080"):
        self.target_url = target_url
        self.start_qps = 200
        self.end_qps = 600
        self.ramp_duration = 600  # 10 minutes
        self.running = False
        self.workers = []
        self.current_qps = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info("🚀 EXT-24C Load Ramp Generator Initialized")
        logger.info(f"   Target: {target_url}")
        logger.info(f"   Ramp: {self.start_qps} → {self.end_qps} QPS over {self.ramp_duration}s")
    
    def calculate_current_qps(self, elapsed_seconds: float) -> int:
        """Calculate current target QPS based on elapsed time"""
        if elapsed_seconds >= self.ramp_duration:
            return self.end_qps
        
        # Linear ramp
        progress = elapsed_seconds / self.ramp_duration
        current = self.start_qps + (self.end_qps - self.start_qps) * progress
        return int(current)
    
    def make_request(self) -> bool:
        """Make a single request to the target"""
        try:
            # Simulate council router request
            payload = {
                'request_id': f"load_test_{int(time.time())}_{random.randint(1000, 9999)}",
                'test_load': True,
                'timestamp': time.time()
            }
            
            response = requests.post(
                f"{self.target_url}/api/v1/route",
                json=payload,
                timeout=5,
                headers={'User-Agent': 'EXT24C-LoadRamp/1.0'}
            )
            
            self.total_requests += 1
            
            if response.status_code == 200:
                self.successful_requests += 1
                return True
            else:
                self.failed_requests += 1
                logger.warning(f"⚠️ Request failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.total_requests += 1
            self.failed_requests += 1
            logger.debug(f"Request error: {e}")
            return False
    
    def worker_thread(self, worker_id: int):
        """Worker thread for generating requests"""
        logger.debug(f"Worker {worker_id} started")
        
        while self.running:
            # Calculate how many requests this worker should make per second
            worker_qps = max(1, self.current_qps // len(self.workers))
            interval = 1.0 / worker_qps if worker_qps > 0 else 1.0
            
            start_time = time.time()
            self.make_request()
            
            # Sleep to maintain target rate
            elapsed = time.time() - start_time
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)
        
        logger.debug(f"Worker {worker_id} stopped")
    
    def start_ramp(self, num_workers: int = 10):
        """Start the load ramp"""
        logger.info(f"🎯 Starting load ramp with {num_workers} workers")
        
        self.running = True
        self.current_qps = self.start_qps
        start_time = time.time()
        
        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self.worker_thread, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        # Main control loop
        try:
            while self.running:
                elapsed = time.time() - start_time
                self.current_qps = self.calculate_current_qps(elapsed)
                
                # Log progress every 30 seconds
                if int(elapsed) % 30 == 0:
                    success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
                    logger.info(f"📊 T+{elapsed:.0f}s: QPS={self.current_qps}, "
                               f"Total={self.total_requests}, Success={success_rate:.1f}%")
                
                # Check if ramp is complete
                if elapsed >= self.ramp_duration:
                    logger.info("✅ Load ramp completed")
                    break
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 Load ramp interrupted")
        
        finally:
            self.stop_ramp()
    
    def stop_ramp(self):
        """Stop the load ramp"""
        logger.info("🛑 Stopping load ramp")
        self.running = False
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        # Final statistics
        success_rate = (self.successful_requests / max(1, self.total_requests)) * 100
        logger.info("📊 Final Statistics:")
        logger.info(f"   Total requests: {self.total_requests}")
        logger.info(f"   Successful: {self.successful_requests}")
        logger.info(f"   Failed: {self.failed_requests}")
        logger.info(f"   Success rate: {success_rate:.1f}%")

def main():
    """Run the load ramp"""
    import argparse
    
    parser = argparse.ArgumentParser(description='EXT-24C Load Ramp Generator')
    parser.add_argument('--target', default='http://localhost:8080', 
                       help='Target URL for load testing')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of worker threads')
    parser.add_argument('--start-qps', type=int, default=200,
                       help='Starting QPS')
    parser.add_argument('--end-qps', type=int, default=600,
                       help='Ending QPS')
    parser.add_argument('--duration', type=int, default=600,
                       help='Ramp duration in seconds')
    
    args = parser.parse_args()
    
    generator = LoadRampGenerator(target_url=args.target)
    generator.start_qps = args.start_qps
    generator.end_qps = args.end_qps
    generator.ramp_duration = args.duration
    
    try:
        generator.start_ramp(num_workers=args.workers)
    except Exception as e:
        logger.error(f"❌ Load ramp failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 