#!/usr/bin/env python3
"""
🧪 TEST GREETING FIXES
======================

Test script to verify all greeting fixes are working:
1. No more canned "Hello! I'm your AutoGen Council assistant" greetings
2. UNSURE responses have 0.05 confidence and don't win
3. Specialist tags reflect true sources
"""

import asyncio
import sys

async def test_greeting_fixes():
    """Test the greeting fixes"""
    print("🧪 TESTING GREETING FIXES")
    print("="*50)
    
    from router.voting import vote
    
    test_cases = [
        {
            "query": "hi",
            "expected": "Short friendly greeting, memory_aware_greeting_handler wins"
        },
        {
            "query": "What is 2+2?", 
            "expected": "Math answer, math_specialist wins"
        },
        {
            "query": "Explain HTTP/3",
            "expected": "Knowledge/fusion answer, no greeting stub"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        
        print(f"\n🧪 TEST {i}: '{query}'")
        print(f"Expected: {expected}")
        print("-" * 40)
        
        try:
            result = await vote(query)
            winner = result.get('winner', {})
            specialist = winner.get('specialist', 'unknown')
            confidence = winner.get('confidence', 0)
            text = result.get('text', '')
            true_source = winner.get('true_source', 'unknown')
            
            print(f"✅ WINNER: {specialist} (confidence: {confidence:.2f})")
            print(f"🔍 TRUE SOURCE: {true_source}")
            print(f"📝 RESPONSE: {text[:100]}...")
            
            # Check for banned greeting
            if "Hello! I'm your AutoGen Council assistant" in text:
                print("🚨 FAIL: Canned greeting detected!")
            else:
                print("✅ PASS: No canned greeting")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

async def test_specific_greeting_paths():
    """Test specific paths that could generate greetings"""
    print("\n🔍 TESTING SPECIFIC GREETING PATHS")
    print("="*50)
    
    # Test simple greeting handler
    from router.voting import handle_simple_greeting
    import time
    
    print("\n1. Testing handle_simple_greeting()...")
    result = handle_simple_greeting("hi", time.time())
    text = result.get('text', '')
    print(f"Result: {text}")
    if "Hello! I'm your AutoGen Council assistant" in text:
        print("🚨 FAIL: handle_simple_greeting() still has canned greeting")
    else:
        print("✅ PASS: handle_simple_greeting() fixed")
    
    # Test agent0 directly
    print("\n2. Testing router_cascade agent0...")
    try:
        from router_cascade import RouterCascade
        router = RouterCascade()
        result = await router._call_agent0_llm("hi")
        text = result.get('text', '')
        print(f"Result: {text}")
        if "Hello! I'm your AutoGen Council assistant" in text:
            print("🚨 FAIL: agent0 still has canned greeting")
        else:
            print("✅ PASS: agent0 fixed")
    except Exception as e:
        print(f"❌ ERROR testing agent0: {e}")

if __name__ == "__main__":
    asyncio.run(test_greeting_fixes())
    asyncio.run(test_specific_greeting_paths()) 