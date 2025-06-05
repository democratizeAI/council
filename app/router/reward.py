"""
Preference/Reward model endpoint for scoring responses.
Used by RL-LoRA training pipeline (#204).
"""

import time
import torch
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from peft import PeftModel
import numpy as np
from prometheus_client import Histogram, Counter

# Prometheus metrics
PREF_LATENCY = Histogram("swarm_pref_latency_seconds", "Preference head latency")
PREF_REQUESTS = Counter("swarm_pref_requests_total", "Total preference scoring requests") 
PREF_ERRORS = Counter("swarm_pref_errors_total", "Preference scoring errors")

router = APIRouter(prefix="/reward", tags=["reward"])

# Global model cache
_preference_model = None
_preference_tokenizer = None

class ScoreRequest(BaseModel):
    prompt: str
    chosen: str
    rejected: str

class ScoreResponse(BaseModel):
    reward_chosen: float
    reward_rejected: float
    preference_score: float  # chosen - rejected
    confidence: float

class BatchScoreRequest(BaseModel):
    pairs: List[ScoreRequest]

def load_preference_model(model_path: str = "models/lora_pref_phi2_20250605"):
    """Load the LoRA preference model."""
    global _preference_model, _preference_tokenizer
    
    if _preference_model is not None:
        return _preference_model, _preference_tokenizer
    
    try:
        # Load base model for classification
        base_model = AutoModelForSequenceClassification.from_pretrained(
            "microsoft/phi-2",
            num_labels=2,
            torch_dtype=torch.float16,
            device_map="auto"
        )
        
        # Load LoRA weights
        model = PeftModel.from_pretrained(base_model, model_path)
        model.eval()
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2")
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        _preference_model = model
        _preference_tokenizer = tokenizer
        
        print(f"✅ Preference model loaded from {model_path}")
        return model, tokenizer
        
    except Exception as e:
        print(f"❌ Failed to load preference model: {e}")
        raise HTTPException(status_code=500, detail=f"Model loading failed: {e}")

def preference_to_score(prompt: str, response: str, model, tokenizer) -> float:
    """Convert response to preference score using the trained model."""
    
    # Format input: prompt + " [SEP] " + response
    text = f"{prompt} [SEP] {response}"
    
    # Tokenize
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )
    
    # Move to device
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    # Get logits
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
    
    # Convert to preference probability (softmax)
    probs = torch.softmax(logits, dim=-1)
    preference_score = probs[0, 1].item()  # probability of being preferred
    
    return preference_score

@router.post("/score", response_model=ScoreResponse)
async def score_preference(req: ScoreRequest):
    """Score a single preference pair."""
    start_time = time.time()
    PREF_REQUESTS.inc()
    
    try:
        model, tokenizer = load_preference_model()
        
        # Score both responses
        chosen_score = preference_to_score(req.prompt, req.chosen, model, tokenizer)
        rejected_score = preference_to_score(req.prompt, req.rejected, model, tokenizer)
        
        # Calculate preference difference
        preference_diff = chosen_score - rejected_score
        confidence = abs(preference_diff)
        
        latency = time.time() - start_time
        PREF_LATENCY.observe(latency)
        
        return ScoreResponse(
            reward_chosen=chosen_score,
            reward_rejected=rejected_score,
            preference_score=preference_diff,
            confidence=confidence
        )
        
    except Exception as e:
        PREF_ERRORS.inc()
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

@router.post("/batch_score")
async def batch_score_preferences(req: BatchScoreRequest):
    """Score multiple preference pairs in batch."""
    start_time = time.time()
    PREF_REQUESTS.inc(len(req.pairs))
    
    try:
        model, tokenizer = load_preference_model()
        
        results = []
        for pair in req.pairs:
            chosen_score = preference_to_score(pair.prompt, pair.chosen, model, tokenizer)
            rejected_score = preference_to_score(pair.prompt, pair.rejected, model, tokenizer)
            
            preference_diff = chosen_score - rejected_score
            confidence = abs(preference_diff)
            
            results.append(ScoreResponse(
                reward_chosen=chosen_score,
                reward_rejected=rejected_score,
                preference_score=preference_diff,
                confidence=confidence
            ))
        
        latency = time.time() - start_time
        PREF_LATENCY.observe(latency)
        
        return {"scores": results, "batch_size": len(req.pairs)}
        
    except Exception as e:
        PREF_ERRORS.inc()
        raise HTTPException(status_code=500, detail=f"Batch scoring failed: {e}")

@router.get("/health")
async def health_check():
    """Check if preference model is loaded and healthy."""
    try:
        model, tokenizer = load_preference_model()
        return {
            "status": "healthy",
            "model_loaded": model is not None,
            "tokenizer_loaded": tokenizer is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "error": str(e)
        }

@router.post("/reload")
async def reload_model():
    """Reload the preference model (for hot updates)."""
    global _preference_model, _preference_tokenizer
    
    _preference_model = None
    _preference_tokenizer = None
    
    try:
        load_preference_model()
        return {"status": "reloaded", "message": "Preference model reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reload failed: {e}") 