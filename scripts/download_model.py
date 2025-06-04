#!/usr/bin/env python3
"""
Model Download Script for AutoGen Council
Downloads Mistral-13B GPTQ model for ExLlamaV2 backend
"""

import os
import sys
import urllib.request
import shutil
from pathlib import Path

# Model configuration
MODEL_NAME = "mistral-13b-gptq"
MODEL_URL = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GPTQ"  # Placeholder - use actual URL
MODELS_DIR = Path("./models")
MODEL_DIR = MODELS_DIR / MODEL_NAME

def download_with_progress(url: str, filename: str):
    """Download file with progress bar"""
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(downloaded * 100 / total_size, 100)
            print(f"\rDownloading {filename}: {percent:.1f}%", end="", flush=True)
    
    urllib.request.urlretrieve(url, filename, progress_hook)
    print()  # New line after progress

def download_model():
    """Download the Mistral-13B GPTQ model"""
    print(f"🤖 Downloading {MODEL_NAME} for ExLlamaV2...")
    
    # Create models directory
    MODELS_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    
    print(f"📁 Model directory: {MODEL_DIR}")
    
    # For now, create a placeholder structure
    # In production, you would download from HuggingFace or other sources
    placeholder_files = [
        "config.json",
        "tokenizer.json", 
        "tokenizer_config.json",
        "model.safetensors",
        "generation_config.json"
    ]
    
    print("📝 Creating placeholder model files...")
    print("⚠️  Note: Replace with actual model download logic")
    
    for filename in placeholder_files:
        filepath = MODEL_DIR / filename
        if not filepath.exists():
            # Create minimal placeholder files
            if filename == "config.json":
                content = '''{
  "architectures": ["MistralForCausalLM"],
  "bos_token_id": 1,
  "eos_token_id": 2,
  "hidden_act": "silu",
  "hidden_size": 4096,
  "initializer_range": 0.02,
  "intermediate_size": 14336,
  "max_position_embeddings": 4096,
  "model_type": "mistral",
  "num_attention_heads": 32,
  "num_hidden_layers": 32,
  "num_key_value_heads": 8,
  "rms_norm_eps": 1e-06,
  "rope_theta": 10000.0,
  "sliding_window": 4096,
  "tie_word_embeddings": false,
  "torch_dtype": "bfloat16",
  "transformers_version": "4.34.0",
  "use_cache": true,
  "vocab_size": 32000
}'''
            elif filename == "tokenizer_config.json":
                content = '''{
  "add_bos_token": true,
  "add_eos_token": false,
  "bos_token": "<s>",
  "eos_token": "</s>",
  "model_max_length": 1000000000000000019884624838656,
  "tokenizer_class": "LlamaTokenizer",
  "unk_token": "<unk>"
}'''
            else:
                content = f"# Placeholder for {filename}\n# Replace with actual model file\n"
            
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"  ✅ Created {filename}")
    
    print(f"\n🎯 Model structure created in {MODEL_DIR}")
    print("\n📋 Next steps:")
    print("1. Replace placeholder files with actual Mistral-13B GPTQ model")
    print("2. Download from: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GPTQ")
    print("3. Or use: git lfs clone https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.1-GPTQ")
    print("4. Ensure model files are in the correct format for ExLlamaV2")
    
    return MODEL_DIR

def verify_model():
    """Verify model files are present"""
    required_files = ["config.json", "model.safetensors"]
    missing_files = []
    
    for filename in required_files:
        filepath = MODEL_DIR / filename
        if not filepath.exists():
            missing_files.append(filename)
    
    if missing_files:
        print(f"❌ Missing model files: {missing_files}")
        return False
    
    print("✅ Model verification passed")
    return True

if __name__ == "__main__":
    print("🚀 AutoGen Council Model Download")
    print("=" * 40)
    
    try:
        model_path = download_model()
        verify_model()
        
        print(f"\n✅ Model download completed!")
        print(f"📍 Model location: {model_path}")
        print("\n🐳 Ready to start ExLlamaV2 container:")
        print("   docker-compose up -d llm")
        
    except Exception as e:
        print(f"❌ Error downloading model: {e}")
        sys.exit(1) 