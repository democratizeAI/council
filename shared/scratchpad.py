#!/usr/bin/env python3
"""
Shared Scratchpad System
========================

Shared memory system for agent collaboration using Redis + Qdrant.
Agents can write findings and read context from other agents.

Usage:
- write(session_id, agent_name, content, tags=[], typ="note")
- read(session_id, limit=10, agent_filter=None)
"""

import time
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class ScratchpadEntry:
    """Single scratchpad entry"""
    session_id: str
    agent: str
    content: str
    timestamp: float
    tags: List[str]
    entry_type: str  # "note", "finding", "digest", "search_result"
    metadata: Dict[str, Any]

# Try to import Redis and Qdrant
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
    
    # Prometheus metrics
    scratchpad_entries_total = Counter(
        'scratchpad_entries_total',
        'Total number of scratchpad entries written',
        ['session_id', 'agent', 'entry_type']
    )
    
    scratchpad_active_sessions = Gauge(
        'scratchpad_active_sessions',
        'Number of active scratchpad sessions'
    )
    
    scratchpad_write_duration = Histogram(
        'scratchpad_write_duration_seconds',
        'Time taken to write scratchpad entries',
        ['backend']
    )
    
    scratchpad_read_duration = Histogram(
        'scratchpad_read_duration_seconds', 
        'Time taken to read scratchpad entries',
        ['backend']
    )
    
except ImportError:
    PROMETHEUS_AVAILABLE = False

class ScratchpadSystem:
    """Shared scratchpad with Redis + Qdrant backend"""
    
    def __init__(self):
        self.redis_client = None
        self.qdrant_client = None
        self.memory_fallback = {}  # In-memory fallback
        self._setup_backends()
    
    def _setup_backends(self):
        """Initialize Redis and Qdrant connections"""
        
        # Redis setup
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host='localhost', 
                    port=6379, 
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
                # Test connection
                self.redis_client.ping()
                logger.info("📊 Redis scratchpad connected")
            except Exception as e:
                logger.warning(f"📊 Redis unavailable: {e} - using memory fallback")
                self.redis_client = None
        else:
            logger.warning("📊 Redis not installed - using memory fallback")
        
        # Qdrant setup
        if QDRANT_AVAILABLE:
            try:
                self.qdrant_client = QdrantClient(host="localhost", port=6333)
                
                # Create collection if it doesn't exist
                collections = self.qdrant_client.get_collections().collections
                collection_names = [c.name for c in collections]
                
                if "scratchpad" not in collection_names:
                    self.qdrant_client.create_collection(
                        collection_name="scratchpad",
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                    )
                    logger.info("🔍 Created Qdrant scratchpad collection")
                else:
                    logger.info("🔍 Qdrant scratchpad collection exists")
                    
            except Exception as e:
                logger.warning(f"🔍 Qdrant unavailable: {e} - semantic search disabled")
                self.qdrant_client = None
        else:
            logger.warning("🔍 Qdrant not installed - semantic search disabled")
    
    def write(self, session_id: str, agent: str, content: str, 
              tags: List[str] = None, entry_type: str = "note", 
              metadata: Dict[str, Any] = None) -> str:
        """Write entry to scratchpad"""
        
        write_start = time.time()
        
        if tags is None:
            tags = []
        if metadata is None:
            metadata = {}
            
        entry = ScratchpadEntry(
            session_id=session_id,
            agent=agent,
            content=content,
            timestamp=time.time(),
            tags=tags,
            entry_type=entry_type,
            metadata=metadata
        )
        
        # Generate unique ID
        entry_id = f"{session_id}:{agent}:{int(entry.timestamp * 1000)}"
        
        # Store in Redis
        if self.redis_client:
            try:
                key = f"scratchpad:{session_id}:{entry_id}"
                self.redis_client.set(key, json.dumps(asdict(entry)), ex=3600)  # 1 hour TTL
                
                # Add to session index
                index_key = f"scratchpad_index:{session_id}"
                self.redis_client.zadd(index_key, {entry_id: entry.timestamp})
                self.redis_client.expire(index_key, 3600)
                
                logger.debug(f"📝 Wrote to Redis: {agent} → {content[:50]}...")
            except Exception as e:
                logger.error(f"❌ Redis write failed: {e}")
        else:
            # Memory fallback
            if session_id not in self.memory_fallback:
                self.memory_fallback[session_id] = []
            self.memory_fallback[session_id].append(asdict(entry))
            
            # Keep only last 100 entries per session
            if len(self.memory_fallback[session_id]) > 100:
                self.memory_fallback[session_id] = self.memory_fallback[session_id][-100:]
        
        # Store in Qdrant for semantic search
        if self.qdrant_client:
            try:
                # Simple embedding: use content length and word count for now
                # In production, you'd use sentence-transformers here
                embedding = self._simple_embedding(content)
                
                point = PointStruct(
                    id=hash(entry_id) % (2**63),  # Convert to valid int64
                    vector=embedding,
                    payload={
                        "session_id": session_id,
                        "agent": agent,
                        "content": content,
                        "timestamp": entry.timestamp,
                        "tags": tags,
                        "entry_type": entry_type,
                        "entry_id": entry_id
                    }
                )
                
                self.qdrant_client.upsert(
                    collection_name="scratchpad",
                    points=[point]
                )
                
                logger.debug(f"🔍 Indexed in Qdrant: {agent} → {content[:50]}...")
            except Exception as e:
                logger.error(f"❌ Qdrant write failed: {e}")
        
        # Update Prometheus metrics
        if PROMETHEUS_AVAILABLE:
            scratchpad_entries_total.labels(
                session_id=session_id[:10],  # Truncate for cardinality
                agent=agent,
                entry_type=entry_type
            ).inc()
            
            backend = "redis" if self.redis_client else "memory"
            scratchpad_write_duration.labels(backend=backend).observe(time.time() - write_start)
            
            # Update active sessions count
            if self.redis_client:
                try:
                    session_count = len(self.redis_client.keys("scratchpad_index:*"))
                    scratchpad_active_sessions.set(session_count)
                except:
                    pass
            else:
                scratchpad_active_sessions.set(len(self.memory_fallback))
        
        return entry_id
    
    def read(self, session_id: str, limit: int = 10, 
             agent_filter: str = None, entry_type_filter: str = None) -> List[ScratchpadEntry]:
        """Read entries from scratchpad"""
        
        entries = []
        
        if self.redis_client:
            try:
                # Get entries from Redis index
                index_key = f"scratchpad_index:{session_id}"
                entry_ids = self.redis_client.zrevrange(index_key, 0, limit - 1)
                
                for entry_id in entry_ids:
                    key = f"scratchpad:{session_id}:{entry_id}"
                    data = self.redis_client.get(key)
                    if data:
                        entry_dict = json.loads(data)
                        entry = ScratchpadEntry(**entry_dict)
                        
                        # Apply filters
                        if agent_filter and entry.agent != agent_filter:
                            continue
                        if entry_type_filter and entry.entry_type != entry_type_filter:
                            continue
                            
                        entries.append(entry)
                        
                logger.debug(f"📖 Read {len(entries)} entries from Redis")
            except Exception as e:
                logger.error(f"❌ Redis read failed: {e}")
        else:
            # Memory fallback
            if session_id in self.memory_fallback:
                all_entries = [ScratchpadEntry(**e) for e in self.memory_fallback[session_id]]
                
                # Apply filters
                filtered_entries = all_entries
                if agent_filter:
                    filtered_entries = [e for e in filtered_entries if e.agent == agent_filter]
                if entry_type_filter:
                    filtered_entries = [e for e in filtered_entries if e.entry_type == entry_type_filter]
                
                # Sort by timestamp (newest first) and limit
                filtered_entries.sort(key=lambda x: x.timestamp, reverse=True)
                entries = filtered_entries[:limit]
        
        return entries
    
    def search(self, session_id: str, query: str, limit: int = 5) -> List[ScratchpadEntry]:
        """Semantic search in scratchpad"""
        
        if not self.qdrant_client:
            logger.warning("🔍 Qdrant not available - falling back to keyword search")
            return self._keyword_search(session_id, query, limit)
        
        try:
            # Simple embedding for query
            query_embedding = self._simple_embedding(query)
            
            # Search in Qdrant
            results = self.qdrant_client.search(
                collection_name="scratchpad",
                query_vector=query_embedding,
                query_filter={
                    "must": [
                        {"key": "session_id", "match": {"value": session_id}}
                    ]
                },
                limit=limit
            )
            
            entries = []
            for result in results:
                payload = result.payload
                entry = ScratchpadEntry(
                    session_id=payload["session_id"],
                    agent=payload["agent"],
                    content=payload["content"],
                    timestamp=payload["timestamp"],
                    tags=payload["tags"],
                    entry_type=payload["entry_type"],
                    metadata={"similarity_score": result.score}
                )
                entries.append(entry)
            
            logger.debug(f"🔍 Found {len(entries)} semantic matches")
            return entries
            
        except Exception as e:
            logger.error(f"❌ Qdrant search failed: {e}")
            return self._keyword_search(session_id, query, limit)
    
    def _keyword_search(self, session_id: str, query: str, limit: int) -> List[ScratchpadEntry]:
        """Fallback keyword search"""
        entries = self.read(session_id, limit=100)  # Get more entries for search
        
        query_words = query.lower().split()
        matches = []
        
        for entry in entries:
            content_lower = entry.content.lower()
            score = sum(1 for word in query_words if word in content_lower)
            if score > 0:
                entry.metadata["similarity_score"] = score / len(query_words)
                matches.append(entry)
        
        # Sort by score and return top results
        matches.sort(key=lambda x: x.metadata.get("similarity_score", 0), reverse=True)
        return matches[:limit]
    
    def _simple_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Simple embedding for text (placeholder for real embeddings)"""
        # This is a very basic embedding - in production use sentence-transformers
        import hashlib
        import struct
        
        # Create deterministic hash-based embedding
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to float vector
        embedding = []
        for i in range(0, min(len(hash_bytes), dim * 4), 4):
            chunk = hash_bytes[i:i+4]
            if len(chunk) == 4:
                value = struct.unpack('I', chunk)[0] / (2**32)  # Normalize to [0,1]
                embedding.append(value)
        
        # Pad if needed
        while len(embedding) < dim:
            embedding.append(0.0)
        
        return embedding[:dim]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scratchpad statistics"""
        stats = {
            "backend": "memory" if not self.redis_client else "redis",
            "semantic_search": self.qdrant_client is not None,
            "total_sessions": 0,
            "total_entries": 0
        }
        
        if self.redis_client:
            try:
                # Count sessions
                session_keys = self.redis_client.keys("scratchpad_index:*")
                stats["total_sessions"] = len(session_keys)
                
                # Count total entries
                for key in session_keys:
                    entries_count = self.redis_client.zcard(key)
                    stats["total_entries"] += entries_count
                    
            except Exception as e:
                logger.error(f"❌ Redis stats failed: {e}")
        else:
            stats["total_sessions"] = len(self.memory_fallback)
            stats["total_entries"] = sum(len(entries) for entries in self.memory_fallback.values())
        
        return stats

# Global scratchpad instance
_scratchpad = None

def get_scratchpad() -> ScratchpadSystem:
    """Get or create global scratchpad instance"""
    global _scratchpad
    if _scratchpad is None:
        _scratchpad = ScratchpadSystem()
    return _scratchpad

# Convenience functions
def write(session_id: str, agent: str, content: str, 
          tags: List[str] = None, entry_type: str = "note") -> str:
    """Write to shared scratchpad"""
    return get_scratchpad().write(session_id, agent, content, tags, entry_type)

def read(session_id: str, limit: int = 10, agent_filter: str = None) -> List[ScratchpadEntry]:
    """Read from shared scratchpad"""
    return get_scratchpad().read(session_id, limit, agent_filter)

def search(session_id: str, query: str, limit: int = 5) -> List[ScratchpadEntry]:
    """Search shared scratchpad"""
    return get_scratchpad().search(session_id, query, limit)

def get_stats() -> Dict[str, Any]:
    """Get scratchpad statistics"""
    return get_scratchpad().get_stats()