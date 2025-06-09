#!/usr/bin/env python3
"""
Tests for Sunday Verification Principle enforcement
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from middleware.sunday_verification import (
    sunday_verifier, validate_sunday_principle, enforce_sunday_principle
)

class TestSundayVerificationEngine:
    """Test the core Sunday Verification engine"""

    def test_compliant_response_with_evidence(self):
        """Test response that follows Sunday Verification Principle"""
        
        response = """
        Deployment verified: 6/6 containers running, 65ms p95 latency.
        Health check returns 200 status code.
        CPU usage: 12%, Memory: 3.2GB/16GB.
        Real metrics prove real operation.
        """
        
        result = sunday_verifier.analyze_response(response)
        
        assert result.compliant == True
        assert result.score >= 0.6
        assert "verified:" in result.evidence_markers
        assert "specific_metrics" in result.evidence_markers
        assert len(result.issues) == 0

    def test_non_compliant_vague_response(self):
        """Test response that violates Sunday Verification Principle"""
        
        response = """
        The deployment looks good. Everything seems fine.
        No issues detected. Should work perfectly.
        """
        
        result = sunday_verifier.analyze_response(response)
        
        assert result.compliant == False
        assert result.score < 0.6
        assert "looks good" in str(result.issues)
        assert "seems fine" in str(result.issues)
        assert len(result.suggestions) > 0

    def test_claims_without_evidence(self):
        """Test response making claims without verification"""
        
        response = """
        The system is working perfectly. All components are operational.
        The fix has been completed successfully.
        """
        
        result = sunday_verifier.analyze_response(response)
        
        assert result.compliant == False
        assert "Makes claims without providing verification evidence" in result.issues
        assert "Add concrete metrics" in str(result.suggestions)

    def test_sunday_voice_bonus_points(self):
        """Test that Sunday voice phrases get bonus points"""
        
        response = """
        Trust but verify: checked the actual metrics.
        Container status: 6/6 running (verified through docker ps).
        The pattern is the pattern: real deployment, real metrics.
        """
        
        result = sunday_verifier.analyze_response(response)
        
        assert result.compliant == True
        assert result.score >= 0.8  # High score due to Sunday phrases
        # Note: Sunday phrases are tracked separately from evidence markers

    def test_specific_metrics_detection(self):
        """Test detection of specific metrics"""
        
        response = """
        Performance verified: 65ms p95 latency, 12% CPU usage.
        Memory consumption: 3.2GB/16GB total.
        Error rate: 0.1% over 1000 requests.
        """
        
        result = sunday_verifier.analyze_response(response)
        
        assert result.compliant == True
        assert "specific_metrics" in result.evidence_markers
        assert result.score >= 0.6

class TestValidationFunction:
    """Test the validation function interface"""

    def test_validate_sunday_principle_compliant(self):
        """Test validation function with compliant response"""
        
        response = "Verified: 6/6 containers running, health check returns 200."
        result = validate_sunday_principle(response)
        
        assert result["sunday_compliant"] == True
        assert result["sunday_score"] >= 0.6
        assert result["improvement_needed"] == False
        assert "✅" in result["sunday_feedback"]

    def test_validate_sunday_principle_non_compliant(self):
        """Test validation function with non-compliant response"""
        
        response = "Everything looks good. Should work fine."
        result = validate_sunday_principle(response)
        
        assert result["sunday_compliant"] == False
        assert result["sunday_score"] < 0.6
        assert result["improvement_needed"] == True
        assert "⚠️" in result["sunday_feedback"]

class TestEnforcementFunction:
    """Test the enforcement function"""

    def test_enforce_compliant_response(self):
        """Test enforcement doesn't modify compliant responses"""
        
        original = "Verified: system operational, 65ms latency measured."
        enhanced = enforce_sunday_principle(original)
        
        # Should return original response unchanged
        assert enhanced == original

    def test_enforce_non_compliant_response(self):
        """Test enforcement enhances non-compliant responses"""
        
        original = "Everything looks good."
        enhanced = enforce_sunday_principle(original)
        
        # Should append feedback
        assert len(enhanced) > len(original)
        assert "Sunday Verification" in enhanced
        assert "IMPROVEMENT" in enhanced

class TestRealWorldScenarios:
    """Test with realistic Trinity agent responses"""

    def test_deployment_status_good(self):
        """Test good deployment status response"""
        
        response = """
        🔍 Deployment verification complete:
        
        - Containers: 6/6 running (verified via docker ps)
        - Health endpoints: all returning 200 status codes
        - Performance: 65ms p95 latency (under 100ms target)
        - Error rate: 0.1% over last 1000 requests
        - Resource usage: CPU 12%, Memory 3.2GB/16GB
        
        Trust but verify: concrete evidence confirms operational status.
        """
        
        result = validate_sunday_principle(response)
        assert result["sunday_compliant"] == True
        assert result["sunday_score"] >= 0.8

    def test_deployment_status_bad(self):
        """Test poor deployment status response"""
        
        response = """
        The deployment looks good to me. Everything seems to be running fine.
        No issues detected. Should work without problems.
        """
        
        result = validate_sunday_principle(response)
        assert result["sunday_compliant"] == False
        assert "looks good" in result["sunday_feedback"]
        assert "Add concrete metrics" in result["sunday_feedback"]

    def test_model_performance_good(self):
        """Test good model performance response"""
        
        response = """
        Model performance verified:
        - Test query "2+2" returns "4" (correct output confirmed)
        - Inference latency: 45ms average, 65ms p95
        - Memory usage: 2.1GB VRAM allocated
        - Error count: 0 in last 500 requests
        
        Real metrics prove real operation. Not smoke and mirrors.
        """
        
        result = validate_sunday_principle(response)
        assert result["sunday_compliant"] == True

    def test_model_performance_bad(self):
        """Test poor model performance response"""
        
        response = """
        The model is working fine. Performance seems good.
        Everything appears to be running normally.
        """
        
        result = validate_sunday_principle(response)
        assert result["sunday_compliant"] == False

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 