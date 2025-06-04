#!/usr/bin/env python3
"""
Debug script to check model loading status and generation
"""

import sys
import os
sys.path.insert(0, '.')

from loader.deterministic_loader import get_loaded_models, generate_response, boot_models

def main():
    print("🔍 DEBUGGING MODEL LOADING")
    print("=" * 50)
    
    # Check current environment
    print(f"SWARM_GPU_PROFILE: {os.environ.get('SWARM_GPU_PROFILE', 'not set')}")
    print(f"SWARM_COUNCIL_ENABLED: {os.environ.get('SWARM_COUNCIL_ENABLED', 'not set')}")
    
    # Check currently loaded models
    print("\n📋 CURRENTLY LOADED MODELS:")
    loaded = get_loaded_models()
    for name, info in loaded.items():
        print(f"  {name}:")
        print(f"    Backend: {info.get('backend', 'unknown')}")
        print(f"    Type: {info.get('type', 'unknown')}")
        print(f"    Handle: {type(info.get('handle', None))}")
        print(f"    VRAM: {info.get('vram_mb', 0)} MB")
    
    if not loaded:
        print("  ❌ NO MODELS LOADED! This explains the mock responses.")
        print("\n🔧 ATTEMPTING REAL MODEL LOADING...")
        
        try:
            # Force real loading
            os.environ["SWARM_GPU_PROFILE"] = "rtx_4070"
            summary = boot_models(profile="rtx_4070")
            print(f"✅ Loading summary: {summary}")
            
            # Check loaded models again
            loaded = get_loaded_models()
            print(f"\n📋 MODELS AFTER REAL LOADING: {len(loaded)} models")
            for name, info in loaded.items():
                print(f"  {name}: {info.get('backend', 'unknown')} backend")
                
        except Exception as e:
            print(f"❌ Real loading failed: {e}")
    
    # Test generation with first available model
    if loaded:
        first_model = list(loaded.keys())[0]
        print(f"\n🧪 TESTING GENERATION WITH {first_model}:")
        
        test_prompts = [
            "What is 2 + 2?",
            "Calculate 15 * 16",
            "Write a Python function for factorial"
        ]
        
        for prompt in test_prompts:
            print(f"\n  Prompt: {prompt}")
            try:
                response = generate_response(first_model, prompt, max_tokens=100)
                print(f"  Response: {response}")
                
                # Check if it's a mock response
                if "Response from" in response and any(generic in response for generic in [
                    "I can help with mathematical calculations",
                    "I understand your question",
                    "Artificial Intelligence refers to"
                ]):
                    print("  ⚠️  MOCK RESPONSE DETECTED!")
                else:
                    print("  ✅ REAL RESPONSE DETECTED!")
                    
            except Exception as e:
                print(f"  ❌ Generation failed: {e}")
    else:
        print("\n❌ No models available for testing")

if __name__ == "__main__":
    main() 