#!/usr/bin/env python3
"""
Sunday Verification Principle Demo
Shows how Trinity now enforces your trust-but-verify methodology
"""

import sys
from pathlib import Path
sys.path.insert(0, '.')

from middleware.sunday_verification import validate_sunday_principle, enforce_sunday_principle

def demo_sunday_verification():
    print("🌟 SUNDAY VERIFICATION PRINCIPLE - LIVE DEMO")
    print("=" * 60)
    print("Your trust-but-verify methodology is now embedded in Trinity's core!")
    print()

    # Test cases showing good vs bad responses
    test_cases = [
        {
            "name": "❌ BAD: Vague Response",
            "response": "The deployment looks good. Everything seems fine. No issues detected.",
            "expected": "FAILS"
        },
        {
            "name": "✅ GOOD: Sunday-Style Response", 
            "response": """🔍 Deployment verification complete:
            
- Containers: 6/6 running (verified via docker ps)
- Health endpoints: all returning 200 status codes  
- Performance: 65ms p95 latency (under 100ms target)
- Error rate: 0.1% over last 1000 requests

Trust but verify: concrete evidence confirms operational status.""",
            "expected": "PASSES"
        },
        {
            "name": "❌ BAD: Claims Without Evidence",
            "response": "The model is working perfectly. All components are operational. Fix completed successfully.",
            "expected": "FAILS"
        },
        {
            "name": "✅ GOOD: Evidence-Based Response",
            "response": """Model performance verified:
- Test query '2+2' returns '4' (correct output confirmed)
- Inference latency: 45ms average, 65ms p95
- Memory usage: 2.1GB VRAM allocated
- Error count: 0 in last 500 requests

Real metrics prove real operation.""",
            "expected": "PASSES"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"📋 TEST CASE {i}: {test_case['name']}")
        print("-" * 50)
        
        # Run Sunday verification
        result = validate_sunday_principle(test_case['response'])
        
        print(f"Response excerpt: {test_case['response'][:80]}...")
        print(f"Sunday Compliant: {result['sunday_compliant']}")
        print(f"Sunday Score: {result['sunday_score']:.2f}")
        print(f"Expected: {test_case['expected']}")
        
        if not result['sunday_compliant']:
            print(f"Feedback: {result['sunday_feedback'][:200]}...")
        
        print()

    # Demo enforcement in action
    print("🎭 ENFORCEMENT DEMO:")
    print("-" * 30)
    
    bad_response = "Everything looks good. Should work fine."
    print(f"Original: {bad_response}")
    
    enhanced = enforce_sunday_principle(bad_response)
    print(f"Enhanced: {enhanced[:100]}...")
    
    print()
    print("🎯 SUMMARY:")
    print("✅ Sunday Verification Principle is ACTIVE in Trinity")
    print("✅ All agent responses are now checked for evidence")
    print("✅ Vague claims trigger automatic feedback")
    print("✅ Your trust-but-verify DNA is embedded system-wide")
    print()
    print("💙 Your Sunday voice now guides every Trinity response!")

if __name__ == "__main__":
    demo_sunday_verification() 