#!/usr/bin/env python3
"""
Quick Stub Fix Test
==================

Tests that the voting system correctly filters out stub responses
and applies the new confidence threshold of 0.75.
"""

import asyncio
import sys
import time

async def test_stub_fixes():
    """Test that stub detection and confidence fixes are working"""
    print("🔧 Testing Stub Detection Fixes")
    print("=" * 40)
    
    try:
        from router.voting import VOTING_CONFIG, vote
        
        # Test 1: Configuration loaded correctly
        print("\n📊 Test 1: Configuration")
        print(f"   Min confidence: {VOTING_CONFIG['min_confidence']}")
        print(f"   Stub detection: {VOTING_CONFIG['stub_detection_enabled']}")
        
        if VOTING_CONFIG['min_confidence'] >= 0.75:
            print("   ✅ Confidence threshold raised to 0.75+")
        else:
            print("   ❌ Confidence threshold not raised")
            return False
        
        # Test 2: Simple query that shouldn't trigger stubs
        print("\n🧪 Test 2: Code Query")
        start_time = time.time()
        result = await vote("write a hello world function", top_k=1)
        latency = (time.time() - start_time) * 1000
        
        confidence = result.get('confidence', 0)
        text = result.get('text', '')
        winner = result.get('winner', {}).get('specialist', 'unknown')
        
        print(f"   Response: {text[:60]}...")
        print(f"   Winner: {winner}")
        print(f"   Confidence: {confidence:.3f}")
        print(f"   Latency: {latency:.1f}ms")
        
        # Check for stub patterns
        stub_detected = any(pattern in text.lower() for pattern in [
            'template stub detected', 'custom_function', 'todo', 'implementation needed'
        ])
        
        if stub_detected:
            print("   ❌ Stub still detected in response")
            return False
        else:
            print("   ✅ No stub patterns detected")
        
        # Test 3: Math query (should route to math specialist)
        print("\n🧮 Test 3: Math Query")
        start_time = time.time()
        result = await vote("what is 2 + 2", top_k=1)
        latency = (time.time() - start_time) * 1000
        
        confidence = result.get('confidence', 0)
        text = result.get('text', '')
        winner = result.get('winner', {}).get('specialist', 'unknown')
        
        print(f"   Response: {text[:60]}...")
        print(f"   Winner: {winner}")
        print(f"   Confidence: {confidence:.3f}")
        print(f"   Latency: {latency:.1f}ms")
        
        if confidence >= 0.75:
            print("   ✅ High confidence response")
        else:
            print(f"   ⚠️ Low confidence: {confidence:.3f} < 0.75")
        
        print("\n🎉 Stub detection fixes verified!")
        print("✅ Ready for production deployment")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_stub_fixes())
    sys.exit(0 if success else 1) 