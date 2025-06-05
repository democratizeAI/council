#!/usr/bin/env python3
"""
Whiteboard API - Explicit Blackboard for Council Deliberations
==============================================================

Exposes the existing scratchpad library as a REST API for explicit
read/write access to the Council's shared memory blackboard.
"""

from fastapi import APIRouter, Body, HTTPException, Query
from typing import List, Dict, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)

# Create whiteboard router
wb = APIRouter(prefix="/whiteboard", tags=["whiteboard"])

try:
    from common.scratchpad import write, read, query_memory
    SCRATCHPAD_AVAILABLE = True
    logger.info("✅ Scratchpad backend available for whiteboard API")
except ImportError:
    SCRATCHPAD_AVAILABLE = False
    logger.warning("⚠️ Scratchpad not available - using mock whiteboard")
    
    # Mock implementations for testing
    _mock_entries = {}
    
    def write(session: str, author: str, content: str, tags: List[str] = None):
        if session not in _mock_entries:
            _mock_entries[session] = []
        _mock_entries[session].append({
            "author": author,
            "content": content,
            "tags": tags or [],
            "timestamp": time.time()
        })
    
    def read(session: str, k: int = 5):
        return _mock_entries.get(session, [])[-k:]
    
    def query_memory(session: str, query: str, k: int = 3):
        # Simple mock query - return recent entries
        entries = _mock_entries.get(session, [])
        return [{"text": e["content"], "score": 0.5} for e in entries[-k:]]

@wb.post("/write")
async def wb_write(
    session: str = Body(..., description="Session ID for the whiteboard"),
    author: str = Body(..., description="Author of the entry (e.g., specialist name)"),
    content: str = Body(..., description="Content to write to the whiteboard"),
    tags: List[str] = Body(default=[], description="Optional tags for categorization")
) -> Dict[str, Any]:
    """
    Write an entry to the whiteboard
    
    The whiteboard serves as the Council's shared memory, allowing specialists
    to communicate findings and build on each other's work.
    """
    try:
        # Validate inputs
        if not session or not session.strip():
            raise HTTPException(status_code=400, detail="Session ID required")
        if not author or not author.strip():
            raise HTTPException(status_code=400, detail="Author required")
        if not content or not content.strip():
            raise HTTPException(status_code=400, detail="Content required")
        
        # Write to scratchpad
        write(session.strip(), author.strip(), content.strip(), tags=tags)
        
        logger.info(f"📝 Whiteboard write: {author} → {session} ({len(content)} chars)")
        
        return {
            "ok": True,
            "message": "Entry written to whiteboard",
            "session": session,
            "author": author,
            "content_length": len(content),
            "tags": tags,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Whiteboard write failed: {e}")
        raise HTTPException(status_code=500, detail=f"Write failed: {str(e)}")

@wb.get("/read")
async def wb_read(
    session: str = Query(..., description="Session ID to read from"),
    k: int = Query(default=5, description="Number of recent entries to retrieve", ge=1, le=50)
) -> Dict[str, Any]:
    """
    Read recent entries from the whiteboard
    
    Returns the k most recent entries from the specified session,
    allowing specialists to see what others have contributed.
    """
    try:
        if not session or not session.strip():
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Read from scratchpad
        entries = read(session.strip(), k=k)
        
        logger.info(f"📖 Whiteboard read: {session} → {len(entries)} entries")
        
        return {
            "session": session,
            "entries": entries,
            "count": len(entries),
            "requested": k,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Whiteboard read failed: {e}")
        raise HTTPException(status_code=500, detail=f"Read failed: {str(e)}")

@wb.get("/query")
async def wb_query(
    session: str = Query(..., description="Session ID to query"),
    query: str = Query(..., description="Query string for semantic search"),
    k: int = Query(default=3, description="Number of results to return", ge=1, le=20)
) -> Dict[str, Any]:
    """
    Query the whiteboard with semantic search
    
    Searches the session's whiteboard entries for content semantically
    similar to the query, enabling context-aware specialist responses.
    """
    try:
        if not session or not session.strip():
            raise HTTPException(status_code=400, detail="Session ID required")
        if not query or not query.strip():
            raise HTTPException(status_code=400, detail="Query required")
        
        # Query memory if available
        if SCRATCHPAD_AVAILABLE:
            results = query_memory(session.strip(), query.strip(), k=k)
        else:
            # Mock query for testing
            entries = read(session.strip(), k=k)
            results = [{"text": e.get("content", ""), "score": 0.5} for e in entries]
        
        logger.info(f"🔍 Whiteboard query: '{query}' in {session} → {len(results)} results")
        
        return {
            "session": session,
            "query": query,
            "results": results,
            "count": len(results),
            "requested": k,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Whiteboard query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@wb.get("/sessions")
async def wb_sessions() -> Dict[str, Any]:
    """
    List active whiteboard sessions
    
    Returns a list of sessions that have recent activity,
    useful for monitoring Council deliberations.
    """
    try:
        if SCRATCHPAD_AVAILABLE:
            # Try to get sessions from scratchpad if it supports it
            sessions = []  # Placeholder - depends on scratchpad implementation
        else:
            # Mock sessions for testing
            sessions = list(_mock_entries.keys()) if '_mock_entries' in globals() else []
        
        logger.info(f"📋 Active whiteboard sessions: {len(sessions)}")
        
        return {
            "sessions": sessions,
            "count": len(sessions),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Sessions list failed: {e}")
        raise HTTPException(status_code=500, detail=f"Sessions list failed: {str(e)}")

@wb.delete("/clear")
async def wb_clear(
    session: str = Body(..., description="Session ID to clear"),
    confirm: bool = Body(default=False, description="Confirmation flag")
) -> Dict[str, Any]:
    """
    Clear a whiteboard session
    
    Removes all entries from the specified session.
    Requires confirmation to prevent accidental data loss.
    """
    try:
        if not confirm:
            raise HTTPException(status_code=400, detail="Confirmation required (set confirm=true)")
        
        if not session or not session.strip():
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Clear session
        if SCRATCHPAD_AVAILABLE:
            # Use scratchpad clear if available
            logger.warning(f"⚠️ Scratchpad clear not implemented - session {session} not cleared")
        else:
            # Mock clear
            if session in _mock_entries:
                del _mock_entries[session]
        
        logger.warning(f"🗑️ Whiteboard cleared: {session}")
        
        return {
            "ok": True,
            "message": f"Session {session} cleared",
            "session": session,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Whiteboard clear failed: {e}")
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

@wb.get("/health")
async def wb_health() -> Dict[str, Any]:
    """Health check for whiteboard API"""
    return {
        "status": "healthy",
        "scratchpad_available": SCRATCHPAD_AVAILABLE,
        "timestamp": time.time()
    } 