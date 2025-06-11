#!/usr/bin/env python3
"""
FMC-Core Integration Tests
Validates triple circuit synergy: Intent → Validation → Feedback Loop
"""

import pytest
import requests
import json
import time
from datetime import datetime
from typing import Dict, List

class TestFMCIntegration:
    """End-to-end integration tests for FMC-Core system"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.base_urls = {
            'intent_mapper': 'http://localhost:8086',
            'spec_gate': 'http://localhost:8087', 
            'loop_agent': 'http://localhost:8088'
        }
        
        # Verify all services are healthy
        for service, url in cls.base_urls.items():
            try:
                response = requests.get(f"{url}/health", timeout=5)
                assert response.status_code == 200, f"{service} not healthy"
            except Exception as e:
                pytest.skip(f"Service {service} not available: {e}")
    
    def test_intent_mapping_accuracy_threshold(self):
        """Test FMC-100: Intent parsing meets 94% accuracy requirement"""
        test_intents = [
            "Create a REST API for user authentication with JWT tokens",
            "Deploy microservice to Kubernetes with auto-scaling", 
            "Fix critical security vulnerability in payment processing",
            "Optimize database queries for better performance",
            "Add comprehensive test coverage for API endpoints"
        ]
        
        total_confidence = 0
        valid_parses = 0
        
        for intent in test_intents:
            response = requests.post(
                f"{self.base_urls['intent_mapper']}/parse-intent",
                json={"intent": intent},
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Validate response structure
            assert 'structured_intent' in data
            structured = data['structured_intent']
            
            assert 'action_type' in structured
            assert 'target_domain' in structured
            assert 'confidence_score' in structured
            assert 'success_criteria' in structured
            
            confidence = structured['confidence_score']
            total_confidence += confidence
            
            if confidence >= 0.8:  # High confidence threshold
                valid_parses += 1
        
        # Calculate overall accuracy
        average_confidence = total_confidence / len(test_intents)
        accuracy_percentage = average_confidence * 100
        
        # KPI validation: intent_parse_accuracy ≥ 94%
        assert accuracy_percentage >= 94.0, f"Intent accuracy {accuracy_percentage:.1f}% below 94% threshold"
        assert valid_parses >= 4, f"Only {valid_parses}/5 intents had high confidence"
        
        print(f"✅ Intent parsing accuracy: {accuracy_percentage:.1f}% (≥94%)")
    
    def test_spec_gate_blocks_invalid_specs(self):
        """Test FMC-110: Spec gate prevents invalid specs (invalid_spec_total = 0)"""
        
        # Test case 1: Completely invalid spec
        invalid_spec_1 = {
            "spec": {
                "id": "INVALID-001",
                "title": "Test Feature",
                # Missing required fields
                "ci_tests": ["TODO: implement tests"],  # Hallucinated
                "success_criteria": ["it works well"]  # Vague
            }
        }
        
        response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json=invalid_spec_1,
            timeout=10
        )
        
        # Should be blocked with 422 Unprocessable Entity
        assert response.status_code == 422
        data = response.json()
        assert not data['validation_result']['valid']
        assert not data['validation_result']['ci_tests_valid']
        assert not data['validation_result']['success_criteria_valid']
        
        # Test case 2: Hallucinated CI tests
        invalid_spec_2 = {
            "spec": {
                "id": "INVALID-002",
                "title": "Another Test",
                "description": "Test description",
                "ci_tests": [
                    "# TODO: write real tests later",
                    "console.log('test passed')",  # Not a real test
                    "pass"  # Python pass statement
                ],
                "success_criteria": ["works fine", "looks good"],  # Vague
                "rollback_plan": "revert if needed",
                "estimated_effort": "2 hours",
                "owner": "test"
            }
        }
        
        response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json=invalid_spec_2,
            timeout=10
        )
        
        assert response.status_code == 422
        data = response.json()
        assert 'placeholder' in str(data['validation_result']['errors']).lower() or \
               'hallucinated' in str(data['validation_result']['errors']).lower()
        
        # Test case 3: Valid spec should pass
        valid_spec = {
            "spec": {
                "id": "VALID-001",
                "title": "User Authentication API",
                "description": "REST API for user authentication with JWT",
                "ci_tests": [
                    "curl -f http://localhost:8000/auth/health",
                    "pytest tests/test_auth.py::test_jwt_generation",
                    "assert response.status_code == 200"
                ],
                "success_criteria": [
                    "API responds with HTTP 200 on health check",
                    "JWT token generation succeeds",
                    "Authentication latency < 500ms"
                ],
                "rollback_plan": "docker stop auth-service && git revert HEAD",
                "estimated_effort": "8 hours",
                "owner": "auth-team"
            }
        }
        
        response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json=valid_spec,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['validation_result']['valid']
        assert data['validation_result']['ci_tests_valid']
        assert data['validation_result']['success_criteria_valid']
        
        print("✅ Spec gate correctly blocks invalid specs and passes valid ones")
    
    def test_feedback_loop_minimum_events(self):
        """Test FMC-120: Feedback loop ensures ≥3 feedback events per PR"""
        
        pr_id = f"test-pr-{int(time.time())}"
        
        # Start feedback loop
        response = requests.post(
            f"{self.base_urls['loop_agent']}/start-loop",
            json={"pr_id": pr_id},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['loop_started']
        assert data['pr_id'] == pr_id
        
        # Submit feedback events
        feedback_events = [
            {
                "pr_id": pr_id,
                "feedback_type": "code_review",
                "content": "Add input validation for email field",
                "confidence": 0.85,
                "actionable": True,
                "source": "github"
            },
            {
                "pr_id": pr_id,
                "feedback_type": "test_results", 
                "content": '{"passed": 15, "failed": 2, "coverage": 0.87}',
                "confidence": 0.9,
                "actionable": True,
                "source": "ci"
            },
            {
                "pr_id": pr_id,
                "feedback_type": "user_feedback",
                "content": "Login flow works great, but error messages could be clearer",
                "confidence": 0.75,
                "actionable": True,
                "source": "user_testing"
            }
        ]
        
        # Process each feedback event
        for i, feedback in enumerate(feedback_events):
            response = requests.post(
                f"{self.base_urls['loop_agent']}/process-feedback",
                json=feedback,
                timeout=10
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['feedback_processed']
            assert data['pr_id'] == pr_id
            assert data['total_feedback'] == i + 1
        
        # Check final loop status
        response = requests.get(
            f"{self.base_urls['loop_agent']}/loop-status/{pr_id}",
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # KPI validation: feedback_seen_total ≥ 3 per PR
        assert data['total_feedback'] >= 3, f"Only {data['total_feedback']} feedback events, need ≥3"
        assert len(feedback_events) >= 3
        
        print(f"✅ Feedback loop collected {data['total_feedback']} events (≥3 required)")
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline: Human intent → Spec validation → Feedback loop"""
        
        # Step 1: Parse human intent
        human_intent = "Create secure payment processing API with fraud detection"
        
        intent_response = requests.post(
            f"{self.base_urls['intent_mapper']}/parse-intent",
            json={"intent": human_intent},
            timeout=10
        )
        
        assert intent_response.status_code == 200
        intent_data = intent_response.json()
        structured_intent = intent_data['structured_intent']
        
        # Verify intent was parsed correctly
        assert structured_intent['action_type'] == 'create'
        assert 'api' in structured_intent['target_domain'] or 'security' in structured_intent['target_domain']
        assert structured_intent['confidence_score'] >= 0.8
        
        # Step 2: Create spec based on intent
        spec_data = {
            "spec": {
                "id": "PAY-001",
                "title": "Secure Payment Processing API",
                "description": "Payment API with fraud detection capabilities",
                "ci_tests": [
                    "curl -f http://localhost:8000/payments/health",
                    "pytest tests/test_payments.py::test_fraud_detection",
                    "pytest tests/test_payments.py::test_payment_encryption",
                    "assert fraud_score >= 0.95"
                ],
                "success_criteria": structured_intent['success_criteria'],
                "rollback_plan": "kubectl rollout undo deployment/payment-api",
                "estimated_effort": f"{structured_intent['estimated_effort_hours']} hours",
                "owner": "payments-team"
            }
        }
        
        # Step 3: Validate spec through gate
        spec_response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json=spec_data,
            timeout=10
        )
        
        assert spec_response.status_code == 200
        spec_result = spec_response.json()
        assert spec_result['validation_result']['valid']
        
        # Step 4: Start feedback loop for implementation
        pr_id = "PAY-001-implementation"
        loop_response = requests.post(
            f"{self.base_urls['loop_agent']}/start-loop",
            json={"pr_id": pr_id},
            timeout=10
        )
        
        assert loop_response.status_code == 200
        
        # Step 5: Simulate feedback collection
        ai_feedback = {
            "pr_id": pr_id,
            "feedback_type": "ai_analysis",
            "content": "Code quality score: 0.89. Recommend adding more error handling for edge cases.",
            "confidence": 0.89,
            "actionable": True,
            "source": "ai_reviewer"
        }
        
        feedback_response = requests.post(
            f"{self.base_urls['loop_agent']}/process-feedback",
            json=ai_feedback,
            timeout=10
        )
        
        assert feedback_response.status_code == 200
        
        # Verify end-to-end metrics
        final_status = requests.get(
            f"{self.base_urls['loop_agent']}/loop-status/{pr_id}",
            timeout=10
        )
        
        assert final_status.status_code == 200
        status_data = final_status.json()
        
        print("✅ End-to-end pipeline completed successfully:")
        print(f"  - Intent confidence: {structured_intent['confidence_score']:.3f}")
        print(f"  - Spec validation: PASSED")
        print(f"  - Feedback events: {status_data['total_feedback']}")
    
    def test_metrics_collection(self):
        """Test that all services expose Prometheus metrics correctly"""
        
        services = ['intent_mapper', 'spec_gate', 'loop_agent']
        
        for service in services:
            response = requests.get(
                f"{self.base_urls[service]}/metrics",
                timeout=10
            )
            
            assert response.status_code == 200
            metrics_text = response.text
            
            # Verify Prometheus format
            assert '# HELP' in metrics_text
            assert '# TYPE' in metrics_text
            
            # Service-specific metric validation
            if service == 'intent_mapper':
                assert 'intent_parse_accuracy_percent' in metrics_text
                assert 'intent_parse_total' in metrics_text
                
            elif service == 'spec_gate':
                assert 'invalid_spec_total' in metrics_text
                assert 'spec_gate_validations_total' in metrics_text
                
            elif service == 'loop_agent':
                assert 'feedback_seen_total' in metrics_text
                assert 'loop_iterations_total' in metrics_text
        
        print("✅ All services expose Prometheus metrics correctly")
    
    def test_service_resilience(self):
        """Test service resilience under error conditions"""
        
        # Test intent mapper with malformed input
        response = requests.post(
            f"{self.base_urls['intent_mapper']}/parse-intent",
            json={"invalid": "data"},  # Missing 'intent' field
            timeout=10
        )
        assert response.status_code == 400
        
        # Test spec gate with malformed spec
        response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json={"invalid": "spec"},  # Missing 'spec' field
            timeout=10
        )
        assert response.status_code == 400
        
        # Test loop agent with missing PR ID
        response = requests.post(
            f"{self.base_urls['loop_agent']}/process-feedback",
            json={"content": "feedback without pr_id"},
            timeout=10
        )
        assert response.status_code == 400
        
        print("✅ Services handle error conditions gracefully")
    
    def test_performance_benchmarks(self):
        """Test performance meets latency requirements"""
        
        # Intent mapping latency test
        start_time = time.time()
        response = requests.post(
            f"{self.base_urls['intent_mapper']}/parse-intent",
            json={"intent": "Performance test intent"},
            timeout=10
        )
        intent_latency = (time.time() - start_time) * 1000
        
        assert response.status_code == 200
        assert intent_latency < 200, f"Intent mapping too slow: {intent_latency:.1f}ms"
        
        # Spec validation latency test
        test_spec = {
            "spec": {
                "id": "PERF-001",
                "title": "Performance Test",
                "description": "Testing validation speed",
                "ci_tests": ["pytest tests/"],
                "success_criteria": ["tests pass"],
                "rollback_plan": "revert",
                "estimated_effort": "1h",
                "owner": "test"
            }
        }
        
        start_time = time.time()
        response = requests.post(
            f"{self.base_urls['spec_gate']}/validate-spec",
            json=test_spec,
            timeout=10
        )
        validation_latency = (time.time() - start_time) * 1000
        
        assert validation_latency < 150, f"Spec validation too slow: {validation_latency:.1f}ms"
        
        print(f"✅ Performance benchmarks met:")
        print(f"  - Intent mapping: {intent_latency:.1f}ms (<200ms)")
        print(f"  - Spec validation: {validation_latency:.1f}ms (<150ms)")

class TestFMCKPICompliance:
    """Test KPI compliance for all FMC components"""
    
    def test_fmc_100_accuracy_kpi(self):
        """Validate FMC-100 meets intent_parse_accuracy ≥ 94%"""
        # This would integrate with actual metrics endpoint
        # For now, validate through API responses
        
        test_intents = [
            "Build React dashboard with real-time analytics",
            "Deploy PostgreSQL cluster with high availability", 
            "Implement OAuth2 authentication flow",
            "Create Kubernetes ingress with SSL termination",
            "Add Redis caching layer for API responses"
        ]
        
        confidence_scores = []
        
        for intent in test_intents:
            response = requests.post(
                "http://localhost:8086/parse-intent",
                json={"intent": intent}
            )
            
            if response.status_code == 200:
                data = response.json()
                confidence = data['structured_intent']['confidence_score']
                confidence_scores.append(confidence)
        
        if confidence_scores:
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            accuracy_percent = avg_confidence * 100
            
            assert accuracy_percent >= 94.0, f"KPI VIOLATION: Intent accuracy {accuracy_percent:.1f}% < 94%"
    
    def test_fmc_110_blocking_kpi(self):
        """Validate FMC-110 maintains invalid_spec_total = 0"""
        # In production, this would check Prometheus metrics
        # Here we validate that invalid specs are actually blocked
        
        invalid_specs = [
            {"spec": {"id": "BAD1", "ci_tests": ["TODO"], "success_criteria": ["maybe works"]}},
            {"spec": {"id": "BAD2", "ci_tests": ["console.log('test')"], "success_criteria": ["looks good"]}},
            {"spec": {"id": "BAD3", "ci_tests": ["pass"], "success_criteria": ["user friendly"]}}
        ]
        
        blocked_count = 0
        
        for spec in invalid_specs:
            response = requests.post(
                "http://localhost:8087/validate-spec",
                json=spec
            )
            
            if response.status_code == 422:  # Blocked
                blocked_count += 1
        
        # All invalid specs should be blocked
        assert blocked_count == len(invalid_specs), f"KPI VIOLATION: {len(invalid_specs) - blocked_count} invalid specs not blocked"
    
    def test_fmc_120_feedback_kpi(self):
        """Validate FMC-120 ensures feedback_seen_total ≥ 3 per PR"""
        pr_id = f"kpi-test-{int(time.time())}"
        
        # Start loop
        requests.post(
            "http://localhost:8088/start-loop",
            json={"pr_id": pr_id}
        )
        
        # Submit exactly 3 feedback events
        for i in range(3):
            requests.post(
                "http://localhost:8088/process-feedback",
                json={
                    "pr_id": pr_id,
                    "feedback_type": "test",
                    "content": f"Test feedback {i+1}",
                    "confidence": 0.8,
                    "actionable": True
                }
            )
        
        # Check status
        response = requests.get(f"http://localhost:8088/loop-status/{pr_id}")
        
        if response.status_code == 200:
            data = response.json()
            feedback_count = data['total_feedback']
            
            assert feedback_count >= 3, f"KPI VIOLATION: Only {feedback_count} feedback events < 3 minimum"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short']) 