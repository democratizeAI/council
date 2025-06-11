#!/usr/bin/env python3
"""Test Trinity API to check if mock mode is disabled"""

import requests
import json

def test_trinity_api():
    print("🔍 Testing Trinity API...")
    
    test_cases = [
        {"prompt": "2+2", "description": "Math test"},
        {"prompt": "Tell me a joke", "description": "Creativity test"},
        {"prompt": "What is Python?", "description": "Knowledge test"}
    ]
    
    url = "http://localhost:9010/orchestrate"
    headers = {
        "X-Agent": "phi3",
        "Content-Type": "application/json"
    }
    
    all_passed = True
    
    for test_case in test_cases:
        print(f"\n📋 {test_case['description']}: {test_case['prompt']}")
        data = {"prompt": test_case['prompt']}
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"📝 Response: {result.get('response', 'No response field')[:100]}...")
                print(f"🤖 Model: {result.get('model_used', 'unknown')}")
                print(f"⏱️ Latency: {result.get('latency_ms', 0)}ms")
                
                # Check if it's still a template
                response_text = result.get('response', '')
                if "I understand your query" in response_text:
                    print("❌ STILL RETURNING TEMPLATE RESPONSES!")
                    all_passed = False
                else:
                    print("✅ Real response received!")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Trinity is returning real AI responses!")
    else:
        print("❌ Some tests failed - Trinity may still be in mock mode")
    
    return all_passed

if __name__ == "__main__":
    test_trinity_api() 