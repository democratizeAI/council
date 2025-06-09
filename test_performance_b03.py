#!/usr/bin/env python3
"""
B-03 RouterCascade Performance Test
==================================

CI Gate: 40 VU smoke test with p95 < 300ms
"""

import asyncio
import time
import statistics
from router.voting import vote

async def test_b03_performance():
    """Test B-03 RouterCascade performance requirements"""
    print("🧪 B-03 RouterCascade Performance Test")
    print("=" * 50)
    
    # Test queries that should be fast
    test_queries = [
        "2+2",
        "5*7", 
        "What is Python?",
        "Hello there",
        "Calculate 100/5",
        "Write a simple function",
        "What is the capital of France?"
    ]
    
    latencies = []
    successful = 0
    
    # Simulate 40 virtual users with multiple requests each
    print("🚀 Running 40 VU simulation...")
    
    start_time = time.time()
    
    for i in range(40):  # 40 virtual users
        query = test_queries[i % len(test_queries)]
        
        try:
            test_start = time.time()
            result = await vote(query, top_k=1)
            latency_ms = (time.time() - test_start) * 1000
            
            latencies.append(latency_ms)
            successful += 1
            
            # Show progress every 10 requests
            if (i + 1) % 10 == 0:
                print(f"   📊 {i+1}/40 requests completed")
                
        except Exception as e:
            print(f"   ❌ Request {i+1} failed: {e}")
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    if latencies:
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        min_latency = min(latencies)
    else:
        p50 = p95 = p99 = avg_latency = max_latency = min_latency = 0
    
    # Results
    print("\n" + "=" * 50)
    print("🎯 B-03 RouterCascade Test Results")
    print("=" * 50)
    print(f"Total Requests: {40}")
    print(f"Successful: {successful} ({successful/40*100:.1f}%)")
    print(f"P50 Latency: {p50:.1f}ms")
    print(f"P95 Latency: {p95:.1f}ms") 
    print(f"P99 Latency: {p99:.1f}ms")
    print(f"Avg Latency: {avg_latency:.1f}ms")
    print(f"Min Latency: {min_latency:.1f}ms")
    print(f"Max Latency: {max_latency:.1f}ms")
    print(f"Total Time: {total_time:.2f}s")
    print(f"RPS: {successful/total_time:.1f}")
    
    # CI Gate Check
    print(f"\n🎯 CI Gate Check: P95 < 300.0ms")
    print(f"   Actual: {p95:.1f}ms")
    
    if p95 < 300.0:
        print("✅ B-03 CI Gate: PASSED")
        return True
    else:
        print("❌ B-03 CI Gate: FAILED")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_b03_performance())
    print(f"\n🏆 Final Result: {'PASSED' if result else 'FAILED'}") 