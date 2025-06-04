#!/usr/bin/env python3
"""
Bootstrap module for AutoGen Council
===================================

Creates singleton instances that are shared across all requests:
- MEMORY: FaissMemory instance (loads index once)
- Other global resources

This eliminates the "loading FAISS" performance penalty on every request.
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Global singleton instances
MEMORY: Optional[object] = None

def initialize_memory(memory_path: str = "memory") -> object:
    """
    Initialize FAISS memory singleton.
    
    This loads the index once at startup instead of on every request,
    eliminating the ~100-400ms "loading FAISS" penalty.
    """
    global MEMORY
    
    if MEMORY is not None:
        logger.info("📚 Memory already initialized, reusing singleton")
        return MEMORY
    
    try:
        logger.info("🧠 Initializing FAISS memory singleton...")
        start_time = time.time()
        
        from faiss_memory import FaissMemory
        MEMORY = FaissMemory(memory_path)
        
        # Warm up the embedding model to avoid first-request lag
        logger.info("🔥 Warming up embedding model...")
        try:
            # Dummy query to JIT the embedding model on GPU/CPU
            warmup_results = MEMORY.query("dummy warmup query", k=1)
            logger.info(f"🔥 Embedding model warmed up: {len(warmup_results)} results")
        except Exception as e:
            logger.warning(f"Warmup query failed (expected for empty index): {e}")
        
        # 🔥 Seed FAISS with sample data for immediate retrieval
        logger.info("🌱 Seeding memory with sample conversations...")
        seed_data = [
            ("Hello! How are you today?", {
                "role": "user", 
                "timestamp": time.time() - 3600,  # 1 hour ago
                "session_id": "seed_001"
            }),
            ("I'm doing great! I'm your AutoGen Council assistant. I can help with math, code, logic, and knowledge questions.", {
                "role": "assistant",
                "timestamp": time.time() - 3590,
                "success": True,
                "confidence": 0.9,
                "specialist": "agent0",
                "greeting_response": True
            }),
            ("What's 15 * 23?", {
                "role": "user",
                "timestamp": time.time() - 1800,  # 30 min ago
                "session_id": "seed_002"
            }),
            ("**345** ⚡ Here's how: 15 × 23 = (15 × 20) + (15 × 3) = 300 + 45 = 345. Quick mental math! 🧮", {
                "role": "assistant", 
                "timestamp": time.time() - 1795,
                "success": True,
                "confidence": 1.0,
                "specialist": "math_specialist",
                "calculation": True
            }),
            ("Can you write a hello world function?", {
                "role": "user",
                "timestamp": time.time() - 900,  # 15 min ago
                "session_id": "seed_003"
            }),
            ("```python\ndef hello_world():\n    \"\"\"Print a friendly greeting\"\"\"\n    print(\"Hello, World!\")\n    return \"Hello, World!\"\n\n# Call the function\nhello_world()\n```\n**Quick tip**: This is the classic first program in any language! 💻", {
                "role": "assistant",
                "timestamp": time.time() - 895,
                "success": True,
                "confidence": 0.85,
                "specialist": "code_specialist",
                "programming": True
            }),
            ("Tell me something cool about space", {
                "role": "user",
                "timestamp": time.time() - 300,  # 5 min ago
                "session_id": "seed_004"
            }),
            ("**Saturn: The Ringed Wonder!** 🌍 Here's a mind-blowing fact: Saturn is so light it would float in water! 📚 With a density of just 0.687 g/cm³, it's the only planet less dense than water. **Bonus connection**: Saturn's moon Enceladus shoots water geysers 500 miles into space! 💡", {
                "role": "assistant",
                "timestamp": time.time() - 295,
                "success": True,
                "confidence": 0.9,
                "specialist": "knowledge_specialist",
                "space_facts": True
            })
        ]
        
        for text, metadata in seed_data:
            try:
                MEMORY.add(text, metadata)
            except Exception as e:
                logger.warning(f"Failed to seed memory with: {text[:50]}... - {e}")
        
        logger.info(f"🌱 Memory seeded with {len(seed_data)} sample conversations")
        
        init_time = (time.time() - start_time) * 1000
        logger.info(f"✅ FAISS memory initialized in {init_time:.1f}ms")
        logger.info(f"📚 Current memory size: {len(MEMORY.data)} entries")
        
        return MEMORY
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize FAISS memory: {e}")
        # Create a dummy memory object to prevent crashes
        class DummyMemory:
            def query(self, text, k=3):
                return []
            def add(self, text, metadata=None):
                pass
        MEMORY = DummyMemory()
        return MEMORY

def get_memory() -> object:
    """
    FastAPI dependency to get the memory singleton.
    
    Usage:
        @app.post("/vote")
        def vote_route(payload: Prompt, memory=Depends(get_memory)):
            ctx = memory.query(payload.prompt, k=3)
    """
    global MEMORY
    
    if MEMORY is None:
        MEMORY = initialize_memory()
    
    return MEMORY

# Initialize on import for direct usage
if MEMORY is None:
    MEMORY = initialize_memory()

logger.info(f"🧠 Global memory initialized at: {type(MEMORY).__name__}") 