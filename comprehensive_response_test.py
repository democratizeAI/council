#!/usr/bin/env python3
"""
Comprehensive test to show raw SwarmAI responses across all gauntlet domains
This will help identify where the system is failing and needs improvement
"""

import asyncio
import aiohttp
import json
import time

# Real questions similar to those in the Titanic Gauntlet
GAUNTLET_QUESTIONS = [
    # MATH DOMAIN (30% weight)
    {
        "domain": "math",
        "prompt": "Calculate: 247 * 38. Show your work step by step.",
        "expected_type": "exact_calculation"
    },
    {
        "domain": "math", 
        "prompt": "If a triangle has sides of length 3, 4, and 5, what is its area?",
        "expected_type": "geometry"
    },
    {
        "domain": "math",
        "prompt": "Solve for x: 2x + 7 = 19",
        "expected_type": "algebra"
    },
    {
        "domain": "math",
        "prompt": "What is 15% of 240?",
        "expected_type": "percentage"
    },
    
    # REASONING DOMAIN (25% weight)
    {
        "domain": "reasoning",
        "prompt": "All birds have wings. Some birds can fly. Some things that can fly are not birds. What can we conclude about wings and flying?",
        "expected_type": "logical_deduction"
    },
    {
        "domain": "reasoning",
        "prompt": "If it's raining, then the ground gets wet. The ground is not wet. What can we conclude?",
        "expected_type": "modus_tollens"
    },
    {
        "domain": "reasoning",
        "prompt": "A farmer has chickens and rabbits. There are 35 heads and 94 legs total. How many chickens and how many rabbits?",
        "expected_type": "constraint_solving"
    },
    
    # CODING DOMAIN (20% weight)
    {
        "domain": "coding",
        "prompt": "Write a Python function that returns the factorial of a number n.",
        "expected_type": "algorithm_implementation"
    },
    {
        "domain": "coding",
        "prompt": "Debug this code: def reverse_string(s): return s[::-1] # What's wrong if it doesn't work for 'hello'?",
        "expected_type": "debugging" 
    },
    {
        "domain": "coding",
        "prompt": "What does this code do? def mystery(arr): return [x for x in arr if x % 2 == 0]",
        "expected_type": "code_comprehension"
    },
    
    # SCIENCE DOMAIN (15% weight)
    {
        "domain": "science",
        "prompt": "What is the molecular formula for glucose and how many carbon atoms does it contain?",
        "expected_type": "chemistry"
    },
    {
        "domain": "science",
        "prompt": "If a ball is dropped from 20 meters high, how long does it take to hit the ground? (g = 9.8 m/s²)",
        "expected_type": "physics"
    },
    {
        "domain": "science",
        "prompt": "What is the difference between mitosis and meiosis?",
        "expected_type": "biology"
    },
    
    # PLANNING DOMAIN (5% weight)
    {
        "domain": "planning",
        "prompt": "You need to get from New York to Tokyo, then to London, then back to New York. What's the most efficient route?",
        "expected_type": "route_optimization"
    },
    {
        "domain": "planning",
        "prompt": "Plan a 3-day trip to Paris with a $500 budget. What are the key priorities?",
        "expected_type": "resource_allocation"
    },
    
    # WRITING DOMAIN (5% weight)
    {
        "domain": "writing",
        "prompt": "Summarize the main themes of Romeo and Juliet in 2-3 sentences.",
        "expected_type": "literary_analysis"
    },
    {
        "domain": "writing",
        "prompt": "Write a professional email declining a job offer politely.",
        "expected_type": "professional_writing"
    }
]

async def test_comprehensive_responses():
    """Test SwarmAI responses across all domains"""
    
    print("🚀 COMPREHENSIVE SWARM AI RESPONSE TEST")
    print("=" * 60)
    print(f"Testing {len(GAUNTLET_QUESTIONS)} questions across 6 domains")
    print("This will show you exactly how your system responds and where it fails")
    print("=" * 60)
    
    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    await asyncio.sleep(5)
    
    domain_results = {}
    total_passed = 0
    total_questions = len(GAUNTLET_QUESTIONS)
    
    async with aiohttp.ClientSession() as session:
        for i, question in enumerate(GAUNTLET_QUESTIONS, 1):
            domain = question['domain']
            if domain not in domain_results:
                domain_results[domain] = {'passed': 0, 'total': 0, 'responses': []}
            
            print(f"\n🔍 QUESTION {i}/{total_questions} - {domain.upper()}")
            print(f"Type: {question['expected_type']}")
            print(f"Prompt: {question['prompt']}")
            print(f"{'='*50}")
            
            try:
                start_time = time.time()
                async with session.post(
                    "http://localhost:8000/hybrid",
                    json={
                        "prompt": question['prompt'],
                        "enable_council": True,
                        "force_council": False,
                        "max_tokens": 300
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        raw_response = data.get("text", "").strip()
                        model_used = data.get("model_used", "unknown")
                        cost_cents = data.get("cost_cents", 0)
                        
                        print(f"✅ SUCCESS")
                        print(f"   Model: {model_used}")
                        print(f"   Latency: {latency_ms:.0f}ms")
                        print(f"   Cost: ${cost_cents/100:.4f}")
                        print(f"   Response Length: {len(raw_response)} chars")
                        print(f"")
                        print(f"🤖 RAW RESPONSE:")
                        print(f"   \"{raw_response}\"")
                        
                        # Simple quality check
                        response_quality = assess_response_quality(question, raw_response)
                        print(f"")
                        print(f"📊 QUALITY ASSESSMENT: {response_quality['status']}")
                        print(f"   Reasoning: {response_quality['reason']}")
                        
                        if response_quality['status'] == 'GOOD':
                            total_passed += 1
                            domain_results[domain]['passed'] += 1
                        
                        domain_results[domain]['total'] += 1
                        domain_results[domain]['responses'].append({
                            'question': question['prompt'],
                            'response': raw_response,
                            'quality': response_quality,
                            'latency_ms': latency_ms,
                            'cost': cost_cents/100
                        })
                        
                    else:
                        error_text = await response.text()
                        print(f"❌ HTTP ERROR: {response.status}")
                        print(f"   Error: {error_text}")
                        domain_results[domain]['total'] += 1
                        
            except Exception as e:
                print(f"💥 CONNECTION ERROR: {e}")
                domain_results[domain]['total'] += 1
            
            print("=" * 60)
    
    # Summary
    print(f"\n📋 COMPREHENSIVE TEST SUMMARY")
    print(f"=" * 60)
    print(f"Overall: {total_passed}/{total_questions} ({total_passed/total_questions*100:.1f}%)")
    print()
    
    for domain, results in domain_results.items():
        if results['total'] > 0:
            accuracy = results['passed'] / results['total'] * 100
            print(f"{domain.upper():12}: {results['passed']}/{results['total']} ({accuracy:.1f}%)")
    
    print(f"\n💡 IMPROVEMENT RECOMMENDATIONS:")
    for domain, results in domain_results.items():
        if results['total'] > 0 and results['passed'] / results['total'] < 0.7:
            print(f"   ⚠️  {domain.upper()} needs work - low accuracy")
    
    print(f"\n📄 Detailed responses saved for analysis")
    
    # Save detailed results
    with open(f"comprehensive_test_results_{int(time.time())}.json", "w") as f:
        json.dump(domain_results, f, indent=2)

def assess_response_quality(question, response):
    """Simple assessment of response quality"""
    domain = question['domain']
    response_lower = response.lower()
    
    if len(response.strip()) < 5:
        return {"status": "POOR", "reason": "Response too short"}
    
    if domain == "math":
        # Look for numbers, calculations, mathematical terms
        if any(char.isdigit() for char in response) or any(term in response_lower for term in ['calculate', 'answer', 'result', '=']):
            return {"status": "GOOD", "reason": "Contains mathematical content"}
        return {"status": "POOR", "reason": "Missing mathematical calculation"}
    
    elif domain == "reasoning":
        # Look for logical terms
        if any(term in response_lower for term in ['therefore', 'conclude', 'because', 'since', 'if', 'then']):
            return {"status": "GOOD", "reason": "Shows logical reasoning"}
        return {"status": "POOR", "reason": "Missing logical reasoning"}
    
    elif domain == "coding":
        # Look for code elements
        if any(term in response for term in ['def ', 'return', 'function', '():', 'import', 'for ', 'if ']):
            return {"status": "GOOD", "reason": "Contains code elements"}
        return {"status": "POOR", "reason": "Missing code elements"}
    
    elif domain == "science":
        # Look for scientific terms
        if any(term in response_lower for term in ['formula', 'atom', 'molecule', 'equation', 'theory']):
            return {"status": "GOOD", "reason": "Contains scientific content"}
        return {"status": "FAIR", "reason": "Some scientific content"}
    
    elif domain == "planning":
        # Look for planning elements
        if any(term in response_lower for term in ['plan', 'step', 'first', 'then', 'strategy', 'budget']):
            return {"status": "GOOD", "reason": "Shows planning structure"}
        return {"status": "FAIR", "reason": "Basic planning attempt"}
    
    elif domain == "writing":
        # Look for structured writing
        if len(response) > 50 and ('.' in response or ',' in response):
            return {"status": "GOOD", "reason": "Well-structured writing"}
        return {"status": "FAIR", "reason": "Basic writing attempt"}
    
    return {"status": "FAIR", "reason": "Response provided"}

if __name__ == "__main__":
    print("🔬 Starting comprehensive SwarmAI response analysis...")
    print("This will help identify exactly where your system needs improvement")
    
    try:
        asyncio.run(test_comprehensive_responses())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        print("Make sure the SwarmAI server is running!") 