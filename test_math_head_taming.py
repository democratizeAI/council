#!/usr/bin/env python3
"""
🧪 TEST MATH HEAD TAMING
========================

Test script to verify:
1. Math head no longer dominates non-math queries (intent gate + length penalty)
2. First-token latency is tracked for honest "Fast response" metrics
3. Math specialist spam is hidden when confidence < 0.8
4. UNSURE responses have 0.05 confidence and don't win
"""

import asyncio
import sys

async def test_math_head_taming():
    """Test that math head is properly tamed"""
    print("🧪 TESTING MATH HEAD TAMING")
    print("="*60)
    
    from router.voting import vote
    
    test_cases = [
        {
            "query": "hello there",
            "expected": "Non-math specialist wins, math excluded by intent gate",
            "should_exclude_math": True
        },
        {
            "query": "tell me about photosynthesis", 
            "expected": "Knowledge specialist or fusion wins, not math",
            "should_exclude_math": True
        },
        {
            "query": "What is 5 * 7?",
            "expected": "Math specialist wins with proper calculation",
            "should_exclude_math": False
        },
        {
            "query": "Calculate 12 + 8",
            "expected": "Math specialist wins",
            "should_exclude_math": False
        },
        {
            "query": "explain quantum computing",
            "expected": "Non-math wins due to length penalty and intent gate",
            "should_exclude_math": True
        }
    ]
    
    math_wins = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        should_exclude_math = test_case["should_exclude_math"]
        
        print(f"\n🧪 TEST {i}: '{query}'")
        print(f"Expected: {expected}")
        print("-" * 50)
        
        try:
            result = await vote(query)
            winner = result.get('winner', {})
            specialist = winner.get('specialist', 'unknown')
            confidence = winner.get('confidence', 0)
            text = result.get('text', '')
            true_source = winner.get('true_source', 'unknown')
            
            # Check performance metrics
            first_token_ms = result.get('first_token_latency_ms', 0)
            total_ms = result.get('total_latency_ms', 0)
            perceived_speed = result.get('perceived_speed', 'unknown')
            
            print(f"✅ WINNER: {specialist} (confidence: {confidence:.2f})")
            print(f"🔍 TRUE SOURCE: {true_source}")
            print(f"📝 RESPONSE: {text[:80]}...")
            print(f"⚡ PERFORMANCE: first-token {first_token_ms:.0f}ms, total {total_ms:.0f}ms, speed: {perceived_speed}")
            
            # Check if math won inappropriately
            is_math_winner = "math" in specialist.lower() or "math" in true_source.lower()
            if is_math_winner:
                math_wins += 1
                if should_exclude_math:
                    print("🚨 CONCERN: Math specialist won on non-math query")
                else:
                    print("✅ EXPECTED: Math specialist won on math query")
            else:
                if should_exclude_math:
                    print("✅ GOOD: Non-math specialist won on non-math query")
                else:
                    print("⚠️ UNEXPECTED: Non-math specialist won on math query")
                    
            # Check UNSURE confidence if math tried
            candidates = result.get('candidates', [])
            for candidate in candidates:
                if 'math' in candidate.get('specialist', '').lower():
                    if 'UNSURE' in candidate.get('text', ''):
                        if candidate.get('confidence', 0) <= 0.05:
                            print("✅ GOOD: Math UNSURE has low confidence (0.05)")
                        else:
                            print(f"🚨 ISSUE: Math UNSURE has high confidence ({candidate.get('confidence', 0):.2f})")
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    math_win_rate = math_wins / total_tests
    print(f"\n📊 MATH HEAD TAMING RESULTS:")
    print(f"Math wins: {math_wins}/{total_tests} ({math_win_rate:.1%})")
    
    if math_win_rate <= 0.4:  # Should be ≤40% vs previous ~80%
        print("✅ SUCCESS: Math head properly tamed!")
    else:
        print("🚨 ISSUE: Math head still dominating")

async def test_length_penalty_scoring():
    """Test the length penalty scoring function"""
    print("\n🧪 TESTING LENGTH PENALTY SCORING")
    print("="*60)
    
    from router.voting import length_penalty, score_answer
    
    test_cases = [
        # (text, query, expected_penalty_range)
        ("42", "what is 2+2", (0.7, 0.8)),  # Math query, short answer → mild penalty
        ("42", "tell me about history", (0.4, 0.5)),  # Non-math query, short answer → heavy penalty  
        ("The answer is 42 because...", "what is 2+2", (0.8, 1.0)),  # Math query, longer answer → light penalty
        ("Photosynthesis is a complex biological process...", "explain photosynthesis", (0.9, 1.0)),  # Non-math, proper length → no penalty
        ("UNSURE", "tell me about quantum", (0.4, 0.5)),  # UNSURE on non-math → heavy penalty
    ]
    
    for i, (text, query, expected_range) in enumerate(test_cases, 1):
        penalty = length_penalty(text, query)
        print(f"Test {i}: '{text[:20]}...' on '{query[:20]}...' → penalty {penalty:.2f}")
        
        if expected_range[0] <= penalty <= expected_range[1]:
            print("✅ PASS: Penalty in expected range")
        else:
            print(f"🚨 FAIL: Expected {expected_range}, got {penalty:.2f}")

if __name__ == "__main__":
    asyncio.run(test_math_head_taming())
    asyncio.run(test_length_penalty_scoring()) 