"""
Mock router for bypass testing - provides immediate responses without model loading
"""
import time
import asyncio
import os
from typing import Dict, List, Optional, Any


class MockRouterCascade:
    """Mock router that returns immediate responses for load testing"""
    
    def __init__(self, **kwargs):
        self.initialized = True
        print("✅ Mock router initialized successfully (bypassing TinyLlama)")
        print(f"🚀 SKIP_MODEL_LOAD={os.getenv('SKIP_MODEL_LOAD', 'false')}")
    
    async def route_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return mock response immediately"""
        # Simulate small processing delay
        await asyncio.sleep(0.05)  # 50ms
        
        return {
            "text": f"Mock response for: {prompt[:50]}...",
            "model_used": "MockRouter",
            "confidence": 0.85,
            "latency_ms": 50.0,
            "context_used": False,
            "provider": "mock",
            "timestamp": time.time()
        }
    
    async def route_query(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Alias for route_request"""
        return await self.route_request(prompt, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return mock statistics"""
        return {
            "total_requests": 0,
            "average_latency": 50.0,
            "mock_mode": True,
            "models_loaded": 0
        } 