#!/usr/bin/env python3
"""
🎯 Enhanced Intent Classification
================================

Hardened intent classification with:
1. Stronger fallback penalties
2. More accurate regex patterns
3. Optional MiniLM classifier (3ms overhead)
4. Confidence scoring improvements

Replaces flaky regex-only routing with production-grade classification.
"""

import re
import os
import logging
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class IntentConfig:
    """Configuration for intent classification"""
    name: str
    patterns: List[str]
    examples: List[str]
    base_confidence: float
    penalty_if_fallback: float = 2.0  # 🚀 HARDENING: Stronger penalty

# 🚀 HARDENING: More precise intent patterns
INTENT_CONFIGS = {
    'math': IntentConfig(
        name='Lightning Math',
        patterns=[
            r'\b\d+\s*[\+\-\*/\^%]\s*\d+\b',          # 2+2, 15*23
            r'\b\d+\.\d+\s*[\+\-\*/\^%]\s*\d+\b',     # 2.5*3
            r'\bsqrt\s*\(|\bsin\s*\(|\bcos\s*\(',     # sqrt(16)
            r'\blog\s*\(|\bexp\s*\(|\babs\s*\(',      # log(10)
            r'\d+\s*\*\*\s*\d+',                       # 2**3
            r'\bcalculate\s+\d+|\bcompute\s+\d+',      # calculate 15
            r'what\s+is\s+\d+.*[\+\-\*/\^].*\d+',     # what is 2+2
            r'how\s+much\s+is\s+\d+.*[\+\-\*/\^].*\d+' # how much is 5*7
        ],
        examples=[
            "2 + 2", "15 * 23", "sqrt(16)", "calculate 25 * 4",
            "what is 100 / 5", "sin(30 degrees)"
        ],
        base_confidence=0.95,
        penalty_if_fallback=3.0  # High penalty - math should be very confident
    ),
    
    'code': IntentConfig(
        name='DeepSeek Coder',
        patterns=[
            r'\bdef\s+\w+\s*\(|\bclass\s+\w+\s*[\(:]',  # def func(), class Foo:
            r'\bfunction\s+\w+\s*\(',                     # function name()
            r'\bwrite.*(?:code|function|script)',         # write code/function
            r'\b(?:python|javascript|java|cpp|rust)\s+code', # python code
            r'\bdebug|fix.*(?:code|bug|error)',          # debug code
            r'\bimport\s+\w+|\bfrom\s+\w+\s+import',     # import statements
            r'\brun.*code|execute.*code',                 # run code
            r'\balgorithm|implement.*algorithm',          # algorithm requests
            r'```(?:python|js|java|cpp|rust)',           # code blocks
        ],
        examples=[
            "write a function", "def hello_world():", "debug this code",
            "python algorithm", "implement bubble sort", "fix the bug"
        ],
        base_confidence=0.85,
        penalty_if_fallback=2.5
    ),
    
    'logic': IntentConfig(
        name='Prolog Logic',
        patterns=[
            r'\bif\s+.*\bthen\b|\bimplies?\b',           # if-then logic
            r'\blogical?|reasoning|premise|conclusion',   # logic terms
            r'\btrue\s+or\s+false|\bvalid\s+or\s+invalid', # boolean logic
            r'\bproof|theorem|lemma|axiom',              # mathematical logic
            r'\band\s+.*\bor\b|\bor\s+.*\band\b',        # boolean operators
            r'\bnot\s+\w+|\bnegation',                   # negation
            r'\bsyllogism|deduction|induction',          # logical reasoning
            r'\bparadox|contradiction|consistent',        # logical concepts
        ],
        examples=[
            "if then logic", "prove this theorem", "is this valid reasoning",
            "logical contradiction", "syllogism analysis"
        ],
        base_confidence=0.75,
        penalty_if_fallback=2.0
    ),
    
    'knowledge': IntentConfig(
        name='FAISS RAG',
        patterns=[
            r'\bwhat\s+is\s+(?!.*\d+.*[\+\-\*/]).*',     # what is X (not math)
            r'\bwho\s+(?:is|was|were)\s+\w+',            # who is/was
            r'\bwhere\s+(?:is|was|are)\s+\w+',           # where is/was
            r'\bwhen\s+(?:is|was|did)\s+\w+',            # when is/was/did
            r'\bexplain\s+(?!.*code).*',                 # explain (not code)
            r'\btell\s+me\s+about\s+\w+',                # tell me about
            r'\bcapital\s+of|country|geography',         # geography
            r'\bhistory|historical|ancient',             # history
            r'\bfacts?\s+about|\binformation\s+about',   # facts/info
            r'\bdefinition\s+of|meaning\s+of',           # definitions
        ],
        examples=[
            "what is Saturn", "who was Einstein", "explain photosynthesis",
            "capital of France", "tell me about sharks", "definition of quantum"
        ],
        base_confidence=0.65,
        penalty_if_fallback=1.5
    ),
    
    'general': IntentConfig(
        name='Agent-0 General',
        patterns=[
            r'\bhello?|hi\b|hey\b|greetings?',           # greetings
            r'\bthank\s*you|thanks',                     # thanks
            r'\bhelp|assist|support',                    # help requests
            r'\bhow\s+are\s+you',                        # social
            r'\bgood\s+(?:morning|afternoon|evening)',   # time greetings
            r'^\w{1,3}[?!]*$',                           # very short queries
        ],
        examples=[
            "hello", "hi there", "thank you", "how are you",
            "help me", "good morning"
        ],
        base_confidence=0.50,
        penalty_if_fallback=1.0  # Low penalty - general is the fallback
    )
}

class EnhancedIntentClassifier:
    """Enhanced intent classifier with hardened routing"""
    
    def __init__(self, use_miniLM: bool = False):
        self.use_miniLM = use_miniLM
        self.miniLM_classifier = None
        
        if use_miniLM:
            self._load_miniLM_classifier()
    
    def _load_miniLM_classifier(self):
        """Load optional MiniLM classifier for production accuracy"""
        try:
            import onnxruntime as ort
            import numpy as np
            
            # Load pre-trained classifier (384-dim MiniLM embeddings)
            classifier_path = "models/intent_classifier.onnx"
            if os.path.exists(classifier_path):
                self.miniLM_classifier = ort.InferenceSession(classifier_path)
                logger.info("🎯 MiniLM intent classifier loaded")
            else:
                logger.warning("🎯 MiniLM classifier not found, using regex fallback")
                
        except ImportError:
            logger.warning("🎯 ONNXRuntime not available, using regex patterns")
        except Exception as e:
            logger.warning(f"🎯 Failed to load MiniLM classifier: {e}")
    
    def classify_intent(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Classify intent with enhanced accuracy
        
        Returns:
            intent: Best intent name
            confidence: Confidence score (0-1)
            all_scores: All intent scores for debugging
        """
        if self.use_miniLM and self.miniLM_classifier:
            return self._classify_with_miniLM(query)
        else:
            return self._classify_with_enhanced_regex(query)
    
    def _classify_with_enhanced_regex(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """Enhanced regex classification with hardened scoring"""
        query_lower = query.lower().strip()
        scores = {}
        
        # Score each intent
        for intent_name, config in INTENT_CONFIGS.items():
            score = 0.0
            matches = 0
            
            # Test each pattern
            for pattern in config.patterns:
                try:
                    if re.search(pattern, query_lower):
                        matches += 1
                        # Weight by pattern specificity (longer = more specific)
                        pattern_weight = min(len(pattern) / 50.0, 1.0)
                        score += config.base_confidence * pattern_weight
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pattern}")
                    continue
            
            # Normalize by number of patterns
            if matches > 0:
                score = score / len(config.patterns)
                # Boost for multiple pattern matches
                if matches > 1:
                    score *= (1.0 + (matches - 1) * 0.1)
            
            # 🚀 HARDENING: Apply fallback penalty
            if intent_name == 'general':
                score -= config.penalty_if_fallback
                # But ensure general always has minimum score as true fallback
                score = max(score, 0.1)
            
            scores[intent_name] = max(0.0, min(1.0, score))
        
        # Find best intent
        best_intent = max(scores.keys(), key=lambda k: scores[k])
        best_confidence = scores[best_intent]
        
        # 🚀 HARDENING: Confidence floor for clear winners
        if best_confidence > 0.8:
            # Clear winner - boost confidence
            best_confidence = min(0.95, best_confidence * 1.1)
        elif best_confidence < 0.3:
            # Low confidence - force to general with penalty applied
            best_intent = 'general'
            best_confidence = 0.25
        
        logger.debug(f"🎯 Intent classification: {query[:30]}... → {best_intent} ({best_confidence:.3f})")
        logger.debug(f"🎯 All scores: {scores}")
        
        return best_intent, best_confidence, scores
    
    def _classify_with_miniLM(self, query: str) -> Tuple[str, float, Dict[str, float]]:
        """Classify using MiniLM neural classifier (3ms overhead)"""
        try:
            start_time = time.time()
            
            # Get embedding for query (requires sentence-transformers)
            from sentence_transformers import SentenceTransformer
            
            # Use cached model
            if not hasattr(self, 'embedding_model'):
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Run ONNX inference
            inputs = {"input": query_embedding.astype(np.float32)}
            outputs = self.miniLM_classifier.run(None, inputs)
            
            # Get probabilities
            probabilities = outputs[0][0]
            intent_names = list(INTENT_CONFIGS.keys())
            
            # Create scores dict
            scores = {intent_names[i]: float(probabilities[i]) for i in range(len(intent_names))}
            
            # Find best
            best_intent = max(scores.keys(), key=lambda k: scores[k])
            best_confidence = scores[best_intent]
            
            classification_time = (time.time() - start_time) * 1000
            logger.debug(f"🎯 MiniLM classification: {classification_time:.1f}ms → {best_intent} ({best_confidence:.3f})")
            
            return best_intent, best_confidence, scores
            
        except Exception as e:
            logger.warning(f"🎯 MiniLM classification failed: {e}, falling back to regex")
            return self._classify_with_enhanced_regex(query)

# Global classifier instance
_classifier = None

def get_intent_classifier(use_miniLM: bool = False) -> EnhancedIntentClassifier:
    """Get global intent classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = EnhancedIntentClassifier(use_miniLM=use_miniLM)
    return _classifier

def classify_query_intent(query: str, use_miniLM: bool = False) -> Tuple[str, float]:
    """
    Main function to classify query intent
    
    Args:
        query: User query to classify
        use_miniLM: Use neural classifier (3ms overhead) vs regex (instant)
    
    Returns:
        (intent_name, confidence_score)
    """
    classifier = get_intent_classifier(use_miniLM=use_miniLM)
    intent, confidence, _ = classifier.classify_intent(query)
    return intent, confidence

# Backwards compatibility
def calculate_confidence(query: str, skill: str) -> float:
    """Legacy function for backwards compatibility"""
    classifier = get_intent_classifier()
    intent, confidence, all_scores = classifier.classify_intent(query)
    
    # Return confidence for requested skill, or 0 if not the top choice
    if intent == skill:
        return confidence
    else:
        return all_scores.get(skill, 0.0)

if __name__ == "__main__":
    # Test the enhanced classifier
    test_queries = [
        "2 + 2",
        "write a hello world function", 
        "what is the capital of France",
        "if A implies B and B implies C, then A implies C",
        "hello there",
        "debug this Python code"
    ]
    
    classifier = EnhancedIntentClassifier()
    
    for query in test_queries:
        intent, confidence, scores = classifier.classify_intent(query)
        print(f"Query: '{query}'")
        print(f"Intent: {intent} (confidence: {confidence:.3f})")
        print(f"All scores: {scores}")
        print("-" * 50) 