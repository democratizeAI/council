#!/usr/bin/env python3
"""
Test script to validate the Council fixes
==========================================

Tests the fixed specialists and consensus fusion system.
"""

import asyncio
import logging
import time
from router_cascade import RouterCascade
from router.voting import vote, consensus_fuse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_fixed_specialists():
    """Test that the fixed specialists work properly"""
    print("🧪 Testing Fixed AutoGen Council Specialists")
    print("=" * 50)
    
    router = RouterCascade()
    
    # Test cases that previously caused issues
    test_cases = [
        ("Give me one fun fact about Saturn", "knowledge"),
        ("Write a hello world function", "code"),
        ("What is 2 + 2?", "math"),
        ("If P then Q, is this logical?", "logic"),
        ("Hello! How are you?", "agent0"),
    ]
    
    for query, expected_skill in test_cases:
        print(f"\n📤 Testing: {query}")
        print(f"   Expected skill: {expected_skill}")
        
        try:
            start_time = time.time()
            result = await router.route_query(query, force_skill=expected_skill)
            latency = (time.time() - start_time) * 1000
            
            print(f"✅ Response ({latency:.1f}ms): {result['text'][:100]}...")
            print(f"   Model: {result.get('model', 'unknown')}")
            print(f"   Confidence: {result.get('confidence', 0):.2f}")
            print(f"   Skill: {result.get('skill_type', 'unknown')}")
            
            # Check for problematic patterns
            if "TODO" in result['text']:
                print("❌ FOUND TODO STUB!")
            elif "mock response" in result['text'].lower():
                print("❌ FOUND MOCK RESPONSE!")
            elif "configure cloud providers" in result['text'].lower():
                print("❌ FOUND CLOUD PROVIDER MESSAGE!")
            else:
                print("✅ Response looks good!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n🎯 Testing Consensus Fusion...")
    
    # Create mock candidates to test fusion
    candidates = [
        {
            "specialist": "math_specialist",
            "text": "The answer is 4! 🧮",
            "confidence": 0.9,
            "model": "lightning-math"
        },
        {
            "specialist": "knowledge_specialist", 
            "text": "Based on my analysis: 2 + 2 equals 4 in base 10 arithmetic.",
            "confidence": 0.8,
            "model": "faiss-rag"
        },
        {
            "specialist": "agent0-local-enhanced",
            "text": "That's a great question! Let me analyze this: What is 2 + 2?. Based on our collective knowledge, here's what I can tell you...",
            "confidence": 0.75,
            "model": "agent0-local"
        }
    ]
    
    try:
        fused_result = await consensus_fuse(candidates, "What is 2 + 2?")
        print(f"✅ Consensus fusion result: {fused_result}")
        
        if len(fused_result) > 20 and "TODO" not in fused_result:
            print("✅ Fusion looks good!")
        else:
            print("⚠️ Fusion may need improvement")
            
    except Exception as e:
        print(f"❌ Fusion error: {e}")

async def test_vote_endpoint():
    """Test the vote endpoint with fixed specialists"""
    print(f"\n🗳️ Testing Vote Endpoint...")
    
    try:
        # Test with reduced specialist set (math + knowledge only per our config)
        result = await vote("Give me one fun fact about Saturn")
        
        print(f"✅ Vote result: {result['text'][:100]}...")
        print(f"   Winner: {result['winner']['specialist']}")
        print(f"   Confidence: {result['winner']['confidence']:.2f}")
        print(f"   Consensus: {result.get('consensus_fusion', False)}")
        print(f"   Total latency: {result['voting_stats']['total_latency_ms']:.1f}ms")
        
        # Check success criteria
        success_checks = [
            result['winner']['confidence'] > 0.5,  # Decent confidence
            "TODO" not in result['text'],  # No stubs
            "mock response" not in result['text'].lower(),  # No mocks
            result['voting_stats']['total_latency_ms'] < 5000,  # Under 5s
        ]
        
        if all(success_checks):
            print("🎉 Vote endpoint looking smooth!")
        else:
            print("⚠️ Vote endpoint needs more work")
            
    except Exception as e:
        print(f"❌ Vote endpoint error: {e}")

async def main():
    """Run all tests"""
    print("🚀 AutoGen Council Fix Validation")
    print("🎯 Checking if the surgical fixes resolved the issues...")
    
    await test_fixed_specialists()
    await test_vote_endpoint()
    
    print(f"\n🏁 Test Complete!")
    print("📋 Expected improvements:")
    print("  ✅ No more 'CloudRetry: Template stub detected' errors")
    print("  ✅ No more mock/stub responses leaking to users")
    print("  ✅ Higher confidence scores (>0.75 instead of 0.63)")
    print("  ✅ Faster responses (specialists disabled = less fan-out)")
    print("  ✅ Smoother consensus fusion")

if __name__ == "__main__":
    asyncio.run(main()) 