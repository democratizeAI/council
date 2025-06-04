#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoGen Warmup Script - Track ① Step D
=======================================

Eliminates the 300ms "first request" spike by pre-compiling CUDA kernels
and warming up all inference paths with diverse prompts.
"""

import asyncio
import time
import random
import requests
import json
from typing import List

# Diverse warmup prompts to cover different model paths and kernel patterns
WARMUP_PROMPTS = [
    # Math prompts (trigger math specialist)
    "2+2", "Calculate 15*23", "What is 144/12?", "Solve x+5=12",
    
    # Code prompts (trigger code specialist)  
    "def hello():", "print('hello')", "for i in range(5):", "import numpy",
    
    # Logic prompts (trigger logic specialist)
    "If A then B", "All cats are mammals", "P implies Q", "True or False",
    
    # Knowledge prompts (trigger knowledge specialist)
    "What is Python?", "Explain AI", "Tell me about oceans", "History of computing",
    
    # Complex prompts (trigger voting)
    "Explain step by step why neural networks work effectively",
    "Analyze the reasoning behind quantum computing advantages",
    "Compare and contrast different machine learning paradigms",
    "Why do we need distributed systems in modern computing?",
    
    # Simple prompts (trigger smart routing)
    "Hello", "Hi there", "Good morning", "Test", "1+1", "Yes", "No", "OK",
    
    # Edge cases
    "x", "a"*100, "The quick brown fox jumps", "🚀", "Test 123",
    
    # Mixed complexity
    "Calculate the area of a circle with radius 5 and explain the formula",
    "Write Python code to sort a list and explain the algorithm",
]

class WarmupClient:
    """Client for warming up the AutoGen API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def warmup_request(self, prompt: str, endpoint: str = "/hybrid") -> dict:
        """Send a single warmup request"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {"prompt": prompt}
                async with session.post(
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def warmup_all_endpoints(self) -> dict:
        """Warm up all API endpoints"""
        print("🔥 Warming up API endpoints...")
        
        endpoints = ["/hybrid", "/orchestrate", "/vote", "/models", "/budget"]
        results = {}
        
        for endpoint in endpoints:
            if endpoint in ["/models", "/budget"]:
                # GET endpoints
                try:
                    import aiohttp
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            results[endpoint] = response.status == 200
                except:
                    results[endpoint] = False
            else:
                # POST endpoints
                test_prompt = "warmup test"
                result = await self.warmup_request(test_prompt, endpoint)
                results[endpoint] = "error" not in result
        
        return results
    
    async def warmup_models(self, num_prompts: int = 32) -> dict:
        """Warm up model inference with diverse prompts"""
        print(f"🚀 Warming up models with {num_prompts} diverse prompts...")
        
        # Select random prompts
        selected_prompts = random.sample(WARMUP_PROMPTS, min(num_prompts, len(WARMUP_PROMPTS)))
        
        results = {
            "total_prompts": len(selected_prompts),
            "successful": 0,
            "failed": 0,
            "total_time_ms": 0,
            "avg_latency_ms": 0
        }
        
        start_time = time.time()
        
        # Process prompts in small batches to avoid overwhelming
        batch_size = 4
        for i in range(0, len(selected_prompts), batch_size):
            batch = selected_prompts[i:i+batch_size]
            
            # Send batch concurrently
            tasks = [self.warmup_request(prompt) for prompt in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception) or "error" in result:
                    results["failed"] += 1
                    print(f"⚠️ Warmup failed for '{batch[j][:20]}...': {result}")
                else:
                    results["successful"] += 1
                    if "latency_ms" in result:
                        results["total_time_ms"] += result["latency_ms"]
            
            # Small delay between batches
            await asyncio.sleep(0.1)
        
        results["avg_latency_ms"] = results["total_time_ms"] / max(results["successful"], 1)
        
        print(f"✅ Warmup complete: {results['successful']}/{results['total_prompts']} successful")
        print(f"📊 Average latency: {results['avg_latency_ms']:.1f}ms")
        
        return results
    
    async def test_streaming(self) -> bool:
        """Test streaming endpoint"""
        print("🌊 Testing streaming endpoint...")
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {"prompt": "Stream test: count to 5"}
                async with session.post(
                    f"{self.base_url}/hybrid?stream=true",
                    json=payload,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        # Read streaming response
                        chunks = 0
                        async for chunk in response.content.iter_any():
                            if chunk:
                                chunks += 1
                                if chunks >= 3:  # Stop after a few chunks
                                    break
                        print(f"✅ Streaming working: received {chunks} chunks")
                        return True
                    else:
                        print(f"❌ Streaming failed: HTTP {response.status}")
                        return False
        except Exception as e:
            print(f"❌ Streaming test failed: {e}")
            return False

async def main():
    """Main warmup routine"""
    print("=" * 60)
    print("🔥 AutoGen Warmup Script - Track ① Step D")
    print("=" * 60)
    
    client = WarmupClient()
    
    # 1. Test server connectivity
    print("📡 Testing server connectivity...")
    try:
        health_result = await client.warmup_request("connectivity test")
        if "error" not in health_result:
            print("✅ Server is responsive")
        else:
            print(f"❌ Server connectivity issue: {health_result}")
            return 1
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return 1
    
    # 2. Warm up all endpoints
    endpoint_results = await client.warmup_all_endpoints()
    working_endpoints = sum(1 for status in endpoint_results.values() if status)
    print(f"📡 Endpoints working: {working_endpoints}/{len(endpoint_results)}")
    
    # 3. Warm up models with diverse prompts
    model_results = await client.warmup_models(num_prompts=32)
    
    # 4. Test streaming
    streaming_ok = await client.test_streaming()
    
    # 5. Final validation
    print("\n" + "=" * 60)
    print("📊 WARMUP SUMMARY")
    print("=" * 60)
    print(f"✅ Models warmed up: {model_results['successful']}/{model_results['total_prompts']}")
    print(f"⚡ Average latency: {model_results['avg_latency_ms']:.1f}ms")
    print(f"📡 Endpoints working: {working_endpoints}/{len(endpoint_results)}")
    print(f"🌊 Streaming: {'✅ Working' if streaming_ok else '❌ Failed'}")
    
    if model_results['successful'] >= 24 and working_endpoints >= 4:
        print("\n🎉 Warmup successful! CUDA kernels compiled, system ready.")
        return 0
    else:
        print("\n⚠️ Warmup incomplete - some issues detected")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 