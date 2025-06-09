#!/usr/bin/env python3
"""
Unit tests for Cost-Aware Router Budget Functionality

Tests the B-05 implementation of cost-aware slotting and budget enforcement.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Import the modules we're testing
from router.slotting import ModelSlotter, SlotDecision, make_slot_decision, get_budget_status
from router.cost_tracking import CostLedger

class TestCostAwareRouter:
    """Test suite for cost-aware routing functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Create a test slotter with controlled budget
        self.slotter = ModelSlotter()
        self.slotter.daily_limit = 0.20  # $0.20 daily budget
        
        # Reset cost ledger for clean tests
        self.test_ledger = CostLedger(max_budget_dollars=0.20)
        self.test_ledger.reset_budget()
    
    def test_cloud_approved_within_budget(self):
        """Test that cloud models are approved when within budget"""
        # Test with low-cost models
        models = ["gpt-4o-mini"]  # Should be ~$0.0004 per 1k tokens
        
        with patch('router.slotting.cost_ledger', self.test_ledger):
            decision = self.slotter.make_slot_decision(models, estimated_tokens=1000)
        
        assert decision.decision_type == "cloud_approved"
        assert decision.models == models
        assert decision.estimated_cost < 0.01  # Should be very low cost
    
    def test_local_fallback_when_budget_exceeded(self):
        """Test fallback to local models when budget would be exceeded"""
        # Simulate high current spend
        self.test_ledger.rolling_cost_dollars = 0.19  # Already at $0.19
        
        # Request expensive model
        models = ["gpt-4o"]  # ~$0.01 per 1k tokens
        
        with patch('router.slotting.cost_ledger', self.test_ledger):
            decision = self.slotter.make_slot_decision(models, estimated_tokens=1000)
        
        assert decision.decision_type == "local_fallback"
        assert "mistral_7b_instruct" in decision.models  # Should fallback to local
        assert "Would exceed daily budget" in decision.reason
    
    def test_emergency_threshold_blocks_cloud(self):
        """Test that emergency threshold blocks cloud usage"""
        # Set spend to 95% of budget (emergency threshold)
        self.test_ledger.rolling_cost_dollars = 0.19  # 95% of $0.20
        
        models = ["gpt-4o-mini"]  # Even cheap model should be blocked
        
        with patch('router.slotting.cost_ledger', self.test_ledger):
            decision = self.slotter.make_slot_decision(models, estimated_tokens=100)
        
        assert decision.decision_type == "local_fallback"
        assert "Emergency threshold exceeded" in decision.reason
    
    def test_warning_threshold_with_large_request(self):
        """Test that warning threshold blocks large requests"""
        # Set spend to 80% of budget (warning threshold)
        self.test_ledger.rolling_cost_dollars = 0.16  # 80% of $0.20
        
        # Large expensive request
        models = ["claude-3-opus"]
        
        with patch('router.slotting.cost_ledger', self.test_ledger):
            decision = self.slotter.make_slot_decision(models, estimated_tokens=2000)
        
        assert decision.decision_type == "local_fallback"
        assert "Warning threshold active" in decision.reason
    
    def test_cost_estimation_accuracy(self):
        """Test that cost estimation works correctly for different models"""
        # Test known model costs
        assert self.slotter.estimate_request_cost(["gpt-4o"], 1000) == 0.010
        assert self.slotter.estimate_request_cost(["gpt-4o-mini"], 1000) == 0.0004
        assert self.slotter.estimate_request_cost(["claude-3-haiku"], 1000) == 0.0007
        
        # Test multiple models
        cost = self.slotter.estimate_request_cost(["gpt-4o", "gpt-4o-mini"], 1000)
        assert cost == 0.0104  # 0.010 + 0.0004
    
    def test_fallback_mapping(self):
        """Test that cloud models map to appropriate local fallbacks"""
        fallbacks = self.slotter.get_fallback_models(["gpt-4o", "claude-3-haiku", "mistral-large"])
        
        assert "mistral_7b_instruct" in fallbacks  # gpt-4o -> mistral_7b_instruct
        assert "tinyllama_1b" in fallbacks         # claude-3-haiku -> tinyllama_1b
        assert len(fallbacks) == 3
    
    def test_budget_status_reporting(self):
        """Test budget status calculation and reporting"""
        self.test_ledger.rolling_cost_dollars = 0.10  # 50% of budget
        
        with patch('router.slotting.cost_ledger', self.test_ledger):
            status = self.slotter.get_budget_status()
        
        assert status["current_spend_usd"] == 0.10
        assert status["daily_limit_usd"] == 0.20
        assert status["utilization_percent"] == 50.0
        assert status["remaining_usd"] == 0.10
        assert not status["is_warning"]
        assert not status["is_emergency"]
    
    def test_environment_budget_override(self):
        """Test that environment variable overrides YAML budget"""
        with patch.dict(os.environ, {'SWARM_DAILY_BUDGET_USD': '0.50'}):
            test_slotter = ModelSlotter()
            assert test_slotter.daily_limit == 0.50
    
    def test_unknown_model_fallback(self):
        """Test behavior with unknown model names"""
        # Unknown model should use default cost
        cost = self.slotter.estimate_request_cost(["unknown_model_123"], 1000)
        assert cost == 0.005  # Default medium cost
        
        # Unknown model should fallback to tinyllama
        fallbacks = self.slotter.get_fallback_models(["unknown_model_123"])
        assert fallbacks == ["tinyllama_1b"]

class TestCostLedger:
    """Test suite for cost tracking ledger"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.ledger = CostLedger(max_budget_dollars=0.20)
        self.ledger.reset_budget()
    
    def test_cost_debit_tracking(self):
        """Test that cost debits are tracked correctly"""
        # Record some costs
        cost1 = self.ledger.debit("gpt-4o", 1000, "test-request-1")
        cost2 = self.ledger.debit("tinyllama_1b", 500, "test-request-2")
        
        assert cost1 > 0
        assert cost2 > 0
        assert self.ledger.rolling_cost_dollars == (cost1 + cost2) / 100.0
        assert len(self.ledger.cost_history) == 2
    
    def test_budget_exceeded_detection(self):
        """Test budget exceeded detection"""
        # Add costs until budget exceeded
        while not self.ledger.is_budget_exceeded():
            self.ledger.debit("gpt-4o", 1000)
        
        assert self.ledger.is_budget_exceeded()
        assert self.ledger.rolling_cost_dollars > 0.20
    
    def test_cost_breakdown_by_model(self):
        """Test cost breakdown reporting by model"""
        self.ledger.debit("gpt-4o", 1000)
        self.ledger.debit("gpt-4o", 500)
        self.ledger.debit("tinyllama_1b", 2000)
        
        breakdown = self.ledger.get_cost_by_model()
        
        assert "gpt-4o" in breakdown
        assert "tinyllama_1b" in breakdown
        assert breakdown["gpt-4o"] > breakdown["tinyllama_1b"]  # gpt-4o is more expensive

def test_convenience_functions():
    """Test the convenience functions work correctly"""
    # Test make_slot_decision convenience function
    decision = make_slot_decision(["gpt-4o-mini"], 500)
    assert isinstance(decision, SlotDecision)
    
    # Test get_budget_status convenience function
    status = get_budget_status()
    assert "current_spend_usd" in status
    assert "daily_limit_usd" in status

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 