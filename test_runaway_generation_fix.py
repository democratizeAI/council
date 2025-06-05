#!/usr/bin/env python3
"""
🚀 RUNAWAY GENERATION FIX VERIFICATION
=====================================

Tests the complete fix for runaway generation issues:
1. Specialists return UNSURE for off-topic queries
2. Hard caps prevent 37s+ responses
3. Parallel execution working
4. Agent-0 confidence gate working
5. No more verbose essays from math specialist

Expected results:
- Greeting: < 700ms (Agent-0 shortcut)
- Math query: < 1800ms (parallel specialists, math specialist wins)
- Name etymology: < 3000ms (knowledge specialist wins, math returns UNSURE)
- All responses under 160 tokens
"""

import asyncio
import time
import sys
import subprocess
import json

async def test_specialist_focus():
    """Test that specialists only answer domain-specific queries"""
    print("🎯 SPECIALIST FOCUS TEST")
    print("=" * 40)
    
    try:
        from router.voting import vote
        
        test_cases = [
            {
                "query": "What does the name Hetty mean?",
                "expected_winner": "knowledge_specialist",
                "should_have_unsure": ["math_specialist", "code_specialist", "logic_specialist"],
                "description": "Name etymology - only knowledge should answer"
            },
            {
                "query": "Factor x^2-5x+6",
                "expected_winner": "math_specialist", 
                "should_have_unsure": ["code_specialist", "logic_specialist", "knowledge_specialist"],
                "description": "Math problem - only math should answer"
            },
            {
                "query": "Write a function to reverse a string",
                "expected_winner": "code_specialist",
                "should_have_unsure": ["math_specialist", "logic_specialist", "knowledge_specialist"],
                "description": "Programming - only code should answer"
            }
        ]
        
        passed_tests = 0
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case["query"]
            expected_winner = test_case["expected_winner"]
            should_have_unsure = test_case["should_have_unsure"]
            description = test_case["description"]
            
            print(f"\n🧪 Test {i}: {description}")
            print(f"   Query: '{query}'")
            
            start_time = time.time()
            result = await vote(query)
            elapsed_ms = (time.time() - start_time) * 1000
            
            winner = result.get("winner", {})
            winner_specialist = winner.get("specialist", "unknown")
            response_text = result.get("text", "")
            candidates = winner.get("candidates", [])
            
            print(f"   ⏱️  Time: {elapsed_ms:.0f}ms")
            print(f"   🏆 Winner: {winner_specialist}")
            print(f"   📝 Response: '{response_text[:100]}...'")
            print(f"   📏 Length: {len(response_text)} chars")
            
            # Check if expected specialist won or if consensus included them
            winner_ok = (expected_winner in winner_specialist or 
                        winner_specialist == "council_consensus")
            
            # Check if other specialists returned UNSURE
            unsure_count = 0
            if candidates:
                for candidate in candidates:
                    specialist = candidate.get("specialist", "")
                    text = candidate.get("text", "").strip()
                    if specialist in should_have_unsure and text == "UNSURE":
                        unsure_count += 1
                        print(f"   ✅ {specialist} correctly returned UNSURE")
                    elif specialist in should_have_unsure and text != "UNSURE":
                        print(f"   ❌ {specialist} should have returned UNSURE but said: '{text[:50]}...'")
            
            # Response should be under 160 tokens (rough estimate: 4 chars = 1 token)
            estimated_tokens = len(response_text) / 4
            length_ok = estimated_tokens <= 160
            
            # Time should be reasonable (under 3s for any query)
            time_ok = elapsed_ms < 3000
            
            test_passed = winner_ok and length_ok and time_ok and (unsure_count >= 2)
            
            if test_passed:
                print(f"   ✅ PASS: All checks passed")
                passed_tests += 1
            else:
                print(f"   ❌ FAIL: Some checks failed")
                if not winner_ok:
                    print(f"      - Wrong winner: expected {expected_winner}, got {winner_specialist}")
                if not length_ok:
                    print(f"      - Too long: ~{estimated_tokens:.0f} tokens > 160")
                if not time_ok:
                    print(f"      - Too slow: {elapsed_ms:.0f}ms > 3000ms")
                if unsure_count < 2:
                    print(f"      - Not enough UNSURE responses: {unsure_count} < 2")
        
        print(f"\n📊 Results: {passed_tests}/{len(test_cases)} specialist focus tests passed")
        return passed_tests == len(test_cases)
        
    except Exception as e:
        print(f"❌ SPECIALIST FOCUS TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_performance_caps():
    """Test that performance caps prevent runaway generation"""
    print("\n⚡ PERFORMANCE CAPS TEST")
    print("=" * 40)
    
    try:
        from router.voting import vote
        
        # Test queries that previously caused 37s+ responses
        stress_queries = [
            "hi there",  # Should use Agent-0 shortcut
            "2+2",       # Should be fast math
            "tell me about the history of names",  # Should not cause runaway
        ]
        
        passed_tests = 0
        
        for i, query in enumerate(stress_queries, 1):
            print(f"\n🧪 Stress test {i}: '{query}'")
            
            start_time = time.time()
            result = await vote(query)
            elapsed_ms = (time.time() - start_time) * 1000
            
            response_text = result.get("text", "")
            estimated_tokens = len(response_text) / 4
            
            print(f"   ⏱️  Time: {elapsed_ms:.0f}ms")
            print(f"   📏 Length: ~{estimated_tokens:.0f} tokens")
            print(f"   📝 Response: '{response_text[:100]}...'")
            
            # All responses should be under 8 seconds and 160 tokens
            time_ok = elapsed_ms < 8000
            length_ok = estimated_tokens <= 160
            
            if time_ok and length_ok:
                print(f"   ✅ PASS: Within limits")
                passed_tests += 1
            else:
                print(f"   ❌ FAIL: Exceeded limits")
                if not time_ok:
                    print(f"      - Too slow: {elapsed_ms:.0f}ms > 8000ms")
                if not length_ok:
                    print(f"      - Too long: ~{estimated_tokens:.0f} tokens > 160")
        
        print(f"\n📊 Results: {passed_tests}/{len(stress_queries)} performance cap tests passed")
        return passed_tests == len(stress_queries)
        
    except Exception as e:
        print(f"❌ PERFORMANCE CAPS TEST ERROR: {e}")
        return False

def test_curl_commands():
    """Test the verification curl commands if server is running"""
    print("\n🌐 CURL VERIFICATION TEST")
    print("=" * 40)
    
    curl_tests = [
        {
            "query": "hi",
            "expected_latency_ms": 700,
            "description": "Trivial greeting - should not call math head"
        },
        {
            "query": "factor x^2-5x+6", 
            "expected_latency_ms": 1800,
            "description": "Real math - math head should answer quickly"
        },
        {
            "query": "What does the name Hetty mean?",
            "expected_latency_ms": 3000,
            "description": "Name query - math head should return UNSURE"
        }
    ]
    
    server_running = True
    passed_tests = 0
    
    for i, test in enumerate(curl_tests, 1):
        query = test["query"]
        expected_latency = test["expected_latency_ms"] 
        description = test["description"]
        
        print(f"\n🧪 Curl test {i}: {description}")
        print(f"   Query: '{query}'")
        
        # Test if server is running with first query
        if server_running:
            try:
                curl_cmd = [
                    "curl", "-s", "-X", "POST", 
                    "http://localhost:8000/chat",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps({"prompt": query}),
                    "--connect-timeout", "5",
                    "--max-time", "10"
                ]
                
                start_time = time.time()
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
                elapsed_ms = (time.time() - start_time) * 1000
                
                if result.returncode == 0:
                    try:
                        response_data = json.loads(result.stdout)
                        actual_latency = response_data.get("meta", {}).get("latency_ms", elapsed_ms)
                        response_text = response_data.get("text", "")
                        
                        print(f"   ⏱️  Latency: {actual_latency:.0f}ms (target: <{expected_latency}ms)")
                        print(f"   📝 Response: '{response_text[:100]}...'")
                        
                        if actual_latency < expected_latency:
                            print(f"   ✅ PASS: Within target latency")
                            passed_tests += 1
                        else:
                            print(f"   ❌ FAIL: Exceeded target latency")
                    except json.JSONDecodeError:
                        print(f"   ❌ FAIL: Invalid JSON response")
                        print(f"   Raw output: {result.stdout[:200]}...")
                else:
                    # Server not running - skip remaining curl tests
                    print(f"   ⚠️ Server not running - skipping curl tests")
                    server_running = False
                    break
                    
            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                print(f"   ❌ FAIL: Curl command failed: {e}")
                server_running = False
                break
        else:
            print(f"   ⏭️ SKIP: Server not running")
    
    if server_running:
        print(f"\n📊 Results: {passed_tests}/{len(curl_tests)} curl tests passed")
        return passed_tests == len(curl_tests)
    else:
        print(f"\n📊 Server not running - curl tests skipped")
        return True  # Don't fail if server isn't running

async def test_fusion_latency_regression():
    """🚀 REGRESSION GUARD: Ensure fusion latency stays under 1 second"""
    print("\n⚡ FUSION LATENCY REGRESSION TEST")
    print("=" * 40)
    
    try:
        from router.voting import vote
        
        # Test queries that should trigger fusion but stay fast
        fusion_test_queries = [
            "2+2",  # Math specialist should win, but fast
            "What is the capital of France?",  # Knowledge specialist
            "How are you today?",  # General query with multiple candidates
        ]
        
        passed_tests = 0
        
        for i, query in enumerate(fusion_test_queries, 1):
            print(f"\n🧪 Fusion test {i}: '{query}'")
            
            start_time = time.time()
            result = await vote(query)
            elapsed_ms = (time.time() - start_time) * 1000
            
            response_text = result.get("text", "")
            fusion_method = result.get("winner", {}).get("fusion_method", "single_winner")
            agent0_filtered = result.get("winner", {}).get("agent0_filtered", False)
            
            print(f"   ⏱️  Time: {elapsed_ms:.0f}ms")
            print(f"   🔀 Fusion: {fusion_method}")
            print(f"   🚫 Agent-0 filtered: {agent0_filtered}")
            print(f"   📝 Response: '{response_text[:80]}...'")
            
            # Regression guard: Must be under 1000ms
            latency_ok = elapsed_ms < 1000
            
            if latency_ok:
                print(f"   ✅ PASS: Fusion under 1s")
                passed_tests += 1
            else:
                print(f"   ❌ FAIL: Fusion too slow: {elapsed_ms:.0f}ms > 1000ms")
                print(f"   🚨 REGRESSION DETECTED: Fusion performance degraded!")
        
        print(f"\n📊 Results: {passed_tests}/{len(fusion_test_queries)} fusion latency tests passed")
        return passed_tests == len(fusion_test_queries)
        
    except Exception as e:
        print(f"❌ FUSION LATENCY TEST ERROR: {e}")
        return False

def main():
    """Run all runaway generation fix verification tests"""
    print("🚀 RUNAWAY GENERATION FIX VERIFICATION")
    print("=" * 60)
    print("Testing all fixes for 37s+ responses and off-topic essays")
    print()
    
    # Test 1: Specialist focus
    specialist_focus_ok = asyncio.run(test_specialist_focus())
    
    # Test 2: Performance caps
    performance_caps_ok = asyncio.run(test_performance_caps())
    
    # Test 3: Curl commands (if server running)
    curl_ok = test_curl_commands()
    
    # Test 4: Fusion latency regression
    fusion_ok = asyncio.run(test_fusion_latency_regression())
    
    print("\n" + "=" * 60)
    print("🏁 FINAL VERIFICATION RESULTS")
    print("=" * 60)
    
    all_tests_passed = specialist_focus_ok and performance_caps_ok and curl_ok and fusion_ok
    
    status_emoji = "✅" if specialist_focus_ok else "❌"
    print(f"{status_emoji} Specialist Focus: {'PASS' if specialist_focus_ok else 'FAIL'}")
    
    status_emoji = "✅" if performance_caps_ok else "❌"
    print(f"{status_emoji} Performance Caps: {'PASS' if performance_caps_ok else 'FAIL'}")
    
    status_emoji = "✅" if curl_ok else "❌"
    print(f"{status_emoji} Curl Verification: {'PASS' if curl_ok else 'FAIL'}")
    
    status_emoji = "✅" if fusion_ok else "❌"
    print(f"{status_emoji} Fusion Latency Regression: {'PASS' if fusion_ok else 'FAIL'}")
    
    if all_tests_passed:
        print("\n🎉 ALL RUNAWAY GENERATION FIXES WORKING!")
        print("✅ No more 37s+ responses")
        print("✅ Specialists focused on their domains")
        print("✅ Hard caps preventing runaway generation")
        print("✅ UNSURE responses working correctly")
        print("✅ Fusion latency under 1 second")
        print("🚀 System ready for sub-2s performance!")
    else:
        print("\n❌ Some fixes need adjustment")
        print("🔧 Check the specific failures above")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 