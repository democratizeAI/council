#!/usr/bin/env python3
"""
Shared Scratchpad System for AutoGen Council
============================================

Provides persistent, searchable memory for multi-agent collaboration.
Agents can write notes, read context, and search similar entries.

Storage:
- Redis: Key-value storage for session data and notes
- Qdrant (optional): Vector embeddings for semantic search

Usage:
    from common.scratchpad import write, read, search_similar
    
    # Agent-0 writes plan
    write("session_123", "agent0", "Refactor utils.py into smaller functions", tags=["code", "planning"])
    
    # Council member reads context
    context = read("session_123")[-3:]  # Last 3 notes
    
    # Search for similar past decisions
    similar = search_similar("refactoring strategy", limit=5)
"""

import json
import time
import hashlib
import logging
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

# Redis for primary storage
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Qdrant for vector search (optional)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class ScratchpadEntry:
    """Single scratchpad entry"""
    id: str
    session_id: str
    agent: str
    content: str
    timestamp: float
    tags: List[str]
    entry_type: str = "note"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ScratchpadManager:
    """
    Shared scratchpad for multi-agent collaboration
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 qdrant_url: str = "http://localhost:6333",
                 session_ttl_hours: int = 24):
        self.redis_url = redis_url
        self.qdrant_url = qdrant_url
        self.session_ttl = timedelta(hours=session_ttl_hours)
        
        # Initialize Redis
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()  # Test connection
                logger.info(f"✅ Redis connected: {redis_url}")
            except Exception as e:
                logger.warning(f"❌ Redis connection failed: {e}")
                self.redis = None
        else:
            logger.warning("📦 Redis not available - using in-memory fallback")
            self.redis = None
            self._memory_store = {}  # In-memory fallback
        
        # Initialize Qdrant (optional)
        self.qdrant = None
        self.embedder = None
        if QDRANT_AVAILABLE:
            try:
                self.qdrant = QdrantClient(url=qdrant_url)
                # Test connection
                collections = self.qdrant.get_collections()
                
                # Create collection if not exists
                collection_name = "scratchpad_embeddings"
                try:
                    self.qdrant.get_collection(collection_name)
                except:
                    self.qdrant.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                
                # Initialize embedder
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info(f"✅ Qdrant connected: {qdrant_url}")
                
            except Exception as e:
                logger.warning(f"❌ Qdrant connection failed: {e} - semantic search disabled")
                self.qdrant = None
        else:
            logger.warning("📦 Qdrant not available - semantic search disabled")
    
    def write(self, session_id: str, agent: str, content: str, 
              tags: List[str] = None, entry_type: str = "note", 
              metadata: Dict[str, Any] = None) -> str:
        """
        Write an entry to the scratchpad
        
        Args:
            session_id: Session identifier
            agent: Agent name (e.g., "agent0", "reason", "spark")
            content: Entry content
            tags: Optional tags for categorization
            entry_type: Type of entry ("note", "plan", "decision", "risk")
            metadata: Additional metadata
            
        Returns:
            Entry ID
        """
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
        
        # Generate unique ID
        entry_id = hashlib.md5(f"{session_id}_{agent}_{time.time()}".encode()).hexdigest()[:12]
        
        entry = ScratchpadEntry(
            id=entry_id,
            session_id=session_id,
            agent=agent,
            content=content,
            timestamp=time.time(),
            tags=tags,
            entry_type=entry_type,
            metadata=metadata
        )
        
        # Store in Redis
        if self.redis:
            try:
                # Add to session list
                session_key = f"scratch:session:{session_id}"
                self.redis.lpush(session_key, entry_id)
                self.redis.expire(session_key, int(self.session_ttl.total_seconds()))
                
                # Store entry data
                entry_key = f"scratch:entry:{entry_id}"
                self.redis.hset(entry_key, mapping=asdict(entry))
                self.redis.expire(entry_key, int(self.session_ttl.total_seconds()))
                
                # Add to agent index
                agent_key = f"scratch:agent:{agent}"
                self.redis.lpush(agent_key, entry_id)
                self.redis.expire(agent_key, int(self.session_ttl.total_seconds()))
                
            except Exception as e:
                logger.error(f"Failed to write to Redis: {e}")
        else:
            # In-memory fallback
            if session_id not in self._memory_store:
                self._memory_store[session_id] = []
            self._memory_store[session_id].append(entry)
        
        # Store embeddings in Qdrant for semantic search
        if self.qdrant and self.embedder:
            try:
                embedding = self.embedder.encode(content).tolist()
                
                point = PointStruct(
                    id=entry_id,
                    vector=embedding,
                    payload={
                        "session_id": session_id,
                        "agent": agent,
                        "content": content,
                        "tags": tags,
                        "entry_type": entry_type,
                        "timestamp": entry.timestamp
                    }
                )
                
                self.qdrant.upsert(
                    collection_name="scratchpad_embeddings",
                    points=[point]
                )
                
            except Exception as e:
                logger.warning(f"Failed to store embedding: {e}")
        
        logger.debug(f"📝 Scratchpad write: {agent} → {content[:50]}...")
        return entry_id
    
    def read(self, session_id: str, limit: int = 10) -> List[ScratchpadEntry]:
        """
        Read entries from a session
        
        Args:
            session_id: Session to read from
            limit: Maximum entries to return (most recent first)
            
        Returns:
            List of scratchpad entries
        """
        entries = []
        
        if self.redis:
            try:
                session_key = f"scratch:session:{session_id}"
                entry_ids = self.redis.lrange(session_key, 0, limit - 1)
                
                for entry_id in entry_ids:
                    entry_key = f"scratch:entry:{entry_id}"
                    entry_data = self.redis.hgetall(entry_key)
                    
                    if entry_data:
                        # Convert Redis data back to ScratchpadEntry
                        entry_data['timestamp'] = float(entry_data['timestamp'])
                        entry_data['tags'] = json.loads(entry_data.get('tags', '[]'))
                        entry_data['metadata'] = json.loads(entry_data.get('metadata', '{}'))
                        
                        entries.append(ScratchpadEntry(**entry_data))
                        
            except Exception as e:
                logger.error(f"Failed to read from Redis: {e}")
        else:
            # In-memory fallback
            if session_id in self._memory_store:
                entries = self._memory_store[session_id][-limit:]
                entries.reverse()  # Most recent first
        
        logger.debug(f"📖 Scratchpad read: {session_id} → {len(entries)} entries")
        return entries
    
    def search_similar(self, query: str, limit: int = 5, 
                      session_id: Optional[str] = None) -> List[ScratchpadEntry]:
        """
        Search for semantically similar entries
        
        Args:
            query: Search query
            limit: Maximum results to return
            session_id: Optional session filter
            
        Returns:
            List of similar entries with scores
        """
        if not (self.qdrant and self.embedder):
            logger.warning("Semantic search not available - returning empty results")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()
            
            # Build search filter
            search_filter = {}
            if session_id:
                search_filter["session_id"] = session_id
            
            # Search Qdrant
            results = self.qdrant.search(
                collection_name="scratchpad_embeddings",
                query_vector=query_embedding,
                limit=limit,
                query_filter=search_filter if search_filter else None
            )
            
            # Convert to ScratchpadEntry objects
            entries = []
            for result in results:
                payload = result.payload
                entry = ScratchpadEntry(
                    id=str(result.id),
                    session_id=payload["session_id"],
                    agent=payload["agent"],
                    content=payload["content"],
                    timestamp=payload["timestamp"],
                    tags=payload["tags"],
                    entry_type=payload["entry_type"],
                    metadata={"similarity_score": result.score}
                )
                entries.append(entry)
            
            logger.debug(f"🔍 Scratchpad search: '{query}' → {len(entries)} results")
            return entries
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for a session"""
        entries = self.read(session_id, limit=100)  # Read more for stats
        
        if not entries:
            return {"total_entries": 0, "agents": [], "tags": [], "latest_activity": None}
        
        agents = list(set(entry.agent for entry in entries))
        all_tags = []
        for entry in entries:
            all_tags.extend(entry.tags)
        unique_tags = list(set(all_tags))
        
        return {
            "total_entries": len(entries),
            "agents": agents,
            "tags": unique_tags,
            "latest_activity": entries[0].timestamp if entries else None,
            "session_id": session_id
        }

# Global scratchpad instance
_scratchpad_manager = None

def get_scratchpad() -> ScratchpadManager:
    """Get or create global scratchpad manager"""
    global _scratchpad_manager
    if _scratchpad_manager is None:
        _scratchpad_manager = ScratchpadManager()
    return _scratchpad_manager

# Convenience functions for direct usage
def write(session_id: str, agent: str, content: str, 
          tags: List[str] = None, entry_type: str = "note", 
          metadata: Dict[str, Any] = None) -> str:
    """Write to scratchpad"""
    return get_scratchpad().write(session_id, agent, content, tags, entry_type, metadata)

def read(session_id: str, limit: int = 10) -> List[ScratchpadEntry]:
    """Read from scratchpad"""
    return get_scratchpad().read(session_id, limit)

def search_similar(query: str, limit: int = 5, 
                  session_id: Optional[str] = None) -> List[ScratchpadEntry]:
    """Search scratchpad"""
    return get_scratchpad().search_similar(query, limit, session_id)

# 🚀 SINGLE-PATH RECIPE: Digest functions for cascading knowledge
def summarize_to_digest(text: str, max_tokens: int = 40) -> str:
    """
    Summarize text to a short digest for cascading knowledge (Recipe Step 3)
    
    Args:
        text: Text to summarize
        max_tokens: Maximum tokens in digest
        
    Returns:
        Short digest string
    """
    # Simple truncation-based summarization for now
    # In production, this could use a summarization model
    words = text.split()
    if len(words) <= max_tokens:
        return text
    
    # Take first part and add summary marker
    digest = " ".join(words[:max_tokens-2]) + "..."
    return digest

def write_fusion_digest(session_id: str, digest_type: str, content: str) -> str:
    """
    Write a digest to scratchpad for cascading knowledge (Recipe Step 3)
    
    Args:
        session_id: Session ID
        digest_type: Type of digest (e.g. "agent0_draft", "specialist_fusion")
        content: Digest content
        
    Returns:
        Entry ID
    """
    return write(
        session_id=session_id,
        agent="digest_system",
        content=content,
        tags=["digest", digest_type],
        entry_type="digest"
    )

def read_conversation_context(session_id: str, k: int = 3) -> List[Dict[str, str]]:
    """
    Read last k digests for cascading knowledge (Recipe Step 3)
    
    Args:
        session_id: Session ID
        k: Number of recent digests to read
        
    Returns:
        List of digest dictionaries with 'content' key
    """
    entries = read(session_id, limit=k*2)  # Read more to filter digests
    
    # Filter to digest entries only
    digest_entries = [e for e in entries if e.entry_type == "digest"][:k]
    
    # Return in format expected by router
    return [{"content": entry.content} for entry in digest_entries] 