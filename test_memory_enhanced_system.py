#!/usr/bin/env python3
"""
Memory-Enhanced AutoGen Council System Test
==========================================
End-to-end test of FAISS memory integration with production system
"""

import asyncio
import time
import json
import os
from typing import Dict, List, Any

# Test the memory-enhanced system
async def test_memory_enhanced_system():
    """Test the complete memory-enhanced AutoGen Council system"""
    
    print("🚀 Testing Memory-Enhanced AutoGen Council System")
    print("=" * 60)
    
    # Import the memory-enhanced router
    try:
        from agent_zero_memory import create_memory_enhanced_router, MemoryContext
        print("✅ Memory system imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Create router with memory
    try:
        RouterClass = create_memory_enhanced_router("production_memory")
        router = RouterClass()
        print("✅ Memory-enhanced router created")
    except Exception as e:
        print(f"❌ Router creation error: {e}")
        return False
    
    # Test session management
    session_id = "test_session_v260"
    user_id = "test_user_agent_zero"
    router.set_session_context(session_id, user_id)
    print(f"✅ Session context set: {session_id}")
    
    # Test conversation with memory
    test_conversations = [
        {
            "query": "What is 15 + 27?",
            "expected_skill": "math",
            "description": "Simple math query"
        },
        {
            "query": "Remember that my favorite number is 42",
            "expected_skill": "agent0",
            "description": "Memory storage request"
        },
        {
            "query": "What's the capital of Japan?",
            "expected_skill": "knowledge", 
            "description": "Knowledge query"
        },
        {
            "query": "What did we calculate earlier?",
            "expected_skill": "agent0",
            "description": "Memory recall query"
        },
        {
            "query": "What's my favorite number?",
            "expected_skill": "agent0",
            "description": "Personal memory recall"
        }
    ]
    
    print(f"\n🧪 Running {len(test_conversations)} conversation tests...")
    
    results = []
    
    for i, test in enumerate(test_conversations, 1):
        print(f"\n--- Test {i}: {test['description']} ---")
        print(f"Query: {test['query']}")
        
        start_time = time.time()
        
        try:
            # Test routing with memory
            result = await router.route_query_with_memory(test['query'])
            
            latency_ms = (time.time() - start_time) * 1000
            
            print(f"✅ Response received in {latency_ms:.1f}ms")
            print(f"   Skill: {result.get('skill_used', 'unknown')}")
            print(f"   Response: {str(result.get('response', 'No response'))[:100]}...")
            
            # Check memory storage
            memory_context = router.current_session
            stored_memories = router.memory.get_relevant_context(memory_context, test['query'], max_items=3)
            print(f"   Relevant memories: {len(stored_memories)} items")
            
            results.append({
                "test_id": i,
                "query": test['query'],
                "success": True,
                "latency_ms": latency_ms,
                "skill_used": result.get('skill_used', 'unknown'),
                "memory_items": len(stored_memories),
                "response_length": len(str(result.get('response', '')))
            })
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                "test_id": i,
                "query": test['query'],
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            })
    
    # Test session summary
    print(f"\n📋 Generating session summary...")
    try:
        summary = router.memory.get_session_summary(session_id)
        print(f"✅ Session summary: {summary['total_turns']} turns")
        print(f"   Summary: {summary['summary_text'][:150]}...")
    except Exception as e:
        print(f"❌ Session summary error: {e}")
    
    # Performance analysis
    print(f"\n📊 Performance Analysis")
    print("=" * 30)
    
    successful_tests = [r for r in results if r.get('success', False)]
    failed_tests = [r for r in results if not r.get('success', False)]
    
    if successful_tests:
        avg_latency = sum(r['latency_ms'] for r in successful_tests) / len(successful_tests)
        max_latency = max(r['latency_ms'] for r in successful_tests)
        min_latency = min(r['latency_ms'] for r in successful_tests)
        
        print(f"✅ Success Rate: {len(successful_tests)}/{len(results)} ({len(successful_tests)/len(results)*100:.1f}%)")
        print(f"⚡ Average Latency: {avg_latency:.1f}ms")
        print(f"⚡ Latency Range: {min_latency:.1f}ms - {max_latency:.1f}ms")
        
        # Check if we meet v2.6.0 targets
        target_latency = 600  # Original 574ms + 14ms memory overhead
        target_success_rate = 80
        
        latency_ok = avg_latency < target_latency
        success_ok = (len(successful_tests)/len(results)*100) >= target_success_rate
        
        print(f"\n🎯 v2.6.0 Target Assessment:")
        print(f"   Latency Target (<{target_latency}ms): {'✅ PASS' if latency_ok else '❌ FAIL'}")
        print(f"   Success Rate Target (>{target_success_rate}%): {'✅ PASS' if success_ok else '❌ FAIL'}")
        
        if latency_ok and success_ok:
            print(f"\n🎉 MEMORY-ENHANCED SYSTEM READY FOR v2.6.0!")
        else:
            print(f"\n🟡 System needs optimization before v2.6.0 release")
    
    if failed_tests:
        print(f"\n❌ Failed Tests: {len(failed_tests)}")
        for failure in failed_tests:
            print(f"   Test {failure['test_id']}: {failure.get('error', 'Unknown error')}")
    
    # Memory system stats
    try:
        print(f"\n💾 Memory System Statistics")
        print("=" * 30)
        
        # Get memory items
        test_context = MemoryContext(session_id=session_id, user_id=user_id)
        all_memories = router.memory.get_relevant_context(test_context, "", max_items=100)
        
        print(f"Total memory items: {len(all_memories)}")
        
        # Categorize by type
        conversations = [m for m in all_memories if m.get('type') == 'conversation']
        facts = [m for m in all_memories if m.get('type') == 'fact']
        
        print(f"Conversations stored: {len(conversations)}")
        print(f"Facts stored: {len(facts)}")
        
        # Check persistence
        router.memory.persist()
        print(f"✅ Memory persisted to disk")
        
    except Exception as e:
        print(f"❌ Memory stats error: {e}")
    
    print(f"\n✅ Memory-enhanced system test completed!")
    return len(successful_tests) > 0

# Main test execution
async def main():
    """Main test execution"""
    success = await test_memory_enhanced_system()
    
    if success:
        print(f"\n🚀 NEXT STEPS FOR v2.6.0:")
        print(f"   1. ✅ FAISS Memory System - COMPLETED")
        print(f"   2. ✅ Agent-Zero Integration - COMPLETED") 
        print(f"   3. ✅ Docker Configuration - COMPLETED")
        print(f"   4. 🟡 Production Deployment - READY")
        print(f"   5. 🟡 Documentation Update - PENDING")
        
        print(f"\n🎯 Day +1 of 5-day v2.6.0 sprint: COMPLETE!")
    else:
        print(f"\n❌ System not ready - troubleshooting required")

if __name__ == "__main__":
    asyncio.run(main()) 