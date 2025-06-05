#!/usr/bin/env python3
"""
Tiny Summarizer - Prevents gigantic answers from being stuffed into ledger
=========================================================================

Implements fast, local summarization to keep summaries to 60-80 tokens max.
"""

import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Try to import transformers for summarization
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available - using fallback summarization")

# Global summarizer instance (lazy loaded)
_summarizer = None

def get_summarizer():
    """Get or create summarizer pipeline (lazy loading)"""
    global _summarizer
    if _summarizer is None and TRANSFORMERS_AVAILABLE:
        try:
            # Use a small, fast summarization model
            _summarizer = pipeline(
                "summarization",
                "philschmid/bart-large-cnn-samsum",
                device=0,  # Try GPU first
                max_length=80,
                min_length=30
            )
            logger.info("✅ Tiny summarizer loaded on GPU")
        except Exception as e:
            logger.warning(f"GPU summarizer failed, trying CPU: {e}")
            try:
                _summarizer = pipeline(
                    "summarization", 
                    "philschmid/bart-large-cnn-samsum",
                    device=-1,  # CPU fallback
                    max_length=80,
                    min_length=30
                )
                logger.info("✅ Tiny summarizer loaded on CPU")
            except Exception as e2:
                logger.error(f"Summarizer loading failed: {e2}")
                _summarizer = False  # Mark as failed
    return _summarizer

@lru_cache(maxsize=100)
def simple_truncate_summary(text: str, max_tokens: int = 80) -> str:
    """Fallback simple truncation when transformers unavailable"""
    words = text.split()
    if len(words) <= max_tokens:
        return text
    
    # Try to find a good break point
    truncated = words[:max_tokens-3]
    summary = " ".join(truncated)
    
    # Add ellipsis if truncated
    if len(words) > max_tokens:
        summary += "..."
    
    return summary

def summarize(text: str, max_tokens: int = 80) -> str:
    """
    Summarize text to max_tokens length
    
    Args:
        text: Input text to summarize
        max_tokens: Maximum tokens in output (default 80)
        
    Returns:
        Summarized text within token limit
    """
    if not text or len(text.strip()) == 0:
        return ""
    
    # If already short enough, return as-is
    word_count = len(text.split())
    if word_count <= max_tokens:
        return text
    
    # Try transformer-based summarization
    summarizer = get_summarizer()
    if summarizer and summarizer is not False:
        try:
            # Prepare text for summarization
            # Limit input length to prevent issues
            input_text = text[:1000] if len(text) > 1000 else text
            
            result = summarizer(input_text)
            if result and len(result) > 0:
                summary = result[0]["summary_text"]
                
                # Ensure we don't exceed max_tokens
                summary_words = summary.split()
                if len(summary_words) > max_tokens:
                    summary = " ".join(summary_words[:max_tokens])
                
                logger.debug(f"📝 Summarized {word_count} → {len(summary.split())} tokens")
                return summary
                
        except Exception as e:
            logger.warning(f"Transformer summarization failed: {e}")
    
    # Fallback to simple truncation
    logger.debug(f"📝 Using simple truncation: {word_count} → {max_tokens} tokens")
    return simple_truncate_summary(text, max_tokens)

def summarize_for_ledger(text: str) -> str:
    """Summarize specifically for ledger/memory system (60-80 tokens)"""
    return summarize(text, max_tokens=70)

def summarize_for_context(text: str) -> str:
    """Summarize for context passing between tiers (80-100 tokens)"""
    return summarize(text, max_tokens=90)

def is_summary_needed(text: str, threshold: int = 100) -> bool:
    """Check if text needs summarization"""
    return len(text.split()) > threshold

# Performance monitoring
def get_summarizer_stats() -> dict:
    """Get summarizer performance statistics"""
    global _summarizer
    return {
        "available": _summarizer is not None and _summarizer is not False,
        "model_loaded": _summarizer is not None,
        "backend": "transformers" if TRANSFORMERS_AVAILABLE and _summarizer else "simple"
    }

if __name__ == "__main__":
    # Test the summarizer
    test_text = """
    The AutoGen Council system uses a multi-tier architecture with local specialists, 
    synthetic agents, and premium LLMs. Each tier has different latency and cost characteristics.
    The math specialist uses SymPy for symbolic computation and can handle complex mathematical
    queries with high accuracy. The code specialist integrates with DeepSeek and provides
    sandbox execution capabilities. The system includes confidence-based routing, cost tracking,
    and comprehensive monitoring across all tiers.
    """
    
    print(f"Original: {len(test_text.split())} words")
    print(f"Text: {test_text.strip()}")
    print()
    
    summary = summarize(test_text)
    print(f"Summary: {len(summary.split())} words")
    print(f"Text: {summary}") 