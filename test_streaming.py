#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streaming endpoint smoke test
Verifies first token ≤ 80ms and complete stream finishes under p95
"""

import asyncio
import aiohttp
import time
import json

async def test_streaming_endpoint():
    """Test the /hybrid/stream endpoint for first-token latency"""
    
    print("🌊 Testing streaming endpoint...")
    
    url = "http://localhost:8000/hybrid/stream"
    payload = {"prompt": "Tell me a story about a brave robot"}
    
    start_time = time.time()
    first_token_time = None
    stream_complete_time = None
    tokens_received = 0
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status != 200:
                    print(f"❌ HTTP {response.status}: {await response.text()}")
                    return False
                
                print(f"✅ Connected to stream (HTTP {response.status})")
                
                async for line in response.content:
                    line_text = line.decode('utf-8').strip()
                    
                    if line_text.startswith('data:'):
                        token_data = line_text[5:]  # Remove 'data:' prefix
                        
                        if first_token_time is None and token_data and token_data != '[STREAM_COMPLETE]':
                            first_token_time = time.time()
                            first_token_latency = (first_token_time - start_time) * 1000
                            print(f"⚡ First token received in {first_token_latency:.1f}ms")
                            
                            # Check first-token target: ≤ 80ms
                            if first_token_latency <= 80:
                                print(f"✅ First-token latency target met ({first_token_latency:.1f}ms ≤ 80ms)")
                            else:
                                print(f"⚠️ First-token latency target missed ({first_token_latency:.1f}ms > 80ms)")
                        
                        if token_data == '[STREAM_COMPLETE]':
                            stream_complete_time = time.time()
                            total_latency = (stream_complete_time - start_time) * 1000
                            print(f"🏁 Stream completed in {total_latency:.1f}ms ({tokens_received} tokens)")
                            break
                        
                        if token_data and not token_data.startswith('['):
                            tokens_received += 1
                            if tokens_received <= 5:  # Show first few tokens
                                print(f"📝 Token {tokens_received}: '{token_data[:20]}...'")
    
    except aiohttp.ClientError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
    
    # Evaluate results
    if first_token_time is None:
        print("❌ No tokens received")
        return False
    
    first_token_latency = (first_token_time - start_time) * 1000
    total_latency = (stream_complete_time - start_time) * 1000 if stream_complete_time else None
    
    print(f"\n📊 Test Results:")
    print(f"   ⚡ First token: {first_token_latency:.1f}ms")
    print(f"   🏁 Total time: {total_latency:.1f}ms" if total_latency else "   🏁 Total time: INCOMPLETE")
    print(f"   📝 Tokens: {tokens_received}")
    
    # Success criteria
    first_token_ok = first_token_latency <= 80
    total_time_ok = total_latency and total_latency <= 200  # P95 target
    tokens_ok = tokens_received > 0
    
    if first_token_ok and total_time_ok and tokens_ok:
        print(f"✅ ALL TESTS PASSED")
        return True
    else:
        print(f"❌ SOME TESTS FAILED:")
        if not first_token_ok:
            print(f"   ❌ First token too slow: {first_token_latency:.1f}ms > 80ms")
        if not total_time_ok:
            if total_latency:
                print(f"   ❌ Total time too slow: {total_latency:.1f}ms > 200ms")
            else:
                print(f"   ❌ Stream did not complete properly")
        if not tokens_ok:
            print(f"   ❌ No tokens received")
        return False

async def main():
    """Run streaming tests"""
    print("🧪 Streaming Endpoint Smoke Test")
    print("=" * 40)
    
    success = await test_streaming_endpoint()
    
    if success:
        print("\n🎉 Streaming implementation ready!")
        return 0
    else:
        print("\n🚨 Streaming tests failed - check implementation")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 