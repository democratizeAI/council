#!/usr/bin/env python3
"""
Test Detailed Escalation Process
Check exactly what happens when Agent-0 gives low confidence
"""

import requests
import time
import json

def test_escalation_process():
    """Test the detailed escalation process"""
    print("🔍 TESTING DETAILED ESCALATION PROCESS")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8001"
    
    # Test with a query that should trigger escalation
    query = "Write a complete neural network implementation in PyTorch with backpropagation"
    print(f"\n📤 Query: {query}")
    
    start_time = time.time()
    try:
        response = requests.post(
            f"{base_url}/vote", 
            json={"prompt": query},
            timeout=60  # Longer timeout to see full process
        )
        total_latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📊 RESPONSE ANALYSIS:")
            print(f"   ⏱️ Total latency: {total_latency:.1f}ms")
            print(f"   🎯 Model used: {data.get('model_used', 'unknown')}")
            print(f"   📊 Confidence: {data.get('confidence', 0)}")
            print(f"   💬 Text: {data.get('text', '')[:100]}...")
            print(f"   🔄 Council used: {data.get('council_used', False)}")
            print(f"   👥 Council voices: {data.get('council_voices', None)}")
            print(f"   🎯 Candidates: {data.get('candidates', [])}")
            print(f"   💰 Cost: {data.get('total_cost_cents', 0)}¢")
            
            # Check if escalation happened
            if data.get('confidence', 1.0) < 0.6:
                print(f"   ✅ Low confidence detected - escalation should have happened")
                
                # Check for specialist activity
                candidates = data.get('candidates', [])
                if candidates:
                    print(f"   🧩 Specialists available: {candidates}")
                else:
                    print(f"   ⚠️ No specialist candidates found")
                    
                # Check for actual specialist results
                model_used = data.get('model_used', '')
                if 'specialist' in model_used or model_used != 'agent0-local-manifest':
                    print(f"   🔥 SPECIALIST ACTIVE: {model_used}")
                else:
                    print(f"   📝 Still using Agent-0 local patterns")
                    
            else:
                print(f"   ⚠️ High confidence - no escalation needed")
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    # Check server logs by making a simple request to see what's logged
    print(f"\n🔍 Testing simple greeting for comparison...")
    try:
        response = requests.post(
            f"{base_url}/vote", 
            json={"prompt": "hi"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   📊 Greeting confidence: {data.get('confidence', 0)}")
            print(f"   🎯 Greeting model: {data.get('model_used', 'unknown')}")
        
    except Exception as e:
        print(f"   ❌ Greeting test error: {e}")

if __name__ == "__main__":
    test_escalation_process() 