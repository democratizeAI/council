#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quality Filters - Track ② P1 Optimizations
===========================================

Implements quality improvements to eliminate repetition and low-value answers:
1. Duplicate-token guard
2. Semantic similarity filter for RAG  
3. Confidence-weighted voting
4. Tighter decoding parameters
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter

class CloudRetryException(Exception):
    """Exception to trigger cloud fallback for quality issues"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Quality issue detected: {reason}")

def check_duplicate_tokens(text: str, window_size: int = 100, threshold: float = 0.06) -> bool:
    """
    Track ② Step 1: Duplicate-token guard (Enhanced)
    
    Detects infinite "Yes yes yes..." loops and repetitive patterns.
    
    Args:
        text: Generated text to check
        window_size: Look at last N characters (increased for better detection)
        threshold: Max ratio of unique tokens allowed (increased sensitivity)
        
    Returns:
        True if text has excessive duplication (should trigger cloud retry)
    """
    if len(text) < 20:  # Skip very short responses
        return False
    
    # Look at the last window_size characters
    recent_text = text[-window_size:]
    
    # Tokenize into words/tokens
    tokens = re.findall(r'\w+', recent_text.lower())
    
    if len(tokens) < 8:  # Need sufficient tokens to evaluate (reduced threshold)
        return False
    
    # Calculate unique token ratio
    unique_tokens = len(set(tokens))
    total_tokens = len(tokens)
    unique_ratio = unique_tokens / total_tokens
    
    # Check for excessive repetition
    if unique_ratio < threshold:
        return True
    
    # Additional check: look for exact phrase repetition (enhanced)
    words = recent_text.split()
    if len(words) >= 4:  # Reduced from 6 to catch shorter repetitions
        # Check for repeated 2-word phrases (more sensitive)
        bigrams = [' '.join(words[i:i+2]) for i in range(len(words)-1)]
        bigram_counts = Counter(bigrams)
        
        # If any 2-word phrase appears more than 3 times, it's repetitive
        for phrase, count in bigram_counts.items():
            if count > 3 and len(phrase.strip()) > 3:  # Ignore very short phrases
                return True
        
        # Check for repeated 3-word phrases
        if len(words) >= 6:
            trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
            trigram_counts = Counter(trigrams)
            
            # If any 3-word phrase appears more than twice, it's likely repetitive
            for count in trigram_counts.values():
                if count > 2:
                    return True
    
    # Check for sentence-level repetition
    sentences = re.split(r'[.!?]+', text.strip())
    if len(sentences) >= 3:
        sentence_counts = Counter(sentence.strip().lower() for sentence in sentences if sentence.strip())
        for count in sentence_counts.values():
            if count > 2:  # Same sentence repeated more than twice
                return True
    
    return False

def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate simple semantic similarity between two texts.
    
    This is a lightweight implementation using token overlap.
    For production, consider using sentence-transformers or similar.
    """
    if not text1 or not text2:
        return 0.0
    
    # Tokenize and normalize
    tokens1 = set(re.findall(r'\w+', text1.lower()))
    tokens2 = set(re.findall(r'\w+', text2.lower()))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    
    return intersection / union if union > 0 else 0.0

def filter_semantic_duplicates(new_text: str, existing_chunks: List[str], 
                              similarity_threshold: float = 0.9) -> bool:
    """
    Track ② Step 2: Semantic similarity filter for RAG
    
    Prevents copy-pasta blurbs by checking semantic similarity with existing content.
    
    Args:
        new_text: New text chunk to evaluate
        existing_chunks: Previously added chunks 
        similarity_threshold: Max similarity allowed (default 0.9)
        
    Returns:
        True if text should be filtered out (too similar to existing)
    """
    # Fix for single semantic-similarity edge: adjust threshold for short prompts
    # Very short prompts need a higher threshold to avoid false positives
    if len(new_text.split()) < 15:
        dup_thresh = 0.93
    else:
        dup_thresh = similarity_threshold
    
    for existing in existing_chunks:
        similarity = calculate_semantic_similarity(new_text, existing)
        if similarity > dup_thresh:
            return True  # Filter out - too similar
    
    return False  # Keep - sufficiently different

def calculate_response_confidence(text: str, model_name: str, 
                                 response_metadata: Dict[str, Any] = None) -> float:
    """
    Track ② Step 3: Confidence scoring for responses
    
    Calculates confidence based on response quality indicators.
    """
    if not text or len(text.strip()) < 10:
        return 0.1  # Very low confidence for short/empty responses
    
    confidence = 0.5  # Base confidence
    
    # Length-based scoring (penalize very short responses)
    if len(text) < 30:
        confidence -= 0.3  # Penalize stub answers
    elif len(text) > 50:
        confidence += 0.2  # Reward substantial responses
    
    # Content quality indicators
    text_lower = text.lower()
    
    # Positive indicators
    if any(indicator in text_lower for indicator in ['because', 'therefore', 'specifically', 'for example']):
        confidence += 0.1  # Explanatory language
    
    if re.search(r'\d+', text):
        confidence += 0.05  # Contains numbers/facts
    
    # Negative indicators  
    if any(bad in text_lower for bad in ['todo', 'fixme', 'xxx', 'placeholder']):
        confidence -= 0.4  # Development artifacts
    
    if text.count('...') > 2:
        confidence -= 0.2  # Excessive ellipses
    
    if 'response from' in text_lower:
        confidence -= 0.3  # Template responses
    
    # Model-specific adjustments
    if 'math' in model_name and any(op in text for op in ['+', '-', '*', '/', '=']):
        confidence += 0.2  # Math model doing math
    
    # Use logprobs if available (simulated for now)
    if response_metadata and 'logprobs' in response_metadata:
        avg_logprob = response_metadata['logprobs']
        if avg_logprob > -2.0:  # High probability tokens
            confidence += 0.1
        elif avg_logprob < -4.0:  # Low probability tokens
            confidence -= 0.1
    
    return max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

def apply_confidence_weighted_voting(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Track ② Step 3: Confidence-weighted voting
    
    Selects the best response based on confidence scores and quality metrics.
    """
    if not candidates:
        raise CloudRetryException("No candidates for voting")
    
    # Calculate confidence for each candidate
    scored_candidates = []
    
    for candidate in candidates:
        text = candidate.get('text', '')
        model = candidate.get('model', 'unknown')
        metadata = candidate.get('metadata', {})
        
        # Check for quality issues first
        if check_duplicate_tokens(text):
            confidence = 0.05  # Very low confidence for repetitive text
        else:
            confidence = calculate_response_confidence(text, model, metadata)
        
        scored_candidates.append({
            **candidate,
            'confidence': confidence,
            'quality_score': confidence  # Alias for backward compatibility
        })
    
    # Sort by confidence (highest first)
    scored_candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    winner = scored_candidates[0]
    
    # If the winner has very low confidence, trigger cloud retry
    if winner['confidence'] < 0.2:
        raise CloudRetryException(f"All local responses have low confidence (best: {winner['confidence']:.3f})")
    
    return {
        'text': winner['text'],
        'winner': {
            'model': winner.get('model', 'unknown'),
            'confidence': winner['confidence']
        },
        'all_candidates': scored_candidates,
        'voting_stats': {
            'total_candidates': len(candidates),
            'winner_confidence': winner['confidence'],
            'confidence_spread': scored_candidates[0]['confidence'] - scored_candidates[-1]['confidence']
        }
    }

def get_optimal_decoding_params(model_name: str, prompt_type: str = "general") -> Dict[str, Any]:
    """
    Track ② Step 4: Tighter decoding parameters
    
    Returns optimized generation parameters to eliminate run-on filler 
    while keeping creativity.
    """
    # Base parameters for quality generation
    params = {
        'top_p': 0.92,           # Slightly more selective than default 0.95
        'temperature': 0.7,      # Balanced creativity/coherence
        'min_p': 0.05,          # Filter very low probability tokens
        'repetition_penalty': 1.1,  # Mild repetition penalty
        'max_new_tokens': 150,   # Reasonable length limit
        'do_sample': True,       # Enable sampling
        'early_stopping': True   # Stop at natural endings
    }
    
    # Model-specific adjustments
    if 'math' in model_name.lower():
        params.update({
            'temperature': 0.5,      # More deterministic for math
            'top_p': 0.9,           # More focused
            'max_new_tokens': 100   # Math answers can be shorter
        })
    
    elif 'code' in model_name.lower():
        params.update({
            'temperature': 0.6,      # Slightly more deterministic
            'repetition_penalty': 1.05,  # Lower penalty for code repetition
            'max_new_tokens': 200   # Code might need more tokens
        })
    
    # Prompt-type adjustments  
    if prompt_type == "simple":
        params.update({
            'temperature': 0.6,      # More focused for simple queries
            'max_new_tokens': 75    # Shorter for simple answers
        })
    
    elif prompt_type == "complex":
        params.update({
            'temperature': 0.8,      # More creativity for complex reasoning
            'max_new_tokens': 250   # Allow longer explanations
        })
    
    return params

def post_process_response(text: str, model_name: str) -> str:
    """
    Post-process response to improve quality.
    """
    if not text:
        return text
    
    # Remove common artifacts
    text = re.sub(r'^Response from \w+:\s*', '', text)  # Remove template prefixes
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    # Remove trailing incomplete sentences for better quality
    if text and not text[-1] in '.!?':
        # Find the last complete sentence
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) > 1:
            complete_sentences = sentences[:-1]  # Drop incomplete last sentence
            text = '. '.join(complete_sentences).strip()
            if text and not text.endswith('.'):
                text += '.'
    
    return text

# Quality metrics for monitoring
def calculate_quality_metrics(text: str) -> Dict[str, float]:
    """Calculate quality metrics for monitoring and debugging"""
    if not text:
        return {'length': 0, 'unique_ratio': 0, 'sentence_count': 0}
    
    words = text.split()
    unique_words = len(set(word.lower() for word in words))
    
    return {
        'length': len(text),
        'word_count': len(words),
        'unique_ratio': unique_words / max(len(words), 1),
        'sentence_count': len(re.split(r'[.!?]+', text.strip())),
        'avg_word_length': sum(len(word) for word in words) / max(len(words), 1)
    } 