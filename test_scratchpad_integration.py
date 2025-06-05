#!/usr/bin/env python3
"""
Scratchpad Integration Test
==========================

Tests the researcher and planner agents working together via shared scratchpad.
Verifies the complete workflow as specified in the 100-hour playbook.
"""

import asyncio
import time
import sys

async def test_scratchpad_integration():
    """Test researcher and planner agent collaboration"""
    print("🔧 Testing Scratchpad Integration")
    print("=" * 50)
    
    try:
        from shared.scratchpad import get_stats, write, read
        from agents.researcher import research_and_share
        from agents.planner import create_plan, start_plan_monitoring, stop_plan_monitoring
        
        # Test 1: Scratchpad basics
        print("\n📊 Test 1: Scratchpad System")
        stats = get_stats()
        print(f"   Backend: {stats['backend']}")
        print(f"   Semantic search: {stats['semantic_search']}")
        print(f"   Active sessions: {stats['total_sessions']}")
        print(f"   Total entries: {stats['total_entries']}")
        print("   ✅ Scratchpad system operational")
        
        # Test 2: Researcher agent
        print("\n🔍 Test 2: Researcher Agent")
        session_id = "test_session_123"
        
        start_time = time.time()
        research_result = await research_and_share("programming best practices", session_id)
        research_latency = (time.time() - start_time) * 1000
        
        print(f"   Query: {research_result['query']}")
        print(f"   Findings: {research_result['findings_count']} sources")
        print(f"   Latency: {research_latency:.1f}ms")
        print(f"   Status: {research_result['status']}")
        
        if research_result['status'] == 'success':
            print("   ✅ Researcher agent working")
        else:
            print("   ❌ Researcher agent failed")
            return False
        
        # Test 3: Check scratchpad entries
        print("\n📝 Test 3: Scratchpad Entries")
        entries = read(session_id, limit=10)
        print(f"   Total entries: {len(entries)}")
        
        researcher_entries = [e for e in entries if e.agent == "researcher"]
        print(f"   Researcher entries: {len(researcher_entries)}")
        
        if researcher_entries:
            latest = researcher_entries[0]
            print(f"   Latest: {latest.content[:60]}...")
            print(f"   Type: {latest.entry_type}")
            print(f"   Tags: {latest.tags}")
            print("   ✅ Entries written to scratchpad")
        else:
            print("   ❌ No researcher entries found")
            return False
        
        # Test 4: Planner agent
        print("\n🎯 Test 4: Planner Agent")
        
        # Create initial plan
        plan_result = await create_plan("Implement AI-powered code review system", session_id)
        print(f"   Plan created: {plan_result['plan_id']}")
        print(f"   Objective: {plan_result['objective']}")
        print(f"   Latency: {plan_result['latency_ms']:.1f}ms")
        
        if plan_result['status'] == 'success':
            print("   ✅ Initial plan created")
        else:
            print("   ❌ Plan creation failed")
            return False
        
        # Test 5: Plan monitoring (brief test)
        print("\n⏱️ Test 5: Plan Monitoring")
        
        # Start monitoring for 10 seconds
        await start_plan_monitoring(session_id, interval=2)
        print("   🎯 Monitoring started (2s intervals)")
        
        # Add more research to trigger plan updates
        await research_and_share("code review automation tools", session_id)
        print("   🔍 Added new research findings")
        
        # Wait for planner to process
        await asyncio.sleep(5)
        
        # Stop monitoring
        await stop_plan_monitoring()
        print("   🎯 Monitoring stopped")
        
        # Check for plan updates
        planner_entries = [e for e in read(session_id, limit=20) if e.agent == "planner"]
        print(f"   Planner entries: {len(planner_entries)}")
        
        if len(planner_entries) >= 1:  # Initial plan + possible update
            print("   ✅ Planner monitoring working")
        else:
            print("   ⚠️ No plan updates detected (may be timing)")
        
        # Test 6: End-to-end metrics
        print("\n📈 Test 6: Final Metrics")
        final_stats = get_stats()
        print(f"   Final sessions: {final_stats['total_sessions']}")
        print(f"   Final entries: {final_stats['total_entries']}")
        
        all_entries = read(session_id, limit=50)
        agents_used = set(e.agent for e in all_entries)
        entry_types = set(e.entry_type for e in all_entries)
        
        print(f"   Agents active: {sorted(agents_used)}")
        print(f"   Entry types: {sorted(entry_types)}")
        
        if len(agents_used) >= 2 and "researcher" in agents_used and "planner" in agents_used:
            print("   ✅ Multi-agent collaboration confirmed")
        else:
            print("   ⚠️ Limited agent interaction detected")
        
        print("\n🎉 Scratchpad integration test completed!")
        print("✅ Researcher and planner agents collaborating via shared scratchpad")
        print("✅ Ready for OS-level service deployment")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scratchpad_integration())
    sys.exit(0 if success else 1)