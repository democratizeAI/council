#!/usr/bin/env python3
"""
Test Cascading Knowledge Fix
=============================

Tests the complete fix for:
1. Greeting filter (stops specialists from greeting)  
2. Cascading knowledge (digest writing and reading)
3. Progressive reasoning (specialists see Agent-0 draft)
"""

import asyncio
import time
import requests
import json

BASE_URL = "http://localhost:8080"

def test_simple_greeting():
    """Test 1: Simple greeting should be instant, no specialist greetings"""
    print("\n🧪 TEST 1: Simple Greeting")
    print("=" * 40)
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json={
            "prompt": "hi",
            "session_id": "test_greeting"
        }, timeout=10)
        
        latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Response: {data.get('text', '')}")
            print(f"⏱️ Latency: {latency:.0f}ms")
            print(f"🔍 Status: {data.get('status', 'unknown')}")
            
            # Check if greeting was handled correctly
            if latency < 100 and "Hi!" in data.get('text', ''):
                print("✅ PASS: Fast greeting response")
                return True
            else:
                print(f"❌ FAIL: Expected fast greeting, got {latency:.0f}ms")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_math_no_greeting():
    """Test 2: Math query should NOT get greeting from math specialist"""
    print("\n🧪 TEST 2: Math Query (No Specialist Greeting)")
    print("=" * 50)
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json={
            "prompt": "What is 15 * 7?",
            "session_id": "test_math"
        }, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('text', '')
            print(f"✅ Response: {text}")
            
            # Check for greeting patterns (should NOT be present)
            greeting_patterns = ["Hi!", "Hello!", "Hey!", "How can I help"]
            has_greeting = any(pattern in text for pattern in greeting_patterns)
            
            if has_greeting:
                print("❌ FAIL: Math specialist returned greeting!")
                print(f"   Response contained: {text}")
                return False
            else:
                print("✅ PASS: No greeting from specialist")
                # Check if answer is correct
                if "105" in text:
                    print("✅ PASS: Correct math answer")
                    return True
                else:
                    print(f"⚠️ Math answer may be incorrect: {text}")
                    return True  # Still pass if no greeting
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_cascading_knowledge():
    """Test 3: Multiple conversation turns should build context"""
    print("\n🧪 TEST 3: Cascading Knowledge")
    print("=" * 40)
    
    session_id = "test_cascading"
    
    try:
        # Turn 1: Establish context
        print("Turn 1: Setting context...")
        response1 = requests.post(f"{BASE_URL}/chat", json={
            "prompt": "My bike is turquoise.",
            "session_id": session_id
        }, timeout=10)
        
        if response1.status_code == 200:
            print(f"✅ Turn 1 response: {response1.json().get('text', '')}")
        else:
            print(f"❌ Turn 1 failed: {response1.status_code}")
            return False
        
        # Small delay to ensure digest is written
        time.sleep(1)
        
        # Turn 2: Query the established context
        print("\nTurn 2: Querying context...")
        response2 = requests.post(f"{BASE_URL}/chat", json={
            "prompt": "What colour is my bike?",
            "session_id": session_id
        }, timeout=10)
        
        if response2.status_code == 200:
            text2 = response2.json().get('text', '')
            print(f"✅ Turn 2 response: {text2}")
            
            # Check if context was preserved
            if "turquoise" in text2.lower():
                print("✅ PASS: Context preserved across turns")
                return True
            else:
                print("⚠️ Context may not have been preserved")
                print(f"   Expected 'turquoise' in: {text2}")
                return False
        else:
            print(f"❌ Turn 2 failed: {response2.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_math_with_context():
    """Test 4: Math specialist should see context"""
    print("\n🧪 TEST 4: Progressive Reasoning")
    print("=" * 40)
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json={
            "prompt": "Factor x^2-5x+6",
            "session_id": "test_progressive"
        }, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('text', '')
            print(f"✅ Response: {text}")
            
            # Check for math solution
            if "x-2" in text and "x-3" in text:
                print("✅ PASS: Correct factorization")
                return True
            elif "UNSURE" in text:
                print("⚠️ Math specialist returned UNSURE")
                return False
            else:
                print(f"⚠️ Unexpected math response: {text}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def run_all_tests():
    """Run all test cases"""
    print("🚀 CASCADING KNOWLEDGE & GREETING FIX TESTS")
    print("=" * 50)
    
    tests = [
        ("Simple Greeting", test_simple_greeting),
        ("Math No Greeting", test_math_no_greeting),
        ("Cascading Knowledge", test_cascading_knowledge),
        ("Progressive Reasoning", test_math_with_context),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
        
        # Pause between tests
        time.sleep(2)
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 30)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Greeting filter working")
        print("✅ Cascading knowledge working")
        print("✅ Progressive reasoning working")
    else:
        print("⚠️ Some tests failed - check logs")
    
    return passed == total

if __name__ == "__main__":
    print("Starting test suite...")
    print("Make sure the server is running on http://localhost:8080")
    
    # Check if server is running (try simple GET first)
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️ Server responded with {response.status_code}, trying anyway...")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please start the server first")
        exit(1)
    
    # Run tests
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1) 