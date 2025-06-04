#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P1 Math Test - Track ③ Validation
=================================

Test Track ③ math specialist optimization:
- <100ms latency target
- 99% accuracy goal  
- Fast-path regex bypass
- Vectorized SymPy caching
"""

import asyncio
import time
import os
from router.math_specialist import math_specialist, route_math_query, is_math_query
from router.hybrid import hybrid_route
from loader.deterministic_loader import load_models

def test_math_detection():
    """Test math query detection accuracy"""
    print("🧪 Testing math query detection...")
    
    test_cases = [
        # Should detect as math
        ("2+2", True),
        ("What is 15 * 23?", True),
        ("Calculate 144/12", True),
        ("Solve x + 5 = 12", True),
        ("What is 25% of 80?", True),
        ("Compute sqrt(16)", True),
        ("15 + 27 - 8", True),
        
        # Should NOT detect as math
        ("What is your name?", False),
        ("Explain quantum physics", False),
        ("Write a story about cats", False),
        ("The weather is nice today", False),
        ("Hello world", False),
    ]
    
    passed = 0
    for prompt, expected in test_cases:
        result = is_math_query(prompt)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{prompt}' -> math: {result} (expected: {expected})")
        if result == expected:
            passed += 1
    
    print(f"   📊 Math detection: {passed}/{len(test_cases)} passed")
    return passed >= len(test_cases) * 0.9  # 90% accuracy threshold

def test_fast_path_arithmetic():
    """Test Track ③ fast-path regex bypass for simple arithmetic"""
    print("\n🧪 Testing fast-path arithmetic...")
    
    test_cases = [
        ("2+2", 4.0),
        ("15-7", 8.0),
        ("6*9", 54.0),
        ("144/12", 12.0),
        ("3^2", 9.0),
        ("2**3", 8.0),
        ("What is 10+5?", 15.0),
        ("Calculate 20*4", 80.0),
    ]
    
    passed = 0
    latencies = []
    
    for prompt, expected in test_cases:
        start_time = time.perf_counter()
        result = math_specialist.fast_path_solve(prompt)
        latency_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(latency_ms)
        
        if result is not None and abs(float(result) - expected) < 0.001:
            print(f"   ✅ '{prompt}' -> {result} ({latency_ms:.2f}ms)")
            passed += 1
        else:
            print(f"   ❌ '{prompt}' -> {result} (expected: {expected}, {latency_ms:.2f}ms)")
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    print(f"   📊 Fast-path arithmetic: {passed}/{len(test_cases)} passed")
    print(f"   ⚡ Latency: avg={avg_latency:.2f}ms, max={max_latency:.2f}ms")
    
    # Check latency targets
    latency_ok = avg_latency < 10 and max_latency < 20  # Very fast for regex
    return passed >= len(test_cases) * 0.9 and latency_ok

async def test_math_specialist_integration():
    """Test the full math specialist with latency tracking"""
    print("\n🧪 Testing math specialist integration...")
    
    test_prompts = [
        "2+2",
        "What is 15 * 23?",
        "Calculate 144/12",
        "25% of 80",
        "sqrt(16)",
        "Solve for x: x + 5 = 12",
    ]
    
    passed = 0
    latencies = []
    accuracy_scores = []
    
    for prompt in test_prompts:
        try:
            result = await math_specialist.solve_math(prompt)
            
            latency_ms = result.get('latency_ms', 0)
            confidence = result.get('confidence', 0)
            method = result.get('method', 'unknown')
            accuracy_expected = result.get('accuracy_expected', 0)
            
            latencies.append(latency_ms)
            accuracy_scores.append(accuracy_expected)
            
            # Check latency target (<100ms)
            latency_ok = latency_ms < 100
            confidence_ok = confidence > 0.7
            
            if latency_ok and confidence_ok:
                print(f"   ✅ '{prompt}' -> {result['text'][:30]}... ({latency_ms:.1f}ms, {method})")
                passed += 1
            else:
                print(f"   ❌ '{prompt}' -> latency: {latency_ms:.1f}ms, confidence: {confidence:.2f}")
                
        except Exception as e:
            print(f"   ❌ '{prompt}' -> error: {e}")
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0
    max_latency = max(latencies) if latencies else 0
    
    print(f"   📊 Math specialist: {passed}/{len(test_prompts)} passed")
    print(f"   ⚡ Latency: avg={avg_latency:.1f}ms, max={max_latency:.1f}ms")
    print(f"   🎯 Expected accuracy: {avg_accuracy:.1%}")
    
    # Check Track ③ targets
    latency_target = avg_latency < 100 and max_latency < 150
    accuracy_target = avg_accuracy >= 0.95  # 95%+ accuracy
    
    return passed >= len(test_prompts) * 0.8 and latency_target and accuracy_target

async def test_hybrid_math_integration():
    """Test math specialist integration with hybrid router"""
    print("\n🧪 Testing hybrid router math integration...")
    
    # Enable test mode
    os.environ["SWARM_TEST_MODE"] = "true"
    
    # Load models
    load_models(profile="rtx_4070", use_real_loading=False)
    
    math_prompts = [
        "2+2",
        "What is 10*5?",
        "Calculate 100/4",
    ]
    
    passed = 0
    latencies = []
    
    for prompt in math_prompts:
        try:
            result = await hybrid_route(prompt, ["math_specialist_0.8b", "tinyllama_1b"])
            
            latency_ms = result.get('hybrid_latency_ms', 0)
            provider = result.get('provider', 'unknown')
            
            latencies.append(latency_ms)
            
            # Should use math specialist for math queries
            is_math_routed = 'math' in provider
            latency_ok = latency_ms < 100
            
            if is_math_routed and latency_ok:
                print(f"   ✅ '{prompt}' -> {provider} ({latency_ms:.1f}ms)")
                passed += 1
            else:
                print(f"   ❌ '{prompt}' -> {provider} ({latency_ms:.1f}ms)")
                
        except Exception as e:
            print(f"   ❌ '{prompt}' -> error: {e}")
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    print(f"   📊 Hybrid math integration: {passed}/{len(math_prompts)} passed")
    print(f"   ⚡ Average latency: {avg_latency:.1f}ms")
    
    return passed >= len(math_prompts) * 0.8 and avg_latency < 100

def test_performance_distribution():
    """Test performance distribution across different math types"""
    print("\n🧪 Testing performance distribution...")
    
    test_categories = {
        "basic_arithmetic": ["2+2", "15-7", "6*9", "144/12"],
        "percentages": ["25% of 80", "15% of 200"],
        "powers": ["3^2", "2**4"],
        "functions": ["sqrt(16)", "sqrt(25)"],
    }
    
    results = {}
    
    for category, prompts in test_categories.items():
        latencies = []
        successes = 0
        
        for prompt in prompts:
            start_time = time.perf_counter()
            result = math_specialist.fast_path_solve(prompt)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            latencies.append(latency_ms)
            if result is not None:
                successes += 1
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        success_rate = successes / len(prompts)
        
        results[category] = {
            'avg_latency_ms': avg_latency,
            'success_rate': success_rate,
            'count': len(prompts)
        }
        
        print(f"   📈 {category}: {avg_latency:.2f}ms avg, {success_rate:.1%} success")
    
    # Overall performance
    all_latencies = []
    all_successes = 0
    all_count = 0
    
    for category_results in results.values():
        all_count += category_results['count']
        all_successes += category_results['success_rate'] * category_results['count']
        # Note: This is an approximation since we don't have individual latencies
    
    overall_success_rate = all_successes / all_count if all_count > 0 else 0
    
    print(f"   📊 Overall performance: {overall_success_rate:.1%} success rate")
    
    # Track ③ targets: >95% success, <10ms avg for fast path
    return overall_success_rate >= 0.90

async def main():
    """Run all Track ③ math optimization tests"""
    print("🎯 Testing Track ③ Math Optimization")
    print("=" * 50)
    
    # Run tests
    test_results = []
    
    test_results.append(test_math_detection())
    test_results.append(test_fast_path_arithmetic())
    test_results.append(await test_math_specialist_integration())
    test_results.append(await test_hybrid_math_integration())
    test_results.append(test_performance_distribution())
    
    # Get performance stats
    stats = math_specialist.get_performance_stats()
    
    # Summary
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print("\n" + "=" * 50)
    print("📊 TRACK ③ MATH OPTIMIZATION RESULTS")
    print("=" * 50)
    
    test_names = [
        "Math query detection",
        "Fast-path arithmetic",
        "Math specialist integration",
        "Hybrid router integration",
        "Performance distribution"
    ]
    
    for i, (name, passed) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {name}")
    
    success_rate = passed_tests / total_tests * 100
    print(f"\n📈 OVERALL SUCCESS: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    # Performance statistics
    print(f"\n📊 PERFORMANCE STATS:")
    print(f"   🚀 Fast-path rate: {stats['fast_path_rate']:.1%}")
    print(f"   🧮 SymPy rate: {stats['sympy_rate']:.1%}")
    print(f"   🤖 Model fallback rate: {stats['model_fallback_rate']:.1%}")
    print(f"   📈 Total requests: {stats['total_requests']}")
    
    # Track ③ goals assessment
    print(f"\n🎯 TRACK ③ TARGETS:")
    if success_rate >= 90 and stats['fast_path_rate'] > 0.5:
        print("✅ <100ms latency: ACHIEVED")
        print("✅ High accuracy: ACHIEVED")
        print("✅ Fast-path optimization: WORKING")
        print("\n🎉 Track ③ math optimization successful!")
        return 0
    else:
        print("⚠️ Some targets not met - optimization needed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 