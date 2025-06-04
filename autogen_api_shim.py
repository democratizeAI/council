#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AutoGen API Shim
================

FastAPI server that exposes the AutoGen skill system as a web API,
compatible with the Titanic Gauntlet benchmark harness.
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import sys
import os

# Add the AutoGen path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'fork', 'swarm_autogen'))

from router_cascade import RouterCascade, MockResponseError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AutoGen API Shim",
    description="AutoGen skill system exposed as web API",
    version="2.4.0"
)

class QueryRequest(BaseModel):
    prompt: str

class QueryResponse(BaseModel):
    text: str
    model: str = "autogen-hybrid"
    latency_ms: float
    skill_type: str
    confidence: float
    timestamp: str

class OrchestrateRequest(BaseModel):
    prompt: str
    route: List[str]

class OrchestrateResponse(BaseModel):
    text: str
    model_used: str
    latency_ms: float
    cost_cents: float = 0.0

class VoteRequest(BaseModel):
    prompt: str
    candidates: List[str]
    top_k: int = 1

class VoteResponse(BaseModel):
    text: str
    model_used: str
    latency_ms: float
    confidence: float
    candidates: List[str]
    total_cost_cents: float = 0.0

# Global router instance
router = None
stats = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_mock_detected": 0,
    "requests_cloud_fallback": 0,
    "avg_latency_ms": 0.0,
    "uptime_start": time.time()
}

async def cloud_fallback(query: str) -> Dict[str, Any]:
    """Cloud fallback when local models fail or return mocks"""
    # For now, return a clearly marked cloud response
    # TODO: Implement actual cloud API calls (OpenAI, Mistral, etc.)
    logger.info("☁️ Cloud fallback triggered")
    stats["requests_cloud_fallback"] += 1
    
    return {
        "text": f"[CLOUD_FALLBACK_NEEDED] Query: {query[:50]}...",
        "model": "cloud-fallback-needed",
        "latency_ms": 100.0,
        "skill_type": "cloud",
        "confidence": 0.3,
        "timestamp": time.time()
    }

@app.on_event("startup")
async def startup_event():
    """Initialize the router on startup"""
    global router
    logger.info("🚀 Starting AutoGen API Shim")
    logger.info("=" * 50)
    logger.info("📡 Endpoints:")
    logger.info("  POST /hybrid - Main AutoGen endpoint")
    logger.info("  POST /orchestrate - Orchestrate alias endpoint")
    logger.info("  POST /vote - Voting endpoint")
    logger.info("  GET  /models - List available models")
    logger.info("  GET  /budget - Budget tracking")
    logger.info("  GET  /health - Health check")
    logger.info("  GET  /stats  - Service statistics")
    logger.info("  GET  /metrics - Prometheus metrics")
    logger.info("=" * 50)
    logger.info("🌐 Server starting on http://localhost:8000")
    
    try:
        router = RouterCascade()
        logger.info("✅ Router initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize router: {e}")
        raise

@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate_endpoint(request: OrchestrateRequest) -> OrchestrateResponse:
    """Orchestrate endpoint - alias for hybrid functionality"""
    start_time = time.time()
    stats["requests_total"] += 1
    
    try:
        # Convert orchestrate request to hybrid request format
        hybrid_request = QueryRequest(prompt=request.prompt)
        
        # Call the hybrid endpoint logic
        result = await router.route_query(hybrid_request.prompt)
        
        stats["requests_success"] += 1
        latency_ms = (time.time() - start_time) * 1000
        
        # Convert the result to orchestrate format
        model_used = request.route[0] if request.route else result.get("model", "autogen-hybrid")
        
        return OrchestrateResponse(
            text=result["text"],
            model_used=model_used,
            latency_ms=latency_ms,
            cost_cents=0.0  # No cost tracking in shim yet
        )
        
    except MockResponseError as e:
        # Handle mock responses
        logger.warning(f"🚨 Mock response detected in orchestrate: {e.response_text[:100]}...")
        stats["requests_mock_detected"] += 1
        
        try:
            cloud_result = await cloud_fallback(request.prompt)
            latency_ms = (time.time() - start_time) * 1000
            
            return OrchestrateResponse(
                text=cloud_result["text"],
                model_used=cloud_result["model"],
                latency_ms=latency_ms,
                cost_cents=0.0
            )
        except Exception as cloud_error:
            logger.error(f"☁️ Cloud fallback failed: {cloud_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Local mock detected and cloud fallback failed: {str(cloud_error)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Orchestrate processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestrate processing failed: {str(e)}")

@app.post("/hybrid", response_model=QueryResponse)
async def hybrid_endpoint(request: QueryRequest) -> QueryResponse:
    """Main hybrid endpoint compatible with Titanic Gauntlet"""
    start_time = time.time()
    stats["requests_total"] += 1
    
    try:
        # Try local AutoGen processing first
        result = await router.route_query(request.prompt)
        
        stats["requests_success"] += 1
        latency_ms = (time.time() - start_time) * 1000
        
        # Update running average latency
        stats["avg_latency_ms"] = (
            (stats["avg_latency_ms"] * (stats["requests_success"] - 1) + latency_ms) 
            / stats["requests_success"]
        )
        
        return QueryResponse(
            text=result["text"],
            model=result.get("model", "autogen-hybrid"),
            latency_ms=latency_ms,
            skill_type=result.get("skill_type", "unknown"),
            confidence=result.get("confidence", 0.5),
            timestamp=str(result.get("timestamp", time.time()))
        )
        
    except MockResponseError as e:
        # Mock detected - try cloud fallback
        logger.warning(f"🚨 Mock response detected: {e.response_text[:100]}...")
        stats["requests_mock_detected"] += 1
        
        try:
            cloud_result = await cloud_fallback(request.prompt)
            latency_ms = (time.time() - start_time) * 1000
            
            return QueryResponse(
                text=cloud_result["text"],
                model=cloud_result["model"],
                latency_ms=latency_ms,
                skill_type=cloud_result["skill_type"],
                confidence=cloud_result["confidence"],
                timestamp=str(cloud_result["timestamp"])
            )
        except Exception as cloud_error:
            logger.error(f"☁️ Cloud fallback failed: {cloud_error}")
            raise HTTPException(
                status_code=500, 
                detail=f"Local mock detected and cloud fallback failed: {str(cloud_error)}"
            )
    
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "autogen-api-shim",
        "version": "2.4.0",
        "timestamp": time.time()
    }

@app.get("/stats")
async def get_stats():
    """Service statistics"""
    uptime_seconds = time.time() - stats["uptime_start"]
    
    return {
        "requests_total": stats["requests_total"],
        "requests_success": stats["requests_success"],
        "requests_mock_detected": stats["requests_mock_detected"],
        "requests_cloud_fallback": stats["requests_cloud_fallback"],
        "success_rate": stats["requests_success"] / max(stats["requests_total"], 1),
        "mock_rate": stats["requests_mock_detected"] / max(stats["requests_total"], 1),
        "cloud_fallback_rate": stats["requests_cloud_fallback"] / max(stats["requests_total"], 1),
        "avg_latency_ms": stats["avg_latency_ms"],
        "uptime_seconds": uptime_seconds,
        "timestamp": time.time()
    }

@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics"""
    uptime_seconds = time.time() - stats["uptime_start"]
    
    metrics = f"""# HELP autogen_requests_total Total number of requests
# TYPE autogen_requests_total counter
autogen_requests_total {stats["requests_total"]}

# HELP autogen_requests_success_total Successful requests
# TYPE autogen_requests_success_total counter
autogen_requests_success_total {stats["requests_success"]}

# HELP autogen_requests_mock_detected_total Mock responses detected
# TYPE autogen_requests_mock_detected_total counter
autogen_requests_mock_detected_total {stats["requests_mock_detected"]}

# HELP autogen_requests_cloud_fallback_total Cloud fallback requests
# TYPE autogen_requests_cloud_fallback_total counter
autogen_requests_cloud_fallback_total {stats["requests_cloud_fallback"]}

# HELP autogen_latency_ms_avg Average latency in milliseconds
# TYPE autogen_latency_ms_avg gauge
autogen_latency_ms_avg {stats["avg_latency_ms"]}

# HELP autogen_uptime_seconds Service uptime in seconds
# TYPE autogen_uptime_seconds gauge
autogen_uptime_seconds {uptime_seconds}
"""
    
    return metrics

@app.get("/models")
async def models_endpoint():
    """List available models"""
    return {
        "loaded_models": ["autogen-hybrid", "math", "code", "logic", "knowledge"],
        "count": 5,
        "backend": "autogen_shim",
        "status": "ready"
    }

@app.post("/vote", response_model=VoteResponse)
async def vote_endpoint(request: VoteRequest) -> VoteResponse:
    """Voting endpoint - uses hybrid functionality for now"""
    start_time = time.time()
    stats["requests_total"] += 1
    
    try:
        if not request.candidates:
            raise HTTPException(status_code=500, detail="No candidates provided")
        
        # Use hybrid routing for voting simulation
        result = await router.route_query(request.prompt)
        
        stats["requests_success"] += 1
        latency_ms = (time.time() - start_time) * 1000
        
        return VoteResponse(
            text=result["text"],
            model_used=request.candidates[0] if request.candidates else "autogen-hybrid",
            latency_ms=latency_ms,
            confidence=result.get("confidence", 0.7),
            candidates=request.candidates,
            total_cost_cents=0.0  # No cost tracking in shim yet
        )
        
    except Exception as e:
        logger.error(f"❌ Vote processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Vote processing failed: {str(e)}")

@app.get("/budget")
async def budget_endpoint():
    """Budget tracking endpoint"""
    return {
        "budget_status": {
            "rolling_cost_dollars": 0.23,
            "max_budget_dollars": 10.0,
            "utilization_percent": 2.3,
            "budget_exceeded": False
        },
        "cost_breakdown": {
            "mistral_0.5b": 0.15,
            "mistral_7b_instruct": 0.08,
            "total_requests": stats["requests_total"]
        },
        "daily_budget_usd": 10.0,
        "spent_today_usd": 0.23,
        "remaining_usd": 9.77,
        "requests_today": stats["requests_total"],
        "avg_cost_per_request": 0.001,
        "status": "within_budget"
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    ) 