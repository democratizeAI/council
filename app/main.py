# -*- coding: utf-8 -*-
"""
SwarmAI FastAPI Main Application
"""

import os
import time
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from loader.deterministic_loader import boot_models, get_loaded_models
from app.router_intent import route, health_check
from router.voting import vote
from router.cost_tracking import debit, get_budget_status, get_cost_breakdown, downgrade_route

# Prometheus metrics
REQUEST_LATENCY = Histogram(
    "swarm_router_request_latency", 
    "Router request latency in seconds",
    buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5)
)

ROUTER_REQUESTS = Counter(
    "swarm_router_requests_total",
    "Total router requests"
)

# Pydantic models for API
class OrchestrateRequest(BaseModel):
    prompt: str
    route: List[str]

class OrchestrateResponse(BaseModel):
    text: str
    model_used: str
    latency_ms: float
    cost_cents: float

class VotingRequest(BaseModel):
    prompt: str
    candidates: List[str]
    top_k: int = 2

class VotingResponse(BaseModel):
    text: str
    winner: Dict[str, Any]
    all_candidates: List[Dict[str, Any]]
    voting_stats: Dict[str, Any]
    total_cost_cents: float

class BudgetResponse(BaseModel):
    budget_status: Dict[str, float]
    cost_breakdown: Dict[str, float]

# Global variable to track model loading status
model_loading_summary = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown"""
    global model_loading_summary
    
    # Startup
    echo("[STARTUP] SwarmAI FastAPI starting up...")
    profile = os.environ.get("SWARM_GPU_PROFILE", "rtx_4070")
    echo(f"[PROFILE] Using GPU profile: {profile}")
    
    try:
        model_loading_summary = boot_models(profile=profile)
        echo(f"[OK] Model loading complete: {model_loading_summary}")
    except Exception as e:
        echo(f"[ERROR] Model loading failed: {e}")
        model_loading_summary = {"error": str(e)}
    
    yield
    
    # Shutdown
    echo("[SHUTDOWN] SwarmAI FastAPI shutting down...")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="SwarmAI Router 2.0",
    description="Intelligent AI model routing, orchestration, and confidence-weighted voting with cost tracking",
    version="1.0.0",
    lifespan=lifespan
)

def echo(msg: str):
    print(time.strftime('%H:%M:%S'), msg, flush=True)

@app.post("/orchestrate", response_model=OrchestrateResponse)
async def orchestrate(request: OrchestrateRequest):
    """Route a prompt to specified model heads with cost tracking"""
    
    start_time = time.time()
    
    try:
        ROUTER_REQUESTS.inc()
        
        # Apply budget-aware routing
        cost_optimized_route = downgrade_route(request.route)
        if cost_optimized_route != request.route:
            echo(f"💰 Budget-aware routing: {request.route} -> {cost_optimized_route}")
        
        with REQUEST_LATENCY.time():
            result = await route(request.prompt, cost_optimized_route)
        
        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000
        
        # Determine which model was actually used (simplified)
        loaded_models = get_loaded_models()
        available_heads = [h for h in cost_optimized_route if h in loaded_models]
        model_used = available_heads[0] if available_heads else "unknown"
        
        # Track cost
        tokens = len(result.split())  # Simple token estimate
        cost_cents = debit(model_used, tokens)
        
        return OrchestrateResponse(
            text=result,
            model_used=model_used,
            latency_ms=latency_ms,
            cost_cents=cost_cents
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vote", response_model=VotingResponse)
async def vote_endpoint(request: VotingRequest):
    """Router 2.0: Confidence-weighted voting across multiple model heads with cost tracking"""
    
    start_time = time.time()
    
    try:
        ROUTER_REQUESTS.inc()
        
        # Apply budget-aware candidate selection
        cost_optimized_candidates = downgrade_route(request.candidates)
        if cost_optimized_candidates != request.candidates:
            echo(f"💰 Budget-aware voting: {request.candidates} -> {cost_optimized_candidates}")
        
        with REQUEST_LATENCY.time():
            result = await vote(request.prompt, cost_optimized_candidates, request.top_k)
        
        # Track costs for all candidates that responded
        total_cost_cents = 0.0
        for candidate in result["all_candidates"]:
            # Safely estimate tokens from response snippet
            response_text = candidate.get("response_snippet", "")
            if isinstance(response_text, str):
                tokens = len(response_text.split())
                cost = debit(candidate["model"], tokens)
                total_cost_cents += cost
        
        return VotingResponse(
            text=result["text"],
            winner=result["winner"],
            all_candidates=result["all_candidates"],
            voting_stats=result["voting_stats"],
            total_cost_cents=total_cost_cents
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/budget", response_model=BudgetResponse)
async def budget():
    """Get current budget status and cost breakdown"""
    try:
        return BudgetResponse(
            budget_status=get_budget_status(),
            cost_breakdown=get_cost_breakdown()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Budget check failed: {e}")

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        return await health_check()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.get("/models")
async def models():
    """Get currently loaded models"""
    try:
        loaded_models = get_loaded_models()
        
        models_info = {}
        for name, info in loaded_models.items():
            models_info[name] = {
                "backend": info.get("backend", "unknown"),
                "type": info.get("type", "unknown"),
                "vram_mb": info.get("vram_mb", 0),
                "loaded_at": info.get("loaded_at", 0)
            }
        
        return {
            "total_models": len(loaded_models),
            "loaded_models": models_info,  # Include this field for test compatibility
            "models": models_info,  # Keep this too for new API
            "loading_summary": model_loading_summary
        }
    except Exception as e:
        echo(f"❌ Models endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get models: {e}")

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 