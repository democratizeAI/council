#!/usr/bin/env python3
"""
Tests for QA-302 Gemini Streaming Auditor Webhook
================================================

Tests the webhook functionality, policy assertions, and rollback triggers
for the Gemini streaming auditor implementation.

Features tested:
- Webhook payload processing
- Policy assertion logic (unit_coverage, latency_regression, cost_delta)
- Rollback trigger mechanism
- Prometheus metrics recording
- Comment posting and notification handling
"""

import pytest
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gemini_audit.main import (
    GeminiStreamingAuditor,
    MetaWebhookPayload,
    PolicyAssertion,
    PolicyViolation
)

class TestGeminiWebhookProcessing:
    """Test webhook processing and policy assertion logic"""
    
    def setup_method(self):
        """Setup test auditor instance"""
        self.auditor = GeminiStreamingAuditor()
        self.auditor.redis_client = AsyncMock()
        
    @pytest.mark.asyncio
    async def test_webhook_payload_parsing(self):
        """Test webhook payload parsing and validation"""
        # Valid payload
        payload_data = {
            "pr_id": "QA-302-test-01",
            "meta": {
                "unit_coverage": 96.5,
                "latency_regression": 0.7,
                "cost_delta": 0.002
            },
            "timestamp": time.time(),
            "source": "ci_pipeline"
        }
        
        payload = MetaWebhookPayload(**payload_data)
        
        assert payload.pr_id == "QA-302-test-01"
        assert payload.meta["unit_coverage"] == 96.5
        assert payload.meta["latency_regression"] == 0.7
        assert payload.meta["cost_delta"] == 0.002
        assert payload.source == "ci_pipeline"
        
    @pytest.mark.asyncio
    async def test_policy_assertions_all_pass(self):
        """Test policy assertions when all policies pass"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-pass-test",
            meta={
                "unit_coverage": 97.0,  # >= 95% ✅
                "latency_regression": 0.5,  # <= 1% ✅
                "cost_delta": 0.005  # <= $0.01 ✅
            }
        )
        
        assertions = await self.auditor._run_policy_assertions(payload)
        
        assert len(assertions) == 3
        assert all(a.passed for a in assertions)
        
        # Check specific assertions
        coverage_assertion = next(a for a in assertions if a.policy_name == "unit_coverage")
        assert coverage_assertion.passed
        assert coverage_assertion.value == 97.0
        assert coverage_assertion.threshold == 95.0
        assert coverage_assertion.operator == ">="
        
        latency_assertion = next(a for a in assertions if a.policy_name == "latency_regression")
        assert latency_assertion.passed
        assert latency_assertion.value == 0.5
        assert latency_assertion.threshold == 1.0
        assert latency_assertion.operator == "<="
        
        cost_assertion = next(a for a in assertions if a.policy_name == "cost_delta")
        assert cost_assertion.passed
        assert cost_assertion.value == 0.005
        assert cost_assertion.threshold == 0.01
        assert cost_assertion.operator == "<="
        
    @pytest.mark.asyncio
    async def test_policy_assertions_coverage_fail(self):
        """Test policy assertions when unit coverage fails"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-coverage-fail",
            meta={
                "unit_coverage": 92.0,  # < 95% ❌
                "latency_regression": 0.5,  # <= 1% ✅
                "cost_delta": 0.005  # <= $0.01 ✅
            }
        )
        
        assertions = await self.auditor._run_policy_assertions(payload)
        
        assert len(assertions) == 3
        failed_assertions = [a for a in assertions if not a.passed]
        assert len(failed_assertions) == 1
        
        coverage_assertion = failed_assertions[0]
        assert coverage_assertion.policy_name == "unit_coverage"
        assert not coverage_assertion.passed
        assert coverage_assertion.value == 92.0
        assert "92.0% vs required 95.0%" in coverage_assertion.reason
        
    @pytest.mark.asyncio
    async def test_policy_assertions_latency_fail(self):
        """Test policy assertions when latency regression fails"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-latency-fail",
            meta={
                "unit_coverage": 97.0,  # >= 95% ✅
                "latency_regression": 1.5,  # > 1% ❌
                "cost_delta": 0.005  # <= $0.01 ✅
            }
        )
        
        assertions = await self.auditor._run_policy_assertions(payload)
        
        failed_assertions = [a for a in assertions if not a.passed]
        assert len(failed_assertions) == 1
        
        latency_assertion = failed_assertions[0]
        assert latency_assertion.policy_name == "latency_regression"
        assert not latency_assertion.passed
        assert latency_assertion.value == 1.5
        assert "1.5% vs max 1.0%" in latency_assertion.reason
        
    @pytest.mark.asyncio
    async def test_policy_assertions_cost_fail(self):
        """Test policy assertions when cost delta fails"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-cost-fail",
            meta={
                "unit_coverage": 97.0,  # >= 95% ✅
                "latency_regression": 0.5,  # <= 1% ✅
                "cost_delta": 0.015  # > $0.01 ❌
            }
        )
        
        assertions = await self.auditor._run_policy_assertions(payload)
        
        failed_assertions = [a for a in assertions if not a.passed]
        assert len(failed_assertions) == 1
        
        cost_assertion = failed_assertions[0]
        assert cost_assertion.policy_name == "cost_delta"
        assert not cost_assertion.passed
        assert cost_assertion.value == 0.015
        assert "$0.015 vs max $0.010" in cost_assertion.reason
        
    @pytest.mark.asyncio
    async def test_policy_assertions_multiple_fail(self):
        """Test policy assertions when multiple policies fail"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-multi-fail",
            meta={
                "unit_coverage": 88.0,  # < 95% ❌
                "latency_regression": 2.1,  # > 1% ❌
                "cost_delta": 0.025  # > $0.01 ❌
            }
        )
        
        assertions = await self.auditor._run_policy_assertions(payload)
        
        failed_assertions = [a for a in assertions if not a.passed]
        assert len(failed_assertions) == 3  # All policies fail
        
        policy_names = {a.policy_name for a in failed_assertions}
        assert policy_names == {"unit_coverage", "latency_regression", "cost_delta"}
        
    @pytest.mark.asyncio
    async def test_pr_monitoring_start(self):
        """Test PR monitoring initialization"""
        pr_id = "QA-302-monitor-test"
        
        # Verify PR not in monitoring initially
        assert pr_id not in self.auditor.monitored_prs
        
        # Start monitoring
        self.auditor._start_pr_monitoring(pr_id)
        
        # Verify PR is now being monitored
        assert pr_id in self.auditor.monitored_prs
        
        pr_data = self.auditor.monitored_prs[pr_id]
        assert "started_at" in pr_data
        assert "violations" in pr_data
        assert "last_check" in pr_data
        assert isinstance(pr_data["violations"], list)
        assert len(pr_data["violations"]) == 0
        
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.patch')
    async def test_patchctl_rollback_trigger(self, mock_patch):
        """Test PatchCtl rollback trigger functionality"""
        # Mock successful PatchCtl response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_patch.return_value.__aenter__.return_value = mock_response
        
        pr_id = "QA-302-rollback-test"
        violations = [
            PolicyAssertion(
                policy_name="unit_coverage",
                value=88.0,
                threshold=95.0,
                operator=">=",
                passed=False,
                reason="Coverage too low"
            )
        ]
        
        # Trigger rollback
        await self.auditor._trigger_patchctl_rollback(pr_id, violations)
        
        # Verify PatchCtl was called
        mock_patch.assert_called_once()
        
        # Check call arguments
        call_args = mock_patch.call_args
        assert f"{self.auditor.patchctl_url}/rollback" in str(call_args)
        
        # Verify payload structure
        call_kwargs = call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        assert payload["pr_id"] == pr_id
        assert payload["reason"] == "gemini_policy_violation"
        assert len(payload["violations"]) == 1
        assert payload["violations"][0]["policy"] == "unit_coverage"
        
    @pytest.mark.asyncio
    async def test_violation_comment_generation(self):
        """Test violation comment generation and storage"""
        pr_id = "QA-302-comment-test"
        violations = [
            PolicyAssertion(
                policy_name="unit_coverage",
                value=88.0,
                threshold=95.0,
                operator=">=",
                passed=False,
                reason="Coverage too low"
            ),
            PolicyAssertion(
                policy_name="cost_delta",
                value=0.025,
                threshold=0.01,
                operator="<=",
                passed=False,
                reason="Cost too high"
            )
        ]
        
        # Generate violation comment
        await self.auditor._post_violation_comment(pr_id, violations)
        
        # Verify comment was stored in Redis
        self.auditor.redis_client.hset.assert_called_once()
        
        call_args = self.auditor.redis_client.hset.call_args
        assert call_args[0][0] == f"gemini:comments:{pr_id}"
        assert call_args[0][1] == "violation_comment"
        
        comment_body = call_args[0][2]
        assert "CI Policy Violation Detected" in comment_body
        assert pr_id in comment_body
        assert "unit_coverage" in comment_body
        assert "cost_delta" in comment_body
        assert "Automatic rollback triggered" in comment_body
        assert "Signed by Gemini Streaming Auditor" in comment_body
        
    @pytest.mark.asyncio
    async def test_signature_generation(self):
        """Test webhook comment signature generation"""
        import asyncio
        
        pr_id = "QA-302-signature-test"
        
        signature1 = self.auditor._generate_signature(pr_id)
        await asyncio.sleep(0.001)  # Small delay to ensure different timestamp
        signature2 = self.auditor._generate_signature(pr_id)
        
        # Signatures should be 16 characters (hex)
        assert len(signature1) == 16
        assert len(signature2) == 16
        
        # Signatures should be different due to timestamp
        assert signature1 != signature2
        
        # Should be valid hex
        assert all(c in "0123456789abcdef" for c in signature1)
        assert all(c in "0123456789abcdef" for c in signature2)

class TestWebhookIntegration:
    """Integration tests for full webhook processing flow"""
    
    def setup_method(self):
        """Setup test auditor with mocked dependencies"""
        self.auditor = GeminiStreamingAuditor()
        self.auditor.redis_client = AsyncMock()
        
    @pytest.mark.asyncio
    @patch('services.gemini_audit.main.aiohttp.ClientSession.patch')
    async def test_full_webhook_process_success(self, mock_patch):
        """Test complete webhook processing for successful policies"""
        # Mock PatchCtl response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_patch.return_value.__aenter__.return_value = mock_response
        
        payload = MetaWebhookPayload(
            pr_id="QA-302-integration-pass",
            meta={
                "unit_coverage": 97.0,
                "latency_regression": 0.5,
                "cost_delta": 0.005
            }
        )
        
        result = await self.auditor.process_meta_webhook(payload)
        
        # Verify successful processing
        assert result["result"] == "policies_passed"
        assert result["violations"] == 0
        assert len(result["assertions"]) == 3
        assert all(a["passed"] for a in result["assertions"])
        
        # Verify PR is being monitored
        assert payload.pr_id in self.auditor.monitored_prs
        
        # Verify no rollback was triggered
        mock_patch.assert_not_called()
        
    @pytest.mark.asyncio
    @patch('services.gemini_audit.main.aiohttp.ClientSession.patch')
    async def test_full_webhook_process_violation(self, mock_patch):
        """Test complete webhook processing for policy violations"""
        # Mock PatchCtl response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_patch.return_value.__aenter__.return_value = mock_response
        
        payload = MetaWebhookPayload(
            pr_id="QA-302-integration-fail",
            meta={
                "unit_coverage": 88.0,  # Violates coverage policy
                "latency_regression": 2.5,  # Violates latency policy
                "cost_delta": 0.005  # Passes cost policy
            }
        )
        
        result = await self.auditor.process_meta_webhook(payload)
        
        # Verify violation detection
        assert result["result"] == "violation_detected"
        assert result["violations"] == 2
        assert len(result["assertions"]) == 3
        
        # Check specific assertion results
        assertions = {a["policy_name"]: a for a in result["assertions"]}
        assert not assertions["unit_coverage"]["passed"]
        assert not assertions["latency_regression"]["passed"]
        assert assertions["cost_delta"]["passed"]
        
        # Verify PR is being monitored with violations
        assert payload.pr_id in self.auditor.monitored_prs
        pr_data = self.auditor.monitored_prs[payload.pr_id]
        assert len(pr_data["violations"]) == 2
        
        # Verify rollback was triggered
        mock_patch.assert_called_once()
        
        # Verify comment was posted
        self.auditor.redis_client.hset.assert_called()

class TestPrometheusMetrics:
    """Test Prometheus metrics recording"""
    
    def setup_method(self):
        """Setup test environment"""
        self.auditor = GeminiStreamingAuditor()
        self.auditor.redis_client = AsyncMock()
        
    @pytest.mark.asyncio
    @patch('services.gemini_audit.main.GEMINI_META_ASSERTIONS_TOTAL')
    @patch('services.gemini_audit.main.GEMINI_ROLLBACK_TRIGGERED_TOTAL')
    async def test_metrics_recording_pass(self, mock_rollback_metric, mock_assertion_metric):
        """Test metrics recording for passing policies"""
        payload = MetaWebhookPayload(
            pr_id="QA-302-metrics-pass",
            meta={
                "unit_coverage": 97.0,
                "latency_regression": 0.5,
                "cost_delta": 0.005
            }
        )
        
        await self.auditor.process_meta_webhook(payload)
        
        # Verify assertion metrics were recorded
        assert mock_assertion_metric.labels.call_count == 3  # 3 policies
        
        # Verify all assertions recorded as "pass"
        for call in mock_assertion_metric.labels.call_args_list:
            assert call[1]["result"] == "pass"
            
        # Verify no rollback metrics
        mock_rollback_metric.labels.assert_not_called()
        
    @pytest.mark.asyncio
    @patch('services.gemini_audit.main.GEMINI_META_ASSERTIONS_TOTAL')
    @patch('services.gemini_audit.main.GEMINI_ROLLBACK_TRIGGERED_TOTAL')
    @patch('services.gemini_audit.main.aiohttp.ClientSession.patch')
    async def test_metrics_recording_fail(self, mock_patch, mock_rollback_metric, mock_assertion_metric):
        """Test metrics recording for failing policies"""
        # Mock PatchCtl response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_patch.return_value.__aenter__.return_value = mock_response
        
        payload = MetaWebhookPayload(
            pr_id="QA-302-metrics-fail",
            meta={
                "unit_coverage": 88.0,  # Fail
                "latency_regression": 2.5,  # Fail
                "cost_delta": 0.005  # Pass
            }
        )
        
        await self.auditor.process_meta_webhook(payload)
        
        # Verify assertion metrics were recorded
        assert mock_assertion_metric.labels.call_count == 3
        
        # Verify rollback metrics were recorded for violations
        assert mock_rollback_metric.labels.call_count == 2  # 2 violations

class TestSlackIntegration:
    """Test Slack notification functionality"""
    
    def setup_method(self):
        """Setup test environment with Slack webhook"""
        self.auditor = GeminiStreamingAuditor()
        self.auditor.redis_client = AsyncMock()
        self.auditor.slack_webhook = "https://hooks.slack.com/test"
        
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.post')
    async def test_slack_notification_send(self, mock_post):
        """Test Slack notification sending"""
        # Mock successful Slack response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        pr_id = "QA-302-slack-test"
        violations = [
            PolicyAssertion(
                policy_name="unit_coverage",
                value=88.0,
                threshold=95.0,
                operator=">=",
                passed=False,
                reason="Coverage too low"
            )
        ]
        
        await self.auditor._send_slack_alert(pr_id, violations)
        
        # Verify Slack API was called
        mock_post.assert_called_once()
        
        # Check payload structure
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        payload = call_kwargs["json"]
        
        assert f"PR {pr_id}" in payload["text"]
        assert len(payload["attachments"]) == 1
        attachment = payload["attachments"][0]
        assert attachment["color"] == "danger"
        assert "unit_coverage" in str(attachment["fields"])

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 