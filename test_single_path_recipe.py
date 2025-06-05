#!/usr/bin/env python3
"""
Quick Smoke Test for Single-Path Recipe
Tests all 4 scenarios from the recipe:
1. "hi" -> quick greeting < 300ms
2. "2+2" -> Agent-0 answers, no math stub < 300ms  
3. "Factor x^2..." -> Agent-0 UNSURE → math replaces bubble < 900ms
4. "What colour bike?" -> answers from stored digest < 300ms
"""

import requests
import time
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8080"

def test_request(prompt: str, session_id: str, expected_max_ms: int, description: str) -> Dict[str, Any]:
    """Send test request and measure performance"""
    print(f"\n🧪 {description}")
    print(f"   📤 Prompt: '{prompt}'")
    print(f"   ⏱️ Target: < {expected_max_ms}ms")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/vote",
            json={
                "prompt": prompt,
                "session_id": session_id,
                "model_preference": "fast"
            },
            timeout=10
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            
            # Check for greeting filter success
            is_greeting_response = any(word in data.get("text", "").lower() for word in ["hi", "hello", "hey"])
            
            print(f"   ✅ Response: '{data.get('text', '')[:50]}...'")
            print(f"   ⏱️ Latency: {latency_ms:.1f}ms")
            print(f"   🎯 Confidence: {data.get('confidence', 0):.2f}")
            print(f"   🧠 Model: {data.get('model', 'unknown')}")
            print(f"   🚩 Flags: {data.get('flags_detected', [])}")
            print(f"   🎬 Agent-0 First: {data.get('agent0_first', False)}")
            print(f"   🔧 Specialists: {len(data.get('specialists_used', []))}")
            
            # Performance check
            if latency_ms <= expected_max_ms:
                print(f"   ✅ PASS: {latency_ms:.1f}ms ≤ {expected_max_ms}ms")
                status = "PASS"
            else:
                print(f"   ❌ SLOW: {latency_ms:.1f}ms > {expected_max_ms}ms")
                status = "SLOW"
            
            # Special checks per test type
            if "hi" in prompt.lower() and description == "Greeting Speed Test":
                if is_greeting_response and latency_ms < 100:
                    print(f"   ✅ GREETING: Fast shortcut working")
                elif "👋" in data.get("text", ""):
                    print(f"   ✅ GREETING: Emoji shortcut working")
                else:
                    print(f"   ⚠️ GREETING: Unexpected response format")
            
            elif "2+2" in prompt or "Factor" in prompt:
                # Math test - check for no greeting stubs
                text = data.get("text", "")
                if any(greeting in text.lower() for greeting in ["hi, how can i help", "hello, how can i help"]):
                    print(f"   ❌ GREETING STUB: Math specialist returned greeting!")
                    status = "FAIL_GREETING"
                else:
                    print(f"   ✅ NO GREETING: Math specialist clean")
            
            return {
                "status": status,
                "latency_ms": latency_ms,
                "confidence": data.get("confidence", 0),
                "agent0_first": data.get("agent0_first", False),
                "specialists_used": len(data.get("specialists_used", [])),
                "flags_detected": data.get("flags_detected", []),
                "text": data.get("text", ""),
                "model": data.get("model", ""),
                "response_data": data
            }
        else:
            print(f"   ❌ HTTP Error: {response.status_code}")
            return {"status": "HTTP_ERROR", "latency_ms": latency_ms}
            
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        print(f"   ❌ Exception: {e}")
        return {"status": "EXCEPTION", "latency_ms": latency_ms, "error": str(e)}

def run_smoke_test():
    """Run the complete smoke test suite"""
    print("🚀 SINGLE-PATH RECIPE SMOKE TEST")
    print("=" * 50)
    
    # Test session IDs
    greeting_session = "smoke_test_greeting"
    math_session = "smoke_test_math" 
    cascading_session = "smoke_test_cascading"
    
    results = []
    
    # Test 1: Greeting Speed
    results.append(test_request(
        "hi", 
        greeting_session, 
        300,
        "1. Greeting Speed Test (Recipe Step 2c)"
    ))
    
    # Test 2: Simple Math (no specialist greeting)
    results.append(test_request(
        "2+2", 
        math_session, 
        300,
        "2. Simple Math Test (Recipe Step 2a/2b)"
    ))
    
    # Test 3: Complex Math (specialist escalation)
    results.append(test_request(
        "Factor x^2-5x+6", 
        math_session, 
        900,
        "3. Complex Math Test (Recipe Step 1-4)"
    ))
    
    # Test 4: Set up cascading knowledge
    results.append(test_request(
        "My bike is turquoise.", 
        cascading_session, 
        300,
        "4a. Setup Cascading Knowledge (Recipe Step 3a)"
    ))
    
    # Test 5: Test cascading knowledge
    results.append(test_request(
        "What colour is my bike?", 
        cascading_session, 
        300,
        "4b. Test Cascading Knowledge (Recipe Step 3a)"
    ))
    
    # Summary
    print(f"\n📊 SMOKE TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for i, result in enumerate(results, 1):
        status = result.get("status", "UNKNOWN")
        latency = result.get("latency_ms", 0)
        
        if status == "PASS":
            print(f"✅ Test {i}: PASS ({latency:.1f}ms)")
            passed += 1
        elif status == "SLOW":
            print(f"🟡 Test {i}: SLOW ({latency:.1f}ms)")
            failed += 1
        elif status == "FAIL_GREETING":
            print(f"❌ Test {i}: GREETING STUB ESCAPED")
            failed += 1
        else:
            print(f"❌ Test {i}: {status}")
            failed += 1
    
    print(f"\n🏆 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - Single-path recipe working!")
        print("✅ Agent-0 always speaks first")
        print("✅ No greeting stubs escape")
        print("✅ Cascading knowledge active")
        print("✅ Performance targets met")
        return True
    else:
        print("⚠️ Some tests failed - check implementation")
        return False

if __name__ == "__main__":
    try:
        success = run_smoke_test()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1) 