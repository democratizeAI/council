"""
OpenAI Provider
===============

Fallback LLM provider using OpenAI GPT models.
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
    """Call OpenAI API with automatic retry on failure"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        raise CloudRetry("No OpenAI API key configured", "openai")
    
    payload = {
        "model": kwargs.get("model", "gpt-3.5-turbo"),
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
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            ) as response:
                latency_ms = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    result = await response.json()
                    text = result['choices'][0]['message']['content']
                    
                    logger.info(f"✅ OpenAI API success: {latency_ms:.1f}ms")
                    
                    return {
                        "text": text,
                        "model": f"openai-{payload['model']}",
                        "skill_type": "agent0",
                        "confidence": 0.9,
                        "latency_ms": latency_ms,
                        "provider": "openai",
                        "timestamp": time.time()
                    }
                elif response.status == 429:
                    error_text = await response.text()
                    logger.warning(f"🚨 OpenAI rate limited: {response.status}")
                    raise CloudRetry(f"OpenAI rate limited: {response.status}", "openai", error_text)
                elif response.status == 402:
                    error_text = await response.text()
                    logger.warning(f"🚨 OpenAI quota exceeded: {response.status}")
                    raise CloudRetry(f"OpenAI quota exceeded: {response.status}", "openai", error_text)
                else:
                    error_text = await response.text()
                    logger.error(f"❌ OpenAI API error {response.status}: {error_text}")
                    raise CloudRetry(f"OpenAI API error: {response.status}", "openai", error_text)
                    
    except asyncio.TimeoutError:
        logger.error("⏰ OpenAI API timeout")
        raise CloudRetry("OpenAI API timeout", "openai")
    except Exception as e:
        logger.error(f"❌ OpenAI API error: {e}")
        raise CloudRetry(f"OpenAI API failed: {e}", "openai") 