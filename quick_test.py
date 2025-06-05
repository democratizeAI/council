#!/usr/bin/env python3
import asyncio
import time
from router.voting import vote

async def quick_test():
    print("🚀 QUICK RUNAWAY GENERATION FIX TEST")
    print("=" * 50)
    
    test_cases = [
        ("hi", "Should be instant greeting"),
        ("2+2", "Should be fast math"),
        ("What does the name Hetty mean?", "Should use knowledge specialist")
    ]
    
    for query, description in test_cases:
        print(f"\n🧪 {description}")
        print(f"Query: '{query}'")
        
        start_time = time.time()
        result = await vote(query)
        elapsed_ms = (time.time() - start_time) * 1000
        
        response_text = result.get("text", "")
        winner = result.get("winner", {}).get("specialist", "unknown")
        
        print(f"⏱️  Time: {elapsed_ms:.0f}ms")
        print(f"🏆 Winner: {winner}")
        print(f"📝 Response: '{response_text[:100]}...'")
        print(f"📏 Length: {len(response_text)} chars")
        
        # Check if within limits
        time_ok = elapsed_ms < 8000
        length_ok = len(response_text) < 640  # ~160 tokens
        
        if time_ok and length_ok:
            print("✅ PASS: Within limits")
        else:
            print("❌ FAIL: Exceeded limits")
            if not time_ok:
                print(f"   - Too slow: {elapsed_ms:.0f}ms > 8000ms")
            if not length_ok:
                print(f"   - Too long: {len(response_text)} chars > 640")

if __name__ == "__main__":
    asyncio.run(quick_test()) 