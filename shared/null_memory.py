"""
Null memory backend for bypass testing - all operations are no-ops
"""
from typing import List, Dict, Any, Optional


class NullMemory:
    """Null memory backend that performs no operations"""
    
    def __init__(self, **kwargs):
        self.initialized = True
        print("✅ Null memory stub initialized successfully")
    
    def query(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        """Return empty results for any query"""
        return []
    
    def add_entry(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Pretend to add entry but do nothing"""
        return True
    
    def get_size(self) -> int:
        """Return mock size"""
        return 0
    
    def clear(self) -> bool:
        """Pretend to clear but do nothing"""
        return True 