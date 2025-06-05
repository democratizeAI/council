#!/usr/bin/env python3
"""
🧪 10-Prompt Smoke Test
Quick validation that GPU optimizations are working before full Titanic suite
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from pathlib import Path

# Quick test prompts covering different skills
TEST_PROMPTS = [
    ("What is 17 * 23?", "math"),
    ("Write a hello world function", "code"), 
    ("What is the capital of France?", "knowledge"),
    ("If A > B and B > C, who is smallest?", "logic"),
    ("What is 25% of 80?", "math"),
    ("Create a function to add two numbers", "code"),
    ("What is photosynthesis?", "knowledge"),
    ("If it's raining then take umbrella. It's raining. What to do?", "logic"),
    ("What is the square root of 144?", "math"),
    ("How do I learn Python?", "general")
]

async def test_prompt(session: aiohttp.ClientSession, prompt: str, expected_skill: str) -> dict:
    """Test a single prompt against the router"""
    start_time = time.time()
    
    try:
        payload = {"prompt": prompt}
        
        # Try voting endpoint first, fallback to hybrid
        async with session.post(
            "http://localhost:8000/vote",
            json=payload,
            timeout=30  # Reduced timeout for smoke test
        ) as resp:
            latency_ms = (time.time() - start_time) * 1000
            
            if resp.status == 200:
                data = await resp.json()
                return {
                    "prompt": prompt[:50],
                    "expected_skill": expected_skill,
                    "response": data.get("text", "")[:100],
                    "model": data.get("model", "unknown"),
                    "confidence": data.get("confidence", 0.0),
                    "latency_ms": latency_ms,
                    "cost_usd": data.get("cost_usd", 0.0),
                    "cached": data.get("cached", False),
                    "status": "success"
                }
            else:
                return {
                    "prompt": prompt[:50],
                    "expected_skill": expected_skill,
                    "response": f"HTTP {resp.status}",
                    "model": "error",
                    "confidence": 0.0,
                    "latency_ms": latency_ms,
                    "cost_usd": 0.0,
                    "cached": False,
                    "status": "error"
                }
                
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "prompt": prompt[:50],
            "expected_skill": expected_skill,
            "response": f"Error: {str(e)[:50]}",
            "model": "error",
            "confidence": 0.0,
            "latency_ms": latency_ms,
            "cost_usd": 0.0,
            "cached": False,
            "status": "error"
        }

async def run_smoke_test():
    """Run the 10-prompt smoke test"""
    print("🧪 10-PROMPT SMOKE TEST")
    print("=" * 50)
    print(f"⏰ Start: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 Testing GPU optimizations with CUDA config")
    print()
    
    results = []
    total_cost = 0.0
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        for i, (prompt, expected_skill) in enumerate(TEST_PROMPTS):
            print(f"🔬 Test {i+1}/10: {prompt[:30]}...")
            
            result = await test_prompt(session, prompt, expected_skill)
            results.append(result)
            
            # Print immediate feedback
            status_icon = "✅" if result["status"] == "success" else "❌"
            latency = result["latency_ms"]
            cost = result["cost_usd"]
            total_cost += cost
            
            print(f"   {status_icon} {latency:.0f}ms, ${cost:.4f}, {result['model']}")
            
            # Small delay between requests
            await asyncio.sleep(0.5)
    
    duration = time.time() - start_time
    
    # Calculate statistics
    success_count = sum(1 for r in results if r["status"] == "success")
    avg_latency = sum(r["latency_ms"] for r in results) / len(results)
    p95_latency = sorted([r["latency_ms"] for r in results])[int(len(results) * 0.95)]
    
    print("\n🏁 SMOKE TEST RESULTS")
    print("=" * 50)
    print(f"✅ Success rate: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"⏱️ Avg latency: {avg_latency:.1f}ms")
    print(f"📊 P95 latency: {p95_latency:.1f}ms")
    print(f"💰 Total cost: ${total_cost:.4f}")
    print(f"⚡ Duration: {duration:.1f}s")
    
    # Performance targets
    target_success = 80  # 80% success rate
    target_p95 = 200     # 200ms P95 latency
    target_cost = 0.02   # $0.02 max cost
    
    print(f"\n🎯 TARGET ANALYSIS:")
    success_ok = success_count/len(results) >= target_success/100
    latency_ok = p95_latency <= target_p95
    cost_ok = total_cost <= target_cost
    
    print(f"   Success: {'✅' if success_ok else '❌'} {success_count/len(results)*100:.1f}% (target: ≥{target_success}%)")
    print(f"   P95 Latency: {'✅' if latency_ok else '❌'} {p95_latency:.1f}ms (target: ≤{target_p95}ms)")
    print(f"   Cost: {'✅' if cost_ok else '❌'} ${total_cost:.4f} (target: ≤${target_cost})")
    
    all_green = success_ok and latency_ok and cost_ok
    print(f"\n{'🟢 ALL GREEN - Ready for full Titanic!' if all_green else '🔴 NEEDS TUNING - Check targets above'}")
    
    # Save results
    report = {
        "test_name": "smoke_test_10",
        "timestamp": datetime.now().isoformat(),
        "total_prompts": len(results),
        "success_count": success_count,
        "success_rate": success_count / len(results),
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "total_cost_usd": total_cost,
        "duration_seconds": duration,
        "targets_met": {
            "success_rate": success_ok,
            "p95_latency": latency_ok,
            "total_cost": cost_ok,
            "all_green": all_green
        },
        "detailed_results": results
    }
    
    Path("reports").mkdir(exist_ok=True)
    report_file = f"reports/smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📁 Report: {report_file}")
    return all_green

if __name__ == "__main__":
    asyncio.run(run_smoke_test()) 