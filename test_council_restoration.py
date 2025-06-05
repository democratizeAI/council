#!/usr/bin/env python3
"""
🌌 Council Restoration Test Suite
================================

Test the restored five-voice Council system:
- Reason · Spark · Edge · Heart · Vision
- Shared scratchpad integration
- Council-first routing
"""

import asyncio
import logging
import time
import os
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

async def test_council_routing():
    """Test Council-first routing vs specialist fallback"""
    print("🌌 Testing Council Restoration")
    print("=" * 50)
    
    # Import after logging setup
    from router_cascade import RouterCascade
    
    # Test both modes
    test_scenarios = [
        {
            "name": "Council Disabled (Specialist Mode)",
            "env": {"SWARM_COUNCIL_ENABLED": "false"},
            "expected_path": "specialist"
        },
        {
            "name": "Council Enabled (Five-Voice Mode)", 
            "env": {"SWARM_COUNCIL_ENABLED": "true"},
            "expected_path": "council"
        }
    ]
    
    test_queries = [
        "Explain quantum computing in simple terms",  # Should trigger council
        "What is 2 + 2?",                           # Might stay with specialist
        "Compare different sorting algorithms",       # Should trigger council
        "Hello there!",                             # Quick response
    ]
    
    for scenario in test_scenarios:
        print(f"\n🧪 **{scenario['name']}**")
        print("-" * 40)
        
        # Set environment for this test
        for key, value in scenario['env'].items():
            os.environ[key] = value
        
        # Create fresh router instance
        router = RouterCascade()
        
        for query in test_queries:
            print(f"\n📤 Query: {query}")
            
            try:
                start_time = time.time()
                result = await router.route_query(query)
                latency = (time.time() - start_time) * 1000
                
                # Analyze response
                skill_type = result.get('skill_type', 'unknown')
                model = result.get('model', 'unknown')
                confidence = result.get('confidence', 0)
                
                print(f"✅ Response ({latency:.1f}ms):")
                print(f"   Path: {skill_type}")
                print(f"   Model: {model}")
                print(f"   Confidence: {confidence:.2f}")
                print(f"   Text: {result.get('text', '')[:80]}...")
                
                # Check if routing matches expectation
                if scenario['expected_path'] == 'council':
                    if 'council' in skill_type or 'council' in model:
                        print("✅ **COUNCIL ROUTING CONFIRMED!**")
                    elif 'explain' in query.lower() or 'compare' in query.lower():
                        print("⚠️ Council might not have triggered (check budget/config)")
                    else:
                        print("✅ Specialist routing (expected for simple query)")
                else:
                    if 'council' not in skill_type:
                        print("✅ Specialist routing confirmed")
                    else:
                        print("❌ Unexpected council routing when disabled")
                        
                # Check for Council metadata
                if 'council_metadata' in result:
                    meta = result['council_metadata']
                    print(f"🌌 Council Details:")
                    print(f"   Voices: {meta.get('voices', [])}")
                    print(f"   Consensus: {meta.get('consensus', False)}")
                    print(f"   Cost: ${meta.get('cost_dollars', 0):.4f}")
                    print(f"   Risk Flags: {meta.get('risk_flags', [])}")
                
            except Exception as e:
                print(f"❌ Error: {e}")

async def test_scratchpad_integration():
    """Test scratchpad reading/writing"""
    print(f"\n📝 Testing Scratchpad Integration")
    print("-" * 40)
    
    try:
        from common.scratchpad import write, read, search_similar
        
        # Test session
        session_id = f"test_session_{int(time.time())}"
        
        # Write some test entries
        print("📝 Writing test entries...")
        entry1 = write(session_id, "agent0", "Planning refactoring for utils.py", tags=["planning", "code"])
        entry2 = write(session_id, "reason", "Analyzed the code structure - needs modularization", tags=["analysis", "code"])
        entry3 = write(session_id, "edge", "Risk: Large refactor could introduce bugs", tags=["risk", "code"])
        
        print(f"   Entry IDs: {entry1}, {entry2}, {entry3}")
        
        # Read back entries
        print("📖 Reading entries...")
        entries = read(session_id, limit=5)
        for entry in entries:
            print(f"   [{entry.agent}] {entry.content} (tags: {entry.tags})")
        
        print(f"✅ Scratchpad working - {len(entries)} entries retrieved")
        
        # Test search if Qdrant available
        try:
            similar = search_similar("refactoring code", limit=3)
            if similar:
                print(f"🔍 Semantic search working - {len(similar)} similar entries found")
            else:
                print("🔍 Semantic search available but no results (expected for new data)")
        except Exception as e:
            print(f"🔍 Semantic search not available: {e}")
        
    except ImportError:
        print("📝 Scratchpad not available - check dependencies (redis, qdrant-client)")
    except Exception as e:
        print(f"❌ Scratchpad test failed: {e}")

async def test_council_config():
    """Test Council configuration loading"""
    print(f"\n⚙️ Testing Council Configuration")
    print("-" * 40)
    
    try:
        import yaml
        
        # Check if council.yml exists and is valid
        config_path = "config/council.yml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            print("✅ council.yml found and valid")
            
            # Check voices
            voices = config.get('voices', {})
            print(f"   Voices configured: {list(voices.keys())}")
            
            # Check each voice has required fields
            required_fields = ['model', 'prompt', 'max_tokens', 'temperature']
            for voice_name, voice_config in voices.items():
                missing = [field for field in required_fields if field not in voice_config]
                if missing:
                    print(f"⚠️ {voice_name} missing: {missing}")
                else:
                    print(f"✅ {voice_name} properly configured")
            
            # Check council settings
            council_config = config.get('council', {})
            print(f"   Council enabled: {council_config.get('enabled', False)}")
            print(f"   Budget: ${council_config.get('max_cost_per_request', 0)}/request")
            print(f"   Triggers: {council_config.get('trigger_keywords', [])}")
            
        else:
            print("❌ config/council.yml not found!")
            
    except Exception as e:
        print(f"❌ Config test failed: {e}")

async def test_end_to_end_flow():
    """Test complete end-to-end Council flow"""
    print(f"\n🚀 Testing End-to-End Council Flow")
    print("-" * 40)
    
    # Enable Council for this test
    os.environ['SWARM_COUNCIL_ENABLED'] = 'true'
    
    try:
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Test query that should definitely trigger Council
        complex_query = "Analyze the pros and cons of microservices vs monolithic architecture, " \
                       "and explain which approach would be better for a startup with limited resources"
        
        print(f"📤 Complex query: {complex_query[:60]}...")
        
        start_time = time.time()
        result = await router.route_query(complex_query)
        total_latency = (time.time() - start_time) * 1000
        
        print(f"⏱️ Total latency: {total_latency:.1f}ms")
        
        # Analyze result
        if result.get('skill_type') == 'council':
            print("✅ **COUNCIL DELIBERATION SUCCESSFUL!**")
            
            # Check response quality
            response_text = result.get('text', '')
            quality_indicators = [
                len(response_text) > 100,  # Substantial response
                'microservices' in response_text.lower(),  # Addressed the topic
                'monolithic' in response_text.lower(),     # Addressed the topic
                any(word in response_text.lower() for word in ['pros', 'cons', 'advantages', 'disadvantages']),
            ]
            
            quality_score = sum(quality_indicators) / len(quality_indicators)
            print(f"📊 Response quality: {quality_score:.0%}")
            print(f"   Length: {len(response_text)} chars")
            print(f"   Preview: {response_text[:150]}...")
            
            # Check metadata
            if 'council_metadata' in result:
                meta = result['council_metadata']
                print(f"🌌 Council metadata:")
                print(f"   Voices: {len(meta.get('voices', []))}")
                print(f"   Consensus: {meta.get('consensus', False)}")
                print(f"   Cost: ${meta.get('cost_dollars', 0):.4f}")
            
            if quality_score > 0.5:
                print("🎉 **COUNCIL RESTORATION SUCCESSFUL!**")
            else:
                print("⚠️ Council working but response quality needs improvement")
                
        else:
            print(f"⚠️ Council not triggered - routed to {result.get('skill_type')}")
            print("   Check: budget limits, trigger keywords, or Council availability")
    
    except Exception as e:
        print(f"❌ E2E test failed: {e}")

async def main():
    """Run all tests"""
    print("🚀 Council Restoration Test Suite")
    print("🎯 Validating five-voice Council with scratchpad integration")
    print("=" * 60)
    
    await test_council_config()
    await test_scratchpad_integration()
    await test_council_routing()
    await test_end_to_end_flow()
    
    print(f"\n🏁 Test Suite Complete!")
    print("📋 Expected p95 latency: ~500-2000ms")
    print("💰 Expected cost: ≤$0.30 per Council deliberation")
    print("🌌 Five voices: Reason · Spark · Edge · Heart · Vision")

if __name__ == "__main__":
    asyncio.run(main()) 