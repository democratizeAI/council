#!/usr/bin/env python3
"""
Model reload script with 4-bit quantization using bitsandbytes
"""

import os
import sys
import time
import torch
from transformers import (
    AutoModelForCausalLM, 
    AutoTokenizer, 
    BitsAndBytesConfig,
    pipeline
)

def reload_model_quantized(model_name: str = "microsoft/phi-2"):
    """Reload model with 4-bit quantization"""
    
    print(f"🔄 Reloading model: {model_name}")
    print(f"🔧 Using 4-bit quantization with bitsandbytes")
    
    # Configure 4-bit quantization
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    
    print(f"📊 GPU memory before loading:")
    if torch.cuda.is_available():
        print(f"   Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
        print(f"   Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
    
    start_time = time.time()
    
    try:
        # Load tokenizer
        print("🔤 Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with quantization
        print("🧠 Loading model with 4-bit quantization...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16
        )
        
        # Create pipeline
        print("🔧 Creating optimized pipeline...")
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device_map="auto",
            torch_dtype=torch.float16,
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.2f}s")
        
        print(f"📊 GPU memory after loading:")
        if torch.cuda.is_available():
            print(f"   Allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
            print(f"   Reserved: {torch.cuda.memory_reserved() / 1024**3:.2f} GB")
        
        # Test generation speed
        print("\n🚀 Testing generation speed...")
        test_prompt = "Write a hello world function:"
        
        gen_start = time.time()
        result = pipe(test_prompt, max_new_tokens=50, do_sample=False)
        gen_time = time.time() - gen_start
        
        generated_text = result[0]['generated_text']
        tokens_generated = len(tokenizer.encode(generated_text)) - len(tokenizer.encode(test_prompt))
        tokens_per_sec = tokens_generated / gen_time if gen_time > 0 else 0
        
        print(f"⚡ Generation time: {gen_time:.3f}s")
        print(f"📝 Tokens generated: {tokens_generated}")
        print(f"🎯 Tokens/second: {tokens_per_sec:.1f}")
        print(f"💬 Result: {generated_text[:100]}...")
        
        # Performance assessment
        if tokens_per_sec >= 45:
            print("✅ EXCELLENT: >45 tokens/s")
        elif tokens_per_sec >= 25:
            print("🟡 GOOD: 25-45 tokens/s")
        else:
            print("🔴 SLOW: <25 tokens/s")
            
        return pipe, tokenizer
        
    except Exception as e:
        print(f"❌ Failed to reload model: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def warmup_model(pipe, tokenizer):
    """Warm up the model with a quick generation"""
    if pipe is None:
        return
        
    print("\n🔥 Warming up model...")
    warmup_start = time.time()
    
    # Quick warmup generation
    result = pipe("1+1=", max_new_tokens=1, do_sample=False)
    warmup_time = time.time() - warmup_start
    
    print(f"🔥 Warmup completed in {warmup_time:.3f}s")
    print("✅ Model ready for fast inference")

if __name__ == "__main__":
    print("🚀 Quantized Model Reload Script")
    print("=" * 40)
    
    # Clear GPU cache
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        print("🧹 GPU cache cleared")
    
    pipe, tokenizer = reload_model_quantized()
    
    if pipe:
        warmup_model(pipe, tokenizer)
        print("\n🎉 Model reload complete!")
        print("💡 Model is now quantized and warmed up for fast inference")
    else:
        print("\n❌ Model reload failed")
        sys.exit(1) 