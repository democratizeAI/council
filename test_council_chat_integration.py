#!/usr/bin/env python3
"""
Test the Council-enhanced chat integration recipe
"""

import os
import asyncio
import sys

# Set environment for testing
os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
os.environ['SWARM_BUDGET'] = '10.00'

async def test_council_chat():
    """Test the Council chat endpoint functionality"""
    print("🧪 Testing Council-enhanced chat integration...")
    
    try:
        # Import the chat function
        sys.path.append('.')
        from app.main import ChatRequest, chat
        
        # Create test request
        request = ChatRequest(
            prompt="Compare microservices vs monolithic architectures for startups",
            session_id="test_integration_123"
        )
        
        print(f"📤 Sending test query: '{request.prompt}'")
        
        # Call chat endpoint
        response = await chat(request)
        
        print("✅ Chat endpoint successful!")
        print(f"📝 Response: {response.text[:100]}...")
        print(f"🎭 Voices: {len(response.voices)} voices detected")
        print(f"💰 Total cost: ${response.cost_usd:.4f}")
        print(f"🔗 Model chain: {' → '.join(response.model_chain)}")
        
        if response.voices:
            print("\n🗣️ Individual voice responses:")
            for voice in response.voices:
                print(f"   {voice['voice']}: {voice['reply'][:60]}... (${voice['cost']:.4f})")
        
        # Test scratchpad integration
        try:
            from common.scratchpad import read as sp_read
            entries = sp_read(request.session_id, limit=5)
            council_entries = [e for e in entries if "council" in e.tags]
            
            if council_entries:
                print(f"\n📝 Scratchpad: {len(council_entries)} Council consensus entries found")
                latest = council_entries[-1]
                print(f"   Latest: {latest.content[:60]}...")
            else:
                print("\n📝 Scratchpad: No Council entries found (expected if scratchpad unavailable)")
                
        except ImportError:
            print("\n📝 Scratchpad: Module not available (continuing without)")
        
        print("\n🎉 Council chat integration test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_council_chat())
    sys.exit(0 if result else 1) 