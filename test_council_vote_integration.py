#!/usr/bin/env python3
"""
Test the Council-enhanced /vote endpoint integration
"""

import os
import asyncio
import sys

# Set environment for testing
os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
os.environ['SWARM_BUDGET'] = '10.00'

async def test_council_vote():
    """Test the enhanced /vote endpoint with Council voices"""
    print("🗳️ Testing Council-enhanced vote endpoint...")
    
    try:
        # Import the vote endpoint function
        sys.path.append('.')
        from app.main import VotingRequest, vote_endpoint
        
        # Create test request with traditional voting candidates
        request = VotingRequest(
            prompt="What are the benefits of renewable energy?",
            candidates=["gpt-3.5-turbo", "claude-3-haiku", "llama-2-7b"],
            top_k=2
        )
        
        print(f"🗳️ Sending vote request: '{request.prompt}'")
        print(f"📊 Candidates: {request.candidates}")
        print(f"🏆 Top-K: {request.top_k}")
        
        # Call enhanced vote endpoint
        response = await vote_endpoint(request)
        
        print("\n✅ Enhanced vote endpoint successful!")
        
        # Traditional voting results
        print(f"\n🏆 VOTING WINNER: {response.winner.get('model', 'unknown')}")
        print(f"📝 Winner response: {response.text[:100]}...")
        print(f"📊 Total candidates: {len(response.all_candidates)}")
        print(f"💰 Total cost: ${response.total_cost_cents/100:.4f}")
        
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
            print("\n🎭 COUNCIL: Not used (expected if disabled)")
        
        # Voting statistics
        if response.voting_stats:
            print(f"\n📈 VOTING STATS:")
            for key, value in response.voting_stats.items():
                print(f"   {key}: {value}")
        
        print("\n🎉 Council + Vote integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_council_vote())
    sys.exit(0 if result else 1) 