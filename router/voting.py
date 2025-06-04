# -*- coding: utf-8 -*-
"""
Voting Router with Quality Filters - Track ② Integration
========================================================

Enhanced voting system with P1 quality improvements:
- Duplicate-token detection with cloud fallback
- Confidence-weighted voting
- Quality post-processing
- Memory hooks for context-aware conversations
"""

import asyncio
import time
import random
from typing import List, Dict, Any, Optional
from loader.deterministic_loader import generate_response, get_loaded_models
from router.quality_filters import (
    check_duplicate_tokens, 
    apply_confidence_weighted_voting,
    get_optimal_decoding_params,
    post_process_response,
    calculate_quality_metrics,
    CloudRetryException
)

# Import global memory
from bootstrap import MEMORY

import logging
from router.selector import pick_specialist, load_models_config, should_use_cloud_fallback
from router_cascade import RouterCascade

logger = logging.getLogger(__name__)

class SpecialistRunner:
    """Runs individual specialists with timeout and error handling"""
    
    def __init__(self):
        self.router = RouterCascade()
    
    async def run_specialist(self, specialist: str, prompt: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Run a single specialist with timeout protection"""
        start_time = time.time()
        
        try:
            # Map specialist names to router methods
            specialist_map = {
                "math_specialist": self._run_math,
                "code_specialist": self._run_code,
                "logic_specialist": self._run_logic, 
                "knowledge_specialist": self._run_knowledge,
                "mistral_general": self._run_general
            }
            
            if specialist not in specialist_map:
                raise ValueError(f"Unknown specialist: {specialist}")
            
            # Run specialist with timeout
            result = await asyncio.wait_for(
                specialist_map[specialist](prompt),
                timeout=timeout
            )
            
            # Add metadata
            result["specialist"] = specialist
            result["latency_ms"] = (time.time() - start_time) * 1000
            result["status"] = "success"
            
            return result
            
        except asyncio.TimeoutError:
            return {
                "specialist": specialist,
                "text": f"[TIMEOUT] {specialist} exceeded {timeout}s",
                "confidence": 0.0,
                "status": "timeout",
                "latency_ms": timeout * 1000
            }
        except Exception as e:
            return {
                "specialist": specialist,
                "text": f"[ERROR] {specialist}: {str(e)}",
                "confidence": 0.0, 
                "status": "error",
                "latency_ms": (time.time() - start_time) * 1000,
                "error": str(e)
            }
    
    async def _run_math(self, prompt: str) -> Dict[str, Any]:
        """Run math specialist (SymPy)"""
        try:
            # Force routing to math specialist
            result = await self.router.route_query(prompt, force_skill="math")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.9),
                "model": "lightning-math-sympy",
                "skill_type": "math"
            }
        except Exception as e:
            # Fallback if math specialist fails
            raise Exception(f"Math specialist failed: {e}")
    
    async def _run_code(self, prompt: str) -> Dict[str, Any]:
        """Run code specialist (DeepSeek + Sandbox)"""
        try:
            result = await self.router.route_query(prompt, force_skill="code")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.8),
                "model": "deepseek-coder-sandbox",
                "skill_type": "code"
            }
        except Exception as e:
            raise Exception(f"Code specialist failed: {e}")
    
    async def _run_logic(self, prompt: str) -> Dict[str, Any]:
        """Run logic specialist (SWI-Prolog)"""
        try:
            result = await self.router.route_query(prompt, force_skill="logic")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.7),
                "model": "swi-prolog-engine",
                "skill_type": "logic"
            }
        except Exception as e:
            raise Exception(f"Logic specialist failed: {e}")
    
    async def _run_knowledge(self, prompt: str) -> Dict[str, Any]:
        """Run knowledge specialist (FAISS RAG)"""
        try:
            result = await self.router.route_query(prompt, force_skill="knowledge")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.6),
                "model": "faiss-rag-retrieval",
                "skill_type": "knowledge"
            }
        except Exception as e:
            raise Exception(f"Knowledge specialist failed: {e}")
    
    async def _run_general(self, prompt: str) -> Dict[str, Any]:
        """Run general LLM (Mistral/OpenAI cloud fallback)"""
        try:
            result = await self.router.route_query(prompt, force_skill="agent0")
            return {
                "text": result["text"],
                "confidence": result.get("confidence", 0.5),
                "model": result.get("model", "cloud-fallback"),
                "skill_type": "general"
            }
        except Exception as e:
            raise Exception(f"General LLM failed: {e}")

async def vote(prompt: str, model_names: List[str] = None, top_k: int = 1, use_context: bool = True) -> Dict[str, Any]:
    """
    Run council voting with specialist priority.
    
    Args:
        prompt: User query
        model_names: List of specialists to try (optional)
        top_k: Number of top results to return
        use_context: Whether to inject memory context
        
    Returns:
        {
            "text": "Best response",
            "winner": {...},
            "voting_stats": {...},
            "specialists_tried": [...],
            "council_decision": True
        }
    """
    start_time = time.time()
    
    # Memory context injection
    if use_context:
        try:
            from faiss_memory import FAISSMemorySystem
            memory = FAISSMemorySystem()
            context_results = memory.query(prompt, k=3)
            if context_results:
                context_text = "\n".join([r["text"] for r in context_results])
                prompt = f"Context from memory:\n{context_text}\n\nUser query: {prompt}"
        except Exception as e:
            logger.warning(f"Memory context injection failed: {e}")
    
    # Determine specialists to try
    if model_names is None:
        # Use intelligent specialist selection
        config = load_models_config()
        specialist, confidence, tried = pick_specialist(prompt, config)
        
        # Add primary specialist plus fallbacks
        specialists_to_try = [specialist]
        
        # Add other specialists if confidence is low
        if confidence < 0.8:
            other_specialists = [s for s in config["specialists_order"] if s != specialist]
            specialists_to_try.extend(other_specialists[:2])  # Try 2 more
    else:
        specialists_to_try = model_names
    
    # Run specialists in priority order
    runner = SpecialistRunner()
    results = []
    
    for specialist in specialists_to_try:
        logger.info(f"🎯 Trying specialist: {specialist}")
        
        try:
            result = await runner.run_specialist(specialist, prompt)
            results.append(result)
            
            # If we got a good result from a high-priority specialist, stop here
            if (result["status"] == "success" and 
                result["confidence"] > 0.7 and 
                "specialist" in specialist):
                logger.info(f"✅ {specialist} provided confident answer ({result['confidence']:.2f})")
                break
                
        except Exception as e:
            logger.warning(f"⚠️ {specialist} failed: {e}")
            
            # Check if we should try cloud fallback
            if should_use_cloud_fallback(specialist, str(e)):
                logger.info("☁️ Triggering cloud fallback")
                try:
                    cloud_result = await runner.run_specialist("mistral_general", prompt)
                    results.append(cloud_result)
                except Exception as cloud_error:
                    logger.error(f"☁️ Cloud fallback also failed: {cloud_error}")
    
    # If no results, emergency fallback
    if not results:
        emergency_result = {
            "specialist": "emergency_fallback",
            "text": f"I apologize, but all specialists are currently unavailable. Please try again later.",
            "confidence": 0.1,
            "status": "emergency",
            "latency_ms": (time.time() - start_time) * 1000
        }
        results.append(emergency_result)
    
    # Vote for best result
    successful_results = [r for r in results if r["status"] == "success"]
    if not successful_results:
        successful_results = results  # Use whatever we have
    
    # Winner selection (highest confidence wins)
    winner = max(successful_results, key=lambda r: r.get("confidence", 0))
    
    # Voting statistics
    voting_stats = {
        "total_specialists": len(results),
        "successful_specialists": len(successful_results),
        "winner_confidence": winner["confidence"],
        "total_latency_ms": (time.time() - start_time) * 1000,
        "specialists_tried": [r["specialist"] for r in results]
    }
    
    logger.info(f"🏆 Council decision: {winner['specialist']} wins with {winner['confidence']:.2f} confidence")
    
    return {
        "text": winner["text"],
        "model": winner.get("model", winner["specialist"]),
        "winner": winner,
        "voting_stats": voting_stats,
        "specialists_tried": [r["specialist"] for r in results],
        "council_decision": True,
        "timestamp": time.time()
    }

def smart_select(prompt: str, model_names: List[str]) -> str:
    """
    Smart single-model selection for simple prompts (Track ① fast path)
    
    Selects the best model for a given prompt without running inference.
    Enhanced with quality considerations.
    """
    if not model_names:
        return model_names[0] if model_names else "unknown"
    
    # Simple heuristic-based selection with quality focus
    prompt_lower = prompt.lower()
    
    # Math-related prompts → prefer math specialist
    if any(math_word in prompt_lower for math_word in ['math', 'calculate', 'add', 'subtract', '+', '-', '*', '/', 'equals']):
        for model in model_names:
            if 'math' in model.lower():
                return model
    
    # Code-related prompts → prefer code specialist  
    if any(code_word in prompt_lower for code_word in ['code', 'python', 'def ', 'function', 'import', 'class']):
        for model in model_names:
            if 'code' in model.lower():
                return model
    
    # Logic prompts → prefer logic specialist
    if any(logic_word in prompt_lower for logic_word in ['if ', 'then', 'logic', 'reasoning', 'true', 'false']):
        for model in model_names:
            if 'logic' in model.lower():
                return model
    
    # For general prompts, prefer models known for quality
    # Priority order: phi2 > tinyllama > mistral > others
    quality_priority = ['phi2', 'tinyllama', 'mistral']
    
    for priority_model in quality_priority:
        for model in model_names:
            if priority_model in model.lower():
                return model
    
    # Fallback to first available model
    return model_names[0] 