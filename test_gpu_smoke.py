#!/usr/bin/env python3
"""GPU Smoke Test - Verify models load on GPU properly"""

import os
import sys

def test_cuda_availability():
    """Test if CUDA is available"""
    print("[TESTING] CUDA availability...")
    
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"   PyTorch CUDA available: {cuda_available}")
        
        if cuda_available:
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0)
            print(f"   GPU devices: {device_count}")
            print(f"   Primary GPU: {device_name}")
            return True
        else:
            print("   [WARNING] CUDA not available - will use CPU")
            return False
    except Exception as e:
        print(f"   [ERROR] CUDA test failed: {e}")
        return False

def test_transformers_gpu():
    """Test transformers model loading on GPU"""
    print("\n[TESTING] Transformers GPU loading...")
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_id = "microsoft/phi-1_5"  # Small model for testing
        print(f"   Loading {model_id}...")
        
        # Try GPU first, fallback to CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"   Target device: {device}")
        
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            trust_remote_code=True
        ).to(device)
        
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Test inference
        prompt = "Hello world"
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=10,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        actual_device = str(next(model.parameters()).device)
        
        print(f"   [OK] Model loaded on: {actual_device}")
        print(f"   [OK] Test response: '{response}'")
        
        return actual_device.startswith("cuda")
        
    except Exception as e:
        print(f"   [ERROR] Transformers GPU test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_deterministic_loader():
    """Test our deterministic loader GPU usage"""
    print("\n[TESTING] Deterministic loader...")
    
    try:
        # Set environment for local-only
        os.environ["SWARM_CLOUD_ENABLED"] = "false"
        os.environ["PROVIDER_PRIORITY"] = "local_mixtral,local_tinyllama"
        
        from loader.deterministic_loader import boot_models, get_loaded_models
        
        # Try to boot models
        result = boot_models(profile="quick_test")  # Use quick_test instead
        print(f"   Boot result: {result}")
        
        # Check loaded models
        loaded = get_loaded_models()
        if loaded:
            print(f"   [OK] {len(loaded)} models loaded:")
            for name, info in loaded.items():
                backend = info.get('backend', 'unknown')
                device = info.get('device', 'unknown')
                print(f"      [MODEL] {name}: {backend} on {device}")
            return True
        else:
            print("   [WARNING] No models loaded")
            return False
            
    except Exception as e:
        print(f"   [ERROR] Deterministic loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run GPU smoke tests"""
    print("[GPU SMOKE TEST]")
    print("=" * 50)
    
    # Test 1: CUDA availability
    cuda_ok = test_cuda_availability()
    
    # Test 2: Transformers GPU loading
    transformers_gpu_ok = test_transformers_gpu()
    
    # Test 3: Our loader
    loader_ok = test_deterministic_loader()
    
    print(f"\n[RESULTS]:")
    print(f"   CUDA Available: {'[OK]' if cuda_ok else '[FAIL]'}")
    print(f"   Transformers GPU: {'[OK]' if transformers_gpu_ok else '[FAIL]'}")
    print(f"   Loader Working: {'[OK]' if loader_ok else '[FAIL]'}")
    
    if cuda_ok and transformers_gpu_ok and loader_ok:
        print(f"\n[SUCCESS] ALL TESTS PASSED - GPU inference ready!")
        return 0
    else:
        print(f"\n[WARNING] Some tests failed - CPU inference mode")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 