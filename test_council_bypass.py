#!/usr/bin/env python3
"""
🌌 Council Bypass Test - Direct Deliberation
============================================

Bypass all trigger checks and directly test Council deliberation.
"""

import asyncio
import os
import time

async def test_council_deliberation():
    """Test Council deliberation directly"""
    print("🌌 Testing Council Deliberation Directly")
    print("=" * 50)
    
    # Set up environment
    os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
    
    # Import after environment setup
    from router.council import CouncilRouter
    
    # Create Council instance
    council = CouncilRouter()
    
    print(f"✅ Council initialized: {council.council_enabled}")
    print(f"   Voice models: {list(council.voice_models.keys())}")
    
    # Test query
    test_query = "Explain the trade-offs between microservices and monolithic architecture"
    
    print(f"\n📤 Testing deliberation on: {test_query}")
    
    try:
        start_time = time.time()
        
        # Call deliberation directly (bypass trigger checks)
        print("🌌 Starting five-voice deliberation...")
        deliberation = await council.council_deliberate(test_query)
        
        total_time = (time.time() - start_time) * 1000
        
        print(f"\n✅ **COUNCIL DELIBERATION SUCCESSFUL!** ({total_time:.1f}ms)")
        print("=" * 60)
        
        # Display results
        print(f"🎯 **Final Council Decision:**")
        print(f"{deliberation.final_response}")
        print("\n" + "=" * 60)
        
        print(f"📊 **Deliberation Statistics:**")
        print(f"   Voices participated: {len(deliberation.voice_responses)}")
        print(f"   Consensus achieved: {deliberation.consensus_achieved}")
        print(f"   Total cost: ${deliberation.total_cost_dollars:.4f}")
        print(f"   Total latency: {deliberation.total_latency_ms:.1f}ms")
        print(f"   Risk flags: {deliberation.risk_flags}")
        
        print(f"\n🎭 **Individual Voice Contributions:**")
        voice_names = {
            'reason': '🧠 Reason',
            'spark': '✨ Spark', 
            'edge': '🗡️ Edge',
            'heart': '❤️ Heart',
            'vision': '🔮 Vision'
        }
        
        for voice, response in deliberation.voice_responses.items():
            voice_icon = voice_names.get(voice.value, voice.value)
            print(f"\n{voice_icon}:")
            print(f"   Response: {response.response[:100]}...")
            print(f"   Model: {response.model_used}")
            print(f"   Confidence: {response.confidence:.2f}")
            print(f"   Latency: {response.latency_ms:.1f}ms")
            print(f"   Cost: ${response.cost_dollars:.4f}")
        
        # Quality assessment
        response_length = len(deliberation.final_response)
        has_microservices = 'microservices' in deliberation.final_response.lower()
        has_monolithic = 'monolithic' in deliberation.final_response.lower()
        has_trade_offs = any(word in deliberation.final_response.lower() 
                           for word in ['trade-off', 'pros', 'cons', 'advantage', 'disadvantage'])
        
        quality_score = sum([
            response_length > 100,
            has_microservices,
            has_monolithic, 
            has_trade_offs,
            deliberation.consensus_achieved
        ]) / 5
        
        print(f"\n📈 **Quality Assessment:** {quality_score:.0%}")
        print(f"   Length: {response_length} chars ✅" if response_length > 100 else f"   Length: {response_length} chars ❌")
        print(f"   Addressed microservices: {'✅' if has_microservices else '❌'}")
        print(f"   Addressed monolithic: {'✅' if has_monolithic else '❌'}")
        print(f"   Discussed trade-offs: {'✅' if has_trade_offs else '❌'}")
        print(f"   Achieved consensus: {'✅' if deliberation.consensus_achieved else '❌'}")
        
        if quality_score >= 0.6:
            print(f"\n🎉 **COUNCIL RESTORATION SUCCESSFUL!**")
            print("   Five voices are working harmoniously!")
            print("   Reason · Spark · Edge · Heart · Vision 🌌")
            return True
        else:
            print(f"\n⚠️ Council functioning but needs quality improvement")
            return False
            
    except Exception as e:
        print(f"❌ Council deliberation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run bypass test"""
    print("🚀 Council Bypass Test")
    print("🎯 Direct five-voice deliberation test")
    print("=" * 50)
    
    success = await test_council_deliberation()
    
    if success:
        print(f"\n🏆 **TEST PASSED!**")
        print("   The five-voice Council is operational!")
        print("   Ready for Agent-Zero integration!")
    else:
        print(f"\n❌ **TEST FAILED**")
        print("   Council needs debugging")

if __name__ == "__main__":
    asyncio.run(main()) 