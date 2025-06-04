#!/usr/bin/env python3
"""
Quick GPU inference test
"""
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

def test_gpu_inference():
    # Set CUDA device
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    
    print("🔧 CUDA available:", torch.cuda.is_available())
    print("🔧 CUDA devices:", torch.cuda.device_count())
    
    print("\n📥 Loading Phi-2...")
    model = AutoModelForCausalLM.from_pretrained(
        'microsoft/phi-2',
        torch_dtype=torch.float16,
        device_map='auto',
        trust_remote_code=True
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        'microsoft/phi-2',
        trust_remote_code=True
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Check where model parameters are
    print(f"🔧 Model device: {next(model.parameters()).device}")
    
    print("\n🔥 Generating on GPU...")
    inputs = tokenizer('What is 8 factorial?', return_tensors='pt')
    inputs = {k: v.to('cuda') for k, v in inputs.items()}
    
    # Monitor GPU before generation
    print(f"🔧 GPU memory before: {torch.cuda.memory_allocated() / 1024**2:.1f} MB")
    
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=20,
            do_sample=False
        )
    
    print(f"🔧 GPU memory after: {torch.cuda.memory_allocated() / 1024**2:.1f} MB")
    
    result = tokenizer.decode(output[0], skip_special_tokens=True)
    print(f"\n✅ Generated: {result}")
    
    # Clean up
    del model
    torch.cuda.empty_cache()
    print("\n🧹 Cleaned up GPU memory")

if __name__ == "__main__":
    test_gpu_inference() 