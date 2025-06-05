#!/usr/bin/env python3
"""
Test the fixed /vote endpoint to verify Agent-0 speaks first
"""

import requests
import time
import json

def test_vote_endpoint():
    """Test the /vote endpoint with Agent-0 first routing"""
    
    test_cases = [
        {
            "prompt": "hi",
            "description": "Greeting test",
            "should_be_agent0": True
        },
        {
            "prompt": "what's new?", 
            "description": "Non-math greeting",
            "should_be_agent0": True
        },
        {
            "prompt": "2+2",
            "description": "Simple math",
            "should_be_agent0_or_math": True
        },
        {
            "prompt": "write a python hello-world",
            "description": "Code request",
            "should_be_agent0_or_code": True
        }
    ]
    
    print("🧪 TESTING /vote ENDPOINT (Agent-0 First)")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['description']}")
        print(f"   📤 Prompt: '{test_case['prompt']}'")
        
        start_time = time.time()
        
        try:
            response = requests.post(
                "http://localhost:8001/vote",
                json={
                    "prompt": test_case["prompt"],
                    "candidates": ["math", "code", "logic", "knowledge"],
                    "top_k": 2
                },
                timeout=10
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract response info (VoteResponse format)
                model_used = data.get("model_used", "unknown")
                confidence = data.get("confidence", 0.0)
                text = data.get("text", "")
                
                print(f"   ✅ Response: '{text[:60]}{'...' if len(text) > 60 else ''}'")
                print(f"   ⏱️ Latency: {latency_ms:.1f}ms")
                print(f"   🎯 Model: {model_used} (confidence: {confidence:.2f})")
                print(f"   📊 Full Response: {data}")
                
                # Validate result
                if model_used == "agent0" or "agent" in model_used:
                    print(f"   ✅ PASS: Agent-0 responded first")
                elif model_used in ["math", "code", "logic", "knowledge"]:
                    print(f"   🟡 SPECIALIST: {model_used} won (may be correct)")
                else:
                    print(f"   🟡 MODEL: {model_used}")
                
                # Check for greeting stubs
                if any(stub in text.lower() for stub in ["hi, how can i help", "hello, how can i help"]):
                    print(f"   ❌ GREETING STUB: Found greeting stub in response!")
                else:
                    print(f"   ✅ CLEAN: No greeting stubs detected")
                
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   📝 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Test the /hybrid endpoint for comparison
    print(f"\n🔍 COMPARISON: Testing /hybrid endpoint")
    try:
        response = requests.post(
            "http://localhost:8001/hybrid",
            json={"prompt": "hi"},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   📤 /hybrid response: '{data.get('text', '')[:60]}...'")
            print(f"   🎯 Provider: {data.get('provider', 'unknown')}")
            print(f"   🎯 Confidence: {data.get('confidence', 0):.2f}")
        else:
            print(f"   ❌ /hybrid failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ /hybrid exception: {e}")

if __name__ == "__main__":
    test_vote_endpoint() 