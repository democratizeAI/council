"""
Router Selector - Specialist Priority System
============================================

Ensures local specialists get first chance before cloud fallback.
"""

import re
import yaml
import os
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

def load_models_config() -> Dict:
    """Load models configuration with specialist priorities"""
    try:
        with open("config/models.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load models config: {e}")
        return {
            "specialists_order": ["math_specialist", "code_specialist", "logic_specialist", "knowledge_specialist", "mistral_general"],
            "confidence_thresholds": {
                "math_specialist": 0.8,
                "code_specialist": 0.7, 
                "logic_specialist": 0.6,
                "knowledge_specialist": 0.5,
                "mistral_general": 0.3
            }
        }

def analyze_intent(prompt: str) -> Tuple[str, float]:
    """Analyze prompt intent and return (intent_type, confidence)"""
    prompt_lower = prompt.lower()
    
    # Math patterns - highest priority
    math_patterns = [
        r'\d+\s*[\+\-\*/\^]\s*\d+',  # 2+2, 5*7, etc.
        r'sqrt|sin|cos|tan|log|exp|factorial',  # math functions
        r'solve|equation|calculate|compute',  # math verbs
        r'derivative|integral|limit|sum',  # calculus
        r'matrix|vector|determinant'  # linear algebra
    ]
    
    for pattern in math_patterns:
        if re.search(pattern, prompt_lower):
            return "math", 0.95
    
    # Code patterns - second priority  
    code_patterns = [
        r'write.*code|write.*function|write.*script',
        r'python|javascript|java|cpp|rust|go\s+code',
        r'def |class |import |function|algorithm',
        r'debug|fix.*code|code.*review',
        r'run.*code|execute.*code'
    ]
    
    for pattern in code_patterns:
        if re.search(pattern, prompt_lower):
            return "code", 0.85
            
    # Logic patterns - third priority
    logic_patterns = [
        r'if.*then|logical|logic|reasoning',
        r'true|false|and|or|not\s+',
        r'proof|theorem|premise|conclusion',
        r'syllogism|deduction|induction'
    ]
    
    for pattern in logic_patterns:
        if re.search(pattern, prompt_lower):
            return "logic", 0.75
    
    # Knowledge patterns - fourth priority
    knowledge_patterns = [
        r'what\s+is|who\s+is|where\s+is|when\s+is|how\s+is',
        r'explain|describe|tell.*about|information.*about',
        r'definition|meaning|concept',
        r'history|facts|trivia'
    ]
    
    for pattern in knowledge_patterns:
        if re.search(pattern, prompt_lower):
            return "knowledge", 0.65
    
    # Default to general
    return "general", 0.4

def pick_specialist(prompt: str, config: Dict = None) -> Tuple[str, float, List[str]]:
    """
    Return best specialist for prompt.
    Returns: (specialist_name, confidence, tried_specialists)
    """
    if config is None:
        config = load_models_config()
    
    intent, intent_confidence = analyze_intent(prompt)
    specialists_order = config.get("specialists_order", [])
    thresholds = config.get("confidence_thresholds", {})
    
    # Create priority scores for each specialist
    specialist_scores = {}
    
    for specialist in specialists_order:
        base_score = 0.0
        
        # Intent-based bonuses (high priority)
        if intent == "math" and "math" in specialist:
            base_score += 0.9
        elif intent == "code" and "code" in specialist:
            base_score += 0.9  
        elif intent == "logic" and "logic" in specialist:
            base_score += 0.8
        elif intent == "knowledge" and "knowledge" in specialist:
            base_score += 0.7
        
        # General capability (lower priority)
        elif "general" in specialist or "mistral" in specialist:
            base_score += 0.1  # Low base score
        
        # Apply confidence threshold
        threshold = thresholds.get(specialist, 0.5)
        if base_score >= threshold:
            specialist_scores[specialist] = base_score
    
    # Penalize fallback/general heads heavily
    for specialist in specialist_scores:
        if "general" in specialist or "mistral" in specialist:
            specialist_scores[specialist] -= 0.5  # Heavy penalty
    
    if not specialist_scores:
        # Emergency fallback
        return "mistral_general", 0.3, []
    
    # Return highest scoring specialist
    best_specialist = max(specialist_scores, key=specialist_scores.get)
    best_score = specialist_scores[best_specialist]
    tried = list(specialist_scores.keys())
    
    logger.info(f"🎯 Intent: {intent} ({intent_confidence:.2f}) → {best_specialist} ({best_score:.2f})")
    
    return best_specialist, best_score, tried

def should_use_cloud_fallback(specialist: str, error: str) -> bool:
    """Determine if we should fall back to cloud providers"""
    # Only use cloud if local specialists completely fail
    cloud_triggers = [
        "CloudRetry",
        "rate limited", 
        "quota exceeded",
        "service unavailable",
        "timeout"
    ]
    
    return any(trigger in error for trigger in cloud_triggers) 