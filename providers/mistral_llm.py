"""
Mistral AI Provider
===================

High-performance, cost-effective LLM provider using Mistral Large.
"""

import os
import time
import asyncio
import aiohttp
import logging
from typing import Dict, Any
from . import CloudRetry

logger = logging.getLogger(__name__)

async def call(prompt: str, **kwargs) -> Dict[str, Any]:
    """Call Mistral API with automatic retry on failure"""
    api_key = os.getenv('MISTRAL_API_KEY')
    
    if not api_key:
        raise CloudRetry("No Mistral API key configured", "mistral")
    
    payload = {
        "model": kwargs.get("model", "mistral-large-latest"),
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": kwargs.get("max_tokens", 150),
        "temperature": kwargs.get("temperature", 0.7)
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.mistral.ai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    text = result['choices'][0]['message']['content']
                    
                    logger.info(f"✅ Mistral API success: {latency_ms:.1f}ms")
                    
                    return {
                        "text": text,
                        "model": "mistral-large-latest",
                        "skill_type": "agent0",
                        "confidence": 0.9,
                        "latency_ms": latency_ms,
                        "provider": "mistral",
                        "timestamp": time.time()
                    }
                elif response.status == 429:
                    error_text = await response.text()
                    logger.warning(f"🚨 Mistral rate limited: {response.status}")
                    raise CloudRetry(f"Mistral rate limited: {response.status}", "mistral", error_text)
                elif response.status == 402:
                    error_text = await response.text()
                    logger.warning(f"🚨 Mistral quota exceeded: {response.status}")
                    raise CloudRetry(f"Mistral quota exceeded: {response.status}", "mistral", error_text)
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Mistral API error {response.status}: {error_text}")
                    raise CloudRetry(f"Mistral API error: {response.status}", "mistral", error_text)
                    
    except asyncio.TimeoutError:
        logger.error("⏰ Mistral API timeout")
        raise CloudRetry("Mistral API timeout", "mistral")
    except Exception as e:
        logger.error(f"❌ Mistral API error: {e}")
        raise CloudRetry(f"Mistral API failed: {e}", "mistral") 