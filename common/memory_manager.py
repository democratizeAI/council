#!/usr/bin/env python3
"""
🧠 MEMORY MANAGER: Write-behind persistence + FAISS re-indexing + Memory GC
=========================================================================

Implements durable memory with:
1. Write-behind thread for async persistence
2. Periodic FAISS re-indexing  
3. Memory garbage collection
4. Redis → Qdrant/SQLite pipeline
"""

import asyncio
import logging
import time
import threading
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import deque
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Prometheus metrics
MEMORY_WRITES = Counter("memory_writes_total", "Total memory writes", labelnames=["storage_type"])
MEMORY_READS = Counter("memory_reads_total", "Total memory reads", labelnames=["storage_type"])
MEMORY_GC_RUNS = Counter("memory_gc_runs_total", "Memory garbage collection runs")
MEMORY_QUEUE_SIZE = Gauge("memory_queue_size", "Items in memory write queue")
MEMORY_PERSISTENCE_LATENCY = Histogram("memory_persistence_seconds", "Memory persistence latency")

@dataclass
class MemoryEntry:
    """Memory entry with metadata"""
    content: str
    timestamp: float
    session_id: str
    entry_type: str = "user_message"
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    embedding: List[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}

class MemoryManager:
    """Production-grade memory manager with persistence and GC"""
    
    def __init__(self, 
                 sqlite_path: str = "./data/memory.db",
                 redis_host: str = "localhost",
                 redis_port: int = 6379,
                 max_memory_entries: int = 10000,
                 gc_interval_hours: int = 24):
        
        self.sqlite_path = Path(sqlite_path)
        self.sqlite_path.parent.mkdir(exist_ok=True)
        
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.max_memory_entries = max_memory_entries
        self.gc_interval_hours = gc_interval_hours
        
        # In-memory cache for fast access
        self.memory_cache: deque = deque(maxlen=max_memory_entries)
        self.session_cache: Dict[str, List[MemoryEntry]] = {}
        
        # Write-behind queue
        self.write_queue: asyncio.Queue = None
        self.write_thread: threading.Thread = None
        self.running = False
        
        # FAISS index (optional)
        self.faiss_index = None
        self.faiss_enabled = False
        
        # Initialize storage
        self._init_sqlite()
        self._init_redis()
        self._init_faiss()
        
        logger.info(f"🧠 MemoryManager initialized: SQLite={self.sqlite_path}, max_entries={max_memory_entries}")
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    entry_type TEXT DEFAULT 'user_message',
                    tags TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    embedding TEXT,  -- JSON array of floats
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_session_id ON memory_entries(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON memory_entries(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_type ON memory_entries(entry_type)")
            
            conn.commit()
            conn.close()
            
            logger.info("✅ SQLite memory storage initialized")
            
        except Exception as e:
            logger.error(f"❌ SQLite initialization failed: {e}")
    
    def _init_redis(self):
        """Initialize Redis connection (optional)"""
        try:
            import redis
            self.redis_client = redis.Redis(
                host=self.redis_host, 
                port=self.redis_port, 
                decode_responses=True,
                socket_connect_timeout=1
            )
            
            # Test connection
            self.redis_client.ping()
            self.redis_enabled = True
            logger.info("✅ Redis memory cache initialized")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable: {e} - using in-memory cache only")
            self.redis_client = None
            self.redis_enabled = False
    
    def _init_faiss(self):
        """Initialize FAISS vector index (optional)"""
        try:
            import faiss
            import numpy as np
            
            # Create a simple flat index for demonstration
            self.faiss_dimension = 768  # Typical embedding dimension
            self.faiss_index = faiss.IndexFlatIP(self.faiss_dimension)  # Inner product
            self.faiss_enabled = True
            
            logger.info("✅ FAISS vector index initialized")
            
        except ImportError:
            logger.info("ℹ️ FAISS not available - semantic search disabled")
            self.faiss_enabled = False
        except Exception as e:
            logger.warning(f"⚠️ FAISS initialization failed: {e}")
            self.faiss_enabled = False
    
    async def start_background_tasks(self):
        """Start write-behind thread and GC tasks"""
        if self.running:
            return
        
        self.running = True
        self.write_queue = asyncio.Queue()
        
        # Start write-behind thread
        self.write_thread = threading.Thread(target=self._write_behind_worker, daemon=True)
        self.write_thread.start()
        
        # Start periodic GC
        asyncio.create_task(self._periodic_gc())
        
        logger.info("🚀 Memory background tasks started")
    
    def _write_behind_worker(self):
        """Write-behind thread worker"""
        logger.info("🧵 Write-behind thread started")
        
        while self.running:
            try:
                # Use threading-safe queue
                import queue
                thread_queue = queue.Queue()
                
                # Simple polling approach
                time.sleep(0.5)
                
                # Batch process queued writes
                self._flush_pending_writes()
                
            except Exception as e:
                logger.error(f"❌ Write-behind worker error: {e}")
                time.sleep(1)
    
    def _flush_pending_writes(self):
        """Flush pending writes to persistent storage"""
        try:
            with MEMORY_PERSISTENCE_LATENCY.time():
                # Flush to SQLite
                self._flush_to_sqlite()
                
                # Flush to Redis (if enabled)
                if self.redis_enabled:
                    self._flush_to_redis()
                
                # Re-index FAISS (if enabled)
                if self.faiss_enabled:
                    self._reindex_faiss()
            
        except Exception as e:
            logger.error(f"❌ Flush failed: {e}")
    
    def _flush_to_sqlite(self):
        """Flush memory cache to SQLite"""
        if not self.memory_cache:
            return
        
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            
            # Get recent entries to persist
            entries_to_persist = list(self.memory_cache)[-100:]  # Last 100 entries
            
            for entry in entries_to_persist:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_entries 
                    (content, timestamp, session_id, entry_type, tags, metadata, embedding)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.content,
                    entry.timestamp,
                    entry.session_id,
                    entry.entry_type,
                    json.dumps(entry.tags),
                    json.dumps(entry.metadata),
                    json.dumps(entry.embedding) if entry.embedding else None
                ))
            
            conn.commit()
            conn.close()
            
            MEMORY_WRITES.labels(storage_type="sqlite").inc(len(entries_to_persist))
            logger.debug(f"💾 Flushed {len(entries_to_persist)} entries to SQLite")
            
        except Exception as e:
            logger.error(f"❌ SQLite flush failed: {e}")
    
    def _flush_to_redis(self):
        """Flush recent entries to Redis for fast access"""
        if not self.redis_client or not self.memory_cache:
            return
        
        try:
            # Store last 50 entries in Redis for fast access
            recent_entries = list(self.memory_cache)[-50:]
            
            pipe = self.redis_client.pipeline()
            
            for entry in recent_entries:
                key = f"memory:{entry.session_id}:{entry.timestamp}"
                value = json.dumps(asdict(entry))
                pipe.setex(key, 3600, value)  # 1 hour TTL
            
            pipe.execute()
            
            MEMORY_WRITES.labels(storage_type="redis").inc(len(recent_entries))
            logger.debug(f"⚡ Cached {len(recent_entries)} entries in Redis")
            
        except Exception as e:
            logger.error(f"❌ Redis flush failed: {e}")
    
    def _reindex_faiss(self):
        """Re-index FAISS with recent embeddings"""
        if not self.faiss_enabled or not self.memory_cache:
            return
        
        try:
            import numpy as np
            
            # Get entries with embeddings
            entries_with_embeddings = [
                entry for entry in self.memory_cache 
                if entry.embedding and len(entry.embedding) == self.faiss_dimension
            ]
            
            if not entries_with_embeddings:
                return
            
            # Clear and rebuild index (simple approach)
            self.faiss_index.reset()
            
            # Add embeddings
            embeddings = np.array([entry.embedding for entry in entries_with_embeddings], dtype=np.float32)
            self.faiss_index.add(embeddings)
            
            logger.debug(f"🔍 Re-indexed {len(entries_with_embeddings)} embeddings in FAISS")
            
        except Exception as e:
            logger.error(f"❌ FAISS re-indexing failed: {e}")
    
    async def _periodic_gc(self):
        """Periodic garbage collection"""
        while self.running:
            try:
                await asyncio.sleep(self.gc_interval_hours * 3600)
                
                logger.info("🗑️ Starting memory garbage collection...")
                gc_start = time.time()
                
                # Memory GC: Keep only recent entries
                if len(self.memory_cache) > self.max_memory_entries:
                    old_size = len(self.memory_cache)
                    # Deque automatically limits size, but let's be explicit
                    entries_to_keep = list(self.memory_cache)[-self.max_memory_entries:]
                    self.memory_cache.clear()
                    self.memory_cache.extend(entries_to_keep)
                    
                    logger.info(f"🗑️ Memory GC: {old_size} → {len(self.memory_cache)} entries")
                
                # Session cache GC: Remove old sessions
                cutoff_time = time.time() - (7 * 24 * 3600)  # 1 week
                old_sessions = []
                
                for session_id, entries in self.session_cache.items():
                    if entries and entries[-1].timestamp < cutoff_time:
                        old_sessions.append(session_id)
                
                for session_id in old_sessions:
                    del self.session_cache[session_id]
                
                if old_sessions:
                    logger.info(f"🗑️ Session GC: Removed {len(old_sessions)} old sessions")
                
                # SQLite GC: Archive very old entries
                self._archive_old_entries()
                
                gc_time = time.time() - gc_start
                MEMORY_GC_RUNS.inc()
                
                logger.info(f"✅ Memory GC completed in {gc_time:.2f}s")
                
            except Exception as e:
                logger.error(f"❌ Memory GC failed: {e}")
    
    def _archive_old_entries(self):
        """Archive very old entries to reduce database size"""
        try:
            conn = sqlite3.connect(str(self.sqlite_path))
            
            # Archive entries older than 30 days
            cutoff_time = time.time() - (30 * 24 * 3600)
            
            # Count old entries
            cursor = conn.execute("SELECT COUNT(*) FROM memory_entries WHERE timestamp < ?", (cutoff_time,))
            old_count = cursor.fetchone()[0]
            
            if old_count > 1000:  # Only archive if significant number
                # Move to archive table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS memory_archive (
                        id INTEGER PRIMARY KEY,
                        content TEXT,
                        timestamp REAL,
                        session_id TEXT,
                        entry_type TEXT,
                        archived_at REAL DEFAULT (julianday('now'))
                    )
                """)
                
                conn.execute("""
                    INSERT INTO memory_archive (content, timestamp, session_id, entry_type)
                    SELECT content, timestamp, session_id, entry_type 
                    FROM memory_entries 
                    WHERE timestamp < ?
                """, (cutoff_time,))
                
                # Delete from main table
                conn.execute("DELETE FROM memory_entries WHERE timestamp < ?", (cutoff_time,))
                
                conn.commit()
                logger.info(f"📦 Archived {old_count} old memory entries")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ Memory archival failed: {e}")
    
    def add_memory(self, content: str, session_id: str = "default", 
                   entry_type: str = "user_message", tags: List[str] = None, 
                   metadata: Dict[str, Any] = None) -> None:
        """Add memory entry (async via write-behind)"""
        entry = MemoryEntry(
            content=content,
            timestamp=time.time(),
            session_id=session_id,
            entry_type=entry_type,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Add to in-memory cache immediately
        self.memory_cache.append(entry)
        
        # Add to session cache
        if session_id not in self.session_cache:
            self.session_cache[session_id] = []
        self.session_cache[session_id].append(entry)
        
        # Update queue size metric
        MEMORY_QUEUE_SIZE.set(len(self.memory_cache))
        
        logger.debug(f"📝 Added memory: {content[:50]}... (session: {session_id})")
    
    def get_recent_memories(self, session_id: str = None, limit: int = 10) -> List[MemoryEntry]:
        """Get recent memories from cache"""
        try:
            MEMORY_READS.labels(storage_type="cache").inc()
            
            if session_id:
                # Get from session cache
                session_entries = self.session_cache.get(session_id, [])
                return session_entries[-limit:]
            else:
                # Get from global cache
                return list(self.memory_cache)[-limit:]
                
        except Exception as e:
            logger.error(f"❌ Memory retrieval failed: {e}")
            return []
    
    def search_memories(self, query: str, session_id: str = None, limit: int = 5) -> List[MemoryEntry]:
        """Search memories (simple text search for now)"""
        try:
            MEMORY_READS.labels(storage_type="search").inc()
            
            # Simple text search in memory cache
            query_lower = query.lower()
            matches = []
            
            search_pool = self.memory_cache
            if session_id and session_id in self.session_cache:
                search_pool = self.session_cache[session_id]
            
            for entry in search_pool:
                if query_lower in entry.content.lower():
                    matches.append(entry)
                    
                if len(matches) >= limit:
                    break
            
            return matches[-limit:]  # Most recent matches
            
        except Exception as e:
            logger.error(f"❌ Memory search failed: {e}")
            return []
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        try:
            sqlite_count = 0
            redis_count = 0
            
            # Count SQLite entries
            try:
                conn = sqlite3.connect(str(self.sqlite_path))
                cursor = conn.execute("SELECT COUNT(*) FROM memory_entries")
                sqlite_count = cursor.fetchone()[0]
                conn.close()
            except:
                pass
            
            # Count Redis entries
            if self.redis_enabled:
                try:
                    redis_count = len(self.redis_client.keys("memory:*"))
                except:
                    pass
            
            return {
                "cache_entries": len(self.memory_cache),
                "session_caches": len(self.session_cache),
                "sqlite_entries": sqlite_count,
                "redis_entries": redis_count,
                "faiss_enabled": self.faiss_enabled,
                "redis_enabled": self.redis_enabled,
                "max_cache_size": self.max_memory_entries,
                "background_running": self.running,
                "queue_size": len(self.memory_cache)
            }
            
        except Exception as e:
            logger.error(f"❌ Memory stats failed: {e}")
            return {"error": str(e)}
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down memory manager...")
        
        self.running = False
        
        # Final flush
        self._flush_pending_writes()
        
        # Wait for write thread
        if self.write_thread and self.write_thread.is_alive():
            self.write_thread.join(timeout=5)
        
        logger.info("✅ Memory manager shutdown complete")

# Global memory manager instance
MEMORY_MANAGER = MemoryManager()

# Convenience functions
def add_memory(content: str, session_id: str = "default", **kwargs) -> None:
    """Add memory entry"""
    MEMORY_MANAGER.add_memory(content, session_id, **kwargs)

def get_recent(session_id: str = None, limit: int = 10) -> List[MemoryEntry]:
    """Get recent memories"""
    return MEMORY_MANAGER.get_recent_memories(session_id, limit)

def search_memory(query: str, session_id: str = None, limit: int = 5) -> List[MemoryEntry]:
    """Search memories"""
    return MEMORY_MANAGER.search_memories(query, session_id, limit)

def get_memory_stats() -> Dict[str, Any]:
    """Get memory system statistics"""
    return MEMORY_MANAGER.get_memory_stats()

async def start_memory_system():
    """Start memory background tasks"""
    await MEMORY_MANAGER.start_background_tasks() 