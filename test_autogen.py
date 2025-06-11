#!/usr/bin/env python3
"""Test real AutoGen API with RouterCascade"""

import requests
import json

def test_autogen_api():
    print("🔍 Testing Real AutoGen API...")
    
    test_cases = [
        {"prompt": "2+2", "description": "Math test"},
        {"prompt": "Tell me a joke", "description": "Creativity test"},
        {"prompt": "What is Python?", "description": "Knowledge test"}
    ]
    
    # Test different endpoints
    endpoints = [
        {"url": "http://localhost:8000/hybrid", "name": "Hybrid Endpoint"},
        {"url": "http://localhost:8000/orchestrate", "name": "Orchestrate Endpoint"}
    ]
    
    all_passed = True
    
    for endpoint in endpoints:
        print(f"\n🔧 Testing {endpoint['name']}: {endpoint['url']}")
        
        for test_case in test_cases:
            print(f"\n📋 {test_case['description']}: {test_case['prompt']}")
            
            # Different request formats for different endpoints
            if "hybrid" in endpoint['url']:
                data = {"prompt": test_case['prompt']}
                headers = {"Content-Type": "application/json"}
            else:  # orchestrate
                data = {"prompt": test_case['prompt'], "route": ["phi3"]}
                headers = {"Content-Type": "application/json"}
            
            try:
                response = requests.post(endpoint['url'], headers=headers, json=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get('text', result.get('response', 'No response'))
                    print(f"✅ Status: {response.status_code}")
                    print(f"📝 Response: {response_text[:100]}...")
                    print(f"🤖 Model: {result.get('model', result.get('model_used', 'unknown'))}")
                    
                    # Check if it's still a template
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
        print("🎉 ALL TESTS PASSED - AutoGen is returning real AI responses!")
    else:
        print("❌ Some tests failed - checking for real AutoGen API...")
    
    return all_passed

if __name__ == "__main__":
    test_autogen_api() 