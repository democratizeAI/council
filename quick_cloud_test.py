#!/usr/bin/env python3
"""Quick test to verify cloud fallback is working consistently"""

import asyncio
import aiohttp
import json

async def test_cloud():
    async with aiohttp.ClientSession() as session:
        for i in range(3):
            payload = {
                "prompt": f"What is the factorial of {5+i}?",
                "preferred_models": ["tinyllama_1b"]
            }
            
            async with session.post(
                "http://localhost:8000/hybrid",
                json=payload,
                timeout=30
            ) as resp:
                data = await resp.json()
                provider = data.get("provider", "unknown")
                cloud_consulted = data.get("cloud_consulted", False)
                response_text = data.get("text", "")[:100]
                
                print(f"Test {i+1}: Provider={provider}, Cloud={cloud_consulted}")
                print(f"Response: {response_text}...")
                print("---")

if __name__ == "__main__":
    asyncio.run(test_cloud()) 