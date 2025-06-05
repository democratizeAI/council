#!/usr/bin/env python3
"""
Test CUDA Transformers Models
Verify that local models are now loading with CUDA support
"""

import requests
import time
import json

def test_transformers_loading():
    """Test if transformers models are loading with CUDA"""
    print("🔥 TESTING CUDA TRANSFORMERS LOADING")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8001"
    
    # Test 1: Check model status
    print("\n1. 🔍 Checking model status...")
    try:
        response = requests.get(f"{base_url}/monitor", timeout=5)
        if response.status_code == 200:
            print("✅ Monitor endpoint accessible")
            # Look for model info in response
            if "CUDA" in response.text or "cuda" in response.text:
                print("✅ CUDA mentioned in monitor")
            else:
                print("⚠️ No CUDA mentioned in monitor")
        else:
            print(f"❌ Monitor endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Monitor endpoint error: {e}")
    
    # Test 2: Force low confidence with complex query
    print("\n2. 🧪 Testing complex query to force model loading...")
    test_queries = [
        "Explain the mathematical proof of Fermat's Last Theorem in detail with step-by-step derivation",
        "Write a complete neural network implementation in PyTorch with backpropagation mathematics",
        "Analyze the quantum mechanical implications of Schrödinger's equation for hydrogen atoms"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Test {i}: {query[:50]}...")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{base_url}/vote", 
                json={"prompt": query},
                timeout=30
            )
            latency = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                model_used = data.get('model_used', 'unknown')
                confidence = data.get('confidence', 0)
                text = data.get('text', '')
                
                print(f"   ✅ Response received in {latency:.1f}ms")
                print(f"   🎯 Model: {model_used}")
                print(f"   📊 Confidence: {confidence}")
                print(f"   💬 Text: {text[:60]}...")
                
                # Check if we got actual model response vs basic pattern
                if model_used != 'agent0-local-manifest' or confidence < 0.9:
                    print(f"   🔥 SUCCESS: Model escalation detected!")
                else:
                    print(f"   📝 Note: Still using local patterns")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   📄 Response: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Request error: {e}")
        
        time.sleep(1)  # Brief pause between tests
    
    # Test 3: Check GPU memory usage
    print("\n3. 🔥 Checking GPU memory usage...")
    try:
        import torch
        if torch.cuda.is_available():
            memory_allocated = torch.cuda.memory_allocated() / (1024**3)  # GB
            memory_reserved = torch.cuda.memory_reserved() / (1024**3)   # GB
            print(f"   📊 GPU Memory Allocated: {memory_allocated:.2f} GB")
            print(f"   📊 GPU Memory Reserved: {memory_reserved:.2f} GB")
            
            if memory_allocated > 0.1:  # More than 100MB
                print("   ✅ Models appear to be loaded in GPU memory")
            else:
                print("   ⚠️ Low GPU memory usage - models may not be loaded")
        else:
            print("   ❌ CUDA not available in test environment")
    except Exception as e:
        print(f"   ❌ GPU check error: {e}")
    
    print("\n🏁 CUDA Test Complete")

if __name__ == "__main__":
    test_transformers_loading() 