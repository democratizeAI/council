"""
LoRA Manager - Mock implementation for testing compatibility
"""

import time
from typing import Dict, Any, List

# Mock cache stats
_cache_stats = {
    "cached_models": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "last_warm": time.time(),
    "cache_size": 0,
    "loaded_adapters": []
}

# Mock adapter cache
_adapter_cache = {}

def get_cache_stats() -> Dict[str, Any]:
    """Get LoRA cache statistics"""
    return _cache_stats.copy()

def warm_cache(model_names: list = None) -> bool:
    """Warm the LoRA model cache"""
    _cache_stats["last_warm"] = time.time()
    if model_names:
        _cache_stats["cached_models"] = len(model_names)
    return True

def clear_cache() -> bool:
    """Clear the LoRA model cache"""
    global _adapter_cache
    _adapter_cache = {}
    _cache_stats["cached_models"] = 0
    _cache_stats["cache_hits"] = 0
    _cache_stats["cache_misses"] = 0
    _cache_stats["cache_size"] = 0
    _cache_stats["loaded_adapters"] = []
    return True

def get(adapter_tag: str):
    """Get an adapter by tag (mock implementation)"""
    if adapter_tag in _adapter_cache:
        _cache_stats["cache_hits"] += 1
        return _adapter_cache[adapter_tag]
    
    # Mock loading
    _cache_stats["cache_misses"] += 1
    mock_adapter = f"MockAdapter_{adapter_tag}"
    _adapter_cache[adapter_tag] = mock_adapter
    _cache_stats["cache_size"] = len(_adapter_cache)
    _cache_stats["loaded_adapters"] = list(_adapter_cache.keys())
    
    return mock_adapter

def _load_adapter(adapter_tag: str):
    """Internal function to load adapter (mock)"""
    return f"LoadedAdapter_{adapter_tag}" 