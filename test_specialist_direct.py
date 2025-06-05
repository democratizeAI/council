#!/usr/bin/env python3
"""
Test Specialists Directly
Test calling each specialist directly to see if they work
"""

import requests
import time

def test_specialist_direct():
    """Test calling specialists directly"""
    print("🔍 TESTING SPECIALISTS DIRECTLY")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8001"
    
    # Test forcing different skills
    test_cases = [
        ("math", "What is 2 + 2?"),
        ("code", "Write a Python hello world function"),
        ("logic", "Prove that all swans are white"),
        ("knowledge", "Explain quantum mechanics"),
    ]
    
    for skill, query in test_cases:
        print(f"\n🎯 Testing {skill} specialist...")
        print(f"   📤 Query: {query}")
        
        try:
            # Try to force routing to specific skill
            start_time = time.time()
            response = requests.post(
                f"{base_url}/vote", 
                json={
                    "prompt": query,
                    "force_skill": skill  # Try to force specific skill
                },
                timeout=30
            )
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ⏱️ Latency: {latency:.1f}ms")
                print(f"   🎯 Model: {data.get('model_used', 'unknown')}")
                print(f"   📊 Confidence: {data.get('confidence', 0)}")
                print(f"   💬 Response: {data.get('text', '')[:80]}...")
                
                # Check if it used the actual specialist
                model_used = data.get('model_used', '')
                if 'agent0-local-manifest' in model_used:
                    print(f"   ⚠️ Still using Agent-0 local patterns")
                else:
                    print(f"   ✅ Using specialist: {model_used}")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Test direct skill endpoint if available
    print(f"\n🔍 Testing if /hybrid endpoint works better...")
    try:
        response = requests.post(
            f"{base_url}/hybrid", 
            json={"prompt": "Write a Python neural network"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Hybrid endpoint working")
            print(f"   🎯 Model: {data.get('model_used', 'unknown')}")
            print(f"   💬 Response: {data.get('text', '')[:80]}...")
        else:
            print(f"   ⚠️ Hybrid endpoint status: {response.status_code}")
            
    except Exception as e:
        print(f"   ⚠️ Hybrid endpoint not available: {e}")
    
    print(f"\n🏁 Specialist Direct Test Complete")

if __name__ == "__main__":
    test_specialist_direct() 