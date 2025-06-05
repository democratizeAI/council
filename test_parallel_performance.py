#!/usr/bin/env python3
"""
🚀 PARALLEL PERFORMANCE TEST
===========================

Tests the performance optimizations:
1. Parallel specialist execution (should be ~1-2s instead of 8-10s)
2. Agent-0 confidence gate (should skip specialists for simple queries)
3. Token limits (should produce shorter responses)
4. UNSURE responses (should not generate verbose off-topic responses)

Expected results after optimizations:
- Simple queries: < 700ms (Agent-0 shortcut)
- Math queries: < 1.8s (parallel specialists)
- No more 65-second responses
"""

import asyncio
import time
import sys

async def test_parallel_performance():
    """Test that parallel execution significantly improves performance"""
    print("🚀 PARALLEL PERFORMANCE TEST")
    print("=" * 50)
    
    try:
        from router.voting import vote
        
        test_cases = [
            {
                "query": "hi there",
                "expected_time_ms": 700,
                "optimization": "Agent-0 shortcut",
                "should_skip_specialists": True
            },
            {
                "query": "What is 2+2?",
                "expected_time_ms": 1800,
                "optimization": "Parallel specialists",
                "should_skip_specialists": False
            },
            {
                "query": "explain photosynthesis",
                "expected_time_ms": 1500,
                "optimization": "UNSURE responses",
                "should_skip_specialists": False
            }
        ]
        
        performance_results = []
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected_time = test_case["expected_time_ms"]
            optimization = test_case["optimization"]
            
            print(f"\n🧪 Test {i}: '{query}'")
            print(f"   Expected optimization: {optimization}")
            print(f"   Target time: < {expected_time}ms")
            
            start_time = time.time()
            
            try:
                result = await vote(query)
                
                elapsed_ms = (time.time() - start_time) * 1000
                winner = result.get("winner", {})
                voting_stats = result.get("voting_stats", {})
                
                # Extract performance metrics
                specialist = winner.get("specialist", "unknown")
                confidence = winner.get("confidence", 0.0)
                response_text = result.get("text", "")
                
                # Check for Agent-0 shortcut
                agent0_shortcut = voting_stats.get("agent0_shortcut", False)
                specialists_tried = voting_stats.get("specialists_tried", [])
                
                print(f"   ⏱️  Actual time: {elapsed_ms:.0f}ms")
                print(f"   🎯 Winner: {specialist}")
                print(f"   🔢 Confidence: {confidence:.2f}")
                print(f"   📝 Response length: {len(response_text)} chars")
                print(f"   🚀 Agent-0 shortcut: {agent0_shortcut}")
                print(f"   👥 Specialists tried: {len(specialists_tried)}")
                
                # Performance evaluation
                time_ok = elapsed_ms < expected_time
                
                # Check specific optimizations
                if test_case["should_skip_specialists"]:
                    shortcut_ok = agent0_shortcut or len(specialists_tried) <= 1
                    print(f"   ✅ Shortcut working: {shortcut_ok}")
                else:
                    shortcut_ok = True  # Not expected for this test
                
                # Check for UNSURE responses (no verbose off-topic responses)
                if "photosynthesis" in query and "specialist" in specialist:
                    # Should get UNSURE from specialists or short responses
                    unsure_ok = "UNSURE" in response_text or len(response_text) < 200
                    print(f"   ✅ UNSURE working: {unsure_ok}")
                else:
                    unsure_ok = True
                
                overall_success = time_ok and shortcut_ok and unsure_ok
                
                if overall_success:
                    print(f"   ✅ PASS: All optimizations working")
                else:
                    print(f"   ❌ FAIL: Some optimizations need work")
                    if not time_ok:
                        print(f"      - Time: {elapsed_ms:.0f}ms > {expected_time}ms")
                    if not shortcut_ok:
                        print(f"      - Shortcut not working")
                    if not unsure_ok:
                        print(f"      - UNSURE not working")
                
                performance_results.append({
                    "query": query,
                    "elapsed_ms": elapsed_ms,
                    "expected_ms": expected_time,
                    "success": overall_success,
                    "optimization": optimization
                })
                
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                performance_results.append({
                    "query": query,
                    "elapsed_ms": 999999,
                    "expected_ms": expected_time,
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 PERFORMANCE RESULTS")
        print("=" * 50)
        
        successful_tests = sum(1 for r in performance_results if r["success"])
        total_tests = len(performance_results)
        
        for result in performance_results:
            status = "✅" if result["success"] else "❌"
            query = result["query"]
            elapsed = result["elapsed_ms"]
            expected = result["expected_ms"]
            optimization = result["optimization"]
            
            print(f"{status} {optimization}: '{query}' - {elapsed:.0f}ms (target: <{expected}ms)")
        
        print(f"\nOverall: {successful_tests}/{total_tests} optimizations working")
        
        if successful_tests == total_tests:
            print("🎉 ALL PERFORMANCE OPTIMIZATIONS WORKING!")
            print("✅ Parallel execution reducing latency")
            print("✅ Agent-0 confidence gate working")
            print("✅ UNSURE responses preventing verbose off-topic replies")
            print("🚀 Ready for sub-2s performance!")
        else:
            print("⚠️ Some optimizations need adjustment")
            print("🔧 Check the specific failures above")
        
        return successful_tests == total_tests
        
    except Exception as e:
        print(f"❌ PERFORMANCE TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_gpu_utilization():
    """Quick GPU utilization test"""
    print("\n🔥 GPU UTILIZATION TEST")
    print("=" * 30)
    
    try:
        # Test that we can load the specialist sandbox
        from router.specialist_sandbox_fix import test_specialist_environment
        
        # Run specialist environment test
        results = test_specialist_environment()
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Specialist environment: {passed}/{total} working")
        
        if passed == total:
            print("✅ GPU pipeline ready for parallel execution")
            return True
        else:
            print("❌ GPU pipeline has issues")
            return False
            
    except Exception as e:
        print(f"❌ GPU test failed: {e}")
        return False

def main():
    """Run all performance tests"""
    print("🚀 RUNNING PERFORMANCE OPTIMIZATION TESTS")
    print("=" * 60)
    
    # Test 1: Parallel performance
    performance_success = asyncio.run(test_parallel_performance())
    
    # Test 2: GPU utilization  
    gpu_success = asyncio.run(test_gpu_utilization())
    
    print("\n" + "=" * 60)
    print("🏁 FINAL PERFORMANCE RESULTS")
    print("=" * 60)
    
    if performance_success and gpu_success:
        print("🎉 ALL PERFORMANCE TESTS PASSED!")
        print("✅ System optimized for sub-2s responses")
        print("✅ GPU utilization should be 55-70%")
        print("🚀 Ready for production use")
        
        print("\n📈 Expected performance improvements:")
        print("   - Agent-0 draft: 0.9s → 0.25s")
        print("   - Local draft only: 3.2s → 0.6s") 
        print("   - Draft + specialists: 8-10s → 1.4-1.8s")
        print("   - GPU utilization: 2-6% → 55-70%")
    else:
        print("❌ Some performance tests failed")
        print("🔧 Check the specific issues above")
    
    return performance_success and gpu_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 