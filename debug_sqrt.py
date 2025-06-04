#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(''), 'fork', 'swarm_autogen'))

from skills.lightning_math import LightningMathAgent
import asyncio

async def test_math_direct():
    agent = LightningMathAgent()
    
    # Test classification
    problem_type = agent.classify_problem("What is the square root of 64?")
    print(f"Classification: {problem_type}")
    
    # Test solver directly
    solution = await agent.solve_math_problem("What is the square root of 64?")
    print(f"Answer: {solution.answer}")
    print(f"Steps: {solution.steps}")
    print(f"Type: {solution.problem_type}")
    print(f"Confidence: {solution.confidence}")

if __name__ == "__main__":
    asyncio.run(test_math_direct())

# Also test via API
import requests
import json

print("\n--- API Test ---")
response = requests.post(
    "http://localhost:8000/hybrid",
    json={"prompt": "What is the square root of 64?"},
    timeout=10
)

print("Response:", response.status_code)
if response.status_code == 200:
    result = response.json()
    print("Text:", result["text"])
    print("Model:", result.get("model", "unknown"))
    print("Skill:", result.get("skill_type", "unknown"))
    print("Meta:", result.get("meta", {}))
else:
    print("Error:", response.text) 