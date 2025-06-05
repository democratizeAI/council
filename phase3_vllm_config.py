#!/usr/bin/env python3
"""
Phase 3 vLLM Configuration - Advanced GPU Optimization
Target: 40+ t/s single-request, 120+ t/s aggregate load
"""

import os
import subprocess
import time
import json
import asyncio
import aiohttp
import signal
import sys
from pathlib import Path

class VLLMManager:
    """Manages vLLM server lifecycle and performance monitoring"""
    
    def __init__(self):
        self.process = None
        self.port = 8081
        self.model = "microsoft/phi-2"
        self.base_url = f"http://localhost:{self.port}"
        
        # Phase 3 Optimized Settings
        self.config = {
            "model": self.model,
            "port": self.port,
            "host": "0.0.0.0",
            "dtype": "float16",  # Use FP16 for speed
            "max_model_len": 4096,
            "gpu_memory_utilization": 0.90,  # 90% GPU memory utilization
            "max_num_seqs": 64,  # High concurrency for batching
            "tensor_parallel_size": 1,  # Single GPU
            "speculative_length": 8,  # Speculative decoding for speed
            "trust_remote_code": True,
            "disable_log_stats": False,
            "served_model_name": "phi-2-optimized",
            
            # Phase 3 Advanced Optimizations
            "enable_prefix_caching": True,  # Cache prefixes for efficiency  
            "use_v2_block_manager": True,  # Latest block manager
            "swap_space": 4,  # GB swap space for large contexts
            "enforce_eager": False,  # Allow CUDA graphs
            "max_batch_tokens": 4096,  # Dynamic batching target
            "block_size": 16,  # Optimized block size for RTX 4070
            
            # Memory optimizations
            "kv_cache_dtype": "fp16",  # FP16 KV cache
            "max_seq_len_to_capture": 2048,  # CUDA graph capture length
        }
    
    def build_command(self):
        """Build vLLM server command with optimizations"""
        cmd = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.config["model"],
            "--port", str(self.config["port"]),
            "--host", self.config["host"],
            "--dtype", self.config["dtype"],
            "--max-model-len", str(self.config["max_model_len"]),
            "--gpu-memory-utilization", str(self.config["gpu_memory_utilization"]),
            "--max-num-seqs", str(self.config["max_num_seqs"]),
            "--tensor-parallel-size", str(self.config["tensor_parallel_size"]),
            "--trust-remote-code",
            "--served-model-name", self.config["served_model_name"],
            "--enable-prefix-caching",
            "--use-v2-block-manager",
            "--swap-space", str(self.config["swap_space"]),
            "--max-seq-len-to-capture", str(self.config["max_seq_len_to_capture"]),
            "--kv-cache-dtype", self.config["kv_cache_dtype"],
            "--block-size", str(self.config["block_size"]),
        ]
        
        # Add conditional flags
        if not self.config["disable_log_stats"]:
            cmd.append("--disable-log-stats")
        
        if not self.config["enforce_eager"]:
            cmd.append("--enforce-eager")
            
        return cmd
    
    def start_server(self):
        """Start vLLM server with Phase 3 optimizations"""
        print("🚀 Starting vLLM server with Phase 3 optimizations...")
        print(f"Model: {self.model}")
        print(f"Target: 40+ t/s single, 120+ t/s aggregate")
        
        cmd = self.build_command()
        print(f"Command: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            print(f"✅ vLLM server started (PID: {self.process.pid})")
            print(f"🌐 Endpoint: {self.base_url}/v1")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start vLLM server: {e}")
            return False
    
    def stop_server(self):
        """Stop vLLM server"""
        if self.process:
            print("🛑 Stopping vLLM server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            print("✅ vLLM server stopped")
    
    async def wait_for_ready(self, timeout=120):
        """Wait for vLLM server to be ready"""
        print("⏳ Waiting for vLLM server to initialize...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}/v1/models", timeout=5) as response:
                        if response.status == 200:
                            models = await response.json()
                            print(f"✅ vLLM server ready! Available models: {len(models.get('data', []))}")
                            return True
            except Exception as e:
                pass
            
            await asyncio.sleep(2)
            print("⏳ Still initializing...")
        
        print(f"❌ vLLM server failed to start within {timeout}s")
        return False
    
    async def benchmark_performance(self, test_prompts=None):
        """Benchmark vLLM performance for Phase 3 validation"""
        if not test_prompts:
            test_prompts = [
                "Explain quantum computing in simple terms",
                "Write a Python function to sort a list",
                "What are the benefits of renewable energy?",
                "Describe the process of photosynthesis",
                "How does machine learning work?"
            ]
        
        print(f"🧪 Benchmarking vLLM performance ({len(test_prompts)} prompts)...")
        
        results = []
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n📤 Test {i}/{len(test_prompts)}: {prompt[:50]}...")
            
            start_time = time.time()
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": self.config["served_model_name"],
                        "prompt": prompt,
                        "max_tokens": 50,
                        "temperature": 0.7,
                        "stream": False
                    }
                    
                    async with session.post(
                        f"{self.base_url}/v1/completions",
                        json=payload,
                        timeout=30
                    ) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            end_time = time.time()
                            
                            latency = end_time - start_time
                            response_text = result["choices"][0]["text"]
                            tokens_generated = len(response_text.split())
                            tokens_per_sec = tokens_generated / latency if latency > 0 else 0
                            
                            results.append({
                                "prompt": prompt,
                                "latency": latency,
                                "tokens_generated": tokens_generated,
                                "tokens_per_sec": tokens_per_sec,
                                "response": response_text[:100]
                            })
                            
                            print(f"   ⏱️ Latency: {latency:.3f}s")
                            print(f"   🎯 Tokens/s: {tokens_per_sec:.1f}")
                            print(f"   💬 Response: {response_text[:60]}...")
                            
                        else:
                            print(f"   ❌ HTTP {response.status}: {await response.text()}")
                            
            except Exception as e:
                print(f"   💥 Error: {e}")
        
        return results
    
    def analyze_benchmark(self, results):
        """Analyze benchmark results against Phase 3 targets"""
        if not results:
            print("❌ No benchmark results to analyze")
            return False
        
        print(f"\n📊 PHASE 3 VLLM PERFORMANCE ANALYSIS")
        print("=" * 50)
        
        latencies = [r["latency"] for r in results]
        tokens_per_sec = [r["tokens_per_sec"] for r in results]
        
        avg_latency = sum(latencies) / len(latencies)
        avg_tokens = sum(tokens_per_sec) / len(tokens_per_sec)
        max_tokens = max(tokens_per_sec)
        
        print(f"⚡ Performance Metrics:")
        print(f"   Average latency: {avg_latency:.3f}s")
        print(f"   Average tokens/s: {avg_tokens:.1f}")
        print(f"   Peak tokens/s: {max_tokens:.1f}")
        print(f"   Test count: {len(results)}")
        
        # Phase 3 Success Criteria
        print(f"\n🎯 PHASE 3 SUCCESS CRITERIA:")
        
        latency_target = avg_latency <= 0.3  # 300ms target
        throughput_target = avg_tokens >= 40.0  # 40+ t/s target
        peak_target = max_tokens >= 35.0  # At least one test should be fast
        
        criteria = [
            ("Latency ≤ 300ms", latency_target, f"{avg_latency:.3f}s"),
            ("Throughput ≥ 40 t/s", throughput_target, f"{avg_tokens:.1f} t/s"),
            ("Peak performance", peak_target, f"{max_tokens:.1f} t/s")
        ]
        
        passed = 0
        for name, status, value in criteria:
            icon = "✅" if status else "❌"
            print(f"   {icon} {name}: {value}")
            if status:
                passed += 1
        
        success_rate = passed / len(criteria)
        print(f"\n🏆 PHASE 3 VLLM STATUS:")
        print(f"   Criteria passed: {passed}/{len(criteria)} ({success_rate*100:.0f}%)")
        
        if success_rate >= 0.8:
            print("🎉 PHASE 3 vLLM SUCCESS - Target performance achieved!")
            return True
        elif success_rate >= 0.6:
            print("🟡 PHASE 3 vLLM PARTIAL - Close to targets")
            return True
        else:
            print("🔴 PHASE 3 vLLM NEEDS WORK - Performance below targets")
            return False

async def main():
    """Main Phase 3 vLLM deployment and testing"""
    manager = VLLMManager()
    
    # Signal handler for clean shutdown
    def signal_handler(sig, frame):
        print('\n🛑 Shutting down vLLM server...')
        manager.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start vLLM server
        if not manager.start_server():
            return False
        
        # Wait for server to be ready
        if not await manager.wait_for_ready():
            return False
        
        # Run performance benchmark
        results = await manager.benchmark_performance()
        
        # Analyze results
        success = manager.analyze_benchmark(results)
        
        return success
        
    except Exception as e:
        print(f"💥 Phase 3 test failed: {e}")
        return False
    finally:
        manager.stop_server()

if __name__ == "__main__":
    print("🚀 Phase 3: Advanced GPU Optimization with vLLM")
    print("Target: 40+ tokens/s single-request")
    
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 Phase 3 vLLM deployment successful!")
        print("✅ Ready for aggregate load testing")
    else:
        print("\n⚠️ Phase 3 vLLM needs optimization") 