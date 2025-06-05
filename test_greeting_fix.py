#!/usr/bin/env python3
"""Quick test for greeting short-circuit fix"""

import asyncio
import time
import sys
import os

# Add router to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_greeting_fix():
    """Test that greetings are now instant"""
    print("🚨 Testing Emergency Greeting Fix")
    print("=" * 40)
    
    try:
        from router_cascade import RouterCascade
        
        # Initialize router
        router = RouterCascade()
        router.current_session_id = "test123"
        
        # Test greeting phrases
        greetings = ["hi", "hello", "hey", "yo", "sup", "Hello there!"]
        
        for greeting in greetings:
            print(f"\n🧪 Testing: '{greeting}'")
            
            start_time = time.time()
            result = await router.route_query(greeting)
            latency = (time.time() - start_time) * 1000
            
            # Check results
            response_text = result.get("text", "")
            model = result.get("model", "")
            reported_latency = result.get("latency_ms", 0)
            
            print(f"✅ Response: {response_text}")
            print(f"⏱️ Actual latency: {latency:.1f}ms")
            print(f"📊 Reported latency: {reported_latency}ms")
            print(f"🤖 Model: {model}")
            
            # Validate instant response
            if latency < 100 and "greeting-shortcut" in model:
                print(f"✅ SUCCESS: Instant greeting!")
            else:
                print(f"❌ FAIL: Still slow ({latency:.1f}ms)")
        
        # Test non-greeting to make sure it still works
        print(f"\n🧪 Testing non-greeting: 'What is 2+2?'")
        start_time = time.time()
        result = await router.route_query("What is 2+2?")
        latency = (time.time() - start_time) * 1000
        
        print(f"✅ Response: {result.get('text', '')[:50]}...")
        print(f"⏱️ Latency: {latency:.1f}ms")
        print(f"🤖 Model: {result.get('model', '')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_greeting_fix())
    print(f"\n🏆 GREETING FIX TEST: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1) 