#!/usr/bin/env python3
"""
Test script to show raw responses from SwarmAI council
"""

import asyncio
import aiohttp
import json

async def test_swarm_responses():
    """Test a few sample questions to see raw SwarmAI responses"""
    
    test_questions = [
        {
            "type": "math", 
            "prompt": "Calculate the result of 15 * 16 and explain your reasoning."
        },
        {
            "type": "reasoning",
            "prompt": "If all roses are flowers and some flowers are red, what can we conclude about roses?"
        },
        {
            "type": "simple",
            "prompt": "What is 2 + 2?"
        }
    ]
    
    print("🚀 Testing SwarmAI Raw Responses")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        for i, question in enumerate(test_questions, 1):
            print(f"\n📝 Question {i} ({question['type']}):")
            print(f"   {question['prompt']}")
            print(f"\n🤖 SwarmAI Response:")
            
            try:
                async with session.post(
                    "http://localhost:8000/hybrid",
                    json={
                        "prompt": question['prompt'],
                        "enable_council": True,
                        "force_council": False,
                        "max_tokens": 200
                    },
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        raw_response = data.get("text", "")
                        model_used = data.get("model_used", "unknown")
                        latency_ms = data.get("hybrid_latency_ms", 0)
                        cost_cents = data.get("cost_cents", 0)
                        
                        print(f"   Model: {model_used}")
                        print(f"   Latency: {latency_ms:.0f}ms")
                        print(f"   Cost: ${cost_cents/100:.4f}")
                        print(f"   Raw Answer: \"{raw_response}\"")
                        
                    else:
                        error_text = await response.text()
                        print(f"   ❌ Error: HTTP {response.status} - {error_text}")
                        
            except Exception as e:
                print(f"   ❌ Connection Error: {e}")
            
            print("-" * 50)

if __name__ == "__main__":
    print("Testing SwarmAI raw responses...")
    print("Make sure the SwarmAI server is running!")
    
    try:
        asyncio.run(test_swarm_responses())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        print("Is the SwarmAI server running? Try: python start_swarm_server.py") 