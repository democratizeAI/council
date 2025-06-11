#!/usr/bin/env python3
"""
RouterCascade - Direct VLLM Routing (No Complex Reasoning Chains)
Uses services/agent_client.py for simple prompt → completion
"""

import asyncio
import time
import logging
import os
from typing import Dict, Any, Optional, List

# Import the thin VLLM client
from services.agent_client import phi3_infer, opus_infer, o3_infer, router_infer

logger = logging.getLogger(__name__)

class MockResponseError(Exception):
    """Exception for mock responses"""
    def __init__(self, response_text):
        self.response_text = response_text
        super().__init__(f"Mock response: {response_text}")

class RouterCascade:
    """
    Direct VLLM RouterCascade - No reasoning chains, just prompt → completion
    Environment-driven configuration via .env
    """
    
    def __init__(self):
        self.vllm_url = os.getenv("VLLM_BASE_URL", "http://phi3mini:8000")
        self.model_name = os.getenv("VLLM_MODEL_NAME", "phi-3-mini-int4")
        self.timeout = int(os.getenv("VLLM_TIMEOUT_SEC", "8"))
        
        logger.info(f"🚀 RouterCascade - VLLM Direct Mode")
        logger.info(f"🔗 VLLM URL: {self.vllm_url}")
        logger.info(f"🤖 Model: {self.model_name}")
        
        # Agent routing map
        self.agents = {
            'phi3': phi3_infer,
            'opus': opus_infer,
            'o3': o3_infer,
            'router': router_infer,
            'default': phi3_infer
        }
    
    async def route_query(self, prompt: str, agent: str = 'phi3') -> Dict[str, Any]:
        """
        Route query directly to VLLM - NO REASONING CHAINS
        
        Args:
            prompt: Input text (no preprocessing)
            agent: Agent type (phi3, opus, o3, router)
            
        Returns:
            Direct VLLM response
        """
        start_time = time.time()
        
        # Get agent function
        agent_func = self.agents.get(agent, self.agents['default'])
        
        logger.info(f"📡 Direct VLLM call: {agent} - {prompt[:50]}...")
        
        try:
            # Direct call - no reasoning, no chains, no preprocessing
            response_text = await agent_func(prompt)
            
            latency_ms = (time.time() - start_time) * 1000
            
            result = {
                "text": response_text,
                "model": f"vllm-{agent}",
                "confidence": 0.95,
                "skill_type": "vllm_direct",
                "timestamp": time.time(),
                "latency_ms": latency_ms,
                "agent": agent
            }
            
            logger.info(f"✅ VLLM response: {len(response_text)} chars in {latency_ms:.1f}ms")
            return result
            
        except Exception as e:
            logger.error(f"❌ VLLM call failed: {e}")
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "text": f"VLLM service error: {str(e)}",
                "model": f"error-{agent}",
                "confidence": 0.0,
                "skill_type": "error",
                "timestamp": time.time(),
                "latency_ms": latency_ms,
                "agent": agent
            }
    
    async def route_phi3(self, prompt: str) -> str:
        """Phi3 direct routing - NO CHAINS"""
        result = await self.route_query(prompt, agent='phi3')
        return result["text"]
    
    async def route_opus(self, prompt: str) -> str:
        """Opus direct routing - NO CHAINS"""
        result = await self.route_query(prompt, agent='opus')
        return result["text"]
    
    async def route_o3(self, prompt: str) -> str:
        """O3 direct routing - NO CHAINS"""
        result = await self.route_query(prompt, agent='o3')
        return result["text"]
    
    async def orchestrate(self, prompt: str, route: List[str] = None) -> Dict[str, Any]:
        """
        Orchestrate endpoint - simplified direct routing
        NO complex reasoning chains, NO multi-step processing
        
        Args:
            prompt: Raw input prompt
            route: Agent preference list (first one wins)
            
        Returns:
            Direct orchestration result
        """
        # Simple agent selection - no complex logic
        agent = (route[0] if route and route else 'phi3')
        
        logger.info(f"🎯 Orchestrate: {agent} for '{prompt[:30]}...'")
        
        # Direct VLLM call
        result = await self.route_query(prompt, agent=agent)
        
        # Return in expected format for APIs
        return {
            "response": result["text"],      # Socket Mode expects this
            "answer": result["text"],        # Some APIs expect this  
            "text": result["text"],          # Keep for compatibility
            "model_used": result["model"],
            "latency_ms": result["latency_ms"],
            "cost_cents": 0.1,              # Minimal VLLM cost
            "agent": agent,
            "skill_type": result["skill_type"],
            "confidence": result["confidence"],
            "timestamp": result["timestamp"]
        }

# Legacy compatibility methods (kept simple)
async def route_phi3(prompt: str) -> str:
    """Legacy phi3 routing function"""
    router = RouterCascade()
    return await router.route_phi3(prompt)

async def route_opus(prompt: str) -> str:
    """Legacy opus routing function"""
    router = RouterCascade()
    return await router.route_opus(prompt)

async def route_o3(prompt: str) -> str:
    """Legacy o3 routing function"""
    router = RouterCascade()
    return await router.route_o3(prompt)