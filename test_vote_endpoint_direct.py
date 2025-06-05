#!/usr/bin/env python3
"""
🎯 DIRECT VOTE ENDPOINT TEST
============================

Test the actual /vote endpoint to verify length penalty is working.
This bypasses the frontend and tests the API directly.
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any

async def test_vote_endpoint_length_penalty():
    """Test that the /vote endpoint applies length penalty"""
    print("🧪 Testing /vote endpoint with length penalty...")
    
    # Import the vote endpoint function directly
    from autogen_api_shim import vote_endpoint, VoteRequest
    
    # Test cases - non-math queries where math head should NOT dominate
    test_cases = [
        {
            "prompt": "explain how photosynthesis works in plants",
            "candidates": ["math_specialist", "knowledge_specialist"],
            "expected_winner": "knowledge_specialist"
        },
        {
            "prompt": "write a hello world function in Python",
            "candidates": ["math_specialist", "code_specialist"],
            "expected_winner": "code_specialist"
        },
        {
            "prompt": "tell me about the history of the Roman Empire",
            "candidates": ["math_specialist", "knowledge_specialist"],
            "expected_winner": "knowledge_specialist"
        }
    ]
    
    # Test math queries where math head SHOULD still win
    math_test_cases = [
        {
            "prompt": "what is 15 * 23",
            "candidates": ["math_specialist", "knowledge_specialist"],
            "expected_winner": "math_specialist"
        },
        {
            "prompt": "calculate the square root of 144",
            "candidates": ["math_specialist", "code_specialist"],
            "expected_winner": "math_specialist"
        }
    ]
    
    print("\n📊 Testing non-math queries (math head should lose)...")
    
    math_wins = 0
    total_non_math = len(test_cases)
    
    for i, test_case in enumerate(test_cases):
        print(f"\n   Test {i+1}: '{test_case['prompt'][:50]}...'")
        
        request = VoteRequest(
            prompt=test_case["prompt"],
            candidates=test_case["candidates"],
            top_k=1
        )
        
        try:
            response = await vote_endpoint(request)
            
            # Check which specialist won
            model_used = response.model_used
            winner = response.model_used
            
            print(f"      Winner: {winner}")
            print(f"      Confidence: {response.confidence:.3f}")
            print(f"      Latency: {response.latency_ms:.1f}ms")
            
            # Check if math specialist won
            is_math_win = "math" in winner.lower()
            if is_math_win:
                math_wins += 1
                print(f"      ❌ Math head won (should have lost)")
            else:
                print(f"      ✅ Correct specialist won")
                
            # Look for length penalty in response (if available)
            # Note: We might need to add this to the response model
            
        except Exception as e:
            print(f"      ⚠️ Error: {e}")
    
    print("\n📊 Testing math queries (math head should win)...")
    
    math_wins_on_math = 0
    total_math = len(math_test_cases)
    
    for i, test_case in enumerate(math_test_cases):
        print(f"\n   Test {i+1}: '{test_case['prompt'][:50]}...'")
        
        request = VoteRequest(
            prompt=test_case["prompt"],
            candidates=test_case["candidates"],
            top_k=1
        )
        
        try:
            response = await vote_endpoint(request)
            
            winner = response.model_used
            print(f"      Winner: {winner}")
            print(f"      Confidence: {response.confidence:.3f}")
            print(f"      Latency: {response.latency_ms:.1f}ms")
            
            # Check if math specialist won
            is_math_win = "math" in winner.lower()
            if is_math_win:
                math_wins_on_math += 1
                print(f"      ✅ Math head correctly won")
            else:
                print(f"      ❌ Math head lost (should have won)")
                
        except Exception as e:
            print(f"      ⚠️ Error: {e}")
    
    # Calculate results
    non_math_math_win_rate = (math_wins / total_non_math) * 100 if total_non_math > 0 else 0
    math_query_math_win_rate = (math_wins_on_math / total_math) * 100 if total_math > 0 else 0
    
    print(f"\n📊 ENDPOINT TEST RESULTS:")
    print(f"   Math wins on non-math queries: {math_wins}/{total_non_math} ({non_math_math_win_rate:.1f}%)")
    print(f"   Math wins on math queries: {math_wins_on_math}/{total_math} ({math_query_math_win_rate:.1f}%)")
    
    # Success criteria
    success = (
        non_math_math_win_rate < 30 and  # Math head should win <30% of non-math queries
        math_query_math_win_rate > 60    # Math head should still win >60% of math queries
    )
    
    if success:
        print("\n✅ /VOTE ENDPOINT LENGTH PENALTY WORKING!")
        print("   - Math head no longer dominates non-math queries")
        print("   - Math head still competitive on math queries")
    else:
        print("\n❌ /VOTE ENDPOINT LENGTH PENALTY NOT WORKING")
        if non_math_math_win_rate >= 30:
            print(f"   - Math head still dominates non-math queries ({non_math_math_win_rate:.1f}%)")
        if math_query_math_win_rate <= 60:
            print(f"   - Math head losing too many math queries ({math_query_math_win_rate:.1f}%)")
        
        print("\n🔍 DEBUGGING INFO:")
        print("   1. Check if vote() function in router/voting.py is being called")
        print("   2. Check if length_penalty() function is being executed")
        print("   3. Verify that specialist responses are getting penalized")
    
    return success

async def test_vote_function_directly():
    """Test the vote function directly to confirm length penalty"""
    print("\n🔬 Testing vote() function directly...")
    
    from router.voting import vote
    
    try:
        # Test non-math query
        result = await vote(
            prompt="explain how photosynthesis works in plants",
            model_names=["math_specialist", "knowledge_specialist"]
        )
        
        winner = result.get("winner", {})
        print(f"   Direct vote result: {winner.get('specialist', 'unknown')}")
        print(f"   Confidence: {winner.get('confidence', 0):.3f}")
        print(f"   Length penalty applied: {result.get('length_penalty_applied', False)}")
        
        if "math" in winner.get("specialist", "").lower():
            print("   ❌ Math head still winning in direct vote()")
            return False
        else:
            print("   ✅ Length penalty working in direct vote()")
            return True
            
    except Exception as e:
        print(f"   ⚠️ Direct vote test failed: {e}")
        return False

async def main():
    """Run vote endpoint length penalty tests"""
    print("🎯 VOTE ENDPOINT LENGTH PENALTY TEST")
    print("=" * 60)
    
    # Test both the direct vote function and the endpoint
    tests = [
        ("Direct vote() function", test_vote_function_directly),
        ("Vote endpoint", test_vote_endpoint_length_penalty)
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
    print("\n🎯 TEST SUMMARY")
    print("=" * 40)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 LENGTH PENALTY FIX WORKING IN VOTE ENDPOINT!")
        print("✅ Math head domination resolved at API level")
        print("✅ Frontend /vote calls should now be balanced")
    else:
        print("\n⚠️ Length penalty fix needs attention")
        print("The issue may be:")
        print("1. Vote endpoint not calling the correct vote() function")
        print("2. Length penalty not being applied properly")
        print("3. Frontend using a different endpoint")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 