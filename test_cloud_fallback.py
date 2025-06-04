#!/usr/bin/env python3
"""
Quick Cloud Fallback Test
Tests if our cloud APIs are working with real responses
"""

import asyncio
import aiohttp
import json
import time

async def test_cloud_fallback():
    """Test cloud fallback with real API responses"""
    
    test_cases = [
        {
            "prompt": "What is 8! (8 factorial)?",
            "expected_keywords": ["40320", "factorial", "8!"]
        },
        {
            "prompt": "2+2?", 
            "expected_keywords": ["4", "four", "equals"]
        },
        {
            "prompt": "What is the capital of France?",
            "expected_keywords": ["Paris", "capital", "France"]
        }
    ]
    
    print("🧪 CLOUD FALLBACK TEST")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {test['prompt']}")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "prompt": test["prompt"],
                    "preferred_models": ["tinyllama_1b"]  # Will trigger cloud fallback
                }
                
                start_time = time.time()
                
                async with session.post(
                    "http://localhost:8000/hybrid",
                    json=payload,
                    timeout=60
                ) as resp:
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    if resp.status == 200:
                        data = await resp.json()
                        
                        response_text = data.get("text", "")
                        provider = data.get("provider", "unknown")
                        model_used = data.get("model_used", "unknown")
                        cloud_consulted = data.get("cloud_consulted", False)
                        
                        print(f"✅ Status: {resp.status}")
                        print(f"🎯 Provider: {provider}")
                        print(f"🤖 Model: {model_used}")
                        print(f"🌩️ Cloud consulted: {cloud_consulted}")
                        print(f"⏱️ Latency: {latency_ms:.1f}ms")
                        print(f"💬 Response: {response_text[:200]}...")
                        
                        # Check if this is a real response (not template)
                        if "Response from " in response_text or "[TEMPLATE]" in response_text:
                            print("⚠️ WARNING: Template response detected - not real cloud inference")
                        elif provider.startswith("cloud_"):
                            print("🎉 SUCCESS: Real cloud response!")
                        else:
                            print("⚠️ WARNING: Not using cloud provider")
                        
                    else:
                        print(f"❌ HTTP Error: {resp.status}")
                        error_text = await resp.text()
                        print(f"Error: {error_text[:200]}")
                        
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print("\n🏁 Cloud fallback test complete!")

if __name__ == "__main__":
    asyncio.run(test_cloud_fallback()) 