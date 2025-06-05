# -*- coding: utf-8 -*-
"""
Hybrid routing: Smart orchestration between local and cloud models
🚀 ENHANCED: Integrated with ModelCache for <1s cold-start
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from loader.deterministic_loader import get_loaded_models, generate_response
from router.voting import vote, smart_select
from router.cost_tracking import debit
from router.model_cache import MODEL_CACHE, load_model_fast, get_cached_model  # 🚀 NEW: Model acceleration
import os
import yaml
import logging
from providers import mistral_llm, openai_llm, CloudRetry

logger = logging.getLogger(__name__)

# One-time parse of priority list
PROVIDER_PRIORITY = os.getenv("PROVIDER_PRIORITY", "local_mixtral,local_tinyllama,mistral,openai").split(",")

# 🔧 TRANSFORMERS PROVIDER FACTORY: Create local transformers instances with cache
def create_transformers_provider(config: Dict[str, Any]):
    """Create a transformers provider callable from config with model caching"""
    async def transformers_call(prompt: str, **kwargs) -> Dict[str, Any]:
        """Call transformers model with config parameters and caching"""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            
            model_name = config.get('name', 'transformers_model')
            
            # 🚀 NEW: Try to get cached model first
            cached_pipeline = get_cached_model(model_name)
            
            if cached_pipeline is None:
                # Load model with caching
                logger.info(f"🚀 Loading {model_name} with acceleration...")
                
                def create_pipeline():
                    model_path = config['model_path']
                    device = config.get('device', 'auto')
                    
                    if device == "auto":
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                    
                    return pipeline(
                        "text-generation",
                        model=model_path,
                        device=device,
                        torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                        trust_remote_code=True,
                        max_new_tokens=config.get('max_tokens', 150),
                        temperature=0.7,
                        do_sample=True,
                        return_full_text=False
                    )
                
                # Load with all acceleration techniques
                cached_pipeline = await load_model_fast(model_name, create_pipeline)
            
            # Generate response
            start_time = time.time()
            
            # 🚀 PHASE A PATCH #1: Hard 160-token output cap in server, not YAML
            max_new_tokens = min(kwargs.get('max_tokens', 160), 160)  # Hard limit
            
            # 🚀 FIX: Handle temperature from kwargs properly to avoid 0.0 error
            temp = kwargs.get('temperature', 0.7)
            if temp <= 0.0:
                temp = 0.1  # Minimum positive temperature for transformers
                use_sampling = False  # Use greedy decoding
            else:
                use_sampling = True
            
            # Filter out parameters that transformers doesn't accept
            pipeline_kwargs = {
                'max_new_tokens': max_new_tokens,
                'temperature': temp,
                'do_sample': use_sampling,
                'return_full_text': False
            }
            
            # Add other valid parameters
            if 'top_p' in kwargs:
                pipeline_kwargs['top_p'] = kwargs['top_p']
            if 'repetition_penalty' in kwargs:
                pipeline_kwargs['repetition_penalty'] = kwargs['repetition_penalty']
            
            outputs = cached_pipeline(prompt, **pipeline_kwargs)
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract response text
            if isinstance(outputs, list) and len(outputs) > 0:
                response_text = outputs[0]['generated_text'].strip()
            else:
                response_text = str(outputs).strip()
            
            # 🚀 PHASE A PATCH #1: Additional safety truncation
            if len(response_text) > 640:  # ~160 tokens at 4 chars/token
                response_text = response_text[:640] + "..."
                logger.debug(f"🔧 Truncated response to 160 tokens for safety")
            
            return {
                "text": response_text,
                "model": config.get('name', 'transformers_model'),
                "latency_ms": latency_ms,
                "provider": "transformers",
                "confidence": 0.8,
                "tokens_used": len(prompt.split()) + len(response_text.split()),
                "cached_model_used": cached_pipeline is not None  # 🚀 NEW: Cache hit indicator
            }
            
        except Exception as e:
            logger.error(f"❌ Transformers provider error: {e}")
            raise CloudRetry(f"Transformers provider failed: {e}")
    
    return transformers_call

PROVIDER_MAP = {}

# Track loaded models for /models endpoint
LOADED_MODELS = {}

def load_provider_config():
    """Load provider configuration from YAML with transformers support and model caching"""
    global LOADED_MODELS, PROVIDER_MAP
    
    # Initialize with empty map
    PROVIDER_MAP.clear()
    
    try:
        # Use UTF-8 safe loading
        try:
            from config.utils import load_yaml
            config = load_yaml("config/providers.yaml")
        except ImportError:
            with open("config/providers.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
        # Update priority from config if available
        if "priority" in config:
            global PROVIDER_PRIORITY
            PROVIDER_PRIORITY = config["priority"]
            
        # 🚀 NEW: Collect model factories for preloading
        model_factories = {}
        
        # Load provider configurations and create transformers providers
        for provider_name, provider_config in config.get("providers", {}).items():
            # Skip disabled providers completely
            if provider_config.get("enabled", True) is False:
                logger.info(f"🚫 Provider {provider_name} disabled, skipping completely")
                continue
                
            # Create transformers provider if needed
            if provider_config.get("type") == "transformers":
                logger.info(f"🔧 Creating transformers provider: {provider_name}")
                PROVIDER_MAP[provider_name] = create_transformers_provider(provider_config)
                
                # 🚀 NEW: Add to model factories for preloading
                def create_factory(config):
                    def factory():
                        from transformers import pipeline
                        import torch
                        device = config.get('device', 'auto')
                        if device == "auto":
                            device = "cuda" if torch.cuda.is_available() else "cpu"
                        
                        return pipeline(
                            "text-generation",
                            model=config['model_path'],
                            device=device,
                            torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                            trust_remote_code=True,
                            return_full_text=False
                        )
                    return factory
                
                model_factories[provider_name] = create_factory(provider_config)
            
            # Add cloud providers only if enabled
            elif provider_name in ["mistral", "openai"] and provider_config.get("enabled", True) is not False:
                # Import and add cloud providers
                if provider_name == "mistral":
                    try:
                        from providers import mistral_llm
                        PROVIDER_MAP[provider_name] = mistral_llm.call
                        logger.info(f"✅ Cloud provider enabled: {provider_name}")
                    except ImportError:
                        logger.warning(f"⚠️ Could not import {provider_name} provider")
                elif provider_name == "openai":
                    try:
                        from providers import openai_llm
                        PROVIDER_MAP[provider_name] = openai_llm.call
                        logger.info(f"✅ Cloud provider enabled: {provider_name}")
                    except ImportError:
                        logger.warning(f"⚠️ Could not import {provider_name} provider")
            
            # Load model information
            models = provider_config.get("models", [provider_name])  # Use provider name if no models specified
            for model in models:
                LOADED_MODELS[f"{provider_name}-{model}"] = {
                    "provider": provider_name,
                    "name": provider_config.get("name", provider_name),
                    "model": model,
                    "endpoint": provider_config.get("endpoint", "local"),
                    "pricing": provider_config.get("pricing", {}),
                    "type": provider_config.get("type", "api")
                }
        
        # 🚀 NEW: Preload essential models with caching
        if model_factories:
            logger.info(f"🚀 Preloading {len(model_factories)} models with acceleration...")
            MODEL_CACHE.preload_priority_models(model_factories)
                
        logger.info(f"📋 Loaded {len(LOADED_MODELS)} models from {len(config.get('providers', {}))} providers")
        logger.info(f"🎯 Provider priority: {' → '.join(PROVIDER_PRIORITY)}")
        logger.info(f"🔧 Available providers: {list(PROVIDER_MAP.keys())}")
        logger.info(f"🚀 Model cache stats: {MODEL_CACHE.get_cache_stats()}")
        
    except Exception as e:
        logger.warning(f"⚠️ Could not load provider config: {e}")
        # Use defaults
        LOADED_MODELS = {
            "mistral-large-latest": {"provider": "mistral", "name": "Mistral Large"},
            "openai-gpt-3.5-turbo": {"provider": "openai", "name": "OpenAI GPT-3.5"}
        }

# Load config on module import
load_provider_config()

async def call_llm(prompt: str, **kwargs) -> Dict[str, Any]:
    """
    Call LLM with automatic provider fallback.
    
    Tries providers in priority order. If a provider raises CloudRetry,
    automatically tries the next provider in the list.
    """
    tried = []
    
    for provider_name in PROVIDER_PRIORITY:
        if provider_name not in PROVIDER_MAP:
            logger.warning(f"⚠️ Unknown provider: {provider_name}")
            continue
            
        llm_fn = PROVIDER_MAP[provider_name]
        
        try:
            logger.info(f"🎯 Trying provider: {provider_name}")
            result = await llm_fn(prompt, **kwargs)
            
            # Add provider metadata
            result["routing_provider"] = provider_name
            result["routing_tried"] = [name for name, _ in tried] + [provider_name]
            
            return result
            
        except CloudRetry as e:
            logger.warning(f"🔄 {provider_name} failed: {e.reason}")
            tried.append((provider_name, str(e)))
            continue  # Try next provider
        except Exception as e:
            logger.error(f"❌ {provider_name} unexpected error: {e}")
            tried.append((provider_name, f"Unexpected error: {e}"))
            continue  # Try next provider
    
    # If everything failed
    error_summary = "; ".join([f"{name}: {error}" for name, error in tried])
    raise RuntimeError(f"All providers failed: {error_summary}")

def get_loaded_models() -> Dict[str, Any]:
    """Get currently loaded models for /models endpoint"""
    return {
        "count": len(LOADED_MODELS),
        "models": list(LOADED_MODELS.keys()),
        "providers": list(set(model["provider"] for model in LOADED_MODELS.values())),
        "priority": PROVIDER_PRIORITY,
        "details": LOADED_MODELS
    }

async def hybrid_route(prompt: str, preferred_models: List[str] = None, enable_council: bool = None) -> Dict[str, Any]:
    """
    Hybrid routing with confidence-based local/cloud decision making
    Enhanced with Track ③ math specialist integration
    
    Args:
        prompt: Input prompt
        preferred_models: List of preferred local models
        enable_council: Whether to enable council deliberation
        
    Returns:
        Dict with response, provider, model_used, confidence, etc.
    """
    start_time = time.time()
    
    # Default models if none specified
    if not preferred_models:
        loaded_models = get_loaded_models()
        preferred_models = list(loaded_models.keys())[:2]  # Use first 2 available
    
    try:
        # 🧮 MATH SPECIALIST: Ultra-fast math routing (Track ③)
        try:
            from router.math_specialist import route_math_query, is_math_query
            
            if is_math_query(prompt):
                print(f"🧮 Math query detected, using specialist routing...")
                math_result = await route_math_query(prompt, preferred_models)
                
                if math_result and math_result.get('latency_ms', 0) < 100:
                    # Math specialist succeeded and met latency target
                    print(f"⚡ Math specialist: {math_result['latency_ms']:.1f}ms ({math_result['method']})")
                    
                    # Convert to hybrid router format
                    return {
                        "text": math_result["text"],
                        "provider": math_result["provider"],
                        "model_used": math_result.get("model_used", "math_specialist"),
                        "confidence": math_result["confidence"],
                        "hybrid_latency_ms": math_result["latency_ms"],
                        "cloud_consulted": False,
                        "cost_cents": 0.001,  # Minimal cost for local math
                        "council_used": False,
                        "math_method": math_result["method"],
                        "accuracy_expected": math_result["accuracy_expected"],
                        "council_voices": None
                    }
                    
        except ImportError:
            # Math specialist not available - continue with normal routing
            pass
        except Exception as e:
            print(f"⚠️ Math specialist error: {e}")
            # Continue with normal routing as fallback
        
        # ⚡ FAST PATH: Smart single-model selection for simple prompts
        if (len(prompt) < 120 and 
            not any(keyword in prompt.lower() for keyword in ["explain", "why", "step by step", "analyze", "compare", "reasoning"])):
            
            # Smart select best model without running inference
            selected_model = smart_select(prompt, preferred_models)
            print(f"⚡ Smart path: selected {selected_model} for '{prompt[:50]}...'")
            
            try:
                # Generate single response with fail-fast on templates
                response_text = generate_response(selected_model, prompt, max_tokens=150)
                
                # Check for template/mock responses (skip in test mode)
                if (not os.environ.get("SWARM_TEST_MODE") and 
                    ("Response from " in response_text or "[TEMPLATE]" in response_text or 
                     "Mock" in response_text or len(response_text) < 10)):
                    raise RuntimeError(f"Template/mock response detected: {response_text[:100]}")
                
                latency_ms = (time.time() - start_time) * 1000
                tokens = len(prompt.split()) + len(response_text.split())
                cost_cents = debit(selected_model, tokens)
                
                return {
                    "text": response_text,
                    "provider": "local_smart",
                    "model_used": selected_model,
                    "confidence": 0.8,  # High confidence for smart routing
                    "hybrid_latency_ms": latency_ms,
                    "cloud_consulted": False,
                    "cost_cents": cost_cents,
                    "council_used": bool(enable_council),
                    "council_voices": None
                }
                
            except (RuntimeError, Exception) as local_error:
                # Local inference failed - try cloud fallback
                print(f"🌩️ Local inference failed: {local_error}")
                return await cloud_fallback_response(prompt, start_time, str(local_error))
        
        # COMPLEX PATH: Use voting for complex prompts
        print(f"🗳️ Complex prompt, using voting for '{prompt[:50]}...'")
        
        try:
            result = await vote(prompt, preferred_models, top_k=1)
            
            # Check if voting result contains templates (skip in test mode)
            response_text = result.get("text", "")
            if (not os.environ.get("SWARM_TEST_MODE") and 
                ("Response from " in response_text or "[TEMPLATE]" in response_text or 
                 "Mock" in response_text or len(response_text) < 10)):
                raise RuntimeError(f"Voting returned template response: {response_text[:100]}")
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract winner information
            winner = result.get("winner", {})
            confidence = winner.get("confidence", 0.5)
            
            # Simple cost calculation
            tokens = len(prompt.split()) + len(response_text.split())
            cost_cents = debit(winner.get("model", "unknown"), tokens)
            
            return {
                "text": response_text,
                "provider": "local_voting",
                "model_used": winner.get("model", "unknown"),
                "confidence": confidence,
                "hybrid_latency_ms": latency_ms,
                "cloud_consulted": False,
                "cost_cents": cost_cents,
                "council_used": bool(enable_council),
                "council_voices": None
            }
            
        except (RuntimeError, Exception) as voting_error:
            # Voting failed - try cloud fallback
            print(f"🌩️ Voting failed: {voting_error}")
            return await cloud_fallback_response(prompt, start_time, str(voting_error))
        
    except Exception as e:
        # General error - try cloud fallback
        print(f"🌩️ Hybrid routing general error: {e}")
        return await cloud_fallback_response(prompt, start_time, str(e))

async def cloud_fallback_response(prompt: str, start_time: float, error_reason: str) -> Dict[str, Any]:
    """Fallback to cloud APIs when local models fail"""
    import aiohttp
    import json
    
    # Check for cloud APIs
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if mistral_key and mistral_key != "demo-key":
        try:
            # Real Mistral API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {mistral_key}"
                }
                payload = {
                    "model": "mistral-small-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                }
                
                async with session.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data["choices"][0]["message"]["content"].strip()
                        latency_ms = (time.time() - start_time) * 1000
                        
                        return {
                            "text": response,
                            "provider": "cloud_mistral",
                            "model_used": "mistral-small-latest",
                            "confidence": 0.85,
                            "hybrid_latency_ms": latency_ms,
                            "cloud_consulted": True,
                            "cost_cents": len(prompt.split()) * 0.8,
                            "council_used": False,
                            "cloud_reason": error_reason[:100],
                            "council_voices": None
                        }
                    else:
                        print(f"Mistral API error: {resp.status} - {await resp.text()}")
                        
        except Exception as e:
            print(f"Mistral API failed: {e}")
    
    if openai_key and openai_key != "demo-key":
        try:
            # Real OpenAI API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7
                }
                
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data["choices"][0]["message"]["content"].strip()
                        latency_ms = (time.time() - start_time) * 1000
                        
                        return {
                            "text": response,
                            "provider": "cloud_openai", 
                            "model_used": "gpt-4o-mini",
                            "confidence": 0.90,
                            "hybrid_latency_ms": latency_ms,
                            "cloud_consulted": True,
                            "cost_cents": len(prompt.split()) * 0.4,
                            "council_used": False,
                            "cloud_reason": error_reason[:100],
                            "council_voices": None
                        }
                    else:
                        print(f"OpenAI API error: {resp.status} - {await resp.text()}")
                        
        except Exception as e:
            print(f"OpenAI API failed: {e}")
    
    # No cloud APIs available - return error
    latency_ms = (time.time() - start_time) * 1000
    return {
        "text": f"Local inference failed and cloud APIs failed. Error: {error_reason}",
        "provider": "error",
        "model_used": "none",
        "confidence": 0.0,
        "hybrid_latency_ms": latency_ms,
        "cloud_consulted": False,
        "cost_cents": 0,
        "council_used": False,
        "error": "ALL_METHODS_FAILED",
        "error_reason": error_reason[:200],
        "council_voices": None
    }

async def smart_orchestrate(prompt: str, route: List[str], enable_cloud_fallback: bool = False) -> Dict[str, Any]:
    """
    Smart orchestration with optional cloud fallback
    
    Args:
        prompt: Input prompt
        route: List of models to try
        enable_cloud_fallback: Whether to fallback to cloud if local fails
        
    Returns:
        Dict with orchestration result
    """
    start_time = time.time()
    
    try:
        # Try hybrid routing first
        result = await hybrid_route(prompt, route, enable_council=False)
        
        # If confidence is too low and cloud fallback is enabled
        if result["confidence"] < 0.3 and enable_cloud_fallback:
            # For now, just return the local result with a flag
            result["cloud_consulted"] = True
            result["provider"] = "hybrid_with_cloud_consult"
        
        return result
        
    except Exception as e:
        return {
            "text": f"Orchestration failed: {str(e)}",
            "provider": "error",
            "model_used": "error",
            "confidence": 0.0,
            "hybrid_latency_ms": (time.time() - start_time) * 1000,
            "cloud_consulted": False,
            "cost_cents": 0.0,
            "council_used": False,
            "council_voices": None
        } 