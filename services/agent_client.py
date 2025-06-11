#!/usr/bin/env python3
"""
Agent Client - Direct VLLM Routing
Simple prompt → completion with no reasoning chains
"""

import os
import httpx
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

# Environment-driven configuration
VLLM_URL = os.getenv("VLLM_BASE_URL", "http://phi3mini:8000")
MODEL = os.getenv("VLLM_MODEL_NAME", "phi-3-mini-int4")
TIMEOUT = int(os.getenv("VLLM_TIMEOUT_SEC", "8"))

# Cloud fallback configuration
CLOUD_O3_URL = os.getenv("CLOUD_O3_URL", "https://api.openai.com/v1/chat/completions")
CLOUD_O3_API_KEY = os.getenv("CLOUD_O3_API_KEY", os.getenv("OPENAI_API_KEY", ""))

async def infer(prompt: str, temperature: float = 0.7) -> str:
    """
    Single-shot VLLM call – no extra chain, just prompt → completion.
    
    Args:
        prompt: Input text for the model
        temperature: Sampling temperature (0.0 = deterministic, 1.0 = creative)
        
    Returns:
        Generated text response
    """
    logger.info(f"🔗 VLLM direct call: {VLLM_URL} model={MODEL}")
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "temperature": temperature,
        "max_tokens": 512,
        "stream": False,
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(f"{VLLM_URL}/v1/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            result = data["choices"][0]["text"].strip()
            
            logger.info(f"✅ VLLM response: {len(result)} chars")
            return result
            
    except Exception as e:
        logger.error(f"❌ VLLM call failed: {e}")
        # Return a simple fallback instead of complex reasoning
        return f"VLLM service unavailable. Prompt was: {prompt[:50]}..."

async def infer_cloud_o3(prompt: str, temperature: float = 0.7) -> str:
    """
    Cloud O3 fallback - direct OpenAI API call
    """
    if not CLOUD_O3_API_KEY:
        return "Cloud O3 not configured"
        
    logger.info("☁️ Cloud O3 fallback")
    
    payload = {
        "model": "o1-preview",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 512
    }
    
    headers = {
        "Authorization": f"Bearer {CLOUD_O3_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(CLOUD_O3_URL, json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            result = data["choices"][0]["message"]["content"].strip()
            
            logger.info(f"✅ Cloud O3 response: {len(result)} chars")
            return result
            
    except Exception as e:
        logger.error(f"❌ Cloud O3 call failed: {e}")
        return f"Cloud service unavailable. Prompt was: {prompt[:50]}..."

# Agent-specific wrappers
async def phi3_infer(prompt: str) -> str:
    """Phi3 agent - direct VLLM call"""
    return await infer(prompt, temperature=0.5)

async def opus_infer(prompt: str) -> str:
    """Opus agent - creative temperature"""
    return await infer(prompt, temperature=0.8)

async def o3_infer(prompt: str) -> str:
    """O3 agent - cloud fallback"""
    return await infer_cloud_o3(prompt, temperature=0.3)

async def router_infer(prompt: str) -> str:
    """Router agent - balanced temperature"""
    return await infer(prompt, temperature=0.6) 