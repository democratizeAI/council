#!/usr/bin/env python3
"""
Shallow Cache Layer for Cost Reduction
=====================================

SHA256-based prompt caching to eliminate duplicate cloud model calls.
This can save 30-40% of costs by caching high-confidence Agent-0 responses.
"""

import hashlib
import redis
import json
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 86400  # 1 day cache TTL
CONFIDENCE_THRESHOLD = 0.80  # Only cache high-confidence responses
MAX_PROMPT_LENGTH = 2048   # Don't cache extremely long prompts

@dataclass
class CachedResponse:
    """Structured cached response"""
    text: str
    confidence: float
    model_used: str
    timestamp: float
    cost_saved_usd: float = 0.0

try:
    # Connect to Redis for caching
    REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
    REDIS_CLIENT.ping()  # Test connection
    REDIS_AVAILABLE = True
    logger.info("💰 Redis cache connected for cost savings")
except Exception as e:
    # Fallback to in-memory cache
    REDIS_CLIENT = None
    REDIS_AVAILABLE = False
    MEMORY_CACHE = {}
    logger.warning(f"💰 Redis unavailable, using memory cache: {e}")

def get_cache_key(prompt: str) -> str:
    """
    Generate SHA256 cache key for prompt.
    
    Args:
        prompt: User prompt to hash
        
    Returns:
        SHA256 hex digest as cache key
    """
    # Normalize prompt: strip whitespace, lowercase for consistent caching
    normalized = prompt.strip().lower()
    
    # Generate SHA256 hash
    key = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    return f"cache:prompt:{key}"

def get_cached_response(prompt: str) -> Optional[CachedResponse]:
    """
    Retrieve cached response for prompt if available.
    
    Args:
        prompt: User prompt to check
        
    Returns:
        CachedResponse if found, None otherwise
    """
    # Skip caching for very long prompts (likely complex/unique)
    if len(prompt) > MAX_PROMPT_LENGTH:
        return None
        
    cache_key = get_cache_key(prompt)
    
    try:
        if REDIS_AVAILABLE:
            # Redis-based cache
            cached_data = REDIS_CLIENT.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"💰 Cache HIT: {prompt[:50]}... (saved ${data.get('cost_saved_usd', 0):.4f})")
                return CachedResponse(**data)
        else:
            # Memory-based fallback cache
            if cache_key in MEMORY_CACHE:
                data = MEMORY_CACHE[cache_key]
                # Check TTL for memory cache
                if time.time() - data['timestamp'] < CACHE_TTL_SECONDS:
                    logger.info(f"💰 Memory Cache HIT: {prompt[:50]}...")
                    return CachedResponse(**data)
                else:
                    # Expired - remove from memory cache
                    del MEMORY_CACHE[cache_key]
                    
    except Exception as e:
        logger.debug(f"💰 Cache read error: {e}")
        
    return None

def store_cached_response(prompt: str, response: Dict[str, Any], cost_saved_usd: float = 0.0) -> bool:
    """
    Store response in cache if it meets quality criteria.
    
    Args:
        prompt: User prompt
        response: Model response with text, confidence, etc.
        cost_saved_usd: Estimated cost savings from caching
        
    Returns:
        True if cached, False if not cached
    """
    # Skip caching for very long prompts
    if len(prompt) > MAX_PROMPT_LENGTH:
        return False
        
    confidence = response.get('confidence', 0.0)
    text = response.get('text', '')
    
    # Only cache high-confidence responses
    if confidence < CONFIDENCE_THRESHOLD:
        logger.debug(f"💰 Not caching low confidence response: {confidence:.2f} < {CONFIDENCE_THRESHOLD}")
        return False
        
    # Don't cache empty or very short responses
    if len(text.strip()) < 10:
        logger.debug(f"💰 Not caching short response: {len(text)} chars")
        return False
        
    # Don't cache error responses
    if any(error_phrase in text.lower() for error_phrase in ['error', 'failed', 'unable to']):
        logger.debug(f"💰 Not caching error response")
        return False
        
    cache_key = get_cache_key(prompt)
    
    cached_response = CachedResponse(
        text=text,
        confidence=confidence,
        model_used=response.get('model', 'unknown'),
        timestamp=time.time(),
        cost_saved_usd=cost_saved_usd
    )
    
    try:
        if REDIS_AVAILABLE:
            # Redis-based cache with TTL
            REDIS_CLIENT.setex(
                cache_key, 
                CACHE_TTL_SECONDS, 
                json.dumps(cached_response.__dict__)
            )
            logger.info(f"💰 Cached high-confidence response: {prompt[:30]}... (conf={confidence:.2f})")
        else:
            # Memory-based fallback cache
            MEMORY_CACHE[cache_key] = cached_response.__dict__
            logger.info(f"💰 Memory cached response: {prompt[:30]}... (conf={confidence:.2f})")
            
        return True
        
    except Exception as e:
        logger.debug(f"💰 Cache store error: {e}")
        return False

def estimate_cost_savings(model_used: str, response_length: int) -> float:
    """
    Estimate cost savings from caching this response.
    
    Args:
        model_used: Name of model that generated response
        response_length: Length of response text
        
    Returns:
        Estimated cost savings in USD
    """
    # Simple cost estimation based on model and response length
    cost_per_token = {
        'gpt-4': 0.00003,        # $0.03/1K tokens
        'gpt-3.5-turbo': 0.000002,  # $0.002/1K tokens  
        'mistral-large': 0.000012,  # $0.012/1K tokens
        'claude-3': 0.000015,   # $0.015/1K tokens
        'agent0': 0.0,          # Local model - no cost
        'local': 0.0            # Local model - no cost
    }
    
    # Rough token estimation (4 chars per token)
    estimated_tokens = response_length / 4
    
    # Get cost per token for this model
    token_cost = cost_per_token.get(model_used, 0.000005)  # Default modest cost
    
    # Estimate savings (input + output cost)
    savings = estimated_tokens * token_cost * 2  # 2x for input+output
    
    return max(savings, 0.0001)  # Minimum savings of $0.0001

def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring.
    
    Returns:
        Dictionary with cache stats
    """
    stats = {
        'cache_type': 'redis' if REDIS_AVAILABLE else 'memory',
        'available': REDIS_AVAILABLE or len(MEMORY_CACHE) >= 0
    }
    
    try:
        if REDIS_AVAILABLE:
            info = REDIS_CLIENT.info('memory')
            stats.update({
                'entries': REDIS_CLIENT.dbsize(),
                'memory_usage_mb': info.get('used_memory', 0) / (1024 * 1024),
                'hit_rate': 'unknown'  # Would need separate tracking
            })
        else:
            stats.update({
                'entries': len(MEMORY_CACHE),
                'memory_usage_mb': 0,  # Memory cache size estimation
                'hit_rate': 'unknown'
            })
            
    except Exception as e:
        logger.debug(f"💰 Cache stats error: {e}")
        stats['error'] = str(e)
        
    return stats

def clear_cache() -> bool:
    """
    Clear all cached responses (for testing/cleanup).
    
    Returns:
        True if cleared successfully
    """
    try:
        if REDIS_AVAILABLE:
            REDIS_CLIENT.flushdb()
            logger.info("💰 Redis cache cleared")
        else:
            MEMORY_CACHE.clear()
            logger.info("💰 Memory cache cleared")
            
        return True
        
    except Exception as e:
        logger.error(f"💰 Cache clear error: {e}")
        return False

# Test the cache system
if __name__ == "__main__":
    # Simple test
    test_prompt = "What is 2+2?"
    test_response = {
        'text': "2+2 equals 4",
        'confidence': 0.95,
        'model': 'test-model'
    }
    
    print("🧪 Testing shallow cache...")
    
    # Test store
    stored = store_cached_response(test_prompt, test_response, cost_saved_usd=0.001)
    print(f"✅ Stored: {stored}")
    
    # Test retrieve
    cached = get_cached_response(test_prompt)
    print(f"✅ Retrieved: {cached}")
    
    # Test stats
    stats = get_cache_stats()
    print(f"📊 Stats: {stats}")
    
    print("🧪 Shallow cache test complete!") 