#!/usr/bin/env python3
"""
Debug Provider System State
Check exactly what providers are loaded and why CUDA models aren't working
"""

import requests
import time

def test_provider_system():
    """Test provider system state"""
    print("🔍 DEBUGGING PROVIDER SYSTEM STATE")
    print("=" * 50)
    
    # Test 1: Check what providers are actually loaded
    print("\n1. 📦 Checking loaded providers...")
    try:
        # Import the hybrid router directly to check state
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        
        from router.hybrid import PROVIDER_MAP, PROVIDER_PRIORITY
        
        print(f"   🎯 Priority order: {PROVIDER_PRIORITY}")
        print(f"   📦 Loaded providers: {list(PROVIDER_MAP.keys())}")
        
        # Check each provider in detail
        for provider_name in PROVIDER_PRIORITY:
            if provider_name in PROVIDER_MAP:
                provider_func = PROVIDER_MAP[provider_name]
                print(f"   ✅ {provider_name}: {type(provider_func).__name__}")
            else:
                print(f"   ❌ {provider_name}: NOT LOADED")
                
    except Exception as e:
        print(f"   ❌ Provider check error: {e}")
    
    # Test 2: Check provider config loading
    print(f"\n2. 📝 Checking provider config...")
    try:
        import yaml
        with open("config/providers.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        providers = config.get("providers", {})
        for name, provider_config in providers.items():
            enabled = provider_config.get("enabled", True)
            provider_type = provider_config.get("type", "unknown")
            print(f"   📦 {name}: {provider_type}, enabled={enabled}")
            
    except Exception as e:
        print(f"   ❌ Config check error: {e}")
    
    # Test 3: Direct transformers test
    print(f"\n3. 🔥 Testing CUDA transformers directly...")
    try:
        import torch
        from transformers import pipeline
        
        print(f"   🔥 CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"   🔥 Creating phi-2 pipeline...")
            
            # Create pipeline directly (this should load into GPU memory)
            start_time = time.time()
            pipe = pipeline(
                "text-generation",
                model="microsoft/phi-2",
                device="cuda",
                torch_dtype=torch.float16,
                trust_remote_code=True,
                return_full_text=False
            )
            load_time = time.time() - start_time
            
            print(f"   ✅ Pipeline created in {load_time:.2f}s")
            
            # Check GPU memory
            memory_allocated = torch.cuda.memory_allocated() / (1024**3)
            print(f"   📊 GPU Memory after loading: {memory_allocated:.2f} GB")
            
            # Test generation
            start_time = time.time()
            outputs = pipe("Write a Python hello world function:", max_new_tokens=50)
            gen_time = time.time() - start_time
            
            print(f"   ⚡ Generation time: {gen_time:.3f}s")
            print(f"   💬 Output: {outputs[0]['generated_text'][:60]}...")
            
        else:
            print(f"   ❌ CUDA not available for direct test")
            
    except Exception as e:
        print(f"   ❌ Direct transformers error: {e}")
    
    # Test 4: Test call_llm function directly  
    print(f"\n4. 🎯 Testing call_llm function...")
    try:
        from router.hybrid import call_llm
        import asyncio
        
        async def test_call():
            result = await call_llm("Write a Python hello world function", max_tokens=50)
            return result
        
        result = asyncio.run(test_call())
        print(f"   ✅ call_llm succeeded")
        print(f"   🎯 Provider: {result.get('routing_provider', 'unknown')}")
        print(f"   🎯 Model: {result.get('model', 'unknown')}")
        print(f"   💬 Text: {result.get('text', '')[:60]}...")
        
    except Exception as e:
        print(f"   ❌ call_llm error: {e}")
    
    print(f"\n🏁 Provider Debug Complete")

if __name__ == "__main__":
    test_provider_system() 