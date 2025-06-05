#!/usr/bin/env python3
"""
Test Full Escalation with Background Processing
Wait to see if specialists run after Agent-0 returns low confidence
"""

import requests
import time
import json

def test_background_escalation():
    """Test if specialists run in background after Agent-0 returns"""
    print("🔍 TESTING BACKGROUND ESCALATION")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8001"
    
    # Test with a complex query that should definitely trigger specialists
    query = "Write a complete PyTorch neural network with custom loss function and backpropagation for deep learning"
    print(f"\n📤 Query: {query}")
    
    # Phase 1: Get Agent-0 response (should be fast but low confidence)
    print(f"\n🚀 Phase 1: Agent-0 first response...")
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{base_url}/vote", 
            json={"prompt": query},
            timeout=120  # Extended timeout for background processing
        )
        
        agent0_latency = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"   ⏱️ Agent-0 latency: {agent0_latency:.1f}ms")
            print(f"   🎯 Model: {data.get('model_used', 'unknown')}")
            print(f"   📊 Confidence: {data.get('confidence', 0)}")
            print(f"   💬 Response: {data.get('text', '')[:100]}...")
            
            # Check if this suggests escalation
            confidence = data.get('confidence', 1.0)
            if confidence < 0.6:
                print(f"   ✅ Low confidence ({confidence:.2f}) - escalation should happen")
                
                # Phase 2: Wait to see if response improves (background refinement)
                print(f"\n⏳ Phase 2: Waiting for background specialist refinement...")
                
                # Make another request to see if the system learned
                time.sleep(2)  # Give background processing time
                
                response2 = requests.post(
                    f"{base_url}/vote", 
                    json={"prompt": query},
                    timeout=60
                )
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    
                    print(f"   🔄 Second response model: {data2.get('model_used', 'unknown')}")
                    print(f"   📊 Second response confidence: {data2.get('confidence', 0)}")
                    print(f"   💬 Second response: {data2.get('text', '')[:100]}...")
                    
                    # Check for improvement
                    if (data2.get('model_used') != data.get('model_used') or 
                        data2.get('confidence', 0) > confidence + 0.1 or
                        len(data2.get('text', '')) > len(data.get('text', '')) + 50):
                        print(f"   🔥 IMPROVEMENT DETECTED - Background specialists working!")
                    else:
                        print(f"   📝 No significant improvement - may need different approach")
                        
                # Phase 3: Check GPU memory directly
                print(f"\n📊 Phase 3: Checking GPU state...")
                try:
                    import torch
                    if torch.cuda.is_available():
                        memory_allocated = torch.cuda.memory_allocated() / (1024**3)
                        print(f"   📊 Current GPU Memory: {memory_allocated:.2f} GB")
                        
                        if memory_allocated > 1.0:
                            print(f"   🔥 Models loaded in GPU memory!")
                        else:
                            print(f"   ⚠️ No significant GPU memory usage")
                    else:
                        print(f"   ❌ CUDA not available for memory check")
                except Exception as e:
                    print(f"   ❌ GPU check error: {e}")
                    
            else:
                print(f"   ⚠️ High confidence ({confidence:.2f}) - no escalation needed")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request error: {e}")
    
    print(f"\n🏁 Background Escalation Test Complete")

if __name__ == "__main__":
    test_background_escalation() 