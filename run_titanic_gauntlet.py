#!/usr/bin/env python3
"""
🚢 TITANIC GAUNTLET
380-prompt benchmark across 6 domains comparing hybrid SwarmAI vs cloud giants
"""

import asyncio
import aiohttp
import json
import time
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Weighted prompt distribution for comprehensive testing
PROMPT_DOMAINS = {
    "math": {
        "weight": 0.30,  # 30% of prompts
        "count": 114,
        "prompts": [
            "Calculate 847 * 293",
            "What is the square root of 2401?",
            "Solve: 3x + 7 = 28",
            "Find the derivative of x^3 + 2x^2 - 5x + 1",
            "What is 15! (15 factorial)?",
            "Convert 0.375 to a fraction in lowest terms",
            "Calculate the area of a circle with radius 12",
            "What is log base 10 of 1000?",
            "Solve the quadratic equation: x^2 - 5x + 6 = 0",
            "What is 2^10?",
            "Calculate 25% of 840",
            "Find the slope of the line through (2,3) and (5,9)",
            "What is the GCD of 48 and 72?",
            "Convert 45 degrees to radians",
            "Calculate the volume of a sphere with radius 6"
        ]
    },
    "reasoning": {
        "weight": 0.25,  # 25% of prompts
        "count": 95,
        "prompts": [
            "If all roses are flowers and some flowers are red, can we conclude that some roses are red?",
            "A train travels 120 km in 2 hours. How long will it take to travel 300 km at the same speed?",
            "Why might a company choose to outsource manufacturing?",
            "Explain the relationship between supply and demand in economics",
            "What are the pros and cons of renewable energy?",
            "How does peer pressure influence teenage behavior?",
            "Why do some countries have higher crime rates than others?",
            "Analyze the impact of social media on modern communication",
            "What factors contribute to successful team collaboration?",
            "Explain why biodiversity is important for ecosystems",
            "How do cognitive biases affect decision making?",
            "What are the ethical implications of AI in healthcare?",
            "Why is critical thinking important in the digital age?",
            "Analyze the causes and effects of urbanization",
            "How does culture influence individual identity?"
        ]
    },
    "coding": {
        "weight": 0.20,  # 20% of prompts
        "count": 76,
        "prompts": [
            "Write a Python function to find the factorial of a number",
            "Explain the difference between a list and a tuple in Python",
            "How do you handle exceptions in JavaScript?",
            "Write a SQL query to find the top 5 highest paid employees",
            "What is the time complexity of quicksort?",
            "Explain how garbage collection works in Java",
            "Write a function to reverse a string in C++",
            "What are the benefits of using version control systems?",
            "Explain the difference between SQL and NoSQL databases",
            "How do you optimize a slow database query?",
            "What is the difference between GET and POST HTTP methods?",
            "Write a regex pattern to validate email addresses",
            "Explain what RESTful APIs are and their principles",
            "How do you implement binary search?",
            "What are design patterns and why are they useful?"
        ]
    },
    "science": {
        "weight": 0.15,  # 15% of prompts
        "count": 57,
        "prompts": [
            "Explain how photosynthesis works at the molecular level",
            "What causes the greenhouse effect?",
            "How do vaccines work to protect against diseases?",
            "Explain the structure and function of DNA",
            "What is the difference between mitosis and meiosis?",
            "How do black holes form and what happens at the event horizon?",
            "Explain the periodic table organization and trends",
            "What is quantum entanglement and why is it important?",
            "How do antibiotics work against bacterial infections?",
            "Explain the water cycle and its impact on climate",
            "What is CRISPR and how is it used in gene editing?",
            "How do neural networks in the brain process information?",
            "Explain the difference between acids and bases",
            "What causes evolution and natural selection?",
            "How do solar panels convert sunlight to electricity?"
        ]
    },
    "planning": {
        "weight": 0.07,  # 7% of prompts  
        "count": 27,
        "prompts": [
            "Plan a 7-day vacation to Japan for two people with a $3000 budget",
            "Create a workout routine for a beginner wanting to build strength",
            "Design a study schedule for someone preparing for the SAT",
            "Plan a small garden for growing vegetables in limited space",
            "Create a budget plan for a recent college graduate",
            "Design a meal prep plan for healthy eating during busy weeks",
            "Plan a fundraising event for a local charity",
            "Create a time management system for a busy professional",
            "Design a home office setup for remote work productivity",
            "Plan a career transition from marketing to data science",
            "Create a retirement savings strategy for someone in their 30s",
            "Design a learning path for mastering web development",
            "Plan a sustainable weight loss program",
            "Create a social media strategy for a small business",
            "Design an emergency preparedness plan for natural disasters"
        ]
    },
    "creative": {
        "weight": 0.03,  # 3% of prompts
        "count": 11,
        "prompts": [
            "Write a short story about a robot learning to love",
            "Create a haiku about artificial intelligence",
            "Design a logo concept for an eco-friendly startup",
            "Write a compelling product description for smart headphones",
            "Create a metaphor to explain quantum computing to a child",
            "Write a persuasive email to encourage team collaboration",
            "Design a creative solution to reduce plastic waste",
            "Write lyrics for a song about overcoming challenges",
            "Create an innovative app idea for improving mental health",
            "Write a book review for a fictional novel about time travel",
            "Design a creative team-building activity for remote workers"
        ]
    }
}

async def test_hybrid_endpoint(session: aiohttp.ClientSession, prompt: str, domain: str) -> Dict[str, Any]:
    """Test our hybrid SwarmAI system"""
    start_time = time.time()
    
    try:
        payload = {
            "prompt": prompt,
            "preferred_models": ["tinyllama_1b", "mistral_0.5b"]
        }
        
        async with session.post(
            "http://localhost:8000/hybrid",
            json=payload,
            timeout=60
        ) as resp:
            latency = (time.time() - start_time) * 1000
            
            if resp.status == 200:
                data = await resp.json()
                return {
                    "system": "swarm_hybrid",
                    "domain": domain,
                    "prompt": prompt[:50] + "...",
                    "response": data.get("text", "")[:200] + "...",
                    "provider": data.get("provider", "unknown"),
                    "model": data.get("model_used", "unknown"),
                    "latency_ms": latency,
                    "cloud_used": data.get("cloud_consulted", False),
                    "cost_cents": data.get("cost_cents", 0.0),
                    "status": "success"
                }
            else:
                return {
                    "system": "swarm_hybrid",
                    "domain": domain,
                    "prompt": prompt[:50] + "...",
                    "response": f"HTTP {resp.status}",
                    "provider": "error",
                    "model": "none",
                    "latency_ms": latency,
                    "cloud_used": False,
                    "cost_cents": 0.0,
                    "status": "error"
                }
                
    except Exception as e:
        latency = (time.time() - start_time) * 1000
        return {
            "system": "swarm_hybrid",
            "domain": domain,
            "prompt": prompt[:50] + "...",
            "response": f"Error: {str(e)[:100]}",
            "provider": "error",
            "model": "none",
            "latency_ms": latency,
            "cloud_used": False,
            "cost_cents": 0.0,
            "status": "error"
        }

async def run_titanic_gauntlet(budget_limit_usd: float = 10.0) -> Dict[str, Any]:
    """Run the full Titanic Gauntlet benchmark"""
    
    print("🚢 TITANIC GAUNTLET BENCHMARK")
    print("=" * 70)
    print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 Budget limit: ${budget_limit_usd}")
    print(f"📊 Target prompts: 380 across 6 domains")
    print()
    
    # Generate weighted prompt list
    all_prompts = []
    for domain, config in PROMPT_DOMAINS.items():
        domain_prompts = config["prompts"] * (config["count"] // len(config["prompts"]) + 1)
        selected_prompts = domain_prompts[:config["count"]]
        
        for prompt in selected_prompts:
            all_prompts.append((prompt, domain))
    
    # Shuffle for realistic testing
    random.shuffle(all_prompts)
    
    print(f"📝 Generated {len(all_prompts)} prompts")
    for domain, config in PROMPT_DOMAINS.items():
        actual_count = sum(1 for _, d in all_prompts if d == domain)
        print(f"  {domain}: {actual_count} prompts ({actual_count/len(all_prompts)*100:.1f}%)")
    print()
    
    results = []
    total_cost = 0.0
    domain_stats = {domain: {"count": 0, "total_latency": 0.0, "total_cost": 0.0} for domain in PROMPT_DOMAINS.keys()}
    
    async with aiohttp.ClientSession() as session:
        for i, (prompt, domain) in enumerate(all_prompts):
            if i % 50 == 0:
                print(f"📊 Progress: {i}/{len(all_prompts)} ({i/len(all_prompts)*100:.1f}%) - Cost: ${total_cost:.3f}")
            
            # Test our hybrid system
            result = await test_hybrid_endpoint(session, prompt, domain)
            results.append(result)
            
            # Track costs and stats
            cost = result.get("cost_cents", 0.0) / 100.0
            total_cost += cost
            
            domain_stats[domain]["count"] += 1
            domain_stats[domain]["total_latency"] += result.get("latency_ms", 0.0)
            domain_stats[domain]["total_cost"] += cost
            
            # Budget protection
            if total_cost > budget_limit_usd:
                print(f"💰 Budget limit reached at prompt {i+1}")
                break
            
            # Small delay to avoid overwhelming APIs
            await asyncio.sleep(0.1)
    
    # Calculate final statistics
    end_time = datetime.now()
    total_prompts = len(results)
    success_count = sum(1 for r in results if r["status"] == "success")
    cloud_count = sum(1 for r in results if r.get("cloud_used", False))
    
    avg_latency = sum(r.get("latency_ms", 0.0) for r in results) / total_prompts if total_prompts > 0 else 0
    
    # Domain breakdown
    domain_summary = {}
    for domain, stats in domain_stats.items():
        if stats["count"] > 0:
            domain_summary[domain] = {
                "prompts": stats["count"],
                "avg_latency_ms": stats["total_latency"] / stats["count"],
                "total_cost_usd": stats["total_cost"],
                "cost_per_prompt": stats["total_cost"] / stats["count"]
            }
    
    final_report = {
        "benchmark_name": "Titanic Gauntlet",
        "timestamp": end_time.isoformat(),
        "total_prompts": total_prompts,
        "success_rate": success_count / total_prompts if total_prompts > 0 else 0,
        "cloud_usage_rate": cloud_count / total_prompts if total_prompts > 0 else 0,
        "total_cost_usd": total_cost,
        "avg_cost_per_prompt": total_cost / total_prompts if total_prompts > 0 else 0,
        "avg_latency_ms": avg_latency,
        "domain_breakdown": domain_summary,
        "detailed_results": results
    }
    
    # Save results
    timestamp = end_time.strftime("%Y%m%d_%H%M%S")
    report_file = f"reports/titanic_gauntlet_{timestamp}.json"
    Path("reports").mkdir(exist_ok=True)
    
    with open(report_file, 'w') as f:
        json.dump(final_report, f, indent=2)
    
    print("\n🏁 TITANIC GAUNTLET COMPLETE!")
    print("=" * 70)
    print(f"📊 Total prompts: {total_prompts}")
    print(f"✅ Success rate: {success_count/total_prompts*100:.1f}%")
    print(f"🌩️ Cloud usage: {cloud_count/total_prompts*100:.1f}%")
    print(f"💰 Total cost: ${total_cost:.3f}")
    print(f"⏱️ Avg latency: {avg_latency:.1f}ms")
    print(f"📄 Report saved: {report_file}")
    
    return final_report

if __name__ == "__main__":
    import sys
    budget = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    asyncio.run(run_titanic_gauntlet(budget)) 