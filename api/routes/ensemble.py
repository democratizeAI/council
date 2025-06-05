from fastapi import APIRouter, HTTPException, Depends
from redis.asyncio import Redis
from typing import Dict, List, Optional
import os
import time
from ..metrics import ensemble_mappings_total, ensemble_cache_size, adapter_select_total
from lora.manager import get_cache_stats, warm_cache, clear_cache
from router.ensemble import choose_adapter, reload_weight_table, get_weight_stats, validate_weights

router = APIRouter(prefix="/admin", tags=["admin"])
r = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

@router.post("/ensemble")
async def set_mapping(cluster_id: str, adapter_tag: str):
    """Set cluster-to-adapter mapping (Redis-based, legacy)"""
    try:
        await r.hset("lora:router_map", cluster_id, adapter_tag)
        ensemble_mappings_total.inc()
        
        return {
            "cluster_id": cluster_id, 
            "adapter_tag": adapter_tag,
            "timestamp": time.time(),
            "status": "mapped"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set mapping: {e}")

@router.get("/ensemble")
async def get_mappings():
    """Get all cluster-to-adapter mappings"""
    try:
        mappings = await r.hgetall("lora:router_map")
        weight_stats = get_weight_stats()
        
        return {
            "redis_mappings": mappings,
            "total_redis_clusters": len(mappings),
            "weight_config": weight_stats,
            "cache_stats": get_cache_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get mappings: {e}")

@router.post("/ensemble/reload")
async def reload_config():
    """Hot-reload adapter weight configuration without restart"""
    try:
        success = reload_weight_table()
        if success:
            return {
                "status": "reloaded",
                "timestamp": time.time(),
                "message": "Weight table reloaded successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reload weight table")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {e}")

@router.get("/ensemble/weights")
async def get_weight_config():
    """Get current weight configuration and statistics"""
    try:
        stats = get_weight_stats()
        validation = validate_weights()
        
        return {
            "weight_stats": stats,
            "validation": validation,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get weight config: {e}")

@router.post("/ensemble/test")
async def test_adapter_selection(cluster_id: str, iterations: int = 100):
    """Test weighted adapter selection for a specific cluster"""
    try:
        if iterations < 1 or iterations > 1000:
            raise HTTPException(status_code=400, detail="Iterations must be between 1 and 1000")
        
        selections = {}
        for _ in range(iterations):
            adapter = choose_adapter(cluster_id)
            selections[adapter] = selections.get(adapter, 0) + 1
        
        # Convert to percentages
        percentages = {
            adapter: (count / iterations) * 100 
            for adapter, count in selections.items()
        }
        
        return {
            "cluster_id": cluster_id,
            "iterations": iterations,
            "selections": selections,
            "percentages": percentages,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {e}")

@router.delete("/ensemble/{cluster_id}")
async def remove_mapping(cluster_id: str):
    """Remove cluster-to-adapter mapping (Redis-based)"""
    try:
        result = await r.hdel("lora:router_map", cluster_id)
        if result == 0:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
        
        return {
            "cluster_id": cluster_id,
            "status": "unmapped",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove mapping: {e}")

@router.post("/ensemble/bulk")
async def set_bulk_mappings(mappings: Dict[str, str]):
    """Set multiple cluster-to-adapter mappings at once (Redis-based)"""
    try:
        if not mappings:
            raise HTTPException(status_code=400, detail="No mappings provided")
        
        # Use Redis pipeline for efficiency
        async with r.pipeline() as pipe:
            for cluster_id, adapter_tag in mappings.items():
                await pipe.hset("lora:router_map", cluster_id, adapter_tag)
            await pipe.execute()
        
        ensemble_mappings_total.inc(len(mappings))
        
        return {
            "mappings_set": len(mappings),
            "clusters": list(mappings.keys()),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set bulk mappings: {e}")

@router.get("/ensemble/stats")
async def get_ensemble_stats():
    """Get comprehensive ensemble system statistics"""
    try:
        redis_mappings = await r.hgetall("lora:router_map")
        cache_stats = get_cache_stats()
        weight_stats = get_weight_stats()
        validation = validate_weights()
        
        # Count Redis adapter usage
        redis_adapter_usage = {}
        for adapter_tag in redis_mappings.values():
            redis_adapter_usage[adapter_tag] = redis_adapter_usage.get(adapter_tag, 0) + 1
        
        return {
            "redis_stats": {
                "total_mappings": len(redis_mappings),
                "unique_adapters": len(set(redis_mappings.values())),
                "adapter_usage": redis_adapter_usage,
                "most_used_adapter": max(redis_adapter_usage.items(), key=lambda x: x[1]) if redis_adapter_usage else None
            },
            "weight_config": weight_stats,
            "config_validation": validation,
            "cache_stats": cache_stats,
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")

@router.post("/ensemble/cache/warm")
async def warm_adapter_cache(adapter_tags: List[str]):
    """Pre-load adapters into cache"""
    try:
        warm_cache(adapter_tags)
        return {
            "warmed_adapters": adapter_tags,
            "cache_stats": get_cache_stats(),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to warm cache: {e}")

@router.post("/ensemble/cache/clear")
async def clear_adapter_cache():
    """Clear all cached adapters"""
    try:
        clear_cache()
        return {
            "status": "cache_cleared",
            "cache_stats": get_cache_stats(),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {e}")

@router.get("/ensemble/cluster/{cluster_id}")
async def get_cluster_mapping(cluster_id: str):
    """Get adapter mapping for specific cluster (checks both Redis and weights)"""
    try:
        # Check Redis first (legacy)
        redis_adapter = await r.hget("lora:router_map", cluster_id)
        
        # Test weighted selection
        weighted_adapter = choose_adapter(cluster_id)
        
        return {
            "cluster_id": cluster_id,
            "redis_mapping": redis_adapter,
            "weighted_selection": weighted_adapter,
            "redis_is_cached": redis_adapter in get_cache_stats()["loaded_adapters"] if redis_adapter else False,
            "weighted_is_cached": weighted_adapter in get_cache_stats()["loaded_adapters"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster mapping: {e}") 