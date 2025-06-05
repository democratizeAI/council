#!/usr/bin/env python3
"""
Test the Council-enhanced /vote endpoint in autogen_api_shim.py
"""

import os
import asyncio
import sys

# Set environment for testing
os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
os.environ['SWARM_BUDGET'] = '10.00'

async def test_shim_council_vote():
    """Test the enhanced shim /vote endpoint with Council voices"""
    print("🗳️ Testing autogen_api_shim Council-enhanced vote endpoint...")
    
    try:
        # Import the shim vote endpoint function
        sys.path.append('.')
        from autogen_api_shim import VoteRequest, vote_endpoint
        
        # Create test request with traditional voting candidates
        request = VoteRequest(
            prompt="Explain the benefits of cloud computing for small businesses",
            candidates=["gpt-3.5-turbo", "claude-3-haiku", "llama-2-7b"],
            top_k=2
        )
        
        print(f"🗳️ Sending shim vote request: '{request.prompt}'")
        print(f"📊 Candidates: {request.candidates}")
        print(f"🏆 Top-K: {request.top_k}")
        
        # Call enhanced shim vote endpoint
        response = await vote_endpoint(request)
        
        print("\n✅ Enhanced shim vote endpoint successful!")
        
        # Traditional voting results
        print(f"\n🏆 VOTING WINNER: {response.model_used}")
        print(f"📝 Winner response: {response.text[:100]}...")
        print(f"📊 Candidates tested: {len(response.candidates)}")
        print(f"💰 Total cost: ${response.total_cost_cents/100:.4f}")
        print(f"⚡ Latency: {response.latency_ms:.1f}ms")
        print(f"🎯 Confidence: {response.confidence:.2f}")
        
        # Council deliberation results
        if response.council_used:
            print(f"\n🎭 COUNCIL DELIBERATION:")
            print(f"🎯 Council consensus: {response.council_consensus[:100]}...")
            print(f"🗣️ Council voices: {len(response.council_voices)} voices")
            
            if response.council_voices:
                print("\n🗣️ Individual Council voices:")
                for voice in response.council_voices:
                    print(f"   {voice['voice']}: {voice['reply'][:60]}... (${voice['cost']:.4f})")
        else:
            print("\n🎭 COUNCIL: Not used")
        
        print("\n🎉 Shim Council + Vote integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_shim_council_vote())
    sys.exit(0 if result else 1) 