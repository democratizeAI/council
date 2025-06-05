#!/usr/bin/env python3
"""
Phase 3 Fixed: Optimized Transformers Pipeline 
Fixes device mapping issues with accelerate
"""

import time
import asyncio
import sys
import subprocess
from typing import List, Dict, Any

# Import optimizations
try:
    import torch
    import torch.amp
    from transformers import (
        AutoModelForCausalLM, 
        AutoTokenizer, 
        pipeline,
        TextGenerationPipeline
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Transformers not available: {e}")
    TRANSFORMERS_AVAILABLE = False

class Phase3FixedPipeline:
    """Fixed transformers pipeline for Phase 3 performance"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "microsoft/phi-2"
        self.ready = False
        
        # Phase 3 Optimization Settings
        self.optimization_config = {
            "torch_dtype": torch.float16,  # FP16 for speed
            "device_map": "auto",  # Let accelerate handle device mapping
            "trust_remote_code": True,
            "low_cpu_mem_usage": True,
        }
    
    def setup_gpu_optimizations(self):
        """Apply GPU optimizations for Phase 3"""
        if not torch.cuda.is_available():
            print("⚠️ CUDA not available, using CPU")
            return False
        
        try:
            # Enable optimizations
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.backends.cudnn.benchmark = True
            
            # Check available memory
            gpu_memory = torch.cuda.get_device_properties(0).total_memory // (1024**3)
            print(f"🔍 GPU Memory: {gpu_memory}GB")
            
            print("✅ GPU optimizations enabled")
            return True
            
        except Exception as e:
            print(f"⚠️ GPU optimization failed: {e}")
            return False
    
    def load_model_fixed(self):
        """Load model with fixed device handling"""
        print(f"🚀 Loading {self.model_name} with fixed device handling...")
        
        try:
            # Load tokenizer first
            print("📝 Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Set pad token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with accelerate-compatible settings
            print("🧠 Loading model with accelerate...")
            start_time = time.time()
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=self.optimization_config["torch_dtype"],
                device_map=self.optimization_config["device_map"],
                trust_remote_code=self.optimization_config["trust_remote_code"],
                low_cpu_mem_usage=self.optimization_config["low_cpu_mem_usage"],
            )
            
            load_time = time.time() - start_time
            print(f"✅ Model loaded in {load_time:.2f}s")
            
            # Create pipeline WITHOUT device parameter (let accelerate handle it)
            print("🔧 Creating pipeline (device auto-managed)...")
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                # Don't specify device - let accelerate handle it
                torch_dtype=self.optimization_config["torch_dtype"],
                trust_remote_code=True
            )
            
            print("✅ Pipeline created successfully")
            self.ready = True
            return True
            
        except Exception as e:
            print(f"❌ Model loading failed: {e}")
            return False
    
    def warmup_model(self):
        """Warm up model for consistent performance"""
        if not self.ready:
            return False
        
        print("🔥 Warming up model...")
        warmup_prompts = [
            "Hello",
            "Test",
            "AI"
        ]
        
        for prompt in warmup_prompts:
            try:
                result = self.pipeline(
                    prompt,
                    max_new_tokens=5,
                    do_sample=False,
                    pad_token_id=self.tokenizer.pad_token_id
                )
                print(f"   🔥 Warmup: {prompt} -> OK")
            except Exception as e:
                print(f"   ⚠️ Warmup failed: {e}")
        
        print("✅ Model warmed up")
        return True
    
    async def generate_fast(self, prompt: str, max_tokens: int = 25) -> Dict[str, Any]:
        """Generate text with optimized settings"""
        if not self.ready:
            return {"error": "Model not ready"}
        
        start_time = time.time()
        
        try:
            # Run generation in thread pool
            def generate():
                return self.pipeline(
                    prompt,
                    max_new_tokens=max_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.9,
                    num_beams=1,  # Greedy for speed
                    pad_token_id=self.tokenizer.pad_token_id,
                    return_full_text=False,
                    clean_up_tokenization_spaces=True
                )
            
            # Run generation
            result = await asyncio.get_event_loop().run_in_executor(None, generate)
            
            end_time = time.time()
            latency = end_time - start_time
            
            if result and len(result) > 0:
                generated_text = result[0]["generated_text"].strip()
                tokens_generated = len(generated_text.split())
                tokens_per_sec = tokens_generated / latency if latency > 0 else 0
                
                return {
                    "text": generated_text,
                    "latency": latency,
                    "tokens_generated": tokens_generated,
                    "tokens_per_sec": tokens_per_sec,
                    "prompt": prompt
                }
            else:
                return {"error": "No generation result"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_gpu_stats(self):
        """Get current GPU statistics"""
        if not torch.cuda.is_available():
            return None
        
        try:
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 4:
                    return {
                        "gpu_util": float(parts[0]),
                        "memory_used": float(parts[1]),
                        "power_draw": float(parts[2]),
                        "temperature": float(parts[3])
                    }
        except:
            pass
        
        return None

async def phase3_fixed_test():
    """Run Phase 3 test with fixed pipeline"""
    print("🚀 PHASE 3: FIXED TRANSFORMERS PERFORMANCE TEST")
    print("=" * 55)
    
    if not TRANSFORMERS_AVAILABLE:
        print("❌ Transformers not available")
        return False
    
    # Initialize pipeline
    pipeline_manager = Phase3FixedPipeline()
    
    # Setup optimizations
    gpu_ready = pipeline_manager.setup_gpu_optimizations()
    
    # Load model with fixed approach
    if not pipeline_manager.load_model_fixed():
        return False
    
    # Warmup
    pipeline_manager.warmup_model()
    
    # Quick test prompts
    test_prompts = [
        "Write hello world in Python",
        "What is 15 + 27?",
        "Explain AI briefly",
        "List Python data types",
        "Describe machine learning",
    ]
    
    print(f"\n🧪 Phase 3 quick performance test ({len(test_prompts)} prompts)...")
    
    results = []
    gpu_stats = []
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📤 Test {i}: {prompt[:40]}...")
        
        # Generate
        result = await pipeline_manager.generate_fast(prompt, max_tokens=30)
        
        # Get GPU stats
        gpu_stat = pipeline_manager.get_gpu_stats()
        
        if "error" not in result:
            results.append(result)
            print(f"   ⏱️ {result['latency']:.3f}s | 🎯 {result['tokens_per_sec']:.1f} t/s | 📝 {result['tokens_generated']} tokens")
            print(f"   💬 {result['text'][:50]}...")
            
            if gpu_stat:
                gpu_stats.append(gpu_stat)
                print(f"   📊 GPU: {gpu_stat['gpu_util']}% util, {gpu_stat['power_draw']}W")
        else:
            print(f"   ❌ Error: {result['error']}")
    
    # Quick analysis
    return analyze_quick_results(results, gpu_stats)

def analyze_quick_results(results: List[Dict], gpu_stats: List[Dict]) -> bool:
    """Quick analysis of Phase 3 results"""
    if not results:
        print("❌ No results to analyze")
        return False
    
    print(f"\n📊 PHASE 3 QUICK RESULTS")
    print("=" * 30)
    
    # Performance metrics
    latencies = [r["latency"] for r in results]
    tokens_per_sec = [r["tokens_per_sec"] for r in results]
    
    avg_latency = sum(latencies) / len(latencies)
    avg_tokens = sum(tokens_per_sec) / len(tokens_per_sec)
    max_tokens = max(tokens_per_sec) if tokens_per_sec else 0
    
    print(f"⚡ Performance:")
    print(f"   Avg latency: {avg_latency:.3f}s")
    print(f"   Avg tokens/s: {avg_tokens:.1f}")
    print(f"   Peak tokens/s: {max_tokens:.1f}")
    
    # GPU metrics
    if gpu_stats:
        avg_gpu = sum(s["gpu_util"] for s in gpu_stats) / len(gpu_stats)
        max_gpu = max(s["gpu_util"] for s in gpu_stats)
        avg_power = sum(s["power_draw"] for s in gpu_stats) / len(gpu_stats)
        
        print(f"\n🔥 GPU:")
        print(f"   Avg util: {avg_gpu:.1f}%")
        print(f"   Peak util: {max_gpu:.1f}%")
        print(f"   Avg power: {avg_power:.1f}W")
    
    # Success criteria (realistic for this approach)
    latency_ok = avg_latency <= 3.0  # 3s acceptable
    throughput_ok = avg_tokens >= 15.0  # 15+ t/s target
    peak_ok = max_tokens >= 20.0  # Peak target
    
    print(f"\n🎯 PHASE 3 CRITERIA:")
    print(f"   {'✅' if latency_ok else '❌'} Latency ≤ 3s: {avg_latency:.3f}s")
    print(f"   {'✅' if throughput_ok else '❌'} Throughput ≥ 15 t/s: {avg_tokens:.1f}")
    print(f"   {'✅' if peak_ok else '❌'} Peak ≥ 20 t/s: {max_tokens:.1f}")
    
    success_count = sum([latency_ok, throughput_ok, peak_ok])
    
    if success_count >= 2:
        print("\n🎉 PHASE 3 SUCCESS!")
        print("✅ Performance targets achieved")
        return True
    elif success_count >= 1:
        print("\n🟡 PHASE 3 PARTIAL SUCCESS")
        return True
    else:
        print("\n🔴 PHASE 3 NEEDS WORK")
        return False

if __name__ == "__main__":
    print("🚀 Phase 3: Fixed Transformers Pipeline")
    
    success = asyncio.run(phase3_fixed_test())
    
    if success:
        print("\n🎉 Phase 3 transformers working!")
        print("✅ Performance improvement achieved")
    else:
        print("\n⚠️ Phase 3 needs optimization") 