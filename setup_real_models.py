#!/usr/bin/env python3
"""
Real Model Setup - Content-First Fixes
======================================

Replace toy models with real quantized models via vLLM:
- Math/General: microsoft/phi-2 (4-bit AWQ) on port 8001
- Code: deepseek-coder-6.7B (4-bit AWQ) on port 8002  
- Knowledge: Qwen-7B-chat (4-bit AWQ) on port 8003
- Logic: prolog_py (PySwip) - already working
- RAG: faiss_rag - already working
"""

import subprocess
import sys
import time
import requests
import os
from pathlib import Path

def install_dependencies():
    """Install vLLM and AutoAWQ for quantization"""
    print("📦 Installing vLLM and AutoAWQ...")
    
    try:
        # Install vLLM
        subprocess.run([sys.executable, "-m", "pip", "install", "vllm"], check=True)
        print("✅ vLLM installed")
        
        # Install AutoAWQ for quantization
        subprocess.run([sys.executable, "-m", "pip", "install", "autoawq"], check=True) 
        print("✅ AutoAWQ installed")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False

def create_models_dir():
    """Create models directory for quantized models"""
    models_dir = Path("/models")
    if not models_dir.exists():
        # Try creating in current directory if /models fails
        models_dir = Path("./models")
        models_dir.mkdir(exist_ok=True)
    
    print(f"📁 Models directory: {models_dir}")
    return models_dir

def quantize_models(models_dir):
    """Quantize models to 4-bit AWQ"""
    print("🔧 Quantizing models to 4-bit AWQ...")
    
    models_to_quantize = [
        ("microsoft/phi-2", "phi2_q4"),
        ("deepseek-ai/deepseek-coder-6.7b-base", "dsc_q4"),  
        ("Qwen/Qwen-7B-Chat", "qwen_q4")
    ]
    
    for model_name, output_name in models_to_quantize:
        output_path = models_dir / output_name
        
        if output_path.exists():
            print(f"✅ {output_name} already exists, skipping")
            continue
            
        print(f"🔧 Quantizing {model_name} → {output_name}")
        
        try:
            # Use AutoAWQ to quantize
            cmd = [
                "autoawq", "quantize", 
                model_name, 
                "--wbits", "4",
                "-o", str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 min timeout
            
            if result.returncode == 0:
                print(f"✅ {output_name} quantized successfully")
            else:
                print(f"❌ {output_name} quantization failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {output_name} quantization timed out")
        except Exception as e:
            print(f"❌ {output_name} quantization error: {e}")

def start_vllm_servers(models_dir):
    """Start vLLM API servers for quantized models"""
    print("🚀 Starting vLLM API servers...")
    
    servers = [
        ("phi2_q4", 8001, "Math/General reasoning"),
        ("dsc_q4", 8002, "Code generation"), 
        ("qwen_q4", 8003, "Knowledge/Chat")
    ]
    
    processes = []
    
    for model_name, port, description in servers:
        model_path = models_dir / model_name
        
        if not model_path.exists():
            print(f"⚠️ {model_name} not found, skipping {description}")
            continue
            
        print(f"🚀 Starting {description} server on port {port}")
        
        cmd = [
            sys.executable, "-m", "vllm.entrypoints.openai.api_server",
            "--model", str(model_path),
            "--port", str(port),
            "--gpu-memory-utilization", "0.3",  # Conservative for 3 models
            "--max-model-len", "2048",
            "--dtype", "float16"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            processes.append((process, port, description))
            print(f"✅ {description} server started (PID: {process.pid})")
            
        except Exception as e:
            print(f"❌ Failed to start {description}: {e}")
    
    # Wait for servers to start
    print("⏱️ Waiting for servers to initialize...")
    time.sleep(30)
    
    # Check server health
    for process, port, description in processes:
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ {description} server healthy on port {port}")
            else:
                print(f"⚠️ {description} server unhealthy: {response.status_code}")
        except Exception as e:
            print(f"❌ {description} server check failed: {e}")
    
    return processes

def create_model_adapters():
    """Create adapter files to use vLLM endpoints"""
    print("📝 Creating model adapter files...")
    
    # Phi-2 Math/General adapter
    phi2_adapter = """#!/usr/bin/env python3
import requests
import json

def generate_math_response(prompt, max_tokens=100):
    \"\"\"Generate math response using Phi-2 via vLLM\"\"\"
    try:
        response = requests.post(
            "http://localhost:8001/v1/completions",
            json={
                "model": "phi2_q4",
                "prompt": f"Solve this math problem step by step:\\n{prompt}\\nAnswer:",
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "stop": ["\\n\\n"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["text"].strip()
        else:
            return f"ERROR: HTTP {response.status_code}"
            
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    # Test
    result = generate_math_response("What is 8 factorial?")
    print(f"Phi-2 response: {result}")
"""
    
    with open("phi2_adapter.py", "w") as f:
        f.write(phi2_adapter)
    
    # DeepSeek Code adapter
    deepseek_adapter = """#!/usr/bin/env python3
import requests
import json

def generate_code_response(prompt, max_tokens=300):
    \"\"\"Generate code using DeepSeek-Coder via vLLM\"\"\"
    try:
        response = requests.post(
            "http://localhost:8002/v1/completions",
            json={
                "model": "dsc_q4",
                "prompt": f"Write clean Python code:\\n{prompt}\\n\\n",
                "max_tokens": max_tokens,
                "temperature": 0.3,
                "stop": ["\\n\\n\\n"]
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["text"].strip()
        else:
            return f"ERROR: HTTP {response.status_code}"
            
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    # Test
    result = generate_code_response("Write a function to calculate GCD")
    print(f"DeepSeek response: {result}")
"""
    
    with open("deepseek_adapter.py", "w") as f:
        f.write(deepseek_adapter)
    
    print("✅ Model adapters created")

def main():
    """Main setup process"""
    print("🚀 REAL MODEL SETUP - Content-First Fixes")
    print("=" * 50)
    
    # Step 1: Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Step 2: Create models directory
    models_dir = create_models_dir()
    
    # Step 3: Quantize models (may take a while)
    quantize_models(models_dir)
    
    # Step 4: Start vLLM servers
    processes = start_vllm_servers(models_dir)
    
    # Step 5: Create adapters
    create_model_adapters()
    
    print("\n🎯 REAL MODELS SETUP COMPLETE")
    print("Next steps:")
    print("1. Test adapters: python phi2_adapter.py")
    print("2. Test adapters: python deepseek_adapter.py") 
    print("3. Wire content guards")
    print("4. Run litmus test")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 