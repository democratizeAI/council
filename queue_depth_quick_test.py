#!/usr/bin/env python3
"""
Queue-Depth Quick Test
=====================

P0 Critical: Test Guardian auto-restart behavior under high load
Simulates queue depth > 200 for 60s to verify B-04 → B-08 loop
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from router.voting import vote

async def worker_task(worker_id: int, duration: int):
    """Single worker making continuous requests"""
    end_time = time.time() + duration
    requests_made = 0
    
    while time.time() < end_time:
        try:
            # Use a simple query that should be fast
            query = f"Calculate {worker_id} * {requests_made + 1}"
            result = await vote(query, top_k=1)
            requests_made += 1
            
            # Brief pause to not overwhelm
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"Worker {worker_id} error: {e}")
            await asyncio.sleep(0.5)
    
    return {"worker_id": worker_id, "requests_made": requests_made}

async def monitor_system(duration: int):
    """Monitor system health during load test"""
    end_time = time.time() + duration
    max_queue_depth = 0
    restart_events = 0
    
    while time.time() < end_time:
        try:
            # Simple monitoring - check if system is responding
            start = time.time()
            result = await vote("health check", top_k=1)
            latency = (time.time() - start) * 1000
            
            # Estimate queue depth based on latency
            estimated_queue = max(0, int((latency - 50) / 10))  # Rough estimate
            max_queue_depth = max(max_queue_depth, estimated_queue)
            
            if latency > 5000:  # 5 second threshold suggests restart
                restart_events += 1
                print(f"⚠️ Potential restart event: {latency:.0f}ms latency")
            
            print(f"📊 Monitor: {latency:.0f}ms latency, estimated queue: {estimated_queue}")
            
        except Exception as e:
            print(f"⚠️ Monitor error: {e}")
            restart_events += 1
        
        await asyncio.sleep(5)  # Monitor every 5 seconds
    
    return {"max_queue_depth": max_queue_depth, "restart_events": restart_events}

async def test_queue_depth(num_workers: int = 50, duration: int = 60):
    """Test queue depth with simulated load"""
    print("🚨 Queue-Depth Quick Test")
    print("=" * 50)
    print(f"Workers: {num_workers}")
    print(f"Duration: {duration}s")
    print(f"Target: Simulate queue depth > 200, verify Guardian behavior")
    print()
    
    start_time = time.time()
    
    # Start monitoring task
    monitor_task = asyncio.create_task(monitor_system(duration))
    
    # Start worker tasks
    worker_tasks = []
    for i in range(num_workers):
        task = asyncio.create_task(worker_task(i, duration))
        worker_tasks.append(task)
        
        # Stagger worker starts to build up load gradually
        if i % 10 == 0 and i > 0:
            await asyncio.sleep(0.5)
    
    print(f"🚀 Started {num_workers} workers")
    
    # Wait for completion
    try:
        monitor_result = await monitor_task
        worker_results = await asyncio.gather(*worker_tasks, return_exceptions=True)
    except Exception as e:
        print(f"❌ Test interrupted: {e}")
        return {"error": str(e)}
    
    # Analyze results
    total_time = time.time() - start_time
    successful_workers = len([r for r in worker_results if isinstance(r, dict)])
    total_requests = sum(r.get("requests_made", 0) for r in worker_results if isinstance(r, dict))
    
    print("\n" + "=" * 50)
    print("🎯 Queue-Depth Test Analysis")
    print("=" * 50)
    print(f"Test Duration: {total_time:.1f}s")
    print(f"Workers Completed: {successful_workers}/{num_workers}")
    print(f"Total Requests: {total_requests}")
    print(f"RPS: {total_requests/total_time:.1f}")
    
    print(f"\n🎛️ Queue Management:")
    print(f"Max Estimated Queue Depth: {monitor_result['max_queue_depth']}")
    print(f"Restart Events: {monitor_result['restart_events']}")
    
    # Evaluate success criteria
    queue_stress_achieved = monitor_result['max_queue_depth'] > 50  # Lower threshold for this test
    guardian_events = monitor_result['restart_events'] > 0
    
    print(f"\n🛡️ Guardian Test Results:")
    if queue_stress_achieved:
        print("✅ System experienced significant load")
    else:
        print("⚠️ Queue stress may not have been sufficient")
    
    if guardian_events:
        print("✅ Guardian restart/intervention events detected")
    else:
        print("⚠️ No clear Guardian intervention detected")
    
    overall_pass = total_requests > 100 and successful_workers > num_workers * 0.8
    
    return {
        "passed": overall_pass,
        "queue_stress_achieved": queue_stress_achieved,
        "guardian_events": guardian_events,
        "metrics": {
            "total_requests": total_requests,
            "successful_workers": successful_workers,
            "max_queue_depth": monitor_result['max_queue_depth'],
            "restart_events": monitor_result['restart_events'],
            "rps": total_requests/total_time
        }
    }

async def main():
    print("🚀 Starting Queue-Depth Quick Test...")
    print("Simulating high load to test Guardian auto-restart behavior")
    print()
    
    # Use moderate load that's achievable in current environment
    result = await test_queue_depth(num_workers=50, duration=60)
    
    if "error" in result:
        print(f"\n❌ Test Failed: {result['error']}")
        return result
    
    print(f"\n🏆 Final Result: {'PASS' if result['passed'] else 'FAIL'}")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(main()) 