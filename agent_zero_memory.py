#!/usr/bin/env python3
"""
Agent-Zero Memory Adapter for AutoGen Council
=============================================
Bridges FAISS memory system into Agent-Zero compatible interface
Integrates with RouterCascade for session persistence
"""

from __future__ import annotations
import os
import time
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from faiss_memory import FaissMemory
from prometheus_client import Counter, Histogram

# Prometheus metrics for Agent-Zero integration
AGENT_MEMORY_OPS = Counter("autogen_agent_memory_operations_total", 
                          "Agent memory operations", ["operation", "session"])
AGENT_MEMORY_LATENCY = Histogram("autogen_agent_memory_latency_seconds",
                                "Agent memory operation latency", ["operation"])

logger = logging.getLogger(__name__)

@dataclass
class MemoryContext:
    """Memory context for Agent-Zero conversations"""
    session_id: str
    user_id: str = "default"
    conversation_turn: int = 0
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class AgentZeroMemory:
    """
    Agent-Zero compatible memory interface using FAISS backend
    
    Provides:
    - Session-based conversation memory
    - Semantic search across history
    - Context-aware response generation
    - Integration with RouterCascade system
    """
    
    def __init__(self, memory_path: str = "agent_memory", max_context_items: int = 10):
        self.memory_path = memory_path
        self.max_context_items = max_context_items
        self.faiss_memory = FaissMemory(db_path=memory_path)
        
        logger.info(f"🧠 AgentZeroMemory initialized: {memory_path}")
    
    @AGENT_MEMORY_LATENCY.labels("add_conversation").time()
    def add_conversation_turn(self, 
                            context: MemoryContext,
                            user_query: str,
                            agent_response: str,
                            metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a conversation turn to memory
        
        Args:
            context: Memory context with session info
            user_query: User's input query
            agent_response: Agent's response
            metadata: Additional metadata (confidence, skill used, etc.)
        
        Returns:
            Memory item UID
        """
        metadata = metadata or {}
        
        # Create conversation memory entry
        memory_text = f"User: {user_query}\nAgent: {agent_response}"
        
        memory_meta = {
            **asdict(context),
            **metadata,
            "type": "conversation",
            "user_query": user_query,
            "agent_response": agent_response,
            "stored_at": time.time()
        }
        
        uid = self.faiss_memory.add(memory_text, memory_meta)
        
        AGENT_MEMORY_OPS.labels(operation="add", session=context.session_id).inc()
        
        logger.debug(f"💾 Added conversation turn: {uid[:8]}... (session: {context.session_id})")
        return uid
    
    @AGENT_MEMORY_LATENCY.labels("add_fact").time()
    def add_learned_fact(self,
                        context: MemoryContext,
                        fact: str,
                        confidence: float = 0.8,
                        source: str = "conversation") -> str:
        """
        Add a learned fact to memory
        
        Args:
            context: Memory context
            fact: The learned fact
            confidence: Confidence in the fact (0.0-1.0)
            source: Source of the fact
        
        Returns:
            Memory item UID
        """
        memory_meta = {
            **asdict(context),
            "type": "fact",
            "confidence": confidence,
            "source": source,
            "stored_at": time.time()
        }
        
        uid = self.faiss_memory.add(fact, memory_meta)
        
        AGENT_MEMORY_OPS.labels(operation="add_fact", session=context.session_id).inc()
        
        logger.debug(f"📚 Added learned fact: {uid[:8]}... (confidence: {confidence})")
        return uid
    
    @AGENT_MEMORY_LATENCY.labels("query").time()
    def get_relevant_context(self,
                           context: MemoryContext,
                           current_query: str,
                           max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get relevant conversation context for current query
        
        Args:
            context: Current memory context
            current_query: User's current query
            max_items: Maximum items to return (default: self.max_context_items)
        
        Returns:
            List of relevant memory items with scores
        """
        max_items = max_items or self.max_context_items
        
        # Search for semantically similar conversations and facts
        results = self.faiss_memory.query(current_query, k=max_items * 2, thresh=0.3)
        
        # Filter and sort by relevance
        relevant_items = []
        
        for item in results:
            # Prioritize items from same session
            session_bonus = 0.1 if item.get("session_id") == context.session_id else 0.0
            
            # Prioritize recent items
            age_hours = (time.time() - item.get("stored_at", 0)) / 3600
            recency_bonus = max(0, 0.05 * (1 - age_hours / 168))  # Decay over week
            
            # Adjust score with bonuses
            adjusted_score = item["score"] + session_bonus + recency_bonus
            item["adjusted_score"] = adjusted_score
            
            relevant_items.append(item)
        
        # Sort by adjusted score and limit
        relevant_items.sort(key=lambda x: x["adjusted_score"], reverse=True)
        relevant_items = relevant_items[:max_items]
        
        AGENT_MEMORY_OPS.labels(operation="query", session=context.session_id).inc()
        
        logger.debug(f"🔍 Found {len(relevant_items)} relevant memories for query")
        return relevant_items
    
    @AGENT_MEMORY_LATENCY.labels("session_summary").time()
    def get_session_summary(self, session_id: str, max_turns: int = 10) -> Dict[str, Any]:
        """
        Get summary of conversation session
        
        Args:
            session_id: Session identifier
            max_turns: Maximum conversation turns to include
        
        Returns:
            Session summary with key topics and recent history
        """
        # Search for all items in this session
        results = self.faiss_memory.query("", k=1000, thresh=0.0)  # Get all items
        
        session_items = [
            item for item in results 
            if item.get("session_id") == session_id and item.get("type") == "conversation"
        ]
        
        # Sort by conversation turn
        session_items.sort(key=lambda x: x.get("conversation_turn", 0))
        
        # Get recent turns
        recent_turns = session_items[-max_turns:] if session_items else []
        
        # Extract key topics (simple keyword extraction)
        all_text = " ".join([item["text"] for item in session_items])
        
        summary = {
            "session_id": session_id,
            "total_turns": len(session_items),
            "recent_turns": recent_turns,
            "summary_text": all_text[:500] + "..." if len(all_text) > 500 else all_text,
            "generated_at": time.time()
        }
        
        AGENT_MEMORY_OPS.labels(operation="session_summary", session=session_id).inc()
        
        logger.debug(f"📋 Generated session summary: {len(session_items)} turns")
        return summary
    
    def format_context_for_prompt(self, context_items: List[Dict[str, Any]]) -> str:
        """
        Format memory context items for inclusion in LLM prompt
        
        Args:
            context_items: List of relevant memory items
        
        Returns:
            Formatted context string for prompt
        """
        if not context_items:
            return ""
        
        context_lines = ["# Relevant Conversation History:"]
        
        for i, item in enumerate(context_items, 1):
            item_type = item.get("type", "unknown")
            score = item.get("adjusted_score", item.get("score", 0))
            
            if item_type == "conversation":
                # Extract user query and agent response
                user_query = item.get("user_query", "")
                agent_response = item.get("agent_response", "")
                context_lines.append(f"{i}. (Score: {score:.2f}) User: {user_query}")
                context_lines.append(f"   Agent: {agent_response}")
            elif item_type == "fact":
                confidence = item.get("confidence", 0)
                context_lines.append(f"{i}. (Score: {score:.2f}, Confidence: {confidence:.2f}) {item['text']}")
            else:
                context_lines.append(f"{i}. (Score: {score:.2f}) {item['text']}")
        
        return "\n".join(context_lines) + "\n"
    
    def persist(self):
        """Force persistence of memory to disk"""
        self.faiss_memory.flush()
        logger.debug("💾 Memory persisted to disk")

# ------------------------------------------------------------------
# Agent-Zero Integration Helper
def create_memory_enhanced_router(memory_path: str = "agent_memory"):
    """
    Factory function to create memory-enhanced RouterCascade
    """
    from router_cascade import RouterCascade
    
    class MemoryEnhancedRouter(RouterCascade):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.memory = AgentZeroMemory(memory_path=memory_path)
            self.current_session = None
        
        def set_session_context(self, session_id: str, user_id: str = "default"):
            """Set current session context"""
            self.current_session = MemoryContext(
                session_id=session_id,
                user_id=user_id,
                conversation_turn=0
            )
            logger.info(f"🎯 Set session context: {session_id}")
        
        async def route_query_with_memory(self, query: str, **kwargs) -> Dict[str, Any]:
            """Route query with memory context"""
            if not self.current_session:
                self.current_session = MemoryContext(session_id="default")
            
            # Get relevant context
            context_items = self.memory.get_relevant_context(self.current_session, query)
            
            # Format context for prompt
            context_prompt = self.memory.format_context_for_prompt(context_items)
            
            # Enhance query with context
            enhanced_query = f"{context_prompt}\n# Current Query:\n{query}" if context_prompt else query
            
            # Route the enhanced query
            result = await self.route_query(enhanced_query, **kwargs)
            
            # Store conversation turn in memory
            if result.get("response"):
                metadata = {
                    "skill_used": result.get("skill_used", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "processing_time_ms": result.get("processing_time_ms", 0)
                }
                
                self.memory.add_conversation_turn(
                    self.current_session,
                    query,
                    result["response"],
                    metadata
                )
                
                # Increment conversation turn
                self.current_session.conversation_turn += 1
            
            return result
    
    return MemoryEnhancedRouter

# ------------------------------------------------------------------
# Quick integration test
if __name__ == "__main__":
    import asyncio
    
    async def test_memory_integration():
        print("🧪 Testing Agent-Zero Memory Integration...")
        
        # Create memory-enhanced router
        RouterClass = create_memory_enhanced_router("test_agent_memory")
        router = RouterClass()
        
        # Set session context
        router.set_session_context("test_session_123", "test_user")
        
        # Test queries with memory
        queries = [
            "What is 2 + 2?",
            "Tell me about Python programming",
            "What did we discuss about math earlier?"
        ]
        
        for query in queries:
            print(f"\n🤖 Query: {query}")
            try:
                result = await router.route_query_with_memory(query)
                print(f"   Response: {result.get('response', 'No response')[:100]}...")
                print(f"   Skill: {result.get('skill_used', 'unknown')}")
            except Exception as e:
                print(f"   Error: {e}")
        
        # Test session summary
        summary = router.memory.get_session_summary("test_session_123")
        print(f"\n📋 Session Summary: {summary['total_turns']} turns")
        
        print("\n✅ Memory integration test completed!")
    
    asyncio.run(test_memory_integration()) 