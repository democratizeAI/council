#!/usr/bin/env python3
"""
🌌 Direct Council Test - Bypass all checks
==========================================

Force Council to deliberate to ensure the five voices work.
"""

import asyncio
import os
import time

async def test_direct_council():
    """Test Council directly by forcing trigger conditions"""
    print("🌌 Direct Council Test - Forcing Deliberation")
    print("=" * 50)
    
    # Set up environment
    os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
    
    # Import after environment setup
    from router.council import CouncilRouter
    
    # Create Council instance
    council = CouncilRouter()
    
    # Force budget to be sufficient by mocking
    original_budget_func = None
    try:
        from router.cost_tracking import get_budget_status
        original_budget_func = get_budget_status
        # Mock sufficient budget
        def mock_budget():
            return {"remaining_budget_dollars": 10.0}
        import router.cost_tracking
        router.cost_tracking.get_budget_status = mock_budget
    except:
        print("⚠️ Budget tracking not available - proceeding anyway")
    
    # Test trigger conditions
    test_queries = [
        "Explain the architecture of microservices",  # Has 'explain'
        "Analyze quantum computing fundamentals",     # Has 'analyze' 
        "Compare different machine learning approaches", # Has 'compare'
        "Design a scalable cloud architecture",       # Has 'design'
    ]
    
    for query in test_queries:
        print(f"\n📤 Testing: {query}")
        
        # Check trigger
        should_trigger, reason = council.should_trigger_council(query)
        print(f"   Trigger check: {should_trigger} ({reason})")
        
        if should_trigger:
            print("🌌 **COUNCIL TRIGGERED!** Starting deliberation...")
            
            try:
                start_time = time.time()
                deliberation = await council.council_deliberate(query)
                total_time = (time.time() - start_time) * 1000
                
                print(f"✅ **DELIBERATION COMPLETE!** ({total_time:.1f}ms)")
                print(f"   Final response: {deliberation.final_response[:100]}...")
                print(f"   Voices used: {list(deliberation.voice_responses.keys())}")
                print(f"   Consensus: {deliberation.consensus_achieved}")
                print(f"   Cost: ${deliberation.total_cost_dollars:.4f}")
                print(f"   Risk flags: {deliberation.risk_flags}")
                
                # Test each voice response
                print(f"\n🎭 **Voice Responses:**")
                for voice, response in deliberation.voice_responses.items():
                    print(f"   {voice.value}: {response.response[:80]}...")
                    print(f"      Model: {response.model_used}, Confidence: {response.confidence:.2f}")
                
                print("🎉 **COUNCIL WORKING PERFECTLY!**")
                return True
                
            except Exception as e:
                print(f"❌ Deliberation failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"⚠️ Council not triggered: {reason}")
    
    # Restore original budget function
    if original_budget_func:
        router.cost_tracking.get_budget_status = original_budget_func
    
    return False

async def test_manual_trigger():
    """Force Council to trigger regardless of conditions"""
    print(f"\n🔧 Manual Council Trigger Test")
    print("-" * 40)
    
    os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
    
    from router.council import CouncilRouter
    
    council = CouncilRouter()
    
    # Override trigger logic
    council.council_enabled = True
    council.min_tokens_for_council = 5  # Lower threshold
    
    test_query = "Compare microservices vs monolithic architectures for startups"
    
    print(f"📤 Query: {test_query}")
    print(f"   Tokens: {len(test_query.split())}")
    print(f"   Keywords: {[kw for kw in council.council_trigger_keywords if kw in test_query.lower()]}")
    
    # Force trigger
    should_trigger, reason = council.should_trigger_council(test_query)
    print(f"   Should trigger: {should_trigger} ({reason})")
    
    if should_trigger:
        print("🌌 Starting forced deliberation...")
        
        try:
            deliberation = await council.council_deliberate(test_query)
            print(f"✅ Success! Response: {deliberation.final_response[:150]}...")
            print(f"   Voices: {len(deliberation.voice_responses)}")
            return True
        except Exception as e:
            print(f"❌ Failed: {e}")
            return False
    else:
        print("❌ Still not triggering - check trigger logic")
        return False

async def main():
    """Run direct Council tests"""
    print("🚀 Direct Council Validation")
    print("🎯 Testing the five-voice system directly")
    print("=" * 50)
    
    success1 = await test_direct_council()
    success2 = await test_manual_trigger()
    
    if success1 or success2:
        print(f"\n🎉 **COUNCIL SYSTEM OPERATIONAL!**")
        print("   Five voices: Reason · Spark · Edge · Heart · Vision")
    else:
        print(f"\n⚠️ Council needs debugging - check voice configurations")

if __name__ == "__main__":
    asyncio.run(main()) 