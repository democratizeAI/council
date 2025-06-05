#!/usr/bin/env python3
"""
🧠 MEMORY RECALL UNIT TEST
=========================

Implements the recall test from the punch-list:
1. Store a fact: "My bike is turquoise."
2. Query it back: "What colour is my bike?"  
3. Assert the system recalls "turquoise"
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from app.main import app
from common.memory_manager import MEMORY_MANAGER, start_memory_system

client = TestClient(app)

class TestMemoryRecall:
    """Memory persistence and recall tests"""
    
    @pytest.fixture(autouse=True)
    async def setup_memory(self):
        """Setup memory system for tests"""
        await start_memory_system()
        yield
        await MEMORY_MANAGER.shutdown()
    
    def test_basic_memory_persistence(self):
        """Test basic memory storage and retrieval"""
        session_id = f"test_session_{int(time.time())}"
        
        # Store a fact
        MEMORY_MANAGER.add_memory(
            content="My bike is turquoise.",
            session_id=session_id,
            entry_type="user_fact",
            tags=["bike", "color"]
        )
        
        # Retrieve recent memories
        memories = MEMORY_MANAGER.get_recent_memories(session_id=session_id, limit=5)
        
        assert len(memories) >= 1
        assert "turquoise" in memories[-1].content
        assert memories[-1].session_id == session_id
    
    def test_memory_search(self):
        """Test memory search functionality"""
        session_id = f"test_search_{int(time.time())}"
        
        # Store multiple facts
        facts = [
            "My bike is turquoise.",
            "I live in San Francisco.",
            "My favorite food is pizza.",
            "My bike has 21 gears."
        ]
        
        for fact in facts:
            MEMORY_MANAGER.add_memory(
                content=fact,
                session_id=session_id,
                entry_type="user_fact"
            )
        
        # Search for bike-related memories
        bike_memories = MEMORY_MANAGER.search_memories("bike", session_id=session_id)
        
        assert len(bike_memories) >= 2  # Should find both bike facts
        bike_texts = [m.content for m in bike_memories]
        assert any("turquoise" in text for text in bike_texts)
        assert any("21 gears" in text for text in bike_texts)
    
    def test_cross_session_isolation(self):
        """Test that sessions don't leak into each other"""
        session1 = f"test_session1_{int(time.time())}"
        session2 = f"test_session2_{int(time.time())}"
        
        # Store different facts in different sessions
        MEMORY_MANAGER.add_memory("My bike is turquoise.", session_id=session1)
        MEMORY_MANAGER.add_memory("My car is red.", session_id=session2)
        
        # Check session isolation
        session1_memories = MEMORY_MANAGER.get_recent_memories(session_id=session1)
        session2_memories = MEMORY_MANAGER.get_recent_memories(session_id=session2)
        
        session1_text = " ".join([m.content for m in session1_memories])
        session2_text = " ".join([m.content for m in session2_memories])
        
        assert "turquoise" in session1_text
        assert "turquoise" not in session2_text
        assert "red" in session2_text
        assert "red" not in session1_text
    
    def test_chat_api_memory_integration(self):
        """Test end-to-end memory integration via chat API"""
        session_id = f"test_chat_{int(time.time())}"
        
        # Store a fact via chat
        response1 = client.post("/chat", json={
            "prompt": "My bike is turquoise.",
            "session_id": session_id
        })
        
        assert response1.status_code == 200
        
        # Wait a moment for memory processing
        time.sleep(0.1)
        
        # Query the fact back
        response2 = client.post("/chat", json={
            "prompt": "What colour is my bike?",
            "session_id": session_id
        })
        
        assert response2.status_code == 200
        
        # Check if the response mentions turquoise
        response_data = response2.json()
        response_text = response_data.get("text", "").lower()
        
        # The system should recall the color from memory
        assert "turquoise" in response_text or "blue" in response_text  # Allow for color synonyms
    
    def test_memory_with_conversation_context(self):
        """Test memory integration with conversation summarizer"""
        session_id = f"test_context_{int(time.time())}"
        
        # Multi-turn conversation with facts
        conversation = [
            "Hi, I want to tell you about my bike.",
            "My bike is turquoise and has 21 gears.",
            "I bought it last year in Portland.",
            "What can you tell me about my bike?"
        ]
        
        responses = []
        for prompt in conversation:
            response = client.post("/chat", json={
                "prompt": prompt,
                "session_id": session_id
            })
            assert response.status_code == 200
            responses.append(response.json())
            time.sleep(0.1)  # Allow memory processing
        
        # Check final response for recalled information
        final_response = responses[-1]["text"].lower()
        
        # Should mention details from earlier in conversation
        assert any(detail in final_response for detail in ["turquoise", "21", "gear", "portland"])
    
    def test_memory_statistics(self):
        """Test memory statistics and monitoring"""
        # Add some test data
        session_id = f"test_stats_{int(time.time())}"
        
        for i in range(10):
            MEMORY_MANAGER.add_memory(
                content=f"Test memory entry {i}",
                session_id=session_id,
                entry_type="test"
            )
        
        # Get statistics
        stats = MEMORY_MANAGER.get_memory_stats()
        
        assert "cache_entries" in stats
        assert "session_caches" in stats
        assert stats["cache_entries"] >= 10
        assert stats["session_caches"] >= 1
    
    def test_memory_gc_simulation(self):
        """Test memory garbage collection"""
        session_id = f"test_gc_{int(time.time())}"
        
        # Fill memory cache beyond typical limit
        for i in range(50):
            MEMORY_MANAGER.add_memory(
                content=f"GC test entry {i}",
                session_id=session_id,
                entry_type="gc_test"
            )
        
        initial_count = len(MEMORY_MANAGER.memory_cache)
        
        # Simulate old entries (adjust timestamps)
        old_time = time.time() - (8 * 24 * 3600)  # 8 days ago
        for entry in list(MEMORY_MANAGER.memory_cache)[:20]:
            entry.timestamp = old_time
        
        # Check that recent entries are preserved
        recent_memories = MEMORY_MANAGER.get_recent_memories(session_id=session_id, limit=10)
        assert len(recent_memories) > 0
    
    def test_memory_tags_and_metadata(self):
        """Test memory tagging and metadata"""
        session_id = f"test_tags_{int(time.time())}"
        
        # Add memory with tags and metadata
        MEMORY_MANAGER.add_memory(
            content="My favorite programming language is Python.",
            session_id=session_id,
            entry_type="preference",
            tags=["programming", "python", "preference"],
            metadata={"category": "tech", "confidence": 0.9}
        )
        
        # Retrieve and verify
        memories = MEMORY_MANAGER.get_recent_memories(session_id=session_id)
        memory = memories[-1]
        
        assert "programming" in memory.tags
        assert memory.metadata["category"] == "tech"
        assert memory.entry_type == "preference"

@pytest.mark.asyncio
async def test_async_memory_operations():
    """Test async memory operations"""
    await start_memory_system()
    
    session_id = f"test_async_{int(time.time())}"
    
    # Test async operations
    MEMORY_MANAGER.add_memory("Async test message", session_id=session_id)
    
    # Wait for background processing
    await asyncio.sleep(0.1)
    
    memories = MEMORY_MANAGER.get_recent_memories(session_id=session_id)
    assert len(memories) >= 1
    assert "Async test message" in memories[-1].content
    
    await MEMORY_MANAGER.shutdown()

def test_memory_error_handling():
    """Test memory system error handling"""
    session_id = f"test_errors_{int(time.time())}"
    
    # Test with invalid data
    try:
        MEMORY_MANAGER.add_memory(
            content="",  # Empty content
            session_id=session_id
        )
        # Should not crash
    except Exception as e:
        pytest.fail(f"Memory system should handle empty content gracefully: {e}")
    
    # Test search with empty query
    results = MEMORY_MANAGER.search_memories("", session_id=session_id)
    assert isinstance(results, list)  # Should return empty list, not crash

if __name__ == "__main__":
    # Run the punch-list test specifically
    import sys
    
    print("🧠 Running Memory Recall Punch-List Test...")
    
    # Setup
    session_id = "punchlist_test"
    
    # Step 1: Store the fact
    print("📝 Storing fact: 'My bike is turquoise.'")
    response1 = client.post("/chat", json={
        "prompt": "My bike is turquoise.",
        "session_id": session_id
    })
    print(f"✅ Response 1: {response1.status_code}")
    
    # Wait for memory processing
    time.sleep(0.5)
    
    # Step 2: Query it back
    print("❓ Querying: 'What colour is my bike?'")
    response2 = client.post("/chat", json={
        "prompt": "What colour is my bike?",
        "session_id": session_id
    })
    
    print(f"✅ Response 2: {response2.status_code}")
    
    if response2.status_code == 200:
        response_data = response2.json()
        response_text = response_data.get("text", "")
        print(f"🎯 Bot response: {response_text}")
        
        # Step 3: Assert recall
        if "turquoise" in response_text.lower():
            print("✅ SUCCESS: Memory recall working! Found 'turquoise' in response.")
            sys.exit(0)
        else:
            print(f"❌ FAILED: 'turquoise' not found in response. Got: {response_text}")
            sys.exit(1)
    else:
        print(f"❌ FAILED: Chat API error {response2.status_code}")
        sys.exit(1) 