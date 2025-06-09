#!/usr/bin/env python3
"""
Cost-Aware Model Slotting for Router 2.0

Intelligent routing based on current budget utilization, request cost estimation,
and quality requirements. Automatically downgrades to local models when budget
constraints require it.
"""

import os
import yaml
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import our cost tracking system
from .cost_tracking import cost_ledger, PROMETHEUS_AVAILABLE

if PROMETHEUS_AVAILABLE:
    from prometheus_client import Counter, Histogram, Gauge
    
    # Slotting metrics
    SLOT_DECISIONS = Counter('swarm_slot_decisions_total', 
                           'Routing decisions by type', ['decision_type'])
    BUDGET_UTILIZATION = Gauge('swarm_budget_utilization_percent',
                              'Current budget utilization percentage')
    REQUEST_COST_ESTIMATE = Histogram('swarm_request_cost_estimate_usd',
                                    'Estimated cost per request in USD')

@dataclass
class SlotDecision:
    """Result of a slotting decision"""
    models: List[str]
    estimated_cost: float
    decision_type: str  # "cloud_approved", "local_fallback", "budget_exceeded"
    reason: str

class ModelSlotter:
    """Handles cost-aware model slotting decisions"""
    
    def __init__(self, prices_file: str = "router/prices.yml"):
        self.prices_file = prices_file
        self.prices = self._load_prices()
        
        # Budget configuration from prices file
        self.daily_limit = self.prices["budget_config"]["daily_limit_usd"]
        self.warning_threshold = self.prices["budget_config"]["warning_threshold"] 
        self.emergency_threshold = self.prices["budget_config"]["emergency_threshold"]
        
        # Override from environment if set
        env_budget = os.getenv("SWARM_DAILY_BUDGET_USD")
        if env_budget:
            self.daily_limit = float(env_budget)
    
    def _load_prices(self) -> Dict:
        """Load pricing configuration from YAML file"""
        try:
            with open(self.prices_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"⚠️ Price file {self.prices_file} not found, using defaults")
            return self._get_default_prices()
    
    def _get_default_prices(self) -> Dict:
        """Default pricing when file is not available"""
        return {
            "cloud_providers": {
                "gpt-4o": {"average_per_1k": 0.010},
                "gpt-4o-mini": {"average_per_1k": 0.0004},
                "claude-3-sonnet": {"average_per_1k": 0.009},
                "claude-3-haiku": {"average_per_1k": 0.0007},
                "mistral-large": {"average_per_1k": 0.016}
            },
            "local_models": {
                "tinyllama_1b": 0.00001,
                "mistral_7b_instruct": 0.0002
            },
            "budget_config": {
                "daily_limit_usd": 0.20,
                "warning_threshold": 0.80,
                "emergency_threshold": 0.95
            }
        }
    
    def estimate_request_cost(self, models: List[str], estimated_tokens: int = 1000) -> float:
        """
        Estimate cost for a request with given models and token count
        
        Args:
            models: List of model names to check
            estimated_tokens: Estimated token count for the request
            
        Returns:
            Estimated cost in USD
        """
        total_cost = 0.0
        
        for model in models:
            # Check cloud providers first
            if model in self.prices["cloud_providers"]:
                cost_per_1k = self.prices["cloud_providers"][model]["average_per_1k"]
                total_cost += (estimated_tokens / 1000.0) * cost_per_1k
            # Then check local models
            elif model in self.prices["local_models"]:
                cost_per_1k = self.prices["local_models"][model]
                total_cost += (estimated_tokens / 1000.0) * cost_per_1k
            else:
                # Unknown model - assume medium cloud cost
                total_cost += (estimated_tokens / 1000.0) * 0.005
        
        return total_cost
    
    def get_budget_status(self) -> Dict[str, float]:
        """Get current budget utilization status"""
        current_spend = cost_ledger.rolling_cost_dollars
        utilization = (current_spend / self.daily_limit) * 100
        
        status = {
            "current_spend_usd": current_spend,
            "daily_limit_usd": self.daily_limit,
            "utilization_percent": utilization,
            "remaining_usd": self.daily_limit - current_spend,
            "warning_threshold": self.warning_threshold,
            "emergency_threshold": self.emergency_threshold,
            "is_warning": utilization >= (self.warning_threshold * 100),
            "is_emergency": utilization >= (self.emergency_threshold * 100)
        }
        
        # Update Prometheus metric
        if PROMETHEUS_AVAILABLE:
            BUDGET_UTILIZATION.set(utilization)
        
        return status
    
    def should_use_cloud(self, estimated_cost: float) -> Tuple[bool, str]:
        """
        Decide if cloud models should be used based on cost and budget
        
        Args:
            estimated_cost: Estimated cost for the request
            
        Returns:
            (should_use_cloud, reason)
        """
        budget_status = self.get_budget_status()
        
        # Check if request would exceed daily budget
        projected_spend = budget_status["current_spend_usd"] + estimated_cost
        
        if projected_spend > self.daily_limit:
            return False, f"Would exceed daily budget (${projected_spend:.4f} > ${self.daily_limit})"
        
        # Check if we're in emergency threshold
        if budget_status["is_emergency"]:
            return False, f"Emergency threshold exceeded ({budget_status['utilization_percent']:.1f}%)"
        
        # Check if we're in warning threshold and this is a large request
        if budget_status["is_warning"] and estimated_cost > 0.01:  # $0.01+ requests
            return False, f"Warning threshold active + large request (${estimated_cost:.4f})"
        
        return True, "Budget allows cloud usage"
    
    def get_fallback_models(self, original_models: List[str]) -> List[str]:
        """
        Get local fallback models when cloud budget is exceeded
        
        Args:
            original_models: Original cloud model selection
            
        Returns:
            List of local fallback models
        """
        fallback_map = {
            # Map cloud models to local equivalents
            "gpt-4o": "mistral_7b_instruct",
            "gpt-4o-mini": "tinyllama_1b", 
            "gpt-4-turbo": "mistral_7b_instruct",
            "claude-3-opus": "mistral_7b_instruct",
            "claude-3-sonnet": "mistral_7b_instruct",
            "claude-3-haiku": "tinyllama_1b",
            "mistral-large": "mistral_7b_instruct",
            "mistral-medium": "tinyllama_1b",
            "mistral-small": "tinyllama_1b"
        }
        
        fallbacks = []
        for model in original_models:
            if model in fallback_map:
                fallbacks.append(fallback_map[model])
            elif model in self.prices["local_models"]:
                # Already local, keep it
                fallbacks.append(model)
            else:
                # Unknown model, default to cheapest local
                fallbacks.append("tinyllama_1b")
        
        return fallbacks
    
    def make_slot_decision(self, 
                          requested_models: List[str], 
                          estimated_tokens: int = 1000,
                          quality_requirement: str = "standard") -> SlotDecision:
        """
        Make a cost-aware slotting decision
        
        Args:
            requested_models: Models requested by the Council
            estimated_tokens: Estimated token count for the request
            quality_requirement: "high", "standard", or "low"
            
        Returns:
            SlotDecision with selected models and reasoning
        """
        # Estimate cost for requested models
        estimated_cost = self.estimate_request_cost(requested_models, estimated_tokens)
        
        # Record cost estimate
        if PROMETHEUS_AVAILABLE:
            REQUEST_COST_ESTIMATE.observe(estimated_cost)
        
        # Check budget constraints
        can_use_cloud, budget_reason = self.should_use_cloud(estimated_cost)
        
        if can_use_cloud:
            # Budget allows cloud usage
            decision = SlotDecision(
                models=requested_models,
                estimated_cost=estimated_cost,
                decision_type="cloud_approved",
                reason=f"Budget OK: {budget_reason}"
            )
            
            if PROMETHEUS_AVAILABLE:
                SLOT_DECISIONS.labels(decision_type="cloud_approved").inc()
                
        else:
            # Need to fall back to local models
            fallback_models = self.get_fallback_models(requested_models)
            fallback_cost = self.estimate_request_cost(fallback_models, estimated_tokens)
            
            decision = SlotDecision(
                models=fallback_models,
                estimated_cost=fallback_cost,
                decision_type="local_fallback",
                reason=f"Cloud blocked: {budget_reason}"
            )
            
            if PROMETHEUS_AVAILABLE:
                SLOT_DECISIONS.labels(decision_type="local_fallback").inc()
        
        print(f"🎯 Slot Decision: {decision.decision_type} - {len(decision.models)} models, ${decision.estimated_cost:.4f}")
        return decision

# Global slotter instance
model_slotter = ModelSlotter()

# Convenience functions for external use
def make_slot_decision(models: List[str], estimated_tokens: int = 1000) -> SlotDecision:
    """Convenience function for making slot decisions"""
    return model_slotter.make_slot_decision(models, estimated_tokens)

def get_budget_status() -> Dict[str, float]:
    """Convenience function for getting budget status"""
    return model_slotter.get_budget_status() 