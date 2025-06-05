#!/usr/bin/env python3
"""
Phi-2 Model Preparation for TensorRT-LLM
Downloads and converts Phi-2 model to TensorRT-LLM compatible format
"""

import os
import shutil
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

def prepare_phi2_model():
    """Download and prepare Phi-2 model for TensorRT-LLM"""
    
    model_name = "microsoft/phi-2"
    output_dir = "/workspace/models/phi-2"
    
    print(f"🚀 Preparing {model_name} for TensorRT-LLM...")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Download tokenizer
        print("📝 Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            trust_remote_code=True,
            cache_dir="/tmp/hf_cache"
        )
        tokenizer.save_pretrained(output_dir)
        
        # Download model
        print("🧠 Downloading model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            trust_remote_code=True,
            cache_dir="/tmp/hf_cache",
            low_cpu_mem_usage=True
        )
        
        # Save model in HF format for TensorRT-LLM conversion
        model.save_pretrained(output_dir)
        
        # Create config file for TensorRT-LLM
        config_content = f"""{{
    "model_type": "phi",
    "architecture": "PhiForCausalLM",
    "dtype": "float16",
    "quantization": {{
        "type": "int4_awq",
        "group_size": 128
    }},
    "vocab_size": {model.config.vocab_size},
    "hidden_size": {model.config.hidden_size},
    "num_hidden_layers": {model.config.num_hidden_layers},
    "num_attention_heads": {model.config.num_attention_heads},
    "intermediate_size": {model.config.intermediate_size},
    "max_position_embeddings": {model.config.max_position_embeddings},
    "use_cache": true,
    "trust_remote_code": true
}}"""
        
        with open(f"{output_dir}/trtllm_config.json", "w") as f:
            f.write(config_content)
        
        print(f"✅ Model prepared successfully in {output_dir}")
        print(f"📊 Model info:")
        print(f"   Vocab size: {model.config.vocab_size}")
        print(f"   Hidden size: {model.config.hidden_size}")
        print(f"   Layers: {model.config.num_hidden_layers}")
        print(f"   Attention heads: {model.config.num_attention_heads}")
        
        # Clean up cache
        shutil.rmtree("/tmp/hf_cache", ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to prepare model: {e}")
        return False

if __name__ == "__main__":
    success = prepare_phi2_model()
    exit(0 if success else 1) 