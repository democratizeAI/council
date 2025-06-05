#!/usr/bin/env python3
"""
🎯 LENGTH PENALTY TEST
=====================

Test the length penalty fix to prevent math head domination.

Expected behavior:
- Math queries: Math head still wins but with mild penalty
- Non-math queries: Math head gets heavy penalty, other specialists win
- Overall: Math head win rate drops from ~80% to ~20-30%
"""

import asyncio
import time
import sys
from typing import Dict, List

async def test_length_penalty_function():
    """Test the length penalty function directly"""
    print("🧪 Testing length penalty function...")
    
    from router.voting import length_penalty
    
    test_cases = [
        # (text, query, expected_penalty_range)
        ("42", "what is 2 + 2", (0.6, 0.8)),  # Math query, short answer → mild penalty
        ("42", "tell me about history", (0.3, 0.5)),  # Non-math query, short answer → heavy penalty
        ("The answer is 42", "what is 6 * 7", (0.8, 1.0)),  # Math query, longer answer → minimal penalty
        ("The Civil War began in 1861 and was fought between...", "tell me about history", (0.9, 1.0)),  # Non-math, proper length → no penalty
        ("", "any query", (0.3, 0.5)),  # Empty response → heavy penalty
    ]
    
    all_passed = True
    
    for text, query, expected_range in test_cases:
        penalty = length_penalty(text, query)
        min_expected, max_expected = expected_range
        
        passed = min_expected <= penalty <= max_expected
        status = "✅" if passed else "❌"
        
        print(f"   {status} '{text[:20]}...' for '{query[:30]}...' → penalty: {penalty:.2f} (expected: {min_expected:.2f}-{max_expected:.2f})")
        
        if not passed:
            all_passed = False
    
    return all_passed

async def test_voting_rebalance():
    """Test that voting is rebalanced after length penalty"""
    print("\n🗳️ Testing voting rebalance...")
    
    from router.voting import vote
    
    # Test scenarios where math head should NOT dominate
    non_math_queries = [
        "tell me about the history of France",
        "explain how photosynthesis works", 
        "write a hello world function in Python",
        "what are the causes of climate change",
        "describe the structure of DNA"
    ]
    
    # Test scenarios where math head SHOULD still win (but with penalty applied)
    math_queries = [
        "what is 2 + 2",
        "calculate 15 * 23",
        "solve for x: 2x + 5 = 15",
        "what is the square root of 16",
        "how much is 100 / 4"
    ]
    
    math_wins = 0
    non_math_wins = 0
    
    print("   Testing non-math queries (math head should lose)...")
    for query in non_math_queries:
        try:
            result = await vote(query)
            winner_specialist = result.get("winner", {}).get("specialist", "unknown")
            
            is_math_win = "math" in winner_specialist.lower()
            if is_math_win:
                math_wins += 1
                print(f"      ❌ '{query[:40]}...' → {winner_specialist} (math head won)")
            else:
                non_math_wins += 1
                print(f"      ✅ '{query[:40]}...' → {winner_specialist}")
                
        except Exception as e:
            print(f"      ⚠️ '{query[:40]}...' → Error: {e}")
    
    print("   Testing math queries (math head should still win, but with penalty)...")
    math_head_math_wins = 0
    for query in math_queries:
        try:
            result = await vote(query)
            winner_specialist = result.get("winner", {}).get("specialist", "unknown")
            
            # Check if length penalty was applied
            length_penalty_applied = result.get("length_penalty_applied", False)
            
            is_math_win = "math" in winner_specialist.lower()
            if is_math_win:
                math_head_math_wins += 1
                penalty_status = "with penalty" if length_penalty_applied else "no penalty"
                print(f"      ✅ '{query[:40]}...' → {winner_specialist} ({penalty_status})")
            else:
                print(f"      ❌ '{query[:40]}...' → {winner_specialist} (math head lost on math query)")
                
        except Exception as e:
            print(f"      ⚠️ '{query[:40]}...' → Error: {e}")
    
    # Calculate win rates
    total_non_math = len(non_math_queries)
    total_math = len(math_queries)
    
    non_math_math_win_rate = (math_wins / total_non_math) * 100 if total_non_math > 0 else 0
    math_query_math_win_rate = (math_head_math_wins / total_math) * 100 if total_math > 0 else 0
    
    print(f"\n📊 Results:")
    print(f"   Math head wins on non-math queries: {math_wins}/{total_non_math} ({non_math_math_win_rate:.1f}%)")
    print(f"   Math head wins on math queries: {math_head_math_wins}/{total_math} ({math_query_math_win_rate:.1f}%)")
    
    # Success criteria
    success = (
        non_math_math_win_rate < 30 and  # Math head should win <30% of non-math queries
        math_query_math_win_rate > 60    # Math head should still win >60% of math queries
    )
    
    if success:
        print("   ✅ Voting rebalance successful!")
        print("   - Math head domination reduced on non-math queries")
        print("   - Math head still competitive on math queries")
    else:
        print("   ❌ Voting rebalance needs adjustment")
        if non_math_math_win_rate >= 30:
            print(f"   - Math head still dominates non-math queries ({non_math_math_win_rate:.1f}%)")
        if math_query_math_win_rate <= 60:
            print(f"   - Math head losing too many math queries ({math_query_math_win_rate:.1f}%)")
    
    return success

async def test_metrics_integration():
    """Test that metrics are being tracked"""
    print("\n📊 Testing metrics integration...")
    
    try:
        from monitoring.hardening_metrics import (
            track_length_penalty, 
            track_specialist_win,
            swarm_length_penalty_applied,
            swarm_specialist_win_counts
        )
        
        # Test tracking functions
        track_length_penalty("math_specialist", 0.9, 0.6)
        track_specialist_win("code_specialist")
        
        print("   ✅ Metrics tracking functions work")
        return True
        
    except Exception as e:
        print(f"   ❌ Metrics integration failed: {e}")
        return False

async def main():
    """Run length penalty verification tests"""
    print("🎯 LENGTH PENALTY VERIFICATION")
    print("=" * 50)
    print("Testing math head rebalancing fix...")
    
    tests = [
        ("Length Penalty Function", test_length_penalty_function),
        ("Voting Rebalance", test_voting_rebalance),
        ("Metrics Integration", test_metrics_integration)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name}...")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n🎯 LENGTH PENALTY TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 LENGTH PENALTY FIX SUCCESSFUL!")
        print("✅ Math head no longer dominates non-math queries")
        print("✅ Math head still competitive on math queries")
        print("✅ Metrics tracking integrated")
        print("\n📊 Monitor these metrics:")
        print("   - swarm_math_head_win_ratio (should be ~0.2-0.3)")
        print("   - swarm_length_penalty_applied_total")
        print("   - swarm_specialist_win_counts_total")
    else:
        print("\n⚠️ Length penalty fix needs refinement")
        print("Check the failing tests above for details")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 