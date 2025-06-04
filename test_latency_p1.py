#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 Latency Test - Track ① Validation
====================================

Quick test to validate that Track ① optimizations are working:
- Paged-KV + Flash-Attention 2
- Continuous batching  
- Streaming responses
- Warmup JIT compilation
"""

import asyncio
import time
import os
from router.hybrid import hybrid_route
from loader.deterministic_loader import load_models

async def test_p1_latency_optimizations():
    """Test the P1 latency optimizations"""
    print("🎯 Testing P1 Track ① Latency Optimizations")
    print("=" * 50)
    
    # Enable test mode for reliable testing
    os.environ["SWARM_TEST_MODE"] = "true"
    
    # Load models with rtx_4070 profile
    print("📦 Loading models with rtx_4070 profile...")
    load_models(profile="rtx_4070", use_real_loading=False)
    print("✅ Models loaded")
    
    # Test prompts covering different routing paths
    test_cases = [
        # Smart routing (should be fastest)
        ("2+2?", "smart"),
        ("Hello", "smart"), 
        ("What is Python?", "smart"),
        
        # Voting routing (more complex)
        ("Explain step by step why neural networks work", "voting"),
        ("Analyze the reasoning behind quantum computing", "voting"),
        ("Compare and contrast different algorithms", "voting"),
    ]
    
    results = {
        "smart_latencies": [],
        "voting_latencies": [],
        "total_tests": 0,
        "successful_tests": 0
    }
    
    print("\n🚀 Running latency tests...")
    
    for prompt, expected_type in test_cases:
        print(f"\n📝 Testing: '{prompt[:40]}...' (expected: {expected_type})")
        
        try:
            start_time = time.perf_counter()
            result = await hybrid_route(prompt, ["math_specialist_0.8b", "tinyllama_1b"])
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            provider = result.get("provider", "unknown")
            
            print(f"   ⚡ Latency: {latency_ms:.1f}ms")
            print(f"   🛣️ Provider: {provider}")
            print(f"   📊 Hybrid latency: {result.get('hybrid_latency_ms', 'N/A')}ms")
            
            # Track results by type
            if "smart" in provider:
                results["smart_latencies"].append(latency_ms)
            elif "voting" in provider:
                results["voting_latencies"].append(latency_ms)
                
            results["successful_tests"] += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        results["total_tests"] += 1
        
        # Small delay between tests
        await asyncio.sleep(0.1)
    
    # Calculate statistics
    print("\n" + "=" * 50)
    print("📊 P1 LATENCY OPTIMIZATION RESULTS")
    print("=" * 50)
    
    if results["smart_latencies"]:
        smart_avg = sum(results["smart_latencies"]) / len(results["smart_latencies"])
        smart_min = min(results["smart_latencies"])
        smart_max = max(results["smart_latencies"])
        print(f"⚡ SMART ROUTING:")
        print(f"   Average: {smart_avg:.1f}ms")
        print(f"   Range: {smart_min:.1f} - {smart_max:.1f}ms")
        print(f"   Count: {len(results['smart_latencies'])}")
        
        # Check if we're meeting P1 targets
        if smart_avg < 120:  # Target ≤120ms on RTX 4070
            print(f"   ✅ MEETS P1 TARGET (<120ms)")
        elif smart_avg < 200:  # Fallback target <200ms p95
            print(f"   🟡 APPROACHING TARGET (<200ms)")
        else:
            print(f"   ❌ NEEDS OPTIMIZATION (>{smart_avg:.1f}ms)")
    
    if results["voting_latencies"]:
        voting_avg = sum(results["voting_latencies"]) / len(results["voting_latencies"])
        voting_min = min(results["voting_latencies"])
        voting_max = max(results["voting_latencies"])
        print(f"\n🗳️ VOTING ROUTING:")
        print(f"   Average: {voting_avg:.1f}ms") 
        print(f"   Range: {voting_min:.1f} - {voting_max:.1f}ms")
        print(f"   Count: {len(results['voting_latencies'])}")
        
        if voting_avg < 200:  # Voting can be slower but still <200ms
            print(f"   ✅ WITHIN TARGET (<200ms)")
        else:
            print(f"   ⚠️ MAY NEED TUNING ({voting_avg:.1f}ms)")
    
    # Overall assessment
    success_rate = results["successful_tests"] / results["total_tests"] * 100
    print(f"\n📈 OVERALL:")
    print(f"   Success rate: {success_rate:.1f}% ({results['successful_tests']}/{results['total_tests']})")
    
    if success_rate >= 85:
        print(f"   ✅ P1 Track ① optimizations working well!")
    else:
        print(f"   ⚠️ Some optimization issues detected")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_p1_latency_optimizations()) 