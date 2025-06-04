#!/usr/bin/env python3
"""Test real inference with the SwarmAI API"""

import requests
import json

def test_inference():
    url = "http://127.0.0.1:8000/orchestrate"
    
    # Test cases for different models
    test_cases = [
        {
            "prompt": "What is 2 + 2?",
            "route": ["math_specialist_0.8b"],
            "name": "Math Test"
        },
        {
            "prompt": "Write a Python function to add two numbers",
            "route": ["codellama_0.7b"],
            "name": "Code Test"
        },
        {
            "prompt": "Hello, how are you?",
            "route": ["openchat_3.5_0.4b"],
            "name": "Chat Test"
        }
    ]
    
    print("🧪 Testing Real Inference Capability")
    print("="*50)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Prompt: {test['prompt']}")
        print(f"   Model: {test['route'][0]}")
        
        try:
            response = requests.post(url, json=test, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📤 Response: {result.get('text', 'No text field')[:100]}...")
            else:
                print(f"   ❌ Status: {response.status_code}")
                print(f"   📤 Error: {response.text[:100]}...")
                
        except Exception as e:
            print(f"   ⚠️ Exception: {e}")
    
    print("\n" + "="*50)
    print("🏆 Real inference testing complete!")

if __name__ == "__main__":
    test_inference() 