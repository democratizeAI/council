# Router 2.0 - Advanced AI model routing and orchestration 

"""
Router module for AutoGen Council
Provides health checking and initialization validation
"""

import os
import time
import logging
import asyncio
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)

LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://localhost:8000/v1")
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))
HEALTH_CHECK_RETRIES = int(os.getenv("HEALTH_CHECK_RETRIES", "3"))

class HealthCheckError(Exception):
    """Raised when health checks fail"""
    pass

async def check_llm_health() -> bool:
    """
    Check if LLM endpoint is healthy and responsive
    
    Returns:
        bool: True if healthy, False otherwise
        
    Raises:
        HealthCheckError: If health check fails after retries
    """
    for attempt in range(HEALTH_CHECK_RETRIES):
        try:
            async with aiohttp.ClientSession() as session:
                # Check models endpoint
                async with session.get(
                    f"{LLM_ENDPOINT}/models", 
                    timeout=HEALTH_CHECK_TIMEOUT
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        logger.info(f"✅ LLM health check passed on attempt {attempt + 1}")
                        logger.info(f"Available models: {[m.get('id') for m in models_data.get('data', [])]}")
                        return True
                    else:
                        logger.warning(f"⚠️ LLM endpoint returned {response.status} on attempt {attempt + 1}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ LLM health check timeout on attempt {attempt + 1}")
        except Exception as e:
            logger.warning(f"⚠️ LLM health check error on attempt {attempt + 1}: {e}")
        
        if attempt < HEALTH_CHECK_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    raise HealthCheckError(f"LLM endpoint unhealthy after {HEALTH_CHECK_RETRIES} attempts")

def check_llm_sync() -> bool:
    """
    Synchronous wrapper for LLM health check
    Used for startup validation
    """
    try:
        import requests
        
        for attempt in range(HEALTH_CHECK_RETRIES):
            try:
                response = requests.get(f"{LLM_ENDPOINT}/models", timeout=HEALTH_CHECK_TIMEOUT)
                response.raise_for_status()
                
                models_data = response.json()
                logger.info(f"✅ LLM sync health check passed on attempt {attempt + 1}")
                logger.info(f"Available models: {[m.get('id') for m in models_data.get('data', [])]}")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ LLM sync health check error on attempt {attempt + 1}: {e}")
                if attempt < HEALTH_CHECK_RETRIES - 1:
                    time.sleep(2 ** attempt)
        
        raise HealthCheckError(f"LLM endpoint unhealthy after {HEALTH_CHECK_RETRIES} attempts")
        
    except ImportError:
        logger.warning("⚠️ requests not available, skipping sync health check")
        return False

# Optional startup health check
# Only run if explicitly enabled to avoid blocking imports
if os.getenv("ROUTER_STARTUP_HEALTH_CHECK", "false").lower() == "true":
    logger.info("🔍 Running startup health check...")
    try:
        check_llm_sync()
        logger.info("🟢 Startup health check passed")
    except HealthCheckError as e:
        logger.error(f"🔴 Startup health check failed: {e}")
        # Don't raise here to allow graceful degradation
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error in startup health check: {e}")

logger.info(f"📡 Router module initialized, LLM endpoint: {LLM_ENDPOINT}") 