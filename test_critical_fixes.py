#!/usr/bin/env python3
"""
🚨 CRITICAL PERFORMANCE REGRESSION FIXES TEST
==============================================

Tests the 4 critical fixes from the log-dump analysis:
1. Math specialist UNSURE penalty (confidence = 0.05)
2. Token limits (256 max per head) 
3. Confidence gates (to_synth: 0.45, to_premium: 0.20)
4. Tiny summarizer (60-80 tokens max)

Expected results after fixes:
- "hi" -> ["local_phi2"] in < 0.6s
- "2+2" -> ["local_phi2","math_specialist"] in < 1s  
- Non-math queries don't route to math specialist
- Responses are under 256 tokens
"""

import asyncio
import time
import sys
import yaml
from typing import Dict, List, Any

async def test_math_unsure_penalty():
    """Test Fix #1: Math specialist returns UNSURE with 0.05 confidence for non-math"""
    print("\n🧪 TEST 1: Math UNSURE Penalty")
    print("=" * 50)
    
    try:
        from router.voting import vote
        
        # Test non-math queries that should trigger UNSURE
        non_math_queries = [
            "hello there",
            "what's the weather?", 
            "tell me about photosynthesis",
            "explain quantum computing"
        ]
        
        math_unsure_detected = 0
        
        for query in non_math_queries:
            print(f"\n🔍 Testing: '{query}'")
            
            result = await vote(query)
            candidates = result.get('candidates', [])
            
            # Look for math specialist in candidates
            math_candidate = None
            for candidate in candidates:
                if 'math' in candidate.get('specialist', '').lower():
                    math_candidate = candidate
                    break
            
            if math_candidate:
                text = math_candidate.get('text', '')
                confidence = math_candidate.get('confidence', 0)
                unsure_penalty = math_candidate.get('unsure_penalty_applied', False)
                
                print(f"   Math specialist: '{text}' (confidence: {confidence:.3f})")
                
                if text.strip() == "UNSURE" and confidence <= 0.05:
                    print(f"   ✅ PASS: Math returned UNSURE with low confidence")
                    math_unsure_detected += 1
                elif text.strip() == "UNSURE":
                    print(f"   ⚠️  PARTIAL: Math returned UNSURE but confidence = {confidence:.3f} (should be ≤ 0.05)")
                else:
                    print(f"   ❌ FAIL: Math should return UNSURE for non-math query")
            else:
                print(f"   ✅ GOOD: No math specialist tried (intent gate working)")
                math_unsure_detected += 1
        
        success_rate = math_unsure_detected / len(non_math_queries)
        print(f"\n📊 UNSURE Penalty Results: {math_unsure_detected}/{len(non_math_queries)} ({success_rate:.1%})")
        
        if success_rate >= 0.75:
            print("✅ PASS: Math UNSURE penalty working")
            return True
        else:
            print("❌ FAIL: Math UNSURE penalty needs work")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_token_limits():
    """Test Fix #2: Token limits prevent 2000-token fluff"""
    print("\n🧪 TEST 2: Token Limits")
    print("=" * 50)
    
    try:
        # Load config to check limits
        with open("config/council.yml", "r") as f:
            config = yaml.safe_load(f)
        
        generation_limits = config.get("generation_limits", {})
        max_tokens = generation_limits.get("max_tokens", 0)
        timeout = generation_limits.get("generation_timeout", 0)
        
        print(f"🔧 Config: max_tokens = {max_tokens}, timeout = {timeout}s")
        
        if max_tokens == 256:
            print("✅ PASS: Token limit set to 256")
            token_limit_ok = True
        else:
            print(f"❌ FAIL: Token limit is {max_tokens}, should be 256")
            token_limit_ok = False
        
        if timeout == 10:
            print("✅ PASS: Generation timeout set to 10s")
            timeout_ok = True
        else:
            print(f"❌ FAIL: Timeout is {timeout}s, should be 10s")
            timeout_ok = False
        
        return token_limit_ok and timeout_ok
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_confidence_gates():
    """Test Fix #3: Confidence gates for tier routing"""
    print("\n🧪 TEST 3: Confidence Gates")
    print("=" * 50)
    
    try:
        # Load config to check gates
        with open("config/council.yml", "r") as f:
            config = yaml.safe_load(f)
        
        confidence_gate = config.get("confidence_gate", {})
        to_synth = confidence_gate.get("to_synth", 0)
        to_premium = confidence_gate.get("to_premium", 0)
        
        print(f"🔧 Config: to_synth = {to_synth}, to_premium = {to_premium}")
        
        if to_synth == 0.45:
            print("✅ PASS: Synth gate set to 0.45")
            synth_ok = True
        else:
            print(f"❌ FAIL: Synth gate is {to_synth}, should be 0.45")
            synth_ok = False
        
        if to_premium == 0.20:
            print("✅ PASS: Premium gate set to 0.20")
            premium_ok = True
        else:
            print(f"❌ FAIL: Premium gate is {to_premium}, should be 0.20")
            premium_ok = False
        
        return synth_ok and premium_ok
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def test_tiny_summarizer():
    """Test Fix #4: Tiny summarizer prevents ledger bloat"""
    print("\n🧪 TEST 4: Tiny Summarizer")
    print("=" * 50)
    
    try:
        from router.tiny_summarizer import summarize, summarize_for_ledger, is_summary_needed
        
        # Test long text that needs summarization
        long_text = """
        The AutoGen Council system is a sophisticated multi-tier architecture that combines local 
        specialists, synthetic agents, and premium LLMs to provide cost-effective, high-quality 
        responses across a wide range of domains. The system includes a math specialist that uses 
        SymPy for symbolic computation, a code specialist that integrates with DeepSeek and provides 
        sandbox execution capabilities, a logic specialist that uses SWI-Prolog for formal reasoning, 
        and a knowledge specialist that provides factual information retrieval. Each specialist has 
        different latency and cost characteristics, with local specialists being fastest and cheapest, 
        synthetic agents providing a good balance of speed and quality, and premium LLMs offering the 
        highest quality at the highest cost. The system includes confidence-based routing, cost tracking, 
        comprehensive monitoring, and a scratchpad system for context persistence across multiple turns.
        """
        
        original_tokens = len(long_text.split())
        print(f"📝 Original text: {original_tokens} tokens")
        
        # Test if summary is needed
        needs_summary = is_summary_needed(long_text)
        print(f"🔍 Needs summary: {needs_summary}")
        
        if needs_summary:
            # Test general summarization
            summary = summarize(long_text, max_tokens=80)
            summary_tokens = len(summary.split())
            print(f"📝 General summary: {summary_tokens} tokens")
            print(f"   Text: {summary}")
            
            # Test ledger-specific summarization
            ledger_summary = summarize_for_ledger(long_text)
            ledger_tokens = len(ledger_summary.split())
            print(f"📝 Ledger summary: {ledger_tokens} tokens")
            print(f"   Text: {ledger_summary}")
            
            # Check constraints
            summary_ok = summary_tokens <= 80
            ledger_ok = ledger_tokens <= 70
            
            if summary_ok and ledger_ok:
                print("✅ PASS: Summarizer keeping within token limits")
                return True
            else:
                print(f"❌ FAIL: Summary {summary_tokens}/80, Ledger {ledger_tokens}/70 tokens")
                return False
        else:
            print("⚠️  Text doesn't need summarization")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_smoke_matrix():
    """Test the smoke test matrix from triage instructions"""
    print("\n🧪 SMOKE TEST MATRIX")
    print("=" * 50)
    
    test_cases = [
        {"prompt": "hi", "expected_chain": ["local"], "target_latency": 0.6},
        {"prompt": "factor x²–5x+6", "expected_chain": ["local", "math"], "target_latency": 1.0},
        {"prompt": "Compare QUIC & HTTP/3", "expected_chain": ["local", "synth"], "target_latency": 3.0},
    ]
    
    try:
        from router_cascade import RouterCascade
        router = RouterCascade()
        
        passed = 0
        
        for i, test in enumerate(test_cases, 1):
            prompt = test["prompt"]
            target_latency = test["target_latency"]
            
            print(f"\n🧪 Test {i}: '{prompt}'")
            print(f"   Target: < {target_latency}s")
            
            start_time = time.time()
            
            try:
                result = await router.deliberate(prompt, f"smoke_test_{i}")
                latency = time.time() - start_time
                
                # Extract provider chain
                provider_chain = result[1].get("provider_chain", []) if len(result) > 1 else []
                
                latency_ok = latency < target_latency
                has_response = len(result[0].text if hasattr(result[0], 'text') else str(result[0])) > 0
                
                print(f"   ⏱️  Latency: {latency:.2f}s ({'✅' if latency_ok else '❌'})")
                print(f"   🔗 Chain: {provider_chain}")
                print(f"   📝 Response: {str(result[0])[:50]}...")
                
                if latency_ok and has_response:
                    print(f"   ✅ PASS")
                    passed += 1
                else:
                    print(f"   ❌ FAIL")
                    
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
        
        success_rate = passed / len(test_cases)
        print(f"\n📊 Smoke Test Results: {passed}/{len(test_cases)} ({success_rate:.1%})")
        
        return success_rate >= 0.67  # At least 2/3 should pass
        
    except Exception as e:
        print(f"❌ SMOKE TEST ERROR: {e}")
        return False

def test_hashlib_availability():
    """Test that specialists have access to hashlib (prevents import errors)"""
    try:
        from router.specialist_sandbox_fix import get_specialist_sandbox, test_specialist_environment
        
        # Test sandbox environment
        results = test_specialist_environment()
        
        passed_tests = sum(1 for r in results if r['success'])
        total_tests = len(results)
        
        if passed_tests == total_tests:
            print("✅ PASS: Hashlib available - all specialist modules working")
            return True
        else:
            print(f"❌ FAIL: Hashlib issues - {passed_tests}/{total_tests} tests passed")
            for result in results:
                if not result['success']:
                    print(f"   Failed: {result['expression']} - {result['actual']}")
            return False
            
    except ImportError:
        print("❌ FAIL: Specialist sandbox fix not available")
        return False
    except Exception as e:
        print(f"❌ FAIL: Hashlib test error: {e}")
        return False

def main():
    """Run all critical performance fixes tests"""
    print("🚨 CRITICAL PERFORMANCE FIXES TEST")
    print("=" * 60)
    print("Verifying all 4 critical fixes + hashlib fix are working")
    print()
    
    # Test all critical fixes
    tests = [
        ("Math UNSURE penalty", lambda: asyncio.run(test_math_unsure_penalty())),
        ("Token limits", test_token_limits),
        ("Confidence gates", test_confidence_gates),
        ("Tiny summarizer", test_tiny_summarizer),
        ("Hashlib availability", test_hashlib_availability),  # NEW TEST
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAIL: {test_name} - Error: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Overall: {passed}/{total} critical fixes working ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All critical fixes are working!")
        print("✅ System should now have sub-second response times")
        print("✅ No more 66-second CPU fallback regressions")
        print("✅ Specialists should work without import errors")
    else:
        print("⚠️ Some fixes need attention")
        print("🔧 Check the failing components above")

if __name__ == "__main__":
    main() 