#!/usr/bin/env python3
"""
QA-302: Streaming Auditor - Property-Based Test Suite
🧪 Gemini-Audit Meta Assertion Validation with Adversarial Fuzzing

Uses hypothesis property-based testing to validate PR meta fields across
hundreds of noisy real-world conditions, ensuring fault-tolerant audit enforcement.
"""

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

import pytest
from hypothesis import given, strategies as st, settings, example, reproduce_failure
from hypothesis.stateful import Bundle, RuleBasedStateMachine, rule, initialize, invariant

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class MetaAssertion:
    """Meta assertion validation result"""
    field_name: str
    value: Any
    expected_range: str
    assertion_result: bool
    violation_type: Optional[str] = None
    red_card_triggered: bool = False
    reproduction_seed: Optional[int] = None

@dataclass
class AuditResult:
    """Complete audit result for a PR meta bundle"""
    pr_id: str
    timestamp: str
    assertions: List[MetaAssertion]
    overall_pass: bool
    violations: List[str]
    red_card_comment: Optional[str] = None
    rollback_triggered: bool = False
    reproduction_seeds: List[int] = None

class GeminiAuditPolicy:
    """Gemini audit policy enforcement with property-based validation"""
    
    def __init__(self):
        self.policy_rules = {
            'unit_coverage': {
                'min_value': 95,
                'max_value': 100,
                'violation_threshold': 95,
                'assertion': lambda x: x >= 95
            },
            'latency_regression': {
                'min_value': -5.0,
                'max_value': 5.0,
                'violation_threshold': 1.0,
                'assertion': lambda x: x <= 1.0
            },
            'cost_delta': {
                'min_value': -0.5,
                'max_value': 0.5,
                'violation_threshold': 0.01,
                'assertion': lambda x: abs(x) <= 0.01
            }
        }
        self.violation_count = 0
        self.red_card_count = 0
        self.audit_history = []

    def validate_field(self, field_name: str, value: Any, seed: Optional[int] = None) -> MetaAssertion:
        """Validate a single meta field against policy"""
        if field_name not in self.policy_rules:
            return MetaAssertion(
                field_name=field_name,
                value=value,
                expected_range="unknown",
                assertion_result=False,
                violation_type="unknown_field",
                reproduction_seed=seed
            )
        
        policy = self.policy_rules[field_name]
        assertion_result = policy['assertion'](value)
        
        violation_type = None
        red_card_triggered = False
        
        if not assertion_result:
            self.violation_count += 1
            
            # Determine violation type
            if field_name == 'unit_coverage' and value < policy['violation_threshold']:
                violation_type = "coverage_below_threshold"
                red_card_triggered = True
            elif field_name == 'latency_regression' and value > policy['violation_threshold']:
                violation_type = "latency_regression_detected"
                red_card_triggered = True
            elif field_name == 'cost_delta' and abs(value) > policy['violation_threshold']:
                violation_type = "cost_delta_exceeded"
                red_card_triggered = True
            
            if red_card_triggered:
                self.red_card_count += 1
        
        expected_range = f"[{policy['min_value']}, {policy['max_value']}]"
        
        return MetaAssertion(
            field_name=field_name,
            value=value,
            expected_range=expected_range,
            assertion_result=assertion_result,
            violation_type=violation_type,
            red_card_triggered=red_card_triggered,
            reproduction_seed=seed
        )

    def audit_pr_meta(self, pr_meta: Dict[str, Any], pr_id: str = None) -> AuditResult:
        """Audit complete PR meta bundle"""
        if pr_id is None:
            pr_id = f"PR-{uuid.uuid4().hex[:8]}"
        
        assertions = []
        violations = []
        red_card_comment = None
        rollback_triggered = False
        reproduction_seeds = []
        
        # Validate each field
        for field_name in ['unit_coverage', 'latency_regression', 'cost_delta']:
            if field_name in pr_meta:
                seed = pr_meta.get(f'{field_name}_seed', None)
                assertion = self.validate_field(field_name, pr_meta[field_name], seed)
                assertions.append(assertion)
                
                if not assertion.assertion_result:
                    violations.append(f"{field_name}: {assertion.violation_type}")
                    
                if assertion.red_card_triggered:
                    rollback_triggered = True
                    if seed:
                        reproduction_seeds.append(seed)
        
        overall_pass = len(violations) == 0
        
        # Generate red card comment if needed
        if rollback_triggered:
            red_card_comment = self.generate_red_card_comment(pr_id, violations, reproduction_seeds)
        
        result = AuditResult(
            pr_id=pr_id,
            timestamp=datetime.now().isoformat(),
            assertions=assertions,
            overall_pass=overall_pass,
            violations=violations,
            red_card_comment=red_card_comment,
            rollback_triggered=rollback_triggered,
            reproduction_seeds=reproduction_seeds
        )
        
        self.audit_history.append(result)
        return result

    def generate_red_card_comment(self, pr_id: str, violations: List[str], seeds: List[int]) -> str:
        """Generate red card comment for policy violations"""
        comment = f"""🚫 **Gemini Policy Violation (property-fuzzed)**

**PR**: {pr_id}
**Timestamp**: {datetime.now().isoformat()}
**Audit Status**: FAILED

**Policy Violations**:
"""
        
        for violation in violations:
            comment += f"- ❌ {violation}\n"
        
        if seeds:
            comment += f"""
**Reproduction Seeds**:
```bash
# Reproduce this failure:
"""
            for seed in seeds:
                comment += f"hypothesis reproduce {seed}\n"
            comment += "```\n"
        
        comment += """
**Required Actions**:
1. ⚠️ **ROLLBACK TRIGGERED** - PR blocked from merge
2. 🔍 Review audit violations above
3. 🛠️ Fix issues and re-submit for audit
4. 🧪 Run property tests locally before re-submission

**Rollback Command**:
```bash
git checkout HEAD~1  # Revert to last known good state
```

*This comment was generated by QA-302 Streaming Auditor*
"""
        return comment

    def get_metrics(self) -> Dict[str, Any]:
        """Get audit metrics for Prometheus"""
        total_audits = len(self.audit_history)
        passed_audits = len([a for a in self.audit_history if a.overall_pass])
        
        return {
            'gemini_meta_assertions_total': {
                'result=pass': passed_audits,
                'result=fail': total_audits - passed_audits,
                'result=red_card': self.red_card_count
            },
            'gemini_violation_count': self.violation_count,
            'gemini_red_card_count': self.red_card_count,
            'gemini_audit_success_rate': passed_audits / total_audits if total_audits > 0 else 0.0
        }

# Property-based test strategies
unit_coverage_strategy = st.integers(min_value=0, max_value=100)
latency_regression_strategy = st.floats(min_value=-5.0, max_value=5.0, allow_nan=False, allow_infinity=False)
cost_delta_strategy = st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)

class TestGeminiAuditProperties:
    """Property-based tests for Gemini audit enforcement"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.policy = GeminiAuditPolicy()
    
    @given(coverage=unit_coverage_strategy)
    @settings(max_examples=100, deadline=None)
    def test_unit_coverage_property(self, coverage):
        """Property test: unit_coverage field validation"""
        seed = getattr(coverage, '_hypothesis_internal_repr', None)
        
        assertion = self.policy.validate_field('unit_coverage', coverage, seed)
        
        # Property: coverage >= 95 should pass, < 95 should fail with red card
        if coverage >= 95:
            assert assertion.assertion_result is True
            assert assertion.violation_type is None
            assert assertion.red_card_triggered is False
        else:
            assert assertion.assertion_result is False
            assert assertion.violation_type == "coverage_below_threshold"
            assert assertion.red_card_triggered is True
        
        # Property: field_name and value should always be preserved
        assert assertion.field_name == 'unit_coverage'
        assert assertion.value == coverage
    
    @given(latency=latency_regression_strategy)
    @settings(max_examples=100, deadline=None)
    def test_latency_regression_property(self, latency):
        """Property test: latency_regression field validation"""
        seed = getattr(latency, '_hypothesis_internal_repr', None)
        
        assertion = self.policy.validate_field('latency_regression', latency, seed)
        
        # Property: latency <= 1.0 should pass, > 1.0 should fail with red card
        if latency <= 1.0:
            assert assertion.assertion_result is True
            assert assertion.violation_type is None
            assert assertion.red_card_triggered is False
        else:
            assert assertion.assertion_result is False
            assert assertion.violation_type == "latency_regression_detected"
            assert assertion.red_card_triggered is True
        
        # Property: field_name and value should always be preserved
        assert assertion.field_name == 'latency_regression'
        assert assertion.value == latency
    
    @given(cost=cost_delta_strategy)
    @settings(max_examples=100, deadline=None)
    def test_cost_delta_property(self, cost):
        """Property test: cost_delta field validation"""
        seed = getattr(cost, '_hypothesis_internal_repr', None)
        
        assertion = self.policy.validate_field('cost_delta', cost, seed)
        
        # Property: abs(cost) <= 0.01 should pass, > 0.01 should fail with red card
        if abs(cost) <= 0.01:
            assert assertion.assertion_result is True
            assert assertion.violation_type is None
            assert assertion.red_card_triggered is False
        else:
            assert assertion.assertion_result is False
            assert assertion.violation_type == "cost_delta_exceeded"
            assert assertion.red_card_triggered is True
        
        # Property: field_name and value should always be preserved
        assert assertion.field_name == 'cost_delta'
        assert assertion.value == cost
    
    @given(
        coverage=unit_coverage_strategy,
        latency=latency_regression_strategy,
        cost=cost_delta_strategy
    )
    @settings(max_examples=200, deadline=None)
    def test_complete_pr_meta_property(self, coverage, latency, cost):
        """Property test: complete PR meta bundle validation"""
        pr_meta = {
            'unit_coverage': coverage,
            'latency_regression': latency,
            'cost_delta': cost,
            'unit_coverage_seed': hash(coverage) % 10000,
            'latency_regression_seed': hash(latency) % 10000,
            'cost_delta_seed': hash(cost) % 10000
        }
        
        result = self.policy.audit_pr_meta(pr_meta)
        
        # Property: overall_pass should be true only if all assertions pass
        expected_pass = (coverage >= 95 and latency <= 1.0 and abs(cost) <= 0.01)
        assert result.overall_pass == expected_pass
        
        # Property: red_card should be triggered if any field violates policy
        expected_red_card = (coverage < 95 or latency > 1.0 or abs(cost) > 0.01)
        assert result.rollback_triggered == expected_red_card
        
        # Property: number of assertions should equal number of fields
        assert len(result.assertions) == 3
        
        # Property: if red card triggered, comment should be generated
        if result.rollback_triggered:
            assert result.red_card_comment is not None
            assert "🚫 Gemini Policy Violation" in result.red_card_comment
            assert "ROLLBACK TRIGGERED" in result.red_card_comment

    @example(coverage=94, latency=1.5, cost=0.02)  # Known failure case
    @given(
        coverage=st.integers(min_value=0, max_value=94),  # Force failures
        latency=st.floats(min_value=1.01, max_value=5.0, allow_nan=False),
        cost=st.floats(min_value=0.011, max_value=0.5, allow_nan=False)
    )
    @settings(max_examples=50, deadline=None)
    def test_guaranteed_failure_scenarios(self, coverage, latency, cost):
        """Property test: scenarios that should always fail"""
        pr_meta = {
            'unit_coverage': coverage,
            'latency_regression': latency,
            'cost_delta': cost
        }
        
        result = self.policy.audit_pr_meta(pr_meta)
        
        # Property: these scenarios should always fail
        assert result.overall_pass is False
        assert result.rollback_triggered is True
        assert len(result.violations) >= 1
        assert result.red_card_comment is not None
        
        # Property: red card comment should contain violation details
        assert "Policy Violations" in result.red_card_comment
        assert "ROLLBACK TRIGGERED" in result.red_card_comment

class TestGeminiAuditStateMachine(RuleBasedStateMachine):
    """Stateful property testing for Gemini audit workflow"""
    
    def __init__(self):
        super().__init__()
        self.policy = GeminiAuditPolicy()
        self.pr_count = 0
    
    pr_metas = Bundle('pr_metas')
    
    @rule(target=pr_metas, 
          coverage=unit_coverage_strategy,
          latency=latency_regression_strategy,
          cost=cost_delta_strategy)
    def generate_pr_meta(self, coverage, latency, cost):
        """Generate a PR meta bundle"""
        self.pr_count += 1
        return {
            'unit_coverage': coverage,
            'latency_regression': latency,
            'cost_delta': cost,
            'pr_number': self.pr_count
        }
    
    @rule(pr_meta=pr_metas)
    def audit_pr(self, pr_meta):
        """Audit a PR meta bundle"""
        result = self.policy.audit_pr_meta(pr_meta)
        
        # Invariant: audit result should always have required fields
        assert result.pr_id is not None
        assert result.timestamp is not None
        assert isinstance(result.assertions, list)
        assert isinstance(result.overall_pass, bool)
        assert isinstance(result.violations, list)
    
    @invariant()
    def audit_history_consistency(self):
        """Invariant: audit history should be consistent"""
        # Total audits should equal number of audit_pr calls
        assert len(self.policy.audit_history) <= self.pr_count
        
        # Violation count should not exceed total audits * 3 (max violations per audit)
        assert self.policy.violation_count <= len(self.policy.audit_history) * 3
        
        # Red card count should not exceed violation count
        assert self.policy.red_card_count <= self.policy.violation_count

class TestGeminiMetrics:
    """Test Gemini audit metrics generation"""
    
    def test_metrics_generation(self):
        """Test metrics are generated correctly"""
        policy = GeminiAuditPolicy()
        
        # Generate some test audits
        test_cases = [
            {'unit_coverage': 98, 'latency_regression': 0.5, 'cost_delta': 0.005},  # Pass
            {'unit_coverage': 90, 'latency_regression': 0.5, 'cost_delta': 0.005},  # Fail - coverage
            {'unit_coverage': 98, 'latency_regression': 2.0, 'cost_delta': 0.005},  # Fail - latency
            {'unit_coverage': 98, 'latency_regression': 0.5, 'cost_delta': 0.05},   # Fail - cost
        ]
        
        for i, meta in enumerate(test_cases):
            policy.audit_pr_meta(meta, f"test-pr-{i}")
        
        metrics = policy.get_metrics()
        
        assert metrics['gemini_meta_assertions_total']['result=pass'] == 1
        assert metrics['gemini_meta_assertions_total']['result=fail'] == 3
        assert metrics['gemini_meta_assertions_total']['result=red_card'] == 3
        assert metrics['gemini_violation_count'] == 3
        assert metrics['gemini_red_card_count'] == 3
        assert metrics['gemini_audit_success_rate'] == 0.25

def test_red_card_comment_generation():
    """Test red card comment generation with reproduction seeds"""
    policy = GeminiAuditPolicy()
    
    pr_meta = {
        'unit_coverage': 85,  # Below threshold
        'latency_regression': 2.5,  # Above threshold
        'cost_delta': 0.05,  # Above threshold
        'unit_coverage_seed': 12345,
        'latency_regression_seed': 67890,
        'cost_delta_seed': 54321
    }
    
    result = policy.audit_pr_meta(pr_meta, "test-pr-red-card")
    
    assert result.rollback_triggered is True
    assert result.red_card_comment is not None
    assert "🚫 Gemini Policy Violation" in result.red_card_comment
    assert "ROLLBACK TRIGGERED" in result.red_card_comment
    assert "hypothesis reproduce" in result.red_card_comment
    assert "12345" in result.red_card_comment
    assert "67890" in result.red_card_comment
    assert "54321" in result.red_card_comment

def test_integration_with_ci():
    """Test integration with CI environment"""
    # Simulate CI environment variables
    os.environ['CI'] = 'true'
    os.environ['GITHUB_PR_NUMBER'] = '42'
    os.environ['GITHUB_SHA'] = 'abc123'
    
    policy = GeminiAuditPolicy()
    
    # Test with failing meta that should trigger CI failure
    failing_meta = {
        'unit_coverage': 80,  # Below threshold
        'latency_regression': 0.5,
        'cost_delta': 0.005
    }
    
    result = policy.audit_pr_meta(failing_meta, "CI-PR-42")
    
    # In CI, failures should be clearly marked
    assert result.rollback_triggered is True
    assert "coverage_below_threshold" in result.violations
    
    # Cleanup
    del os.environ['CI']
    del os.environ['GITHUB_PR_NUMBER'] 
    del os.environ['GITHUB_SHA']

# Hypothesis state machine test instance
TestGeminiAuditStateMachineRunner = TestGeminiAuditStateMachine.TestCase

if __name__ == "__main__":
    # Run property tests when executed directly
    print("🧪 Running QA-302 Property-Based Test Suite")
    print("=" * 60)
    
    # Create policy instance
    policy = GeminiAuditPolicy()
    
    # Run some example tests
    print("\n📊 Testing policy enforcement...")
    
    test_cases = [
        ('unit_coverage', 98, True),
        ('unit_coverage', 85, False),
        ('latency_regression', 0.5, True),
        ('latency_regression', 2.0, False),
        ('cost_delta', 0.005, True),
        ('cost_delta', 0.05, False)
    ]
    
    for field, value, expected_pass in test_cases:
        result = policy.validate_field(field, value)
        status = "✅ PASS" if result.assertion_result else "❌ FAIL"
        print(f"{field}: {value} → {status}")
        if not result.assertion_result:
            print(f"  🚫 Violation: {result.violation_type}")
    
    print(f"\n📈 Final Metrics:")
    metrics = policy.get_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
    
    print("\n✅ QA-302 Property-Based Test Suite Ready for CI Integration") 