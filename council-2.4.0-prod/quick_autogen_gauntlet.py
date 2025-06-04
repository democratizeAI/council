#!/usr/bin/env python3
"""
Quick AutoGen Gauntlet - Direct Testing
=======================================

Test our AutoGen skills directly without needing a web server.
"""

import asyncio
import time
import random
from datetime import datetime
from pathlib import Path
import json

# Import our AutoGen skills directly
from fork.swarm_autogen.router_cascade import route_and_execute

# Quick test prompts across domains
TEST_PROMPTS = [
    # Math (high value)
    ("What is 8 factorial?", "math"),
    ("Calculate 25% of 240", "math"), 
    ("What is the GCD of 48 and 72?", "math"),
    ("Find the area of a circle with radius 12", "math"),
    
    # Code generation  
    ("Write a function to calculate GCD of two numbers", "code"),
    ("Write a function to add two numbers", "code"),
    ("Implement a bubble sort algorithm", "code"),
    
    # Logic reasoning
    ("If A is south of B and B south of C, where is A?", "logic"),
    ("Is John the parent of Mary?", "logic"),
    
    # Knowledge
    ("What is the speed of light?", "knowledge"),
    ("What is machine learning?", "knowledge"),
    ("Explain how photosynthesis works", "knowledge"),
    
    # Reasoning
    ("Why might a company choose to outsource manufacturing?", "reasoning"),
    ("What are the pros and cons of renewable energy?", "reasoning"),
    
    # Planning
    ("Plan a 7-day vacation to Japan for two people with a $3000 budget", "planning"),
]

async def run_quick_gauntlet(max_prompts: int = 15):
    """Run quick gauntlet test"""
    print("🚢 QUICK AUTOGEN GAUNTLET")
    print("=" * 50)
    print(f"⏰ Start time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"📊 Testing {min(max_prompts, len(TEST_PROMPTS))} prompts")
    print()
    
    # Shuffle and select prompts
    test_prompts = TEST_PROMPTS[:max_prompts]
    random.shuffle(test_prompts)
    
    results = []
    total_time = 0.0
    successes = 0
    
    for i, (prompt, domain) in enumerate(test_prompts, 1):
        print(f"📝 Test {i}/{len(test_prompts)}: {domain}")
        print(f"   Q: {prompt[:60]}...")
        
        start_time = time.time()
        try:
            # Route and execute with our AutoGen cascade
            result = await route_and_execute(prompt)
            
            latency = (time.time() - start_time) * 1000
            total_time += latency
            
            # Extract key info
            answer = result.get("answer", "No answer")[:100]
            skill_used = result.get("skill_type", "unknown")
            confidence = result.get("confidence", 0.0)
            
            print(f"   A: {answer}...")
            print(f"   ⚡ {latency:.0f}ms | 🎯 {skill_used} | 📊 {confidence:.2f}")
            
            successes += 1
            
            results.append({
                "prompt": prompt,
                "domain": domain,
                "answer": answer,
                "skill_used": skill_used,
                "latency_ms": latency,
                "confidence": confidence,
                "status": "success"
            })
            
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            total_time += latency
            
            print(f"   ❌ Error: {str(e)[:50]}...")
            print(f"   ⚡ {latency:.0f}ms | 🎯 error")
            
            results.append({
                "prompt": prompt,
                "domain": domain,
                "answer": f"Error: {e}",
                "skill_used": "error",
                "latency_ms": latency,
                "confidence": 0.0,
                "status": "error"
            })
        
        print()
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    # Final statistics
    avg_latency = total_time / len(test_prompts)
    success_rate = successes / len(test_prompts)
    
    print("🏁 QUICK GAUNTLET COMPLETE!")
    print("=" * 50)
    print(f"✅ Success rate: {success_rate*100:.0f}% ({successes}/{len(test_prompts)})")
    print(f"⚡ Avg latency: {avg_latency:.0f}ms")
    print(f"⏱️ Total time: {total_time/1000:.1f}s")
    
    # Breakdown by domain
    domain_stats = {}
    for result in results:
        domain = result["domain"]
        if domain not in domain_stats:
            domain_stats[domain] = {"count": 0, "total_latency": 0, "successes": 0}
        
        domain_stats[domain]["count"] += 1
        domain_stats[domain]["total_latency"] += result["latency_ms"]
        if result["status"] == "success":
            domain_stats[domain]["successes"] += 1
    
    print(f"\n📊 Domain Breakdown:")
    for domain, stats in domain_stats.items():
        avg_lat = stats["total_latency"] / stats["count"]
        success_pct = stats["successes"] / stats["count"] * 100
        print(f"   {domain}: {success_pct:.0f}% success, {avg_lat:.0f}ms avg")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"quick_gauntlet_{timestamp}.json"
    
    final_report = {
        "timestamp": datetime.now().isoformat(),
        "total_prompts": len(test_prompts),
        "success_rate": success_rate,
        "avg_latency_ms": avg_latency,
        "domain_breakdown": domain_stats,
        "detailed_results": results
    }
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print(f"📄 Report saved: {report_file}")
    
    return final_report

if __name__ == "__main__":
    import sys
    max_prompts = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    asyncio.run(run_quick_gauntlet(max_prompts)) 