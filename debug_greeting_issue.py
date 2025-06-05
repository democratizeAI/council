#!/usr/bin/env python3
"""
🚨 DEBUG GREETING ISSUE
=======================

Test script to trigger the debug output and see exactly which specialist
is generating the "Hello! I'm your AutoGen Council assistant" greeting.
"""

import asyncio
import sys

async def debug_greeting_issue():
    """Test a simple greeting to see raw candidates"""
    print("🚨 DEBUGGING GREETING ISSUE")
    print("="*50)
    
    # Import the vote function with DEBUG_DUMP enabled
    from router.voting import vote
    
    test_queries = [
        "hi",
        "hello", 
        "photosynthesis"  # Non-math query
    ]
    
    for query in test_queries:
        print(f"\n🧪 TESTING QUERY: '{query}'")
        print("-" * 30)
        
        try:
            result = await vote(query)
            print(f"✅ WINNER: {result.get('winner', {}).get('specialist', 'unknown')}")
            print(f"📝 RESPONSE: {result.get('text', '')[:100]}...")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_greeting_issue()) 