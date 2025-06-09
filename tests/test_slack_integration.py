#!/usr/bin/env python3
"""
Unit Tests for Slack ↔ Trinity Integration
==========================================
Tests for router/slack.py and middleware/corr_id.py
"""

import pytest
import asyncio
import json
import hmac
import hashlib
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Request

from router.slack import router as slack_router, verify_slack_signature, make_uuid
from middleware.corr_id import CorrelationIdMiddleware, get_correlation_id

# Test app setup
app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
app.include_router(slack_router)

client = TestClient(app)

class TestSlackSignatureVerification:
    """Test HMAC signature verification"""
    
    def test_valid_signature(self):
        """Test valid Slack signature verification"""
        body = "token=test&command=/o3&text=ping"
        timestamp = "1234567890"
        signing_secret = "test_secret"
        
        # Generate expected signature
        basestring = f"v0:{timestamp}:{body}"
        expected_sig = "v0=" + hmac.new(
            signing_secret.encode(),
            basestring.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        result = verify_slack_signature(
            body.encode(), timestamp, expected_sig, signing_secret
        )
        assert result is True
    
    def test_invalid_signature(self):
        """Test invalid signature rejection"""
        body = "token=test&command=/o3&text=ping"
        timestamp = "1234567890"
        signing_secret = "test_secret"
        invalid_signature = "v0=invalid_signature"
        
        result = verify_slack_signature(
            body.encode(), timestamp, invalid_signature, signing_secret
        )
        assert result is False
    
    def test_malformed_signature(self):
        """Test malformed signature handling"""
        body = "test"
        timestamp = "1234567890"
        signing_secret = "test_secret"
        malformed_signature = "invalid_format"
        
        result = verify_slack_signature(
            body.encode(), timestamp, malformed_signature, signing_secret
        )
        assert result is False

class TestSlackCommands:
    """Test Slack command handling"""
    
    def test_slack_commands_endpoint_exists(self):
        """Test that /slack/commands endpoint is accessible"""
        response = client.post("/slack/commands", data={
            "command": "/o3",
            "text": "ping",
            "user_id": "U123456",
            "trigger_id": "12345.67890"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "✅ Received" in data["text"]
        assert "tracking id" in data["text"]
    
    def test_o3_ping_command(self):
        """Test /o3 ping command handling"""
        response = client.post("/slack/commands", data={
            "command": "/o3",
            "text": "ping",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking id" in data["text"]
    
    def test_opus_ping_command(self):
        """Test /opus ping command handling"""
        response = client.post("/slack/commands", data={
            "command": "/opus", 
            "text": "ping",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking id" in data["text"]
    
    def test_ticket_command(self):
        """Test /ticket command handling"""
        response = client.post("/slack/commands", data={
            "command": "/ticket",
            "text": "add title=\"Test ticket\" wave=B owner=Dev effort=2h",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking id" in data["text"]
    
    def test_status_command(self):
        """Test /status command handling"""
        response = client.post("/slack/commands", data={
            "command": "/status",
            "text": "",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking id" in data["text"]
    
    def test_patches_command(self):
        """Test /patches command handling"""
        response = client.post("/slack/commands", data={
            "command": "/patches",
            "text": "",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "tracking id" in data["text"]
    
    def test_unknown_command(self):
        """Test handling of unknown commands"""
        response = client.post("/slack/commands", data={
            "command": "/unknown",
            "text": "test",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        # Should still return tracking ID for unknown commands
        data = response.json()
        assert "tracking id" in data["text"]

class TestSlackInteractive:
    """Test Slack interactive components"""
    
    def test_interactive_endpoint_exists(self):
        """Test that /slack/interactive endpoint exists"""
        payload = json.dumps({
            "type": "block_actions",
            "actions": [{"action_id": "retry_command"}]
        })
        
        response = client.post("/slack/interactive", data={
            "payload": payload
        })
        
        assert response.status_code == 200
    
    def test_retry_button_handling(self):
        """Test retry button interaction"""
        payload = json.dumps({
            "type": "block_actions",
            "actions": [{"action_id": "retry_command"}]
        })
        
        response = client.post("/slack/interactive", data={
            "payload": payload
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "Retrying command" in data["text"]

class TestSlackEvents:
    """Test Slack Events API handling"""
    
    def test_url_verification_challenge(self):
        """Test Slack URL verification challenge"""
        challenge_data = {
            "type": "url_verification",
            "challenge": "test_challenge_string"
        }
        
        response = client.post("/slack/events", json=challenge_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["challenge"] == "test_challenge_string"
    
    def test_app_mention_event(self):
        """Test app mention event handling"""
        event_data = {
            "type": "event_callback",
            "event": {
                "type": "app_mention",
                "text": "@Trinity-Ops help",
                "user": "U123456"
            }
        }
        
        response = client.post("/slack/events", json=event_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
    
    def test_reaction_added_event(self):
        """Test reaction added event handling"""
        event_data = {
            "type": "event_callback", 
            "event": {
                "type": "reaction_added",
                "reaction": "thumbsup",
                "user": "U123456"
            }
        }
        
        response = client.post("/slack/events", json=event_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

class TestSlackWebhooks:
    """Test webhook endpoints for CI/CD integration"""
    
    def test_success_webhook(self):
        """Test success notification webhook"""
        webhook_data = {
            "correlation_id": "test123",
            "event_type": "builder_merge",
            "message": "PR #456 merged successfully"
        }
        
        response = client.post("/slack/webhook/success", json=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["correlation_id"] == "test123"
    
    def test_failure_webhook(self):
        """Test failure notification webhook"""
        webhook_data = {
            "correlation_id": "test123",
            "stage": "Builder",
            "error": "Unit test failed"
        }
        
        response = client.post("/slack/webhook/failure", json=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failure"
        assert data["correlation_id"] == "test123"
        assert data["stage"] == "Builder"
        assert data["retry_available"] is True

class TestSlackHealth:
    """Test Slack service health endpoint"""
    
    def test_health_endpoint(self):
        """Test /slack/health endpoint"""
        response = client.get("/slack/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "slack-integration"
        assert "queue_size" in data
        assert "timestamp" in data

class TestCorrelationIdMiddleware:
    """Test correlation ID middleware functionality"""
    
    def test_correlation_id_generation(self):
        """Test that correlation ID is generated for requests"""
        response = client.post("/slack/commands", data={
            "command": "/o3",
            "text": "ping",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        # Check that correlation ID is in response headers
        assert "X-Corr-ID" in response.headers
        assert len(response.headers["X-Corr-ID"]) > 0
    
    def test_existing_correlation_id_preserved(self):
        """Test that existing correlation ID is preserved"""
        existing_corr_id = "existing123"
        
        response = client.post("/slack/commands", 
            data={
                "command": "/o3",
                "text": "ping", 
                "user_id": "U123456"
            },
            headers={"X-Corr-ID": existing_corr_id}
        )
        
        assert response.status_code == 200
        assert response.headers["X-Corr-ID"] == existing_corr_id

class TestFormEncodedPayload:
    """Test form-encoded Slack payload handling"""
    
    def test_form_encoded_command_parsing(self):
        """Test parsing of form-encoded Slack command payload"""
        # Simulate actual Slack form-encoded payload
        form_data = {
            "token": "test_token",
            "team_id": "T123456", 
            "team_domain": "test-team",
            "channel_id": "C123456",
            "channel_name": "general",
            "user_id": "U123456",
            "user_name": "testuser",
            "command": "/o3",
            "text": "ping",
            "response_url": "https://hooks.slack.com/commands/123",
            "trigger_id": "123.456.789"
        }
        
        response = client.post("/slack/commands", data=form_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["response_type"] == "ephemeral"
        assert "tracking id" in data["text"]

class TestSlackIntegrationFlow:
    """Integration tests for full Slack message flow"""
    
    @pytest.mark.asyncio
    async def test_full_message_flow(self):
        """Test complete message flow with correlation tracking"""
        # 1. Submit command
        response = client.post("/slack/commands", data={
            "command": "/ticket",
            "text": "add title=\"Integration test\" wave=B owner=Test effort=1h",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        correlation_id = response.headers["X-Corr-ID"]
        
        # 2. Test success webhook with same correlation ID  
        success_response = client.post("/slack/webhook/success", json={
            "correlation_id": correlation_id,
            "event_type": "ticket_created",
            "message": "Ticket created successfully"
        })
        
        assert success_response.status_code == 200
        success_data = success_response.json()
        assert success_data["correlation_id"] == correlation_id
    
    def test_error_handling_flow(self):
        """Test error handling and failure notifications"""
        # Submit command that might fail
        response = client.post("/slack/commands", data={
            "command": "/ticket",
            "text": "invalid command format",
            "user_id": "U123456"
        })
        
        assert response.status_code == 200
        correlation_id = response.headers["X-Corr-ID"]
        
        # Test failure webhook
        failure_response = client.post("/slack/webhook/failure", json={
            "correlation_id": correlation_id,
            "stage": "Council",
            "error": "Invalid ticket format"
        })
        
        assert failure_response.status_code == 200
        failure_data = failure_response.json()
        assert failure_data["status"] == "failure"
        assert failure_data["retry_available"] is True

def test_make_uuid_function():
    """Test UUID generation function"""
    uuid1 = make_uuid()
    uuid2 = make_uuid()
    
    # Should generate different UUIDs
    assert uuid1 != uuid2
    # Should be 8 characters (short format)
    assert len(uuid1) == 8
    assert len(uuid2) == 8

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 