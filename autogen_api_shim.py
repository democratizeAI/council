#!/usr/bin/env python3
"""
AutoGen API Shim - FastAPI Wrapper
==================================

Exposes our optimized AutoGen skills via HTTP API for Titanic Gauntlet testing.
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime

# Add AutoGen skills to path
sys.path.append('fork/swarm_autogen')

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Import our optimized AutoGen router
from router_cascade import route_and_execute

# Request/Response models
class HybridRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 150
    temperature: Optional[float] = 0.3
    model: Optional[str] = "autogen"  # Compatibility with Titanic Gauntlet

class HybridResponse(BaseModel):
    text: str
    model: str
    latency_ms: float
    skill_type: str
    confidence: float
    timestamp: str

# FastAPI app
app = FastAPI(
    title="AutoGen API Shim", 
    description="Production AutoGen skills API for benchmarking",
    version="2.3.0"
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "autogen-api-shim",
        "version": "2.3.0", 
        "timestamp": datetime.now().isoformat()
    }

# Main hybrid endpoint for Titanic Gauntlet
@app.post("/hybrid", response_model=HybridResponse)
async def hybrid_endpoint(req: HybridRequest):
    """
    Main hybrid endpoint that routes to AutoGen specialists
    Compatible with Titanic Gauntlet expectations
    """
    start_time = time.time()
    
    try:
        # Route to AutoGen specialists
        result = await route_and_execute(req.prompt)
        
        latency = (time.time() - start_time) * 1000
        
        # Extract response data
        answer = result.get("answer", "No answer generated")
        skill_type = result.get("skill_type", "unknown")
        confidence = result.get("confidence", 0.0)
        
        # Format response for Titanic Gauntlet
        return HybridResponse(
            text=answer,
            model=f"autogen-{skill_type}",
            latency_ms=latency,
            skill_type=skill_type,
            confidence=confidence,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        # Log error but return graceful failure
        latency = (time.time() - start_time) * 1000
        
        print(f"❌ AutoGen error: {e}")
        
        return HybridResponse(
            text=f"Error: {str(e)}",
            model="autogen-error",
            latency_ms=latency,
            skill_type="error",
            confidence=0.0,
            timestamp=datetime.now().isoformat()
        )

# Legacy endpoint for backward compatibility
@app.post("/generate")
async def generate_endpoint(req: HybridRequest):
    """Legacy generate endpoint - routes to hybrid"""
    return await hybrid_endpoint(req)

# Stats endpoint for monitoring
@app.get("/stats")
async def stats_endpoint():
    """Get API statistics"""
    return {
        "service": "autogen-api-shim",
        "skills": ["math", "code", "logic", "knowledge"],
        "gpu_available": True,
        "models_cached": True,
        "timestamp": datetime.now().isoformat()
    }

# Metrics endpoint for Grafana
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus-style metrics endpoint"""
    # Basic metrics for monitoring
    return """# HELP autogen_api_requests_total Total API requests
# TYPE autogen_api_requests_total counter
autogen_api_requests_total 0

# HELP autogen_api_latency_seconds API latency
# TYPE autogen_api_latency_seconds histogram
autogen_api_latency_seconds_bucket{le="0.1"} 0
autogen_api_latency_seconds_bucket{le="0.5"} 0
autogen_api_latency_seconds_bucket{le="1.0"} 0
autogen_api_latency_seconds_bucket{le="+Inf"} 0
"""

if __name__ == "__main__":
    print("🚀 Starting AutoGen API Shim")
    print("=" * 50)
    print("📡 Endpoints:")
    print("  POST /hybrid - Main AutoGen endpoint")
    print("  GET  /health - Health check")
    print("  GET  /stats  - Service statistics")
    print("  GET  /metrics - Prometheus metrics")
    print("=" * 50)
    print("🌐 Server starting on http://localhost:8000")
    
    # Start FastAPI server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    ) 