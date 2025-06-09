"""
Mock router for bypass testing - provides immediate responses
"""
import time
import asyncio
from typing import Dict, List, Optional, Any


class MockRouterCascade:
    """Mock router that returns immediate responses for load testing"""
    
    def __init__(self, **kwargs):
        self.initialized = True
        print("✅ Mock router initialized successfully")
    
    async def route_request(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Return mock response immediately"""
        # Simulate small processing delay
        await asyncio.sleep(0.05)  # 50ms
        
        return {
            "text": f"Mock response for: {prompt[:50]}...",
            "model_used": "MockRouter",
            "confidence": 0.85,
            "latency_ms": 50.0,
            "cost_cents": 0.0,
            "flags": [],
            "skill_type": "mock"
        }
    
    async def process_request_with_context(self, prompt: str, context: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """Mock processing with context"""
        return await self.route_request(prompt, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Return mock stats"""
        return {
            "total_requests": 0,
            "avg_latency_ms": 50.0,
            "mock_mode": True
        } 