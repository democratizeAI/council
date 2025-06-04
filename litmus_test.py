#!/usr/bin/env python3
"""
Litmus Test: Expose Content Smoke
Run 4 critical prompts to prove whether we have real AI or just token garbage.
NOW WITH REAL GRADERS!
"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from pathlib import Path

# Add the tests directory to path to import graders
sys.path.append('tests')
try:
    from graders import grade_response, looks_like_template
    GRADERS_AVAILABLE = True
except ImportError:
    print("⚠️ Real graders not available, falling back to simple checks")
    GRADERS_AVAILABLE = False

# Test cases that require actual reasoning/calculation
LITMUS_TESTS = [
    {
        "prompt": "What is 8!?",
        "expected_answer": "40320",
        "type": "math"
    },
    {
        "prompt": "What is 25% of 240?",
        "expected_answer": "60",
        "type": "math"
    },
    {
        "prompt": "Write a Python function to calculate GCD of two numbers",
        "expected_keywords": ["def", "gcd", "return", "%", "while"],
        "type": "code"
    },
    {
        "prompt": "Logic puzzle: All bloops are razzles. All razzles are lazzles. Are all bloops lazzles?",
        "expected_answer": "yes",
        "type": "reasoning"
    }
]

async def test_endpoint(client: httpx.AsyncClient, endpoint: str, prompt: str):
    """Test a single prompt against an endpoint"""
    try:
        response = await client.post(
            f"http://localhost:8000/{endpoint}",
            json={"prompt": prompt},
            timeout=10.0
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "endpoint": endpoint,
                "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                "response": data.get("text", data.get("response", "")),
                "confidence": data.get("confidence", 0.0),
                "model_used": data.get("model_used", "unknown"),
                "latency_ms": data.get("generation_time_ms", data.get("hybrid_latency_ms", 0))
            }
        else:
            return {
                "endpoint": endpoint,
                "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                "error": f"HTTP {response.status_code}",
                "response": ""
            }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
            "error": str(e),
            "response": ""
        }

def grade_response_fallback(test_case: dict, response: str) -> dict:
    """Fallback grader if real graders not available"""
    response_lower = response.lower().strip()
    
    if test_case["type"] == "math":
        expected = test_case["expected_answer"]
        has_answer = expected in response
        is_garbage = len(response_lower) < 3 or response_lower in ["", "...", '"', "....", "none"]
        
        return {
            "correct": has_answer and not is_garbage,
            "has_expected": has_answer,
            "is_garbage": is_garbage,
            "grade": "PASS" if (has_answer and not is_garbage) else "FAIL"
        }
    
    elif test_case["type"] == "code":
        keywords = test_case["expected_keywords"]
        keyword_count = sum(1 for kw in keywords if kw in response_lower)
        is_garbage = len(response_lower) < 10 or response_lower in ["", "...", '"', "...."]
        
        return {
            "correct": keyword_count >= 3 and not is_garbage,
            "keyword_count": keyword_count,
            "total_keywords": len(keywords),
            "is_garbage": is_garbage,
            "grade": "PASS" if (keyword_count >= 3 and not is_garbage) else "FAIL"
        }
    
    elif test_case["type"] == "reasoning":
        has_yes = "yes" in response_lower
        has_reasoning = any(word in response_lower for word in ["all", "therefore", "thus", "so"])
        is_garbage = len(response_lower) < 5 or response_lower in ["", "...", '"', "...."]
        
        return {
            "correct": has_yes and has_reasoning and not is_garbage,
            "has_answer": has_yes,
            "has_reasoning": has_reasoning,
            "is_garbage": is_garbage,
            "grade": "PASS" if (has_yes and has_reasoning and not is_garbage) else "FAIL"
        }

async def run_litmus_test():
    """Run the litmus test to expose content smoke"""
    print("🚨 LITMUS TEST: Real Content Grading")
    print("=" * 60)
    print(f"🔍 Using {'REAL' if GRADERS_AVAILABLE else 'FALLBACK'} graders")
    print("=" * 60)
    
    endpoints = ["hybrid"]  # Focus on the main endpoint
    
    async with httpx.AsyncClient() as client:
        all_results = []
        
        for test_case in LITMUS_TESTS:
            print(f"\n📝 Testing: {test_case['prompt']}")
            print(f"   Expected ({test_case['type']}): {test_case.get('expected_answer', 'keywords present')}")
            
            for endpoint in endpoints:
                result = await test_endpoint(client, endpoint, test_case["prompt"])
                
                if "error" not in result:
                    # Use real graders if available
                    if GRADERS_AVAILABLE:
                        grade = grade_response(test_case["prompt"], result["response"], test_case["type"])
                    else:
                        grade = grade_response_fallback(test_case, result["response"])
                    
                    result.update(grade)
                    
                    # Enhanced output with real grading
                    status_emoji = "✅" if grade.get("grade") == "PASS" else "❌" if grade.get("grade") == "FAIL_LOUD" else "⚠️"
                    print(f"\n   {status_emoji} {endpoint.upper()}: {grade.get('grade', 'UNKNOWN')}")
                    print(f"      Model: {result['model_used']}")
                    print(f"      Response: '{result['response'][:100]}...'" if len(result['response']) > 100 else f"      Response: '{result['response']}'")
                    print(f"      Latency: {result['latency_ms']:.0f}ms")
                    
                    # Show grading details
                    if GRADERS_AVAILABLE:
                        print(f"      Score: {grade.get('score', 0):.1f}/1.0")
                        if grade.get('reason'):
                            print(f"      Reason: {grade['reason']}")
                        if grade.get('expected') and grade.get('found'):
                            print(f"      Expected: {grade['expected']}, Found: {grade['found']}")
                    
                    if grade.get('grade') == 'FAIL_LOUD':
                        print(f"      🚨 TEMPLATE/GARBAGE DETECTED")
                else:
                    print(f"\n   ❌ {endpoint.upper()}: ERROR")
                    print(f"      Error: {result.get('error', 'Unknown')}")
                
                all_results.append({**result, **test_case})
        
        # Summary with real scoring
        print("\n" + "=" * 60)
        print("🎯 LITMUS TEST SUMMARY (Real Content Grading)")
        print("=" * 60)
        
        total_tests = len([r for r in all_results if 'error' not in r])
        passed = sum(1 for r in all_results if r.get('grade') == 'PASS')
        failed = sum(1 for r in all_results if r.get('grade') in ['FAIL', 'FAIL_LOUD'])
        partial = sum(1 for r in all_results if r.get('grade') == 'PARTIAL')
        errors = sum(1 for r in all_results if 'error' in r)
        
        avg_score = sum(r.get('score', 0) for r in all_results if 'score' in r) / max(total_tests, 1)
        
        print(f"Total Tests: {total_tests + errors}")
        print(f"Passed: {passed} ({passed/(total_tests+errors)*100:.1f}%)")
        print(f"Partial: {partial} ({partial/(total_tests+errors)*100:.1f}%)")
        print(f"Failed: {failed} ({failed/(total_tests+errors)*100:.1f}%)")
        print(f"Errors: {errors} ({errors/(total_tests+errors)*100:.1f}%)")
        print(f"Average Score: {avg_score:.2f}/1.0")
        
        if avg_score >= 0.8:
            print("\n✅ CONCLUSION: Content quality EXCELLENT")
        elif avg_score >= 0.6:
            print("\n⚠️ CONCLUSION: Content quality ACCEPTABLE") 
        elif avg_score >= 0.3:
            print("\n🚨 CONCLUSION: Content quality POOR")
        else:
            print("\n🚨 CONCLUSION: CONTENT SMOKE CONFIRMED")
            print("   The infrastructure works, but AI responses are garbage.")
            print("   Need to fix: 1) Real models 2) Proper grading 3) Quality gates")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"litmus_test_real_grading_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n💾 Detailed results saved to: {filename}")

if __name__ == "__main__":
    asyncio.run(run_litmus_test()) 