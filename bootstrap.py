# bootstrap.py - Global memory instance for the AutoGen Council system
# ==============================================================================
# Creates a thread-safe, persistent FAISS memory that all components can use
# ==============================================================================

from faiss_memory import FaissMemory
import os

# Global memory instance - thread-safe, one instance is enough
MEMORY = FaissMemory(os.getenv("MEMORY_PATH", "memory"))

print(f"🧠 Global memory initialized at: {MEMORY.db_dir}")
print(f"📚 Current memory size: {len(MEMORY.meta)} entries") 