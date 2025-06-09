#!/usr/bin/env python3
"""
Queue-Depth Failover Drill
==========================

P0 Critical: Verify Guardian auto-restart when queue_depth > 200 for 60s
Tests B-04 → B-08 loop self-healing with 500 VU load
"""

import asyncio
import aiohttp
import time
import json
import signal
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class LoadTestMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    max_queue_depth: int = 0
    guardian_restarts: int = 0
    queue_depth_exceeded_duration: float = 0.0

class QueueDepthDrill:
    def __init__(self, target_url: str = "http://localhost:8080"):
        self.target_url = target_url
        self.vote_endpoint = f"{target_url}/vote"
        self.metrics_endpoint = f"{target_url}/metrics"
        self.health_endpoint = f"{target_url}/health"
        
        self.metrics = LoadTestMetrics()
        self.running = True
        self.start_time = None
        
        # Test queries of varying complexity
        self.test_queries = [
            "2+2",
            "What is Python?",
            "Write a hello world function",
            "Calculate the factorial of 10",
            "Explain quantum computing",
            "Create a binary search algorithm",
            "What is machine learning?",
            "Solve x^2 + 5x + 6 = 0",
            "Write a bubble sort algorithm",
            "What is the capital of France?"
        ]
    
    async def single_request(self, session: aiohttp.ClientSession, user_id: int) -> Dict[str, Any]:
        """Single request from a virtual user"""
        query = self.test_queries[user_id % len(self.test_queries)]
        
        try:
            start_time = time.time()
            
            async with session.post(
                self.vote_endpoint,
                json={"prompt": query},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "latency_ms": latency_ms,
                        "status_code": 200,
                        "user_id": user_id,
                        "query": query[:30]
                    }
                else:
                    return {
                        "success": False,
                        "latency_ms": latency_ms,
                        "status_code": response.status,
                        "user_id": user_id,
                        "error": f"HTTP {response.status}"
                    }
                    
        except asyncio.TimeoutError:
            return {
                "success": False,
                "latency_ms": 10000,
                "user_id": user_id,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "latency_ms": 0,
                "user_id": user_id,
                "error": str(e)
            }
    
    async def monitor_queue_depth(self, session: aiohttp.ClientSession):
        """Monitor queue depth and guardian metrics"""
        queue_depth_high_start = None
        
        while self.running:
            try:
                async with session.get(self.metrics_endpoint, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        metrics_text = await response.text()
                        
                        # Parse queue depth from Prometheus metrics
                        queue_depth = 0
                        guardian_restarts = 0
                        
                        for line in metrics_text.split('\n'):
                            if 'swarm_queue_depth' in line and not line.startswith('#'):
                                try:
                                    queue_depth = int(float(line.split()[-1]))
                                except:
                                    pass
                            elif 'guardian_restarts_total' in line and not line.startswith('#'):
                                try:
                                    guardian_restarts = int(float(line.split()[-1]))
                                except:
                                    pass
                        
                        self.metrics.max_queue_depth = max(self.metrics.max_queue_depth, queue_depth)
                        self.metrics.guardian_restarts = guardian_restarts
                        
                        # Track queue depth threshold breach
                        if queue_depth > 200:
                            if queue_depth_high_start is None:
                                queue_depth_high_start = time.time()
                                print(f"🚨 Queue depth exceeded 200: {queue_depth}")
                        else:
                            if queue_depth_high_start is not None:
                                duration = time.time() - queue_depth_high_start
                                self.metrics.queue_depth_exceeded_duration += duration
                                if duration > 60:
                                    print(f"⏰ Queue depth > 200 for {duration:.1f}s - Guardian should restart")
                                queue_depth_high_start = None
                        
                        # Log every 10 seconds
                        if int(time.time()) % 10 == 0:
                            elapsed = time.time() - self.start_time
                            print(f"📊 {elapsed:3.0f}s | Queue: {queue_depth:3d} | Restarts: {guardian_restarts} | RPS: {self.metrics.total_requests/(elapsed+0.1):5.1f}")
                
            except Exception as e:
                print(f"⚠️ Metrics monitoring error: {e}")
            
            await asyncio.sleep(1)
    
    async def virtual_user(self, session: aiohttp.ClientSession, user_id: int):
        """Simulate a single virtual user making requests"""
        request_count = 0
        
        while self.running:
            result = await self.single_request(session, user_id)
            
            self.metrics.total_requests += 1
            if result["success"]:
                self.metrics.successful_requests += 1
            else:
                self.metrics.failed_requests += 1
            
            request_count += 1
            
            # Virtual users make requests every 0.5-2 seconds
            delay = 0.5 + (user_id % 3) * 0.5
            await asyncio.sleep(delay)
    
    async def run_drill(self, num_users: int = 500, duration_seconds: int = 120):
        """Run the queue depth failover drill"""
        print("🚨 Queue-Depth Failover Drill")
        print("=" * 50)
        print(f"Virtual Users: {num_users}")
        print(f"Duration: {duration_seconds}s")
        print(f"Target: Queue depth > 200 for 60s triggers Guardian restart")
        print()
        
        self.start_time = time.time()
        
        # Setup signal handler for graceful shutdown
        def signal_handler(sig, frame):
            print("\n🛑 Stopping drill...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(limit=num_users + 10, limit_per_host=num_users + 10)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Start monitoring task
            monitor_task = asyncio.create_task(self.monitor_queue_depth(session))
            
            # Create virtual user tasks
            user_tasks = []
            for user_id in range(num_users):
                task = asyncio.create_task(self.virtual_user(session, user_id))
                user_tasks.append(task)
            
            print(f"🚀 Starting {num_users} virtual users...")
            
            # Run for specified duration
            try:
                await asyncio.sleep(duration_seconds)
            except KeyboardInterrupt:
                print("User interrupted")
            
            # Shutdown
            print("🛑 Stopping virtual users...")
            self.running = False
            
            # Cancel all tasks
            monitor_task.cancel()
            for task in user_tasks:
                task.cancel()
            
            # Wait for cleanup
            try:
                await asyncio.gather(monitor_task, *user_tasks, return_exceptions=True)
            except:
                pass
        
        # Calculate final metrics
        total_time = time.time() - self.start_time
        if self.metrics.successful_requests > 0:
            self.metrics.avg_latency_ms = 0  # Would need to track individual latencies
        
        return self.analyze_results(total_time)
    
    def analyze_results(self, total_time: float) -> Dict[str, Any]:
        """Analyze drill results"""
        print("\n" + "=" * 50)
        print("🎯 Queue-Depth Drill Analysis")
        print("=" * 50)
        
        print(f"Total Time: {total_time:.1f}s")
        print(f"Total Requests: {self.metrics.total_requests}")
        print(f"Successful: {self.metrics.successful_requests}")
        print(f"Failed: {self.metrics.failed_requests}")
        print(f"Success Rate: {(self.metrics.successful_requests/max(1,self.metrics.total_requests))*100:.1f}%")
        print(f"RPS: {self.metrics.total_requests/total_time:.1f}")
        
        print(f"\n🎛️ Queue Management:")
        print(f"Max Queue Depth: {self.metrics.max_queue_depth}")
        print(f"Queue > 200 Duration: {self.metrics.queue_depth_exceeded_duration:.1f}s")
        print(f"Guardian Restarts: {self.metrics.guardian_restarts}")
        
        # Evaluate success criteria
        queue_test_passed = self.metrics.max_queue_depth > 200
        guardian_test_passed = (
            self.metrics.queue_depth_exceeded_duration > 60 and 
            self.metrics.guardian_restarts > 0
        )
        
        print(f"\n🛡️ Failover Test Results:")
        if queue_test_passed:
            print("✅ Queue depth exceeded 200 threshold")
        else:
            print("❌ Queue depth never exceeded 200 - increase load?")
        
        if guardian_test_passed:
            print("✅ Guardian auto-restart triggered after 60s")
        else:
            print("❌ Guardian auto-restart not detected")
        
        overall_pass = queue_test_passed and guardian_test_passed
        
        return {
            "passed": overall_pass,
            "queue_test_passed": queue_test_passed,
            "guardian_test_passed": guardian_test_passed,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": (self.metrics.successful_requests/max(1,self.metrics.total_requests))*100,
                "max_queue_depth": self.metrics.max_queue_depth,
                "queue_exceeded_duration": self.metrics.queue_depth_exceeded_duration,
                "guardian_restarts": self.metrics.guardian_restarts,
                "rps": self.metrics.total_requests/total_time
            }
        }

async def main():
    drill = QueueDepthDrill()
    
    # Run with 500 VU for 2 minutes as requested
    result = await drill.run_drill(num_users=500, duration_seconds=120)
    
    print(f"\n🏆 Final Result: {'PASS' if result['passed'] else 'FAIL'}")
    
    # Save results
    with open("queue_depth_drill_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"📄 Results saved to: queue_depth_drill_results.json")
    
    return result

if __name__ == "__main__":
    asyncio.run(main()) 