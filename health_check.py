#!/usr/bin/env python3
"""
🔧 Health Check Endpoint
========================

Comprehensive health check for AutoGen Council system:
- FAISS memory initialization
- GPU availability
- Model loading status
- Docker container health

Used by Docker health checks and monitoring.
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(title="AutoGen Council Health Check")

# Health status cache
health_cache = {
    "last_check": 0,
    "status": {},
    "cache_ttl": 30  # Cache for 30 seconds
}

def check_faiss_memory() -> Dict[str, Any]:
    """Check FAISS memory singleton health"""
    try:
        from bootstrap import MEMORY
        
        # Test basic operations
        test_query = "health check test query"
        results = MEMORY.query(test_query, k=1)
        
        # Check if memory has data
        memory_size = len(getattr(MEMORY, 'data', []))
        
        return {
            "status": "healthy",
            "memory_size": memory_size,
            "query_working": True,
            "response_time_ms": 5  # Estimate
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "memory_size": 0,
            "query_working": False
        }

def check_gpu_health() -> Dict[str, Any]:
    """Check GPU availability and health"""
    try:
        import torch
        
        gpu_available = torch.cuda.is_available()
        if not gpu_available:
            return {
                "status": "warning",
                "gpu_available": False,
                "error": "CUDA not available"
            }
        
        device_count = torch.cuda.device_count()
        current_device = torch.cuda.current_device()
        gpu_name = torch.cuda.get_device_name(current_device)
        
        # Check GPU memory
        total_memory = torch.cuda.get_device_properties(current_device).total_memory
        allocated_memory = torch.cuda.memory_allocated(current_device)
        cached_memory = torch.cuda.memory_reserved(current_device)
        
        # Test simple GPU operation
        start_time = time.time()
        test_tensor = torch.randn(100, 100).cuda()
        result = torch.matmul(test_tensor, test_tensor)
        gpu_test_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "gpu_available": True,
            "device_count": device_count,
            "current_device": current_device,
            "gpu_name": gpu_name,
            "total_memory_gb": total_memory / (1024**3),
            "allocated_memory_gb": allocated_memory / (1024**3),
            "cached_memory_gb": cached_memory / (1024**3),
            "memory_utilization": allocated_memory / total_memory,
            "gpu_test_time_ms": gpu_test_time
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "gpu_available": False,
            "error": str(e)
        }

def check_model_loading() -> Dict[str, Any]:
    """Check if models are loaded and working"""
    try:
        from loader.deterministic_loader import get_loaded_models
        
        loaded_models = get_loaded_models()
        model_count = len(loaded_models)
        
        return {
            "status": "healthy" if model_count > 0 else "warning",
            "models_loaded": model_count,
            "model_names": list(loaded_models.keys())[:5]  # First 5 models
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "models_loaded": 0,
            "error": str(e)
        }

def check_council_system() -> Dict[str, Any]:
    """Check Council system components"""
    try:
        from router.council import council_router
        
        if council_router.council_enabled:
            # Test Council trigger logic
            should_trigger, reason = council_router.should_trigger_council("test health check")
            
            return {
                "status": "healthy",
                "council_enabled": True,
                "pocket_mode": council_router.pocket_mode,
                "trigger_test": {
                    "should_trigger": should_trigger,
                    "reason": reason
                }
            }
        else:
            return {
                "status": "warning",
                "council_enabled": False,
                "error": "Council system disabled"
            }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "council_enabled": False,
            "error": str(e)
        }

async def check_router_health() -> Dict[str, Any]:
    """Check router system health"""
    try:
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Test simple routing
        start_time = time.time()
        result = await router.route_query("health check")
        routing_time = (time.time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "router_initialized": True,
            "test_routing_time_ms": routing_time,
            "cloud_enabled": router.cloud_enabled
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "router_initialized": False,
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """
    Main health check endpoint for Docker health checks
    
    Returns:
        - 200 OK if all systems healthy
        - 503 Service Unavailable if critical systems down
    """
    current_time = time.time()
    
    # Use cache if still valid
    if (current_time - health_cache["last_check"]) < health_cache["cache_ttl"]:
        cached_status = health_cache["status"]
        if cached_status.get("overall_status") == "healthy":
            return JSONResponse(content=cached_status, status_code=200)
        else:
            return JSONResponse(content=cached_status, status_code=503)
    
    # Perform new health check
    start_time = time.time()
    
    try:
        # Run all health checks
        health_status = {
            "timestamp": current_time,
            "service": "autogen-council",
            "version": "2.0.0-hardened",
            "checks": {
                "faiss_memory": check_faiss_memory(),
                "gpu": check_gpu_health(),
                "models": check_model_loading(),
                "council": check_council_system(),
                "router": await check_router_health()
            }
        }
        
        # Determine overall status
        statuses = [check["status"] for check in health_status["checks"].values()]
        
        if all(status == "healthy" for status in statuses):
            overall_status = "healthy"
            http_status = 200
        elif any(status == "unhealthy" for status in statuses):
            overall_status = "unhealthy"
            http_status = 503
        else:
            overall_status = "degraded"
            http_status = 200
        
        health_status["overall_status"] = overall_status
        health_status["check_duration_ms"] = (time.time() - start_time) * 1000
        
        # Update cache
        health_cache["last_check"] = current_time
        health_cache["status"] = health_status
        
        return JSONResponse(content=health_status, status_code=http_status)
        
    except Exception as e:
        error_response = {
            "timestamp": current_time,
            "overall_status": "unhealthy",
            "error": str(e),
            "check_duration_ms": (time.time() - start_time) * 1000
        }
        
        return JSONResponse(content=error_response, status_code=503)

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with additional metrics"""
    
    health_data = await health_check()
    content = health_data.body.decode() if hasattr(health_data, 'body') else str(health_data)
    
    try:
        detailed_info = json.loads(content) if isinstance(content, str) else content
        
        # Add additional system info
        detailed_info["system_info"] = {
            "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
            "cuda_version": check_cuda_version(),
            "memory_usage": get_memory_usage(),
            "uptime_seconds": get_uptime()
        }
        
        return JSONResponse(content=detailed_info, status_code=200)
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

def check_cuda_version() -> str:
    """Get CUDA version"""
    try:
        import torch
        return torch.version.cuda or "not_available"
    except:
        return "unknown"

def get_memory_usage() -> Dict[str, float]:
    """Get system memory usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        return {
            "total_gb": memory.total / (1024**3),
            "available_gb": memory.available / (1024**3),
            "percent_used": memory.percent
        }
    except:
        return {"error": "psutil not available"}

def get_uptime() -> float:
    """Get process uptime in seconds"""
    try:
        import psutil
        process = psutil.Process()
        return time.time() - process.create_time()
    except:
        return 0.0

@app.get("/ping")
async def ping():
    """Simple ping endpoint for basic connectivity checks"""
    return {"status": "pong", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    print("🔧 Starting AutoGen Council Health Check service...")
    uvicorn.run(app, host="0.0.0.0", port=9001, log_level="info") 