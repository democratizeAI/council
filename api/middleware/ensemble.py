"""
Ensemble Middleware - Routes requests based on clustering and adapter mappings
"""

import hashlib
import logging
from typing import Dict, Any, Optional
from fastapi import Request

logger = logging.getLogger(__name__)

class EnsembleMiddleware:
    """Middleware for ensemble routing and adapter selection"""
    
    def __init__(self, app):
        self.app = app
        self.redis = None  # Will be set by test fixture
    
    async def _resolve_adapter(self, prompt: str) -> Dict[str, Any]:
        """
        Resolve adapter for a given prompt
        
        Returns dict with:
        - cluster_id: Cluster ID if found
        - adapter_tag: Adapter tag if mapped
        - adapter: Loaded adapter if successful
        - is_miss: True if any step failed
        - reason: Reason for miss (if applicable)
        - error: Error message (if applicable)
        """
        try:
            # Generate prompt hash for cluster lookup
            prompt_hash = hashlib.sha1(prompt.encode()).hexdigest()
            
            # Look up cluster mapping
            if not self.redis:
                return {"is_miss": True, "reason": "redis_unavailable"}
            
            cluster_id = await self.redis.get(f"pattern:cluster:{prompt_hash}")
            if not cluster_id:
                return {"is_miss": True, "reason": "no_cluster_mapping"}
            
            # Look up adapter mapping
            adapter_tag = await self.redis.hget("lora:router_map", cluster_id)
            if not adapter_tag:
                return {
                    "cluster_id": cluster_id,
                    "is_miss": True, 
                    "reason": "no_adapter_mapping"
                }
            
            # Load adapter
            try:
                from lora.manager import get
                adapter = get(adapter_tag)
                return {
                    "cluster_id": cluster_id,
                    "adapter_tag": adapter_tag,
                    "adapter": adapter,
                    "is_miss": False
                }
            except Exception as e:
                return {
                    "cluster_id": cluster_id,
                    "adapter_tag": adapter_tag,
                    "is_miss": True,
                    "reason": "adapter_load_failed",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error resolving adapter: {e}")
            return {"is_miss": True, "reason": "system_error", "error": str(e)}
    
    async def __call__(self, request: Request, call_next):
        """Middleware entry point"""
        # For now, just pass through
        response = await call_next(request)
        return response 