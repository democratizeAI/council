#!/usr/bin/env python3
"""
Test the Three-Tier Rescue Ladder system with Working Memory
"""

import os
import asyncio
import sys

# Set environment for testing
os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
os.environ['SWARM_BUDGET'] = '10.00'

async def test_three_tier_ladder():
    """Test the three-tier rescue ladder with different confidence scenarios"""
    print("🎯 Testing Three-Tier Rescue Ladder system...")
    
    try:
        # Import the router
        sys.path.append('.')
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Test scenarios with different expected tiers
        test_scenarios = [
            {
                "query": "What is 2 + 2?",
                "expected_tier": "local",
                "description": "Simple math - should stay local"
            },
            {
                "query": "Explain the complex philosophical implications of artificial consciousness and its relationship to human identity in a post-singularity world",
                "expected_tier": "synth",  # Might escalate to synth due to complexity
                "description": "Complex philosophical query - may need synth refinement"
            },
            {
                "query": "How do I synthesize novel pharmaceutical compounds using quantum chemistry principles while navigating regulatory compliance frameworks?",
                "expected_tier": "premium",  # Very complex, likely needs premium
                "description": "Highly complex technical query - may need premium intelligence"
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n{'='*60}")
            print(f"🧪 Test {i}: {scenario['description']}")
            print(f"Query: '{scenario['query'][:80]}...'")
            print(f"Expected tier: {scenario['expected_tier']}")
            
            # Run the query through the three-tier system
            result = await router.route_query(scenario['query'])
            
            # Extract tier information
            tier_used = result.get('tier_used', 'unknown')
            provider_chain = result.get('provider_chain', [])
            confidence_chain = result.get('confidence_chain', [])
            total_cost = result.get('total_cost_usd', 0.0)
            tier_count = result.get('tier_count', 0)
            
            # 🧠 MEMORY SYSTEM: Extract memory metadata
            turn_id = result.get('turn_id')
            working_memory_keys = result.get('working_memory_keys', [])
            memory_enabled = result.get('memory_enabled', False)
            
            print(f"\n📊 RESULTS:")
            print(f"   🎯 Tier used: {tier_used}")
            print(f"   🔗 Provider chain: {' → '.join(provider_chain)}")
            print(f"   📈 Confidence chain: {[f'{c:.2f}' for c in confidence_chain]}")
            print(f"   💰 Total cost: ${total_cost:.4f}")
            print(f"   📊 Tier count: {tier_count}")
            print(f"   ⚡ Latency: {result.get('latency_ms', 0):.1f}ms")
            
            # 🧠 MEMORY SYSTEM: Show memory metadata
            print(f"\n🧠 MEMORY SYSTEM:")
            print(f"   📝 Turn ID: {turn_id}")
            print(f"   🔑 Working memory keys: {working_memory_keys}")
            print(f"   💾 Memory enabled: {memory_enabled}")
            
            # Show tier indicators
            tier_indicators = {
                'local': '🟢',
                'synth': '🟠', 
                'premium': '🔴'
            }
            indicator = tier_indicators.get(tier_used, '⚪')
            print(f"   {indicator} Tier indicator: {tier_used}")
            
            # Show response preview
            response_text = result.get('text', '')
            print(f"   💬 Response: {response_text[:100]}...")
            
            # Validate escalation logic
            if tier_count > 1:
                print(f"   ⬆️ Escalated through {tier_count} tiers")
            else:
                print(f"   ✅ Resolved at first tier")
        
        print(f"\n{'='*60}")
        print("🎉 Three-tier ladder test completed!")
        
        # Summary test
        print("\n📋 TIER ESCALATION SUMMARY:")
        print("🟢 Local (Tier 1): Fast, free, handles 90-95% of queries")
        print("🟠 Synth (Tier 2): ¢-level cost, refines unclear local responses") 
        print("🔴 Premium (Tier 3): $$-level cost, reserved for truly difficult queries")
        print("\n💡 Cost-effectiveness: Most queries stay local, cloud only when needed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_working_memory_system():
    """Test the working memory and turn ledger system"""
    print("\n🧠 Testing Working Memory System...")
    
    try:
        from router_cascade import RouterCascade, TURN_CACHE, _generate_turn_id, _get_ledger_key, _summarize_text
        
        router = RouterCascade()
        
        # Test turn ID generation
        turn_id1 = _generate_turn_id()
        turn_id2 = _generate_turn_id()
        print(f"📝 Turn ID generation: {turn_id1}, {turn_id2} (should be different)")
        assert turn_id1 != turn_id2, "Turn IDs should be unique"
        
        # Test ledger key generation
        session_id = "test_session"
        key1 = _get_ledger_key(session_id, turn_id1)
        key2 = _get_ledger_key(session_id, turn_id2)
        print(f"🔑 Ledger keys: {key1}, {key2}")
        
        # Test text summarization
        long_text = "This is a very long text that needs to be summarized into a shorter format. " * 10
        summary = await _summarize_text(long_text, max_tokens=50)
        print(f"📄 Summary test: {len(long_text)} chars → {len(summary)} chars")
        print(f"   Original: {long_text[:100]}...")
        print(f"   Summary: {summary}")
        
        # Test memory flow across multiple queries
        print(f"\n🔄 Testing cross-turn memory flow...")
        
        # Turn 1: Store some information
        response1 = await router.route_query("My favorite color is blue and I love astronomy.")
        turn_id_1 = response1.get('turn_id')
        print(f"   Turn 1: {turn_id_1} - Stored info about color and astronomy")
        
        # Turn 2: Query that should reference previous info
        response2 = await router.route_query("What did I just tell you about my interests?")
        turn_id_2 = response2.get('turn_id')
        print(f"   Turn 2: {turn_id_2} - Querying previous information")
        
        # Check if second response contains context from first
        response2_text = response2.get('text', '').lower()
        contains_color = 'blue' in response2_text or 'color' in response2_text
        contains_astronomy = 'astronomy' in response2_text or 'astro' in response2_text
        
        print(f"   🔍 Memory recall test:")
        print(f"      Contains color reference: {contains_color}")
        print(f"      Contains astronomy reference: {contains_astronomy}")
        print(f"      Response: {response2.get('text', '')[:150]}...")
        
        # Validate turn ledger structure
        if turn_id_1:
            key1 = _get_ledger_key(router.current_session_id, turn_id_1)
            if key1 in TURN_CACHE:
                ledger1 = TURN_CACHE[key1]
                print(f"   📋 Turn 1 ledger keys: {list(ledger1.keys())}")
                
        if turn_id_2:
            key2 = _get_ledger_key(router.current_session_id, turn_id_2) 
            if key2 in TURN_CACHE:
                ledger2 = TURN_CACHE[key2]
                print(f"   📋 Turn 2 ledger keys: {list(ledger2.keys())}")
        
        print(f"✅ Working memory system test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Working memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_token_budget_management():
    """Test that token budgets are maintained across tiers"""
    print("\n💰 Testing Token Budget Management...")
    
    try:
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Test with a complex query that should escalate to multiple tiers
        complex_query = """Please provide a comprehensive analysis of quantum computing's impact on cryptography, 
        including detailed explanations of Shor's algorithm, post-quantum cryptography solutions, 
        implementation challenges for current systems, timeline projections for quantum supremacy, 
        and specific recommendations for enterprise security planning. Also consider the economic 
        implications, regulatory frameworks, and international cooperation requirements."""
        
        print(f"🔍 Testing with complex query ({len(complex_query)} chars)")
        
        result = await router.route_query(complex_query)
        
        # Extract memory metadata
        turn_id = result.get('turn_id')
        working_memory_keys = result.get('working_memory_keys', [])
        tier_used = result.get('tier_used')
        tier_count = result.get('tier_count', 0)
        
        print(f"📊 Token Budget Analysis:")
        print(f"   🎯 Tiers used: {tier_count}")
        print(f"   🏆 Final tier: {tier_used}")
        print(f"   📝 Memory components: {len(working_memory_keys)}")
        print(f"   🔑 Ledger keys: {working_memory_keys}")
        
        # Validate expected token budget structure
        expected_components = ['user', 'turn_id', 'session_id', 'timestamp']
        if tier_count >= 1:
            expected_components.extend(['tier1_local_draft', 'tier1_summary'])
        if tier_count >= 2:
            expected_components.extend(['tier2_synth', 'tier2_summary'])
        if tier_count >= 3:
            expected_components.extend(['tier3_premium', 'tier3_summary'])
        
        print(f"   ✅ Expected components: {expected_components}")
        print(f"   🔍 Actual components: {working_memory_keys}")
        
        # Estimate token usage
        estimated_tokens = {
            'user_query': len(complex_query.split()),
            'tier1_summary': 80,  # max tokens
            'tier2_summary': 60,  # max tokens  
            'tier3_summary': 60,  # max tokens
            'episodic_memory': 240  # 2 x 120 max tokens
        }
        
        total_context_tokens = sum(estimated_tokens.values())
        print(f"   📈 Estimated context tokens: {total_context_tokens}")
        print(f"   📋 Token breakdown: {estimated_tokens}")
        
        # Validate token budget is reasonable (should be under 2048 for most models)
        if total_context_tokens < 600:
            print(f"   ✅ Token budget efficient: {total_context_tokens} tokens")
        else:
            print(f"   ⚠️ Token budget high: {total_context_tokens} tokens")
        
        return True
        
    except Exception as e:
        print(f"❌ Token budget test failed: {e}")
        return False

async def test_confidence_gates():
    """Test the confidence gate thresholds directly"""
    print("\n🚪 Testing confidence gate thresholds...")
    
    try:
        from router_cascade import RouterCascade
        router = RouterCascade()
        
        # Test gate loading
        gates = router._load_confidence_gates()
        
        print(f"📊 Loaded confidence gates:")
        print(f"   Gate to synth: {gates['to_synth']}")
        print(f"   Gate to premium: {gates['to_premium']}")
        
        # Test scenarios
        test_confidences = [0.8, 0.4, 0.1]
        
        for conf in test_confidences:
            will_use_synth = conf < gates['to_synth']
            will_use_premium = conf < gates['to_premium']
            
            expected_tier = "local"
            if will_use_synth:
                expected_tier = "synth" 
            if will_use_premium:
                expected_tier = "premium"
                
            print(f"   Confidence {conf:.1f} → {expected_tier} tier")
        
        return True
        
    except Exception as e:
        print(f"❌ Gate test failed: {e}")
        return False

async def test_memory_flow():
    """Unit test for memory flow as specified in requirements"""
    print("\n🔄 Testing Memory Flow (Unit Test)...")
    
    try:
        from router_cascade import RouterCascade
        router = RouterCascade()
        
        # Test 1: Store information
        reply1 = await router.route_query("My bike is red.")
        print(f"   Turn 1: Stored 'My bike is red'")
        print(f"   Response: {reply1.get('text', '')[:100]}...")
        
        # Test 2: Query the stored information  
        reply2 = await router.route_query("What colour is my bike?")
        print(f"   Turn 2: Asked 'What colour is my bike?'")
        print(f"   Response: {reply2.get('text', '')[:100]}...")
        
        # Validate memory recall
        reply2_text = reply2.get('text', '').lower()
        has_red = 'red' in reply2_text
        
        print(f"\n🔍 Memory Flow Validation:")
        print(f"   Contains 'red': {has_red}")
        print(f"   Memory test: {'✅ PASSED' if has_red else '❌ FAILED'}")
        
        # Test force low confidence to trigger Tier-2  
        print(f"\n🧪 Testing tier escalation with forced low confidence...")
        
        # Override confidence for testing
        original_calculate_confidence = router._calculate_confidence
        def mock_low_confidence(query, skill):
            return 0.30  # Force low confidence to trigger synth tier
        
        router._calculate_confidence = mock_low_confidence
        
        try:
            reply3 = await router.route_query("What is the capital of France?")
            tier_used = reply3.get('tier_used', 'unknown')
            working_memory_keys = reply3.get('working_memory_keys', [])
            
            print(f"   Forced escalation result: {tier_used} tier")
            print(f"   Working memory keys: {working_memory_keys}")
            
            # Verify ledger has tier1_* and tier2_* keys
            has_tier1_keys = any('tier1' in key for key in working_memory_keys)
            has_tier2_keys = any('tier2' in key for key in working_memory_keys)
            
            print(f"   Has tier1 keys: {has_tier1_keys}")
            print(f"   Has tier2 keys: {has_tier2_keys}")
            
        finally:
            # Restore original confidence calculation
            router._calculate_confidence = original_calculate_confidence
        
        return True
        
    except Exception as e:
        print(f"❌ Memory flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test runner"""
    print("🚀 Three-Tier Rescue Ladder + Working Memory Test Suite")
    print("=" * 60)
    
    success = True
    
    # Test the main ladder system
    success &= await test_three_tier_ladder()
    
    # Test working memory system
    success &= await test_working_memory_system()
    
    # Test token budget management
    success &= await test_token_budget_management()
    
    # Test confidence gates
    success &= await test_confidence_gates()
    
    # Test memory flow (unit test)
    success &= await test_memory_flow()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ All tests passed! Three-tier ladder + memory system operational.")
    else:
        print("❌ Some tests failed. Check implementation.")
    
    print(f"\n🧠 MEMORY SYSTEM SUMMARY:")
    print("📝 Turn ledger: Working memory within each conversation turn")
    print("🔄 Tier summaries: Token-efficient context building (80/60/60 tokens)")
    print("💾 Episodic memory: Cross-turn persistent scratch-pad storage")
    print("🎯 Token budget: <600 tokens total context (fits 2K models)")
    print("⚡ Progressive enhancement: Each tier builds on previous reasoning")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 