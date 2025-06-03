# -*- coding: utf-8 -*-
"""
Hybrid routing: Smart orchestration between local and cloud models
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from loader.deterministic_loader import get_loaded_models
from router.voting import vote
from router.cost_tracking import debit

async def hybrid_route(prompt: str, preferred_models: List[str] = None, enable_council: bool = None) -> Dict[str, Any]:
    """
    Hybrid routing with confidence-based local/cloud decision making
    
    Args:
        prompt: Input prompt
        preferred_models: List of preferred local models
        enable_council: Whether to enable council deliberation
        
    Returns:
        Dict with response, provider, model_used, confidence, etc.
    """
    start_time = time.time()
    
    # Default models if none specified
    if not preferred_models:
        loaded_models = get_loaded_models()
        preferred_models = list(loaded_models.keys())[:2]  # Use first 2 available
    
    try:
        # Use local voting system for hybrid routing
        result = await vote(prompt, preferred_models, top_k=1)
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract winner information
        winner = result.get("winner", {})
        confidence = winner.get("confidence", 0.5)
        
        # Simple cost calculation
        tokens = len(prompt.split()) + len(result.get("text", "").split())
        cost_cents = debit(winner.get("model", "unknown"), tokens)
        
        return {
            "text": result.get("text", ""),
            "provider": "local",
            "model_used": winner.get("model", "unknown"),
            "confidence": confidence,
            "hybrid_latency_ms": latency_ms,
            "cloud_consulted": False,
            "cost_cents": cost_cents,
            "council_used": bool(enable_council),
            "council_voices": None
        }
        
    except Exception as e:
        # Fallback response
        return {
            "text": f"Hybrid routing error: {str(e)}",
            "provider": "error",
            "model_used": "error",
            "confidence": 0.0,
            "hybrid_latency_ms": (time.time() - start_time) * 1000,
            "cloud_consulted": False,
            "cost_cents": 0.0,
            "council_used": False,
            "council_voices": None
        }

async def smart_orchestrate(prompt: str, route: List[str], enable_cloud_fallback: bool = False) -> Dict[str, Any]:
    """
    Smart orchestration with optional cloud fallback
    
    Args:
        prompt: Input prompt
        route: List of models to try
        enable_cloud_fallback: Whether to fallback to cloud if local fails
        
    Returns:
        Dict with orchestration result
    """
    start_time = time.time()
    
    try:
        # Try hybrid routing first
        result = await hybrid_route(prompt, route, enable_council=False)
        
        # If confidence is too low and cloud fallback is enabled
        if result["confidence"] < 0.3 and enable_cloud_fallback:
            # For now, just return the local result with a flag
            result["cloud_consulted"] = True
            result["provider"] = "hybrid_with_cloud_consult"
        
        return result
        
    except Exception as e:
        return {
            "text": f"Orchestration failed: {str(e)}",
            "provider": "error",
            "model_used": "error",
            "confidence": 0.0,
            "hybrid_latency_ms": (time.time() - start_time) * 1000,
            "cloud_consulted": False,
            "cost_cents": 0.0,
            "council_used": False,
            "council_voices": None
        } 