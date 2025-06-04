# -*- coding: utf-8 -*-
"""
Voting Router with Quality Filters - Track ② Integration
========================================================

Enhanced voting system with P1 quality improvements:
- Duplicate-token detection with cloud fallback
- Confidence-weighted voting
- Quality post-processing
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

async def vote(prompt: str, model_names: List[str], top_k: int = 1) -> Dict[str, Any]:
    """
    Enhanced voting with quality filters and confidence weighting
    
    Args:
        prompt: Input prompt
        model_names: List of model names to vote with
        top_k: Number of top responses to return
        
    Returns:
        Dict with winner, all candidates, and voting statistics
    """
    if not model_names:
        raise ValueError("No models provided for voting")
    
    start_time = time.time()
    candidates = []
    
    print(f"🗳️ Voting: {len(model_names)} heads for '{prompt[:50]}...'")
    
    # Generate responses from all models
    for model_name in model_names:
        try:
            # Get optimal decoding parameters for this model
            prompt_type = "simple" if len(prompt) < 50 else "complex"
            decoding_params = get_optimal_decoding_params(model_name, prompt_type)
            
            # Generate response with quality parameters
            response_text = generate_response(
                model_name, 
                prompt, 
                max_tokens=decoding_params['max_new_tokens']
            )
            
            # Post-process for quality
            processed_text = post_process_response(response_text, model_name)
            
            # Track ② Step 1: Check for duplicate tokens
            has_duplicates = check_duplicate_tokens(processed_text)
            if has_duplicates:
                print(f"🚨 Duplicate tokens detected in {model_name}: {processed_text[:50]}...")
                # Don't immediately discard - let confidence scoring handle it
            
            candidates.append({
                'text': processed_text,
                'model': model_name,
                'has_duplicates': has_duplicates,
                'quality_metrics': calculate_quality_metrics(processed_text),
                'metadata': {
                    'decoding_params': decoding_params,
                    'processing_time_ms': (time.time() - start_time) * 1000
                }
            })
            
        except Exception as e:
            print(f"❌ Error generating response from {model_name}: {e}")
            # Add a placeholder with very low confidence
            candidates.append({
                'text': f"Error: {str(e)[:100]}",
                'model': model_name,
                'has_duplicates': False,
                'quality_metrics': {'length': 0, 'unique_ratio': 0},
                'metadata': {'error': str(e)}
            })
    
    if not candidates:
        raise CloudRetryException("No valid candidates generated")
    
    try:
        # Track ② Step 3: Apply confidence-weighted voting
        voting_result = apply_confidence_weighted_voting(candidates)
        
        # Add timing information
        voting_time_ms = (time.time() - start_time) * 1000
        voting_result['voting_stats']['voting_time_ms'] = voting_time_ms
        
        winner = voting_result['winner']
        print(f"🏆 Winner: {winner['model']} (confidence: {winner['confidence']:.3f})")
        
        return voting_result
        
    except CloudRetryException as e:
        # All local responses had quality issues - should trigger cloud fallback
        print(f"🌩️ Quality issues detected, triggering cloud fallback: {e.reason}")
        raise e

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