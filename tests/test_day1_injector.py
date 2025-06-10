#!/usr/bin/env python3
"""
Unit tests for Day-1 Event Injector (BC-140)
Tests ticket injection, API interaction, and verification logic
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.append('.')

# Mock dependencies
try:
    import requests
except ImportError:
    requests = Mock()

from scripts.day1_injector import Day1Injector, TICKET_TEMPLATES


class TestDay1Injector(unittest.TestCase):
    """Test Day-1 Event Injector functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.injector = Day1Injector(council_url="http://test-council:8080")
    
    def test_initialization(self):
        """Test injector initialization"""
        self.assertEqual(self.injector.council_url, "http://test-council:8080")
        self.assertEqual(self.injector.ledger_endpoint, "http://test-council:8080/ledger/new")
        self.assertIsNotNone(self.injector.session)
        self.assertEqual(self.injector.session.headers["User-Agent"], "day1-injector/BC-140")
        self.assertEqual(self.injector.session.headers["Content-Type"], "application/json")
    
    def test_ticket_templates_structure(self):
        """Test that ticket templates have required structure"""
        required_fields = ["type", "priority", "title", "description", "labels", "assignee", "estimated_hours", "components"]
        
        for ticket_id, template in TICKET_TEMPLATES.items():
            with self.subTest(ticket_id=ticket_id):
                for field in required_fields:
                    self.assertIn(field, template, f"Ticket {ticket_id} missing field: {field}")
                
                # Validate specific field types
                self.assertIn(template["type"], ["bug", "feature"], f"Invalid type in ticket {ticket_id}")
                self.assertIn(template["priority"], ["low", "medium", "high", "critical"], f"Invalid priority in ticket {ticket_id}")
                self.assertIsInstance(template["title"], str, f"Title should be string in ticket {ticket_id}")
                self.assertIsInstance(template["description"], str, f"Description should be string in ticket {ticket_id}")
                self.assertIsInstance(template["labels"], list, f"Labels should be list in ticket {ticket_id}")
                self.assertIsInstance(template["estimated_hours"], int, f"Estimated hours should be int in ticket {ticket_id}")
                self.assertIsInstance(template["components"], list, f"Components should be list in ticket {ticket_id}")
    
    def test_create_ticket_payload_bug_a(self):
        """Test creating payload for Bug A"""
        payload = self.injector.create_ticket_payload("A")
        
        # Check payload structure
        self.assertIn("row_id", payload)
        self.assertIn("row_type", payload)
        self.assertIn("created_at", payload)
        self.assertIn("created_by", payload)
        self.assertIn("ticket_data", payload)
        self.assertIn("metadata", payload)
        
        # Check row metadata
        self.assertEqual(payload["row_type"], "ticket")
        self.assertEqual(payload["created_by"], "day1-injector")
        self.assertTrue(payload["row_id"].startswith("DAY1_A_"))
        
        # Check ticket data
        ticket_data = payload["ticket_data"]
        self.assertEqual(ticket_data["id"], "A")
        self.assertEqual(ticket_data["type"], "bug")
        self.assertEqual(ticket_data["priority"], "high")
        self.assertEqual(ticket_data["status"], "open")
        self.assertIn("Memory leak in council-router", ticket_data["title"])
        self.assertIn("memory", ticket_data["labels"])
        
        # Check metadata
        metadata = payload["metadata"]
        self.assertEqual(metadata["source"], "day1-injector")
        self.assertEqual(metadata["version"], "BC-140")
    
    def test_create_ticket_payload_bug_b(self):
        """Test creating payload for Bug B"""
        payload = self.injector.create_ticket_payload("B")
        
        ticket_data = payload["ticket_data"]
        self.assertEqual(ticket_data["id"], "B")
        self.assertEqual(ticket_data["type"], "bug")
        self.assertEqual(ticket_data["priority"], "medium")
        self.assertIn("Redis connection retry", ticket_data["title"])
        self.assertIn("redis", ticket_data["labels"])
    
    def test_create_ticket_payload_feature_f(self):
        """Test creating payload for Feature F"""
        payload = self.injector.create_ticket_payload("F")
        
        ticket_data = payload["ticket_data"]
        self.assertEqual(ticket_data["id"], "F")
        self.assertEqual(ticket_data["type"], "feature")
        self.assertEqual(ticket_data["priority"], "medium")
        self.assertIn("A2A message compression", ticket_data["title"])
        self.assertIn("feature", ticket_data["labels"])
        self.assertIn("compression", ticket_data["labels"])
    
    def test_create_ticket_payload_with_custom_fields(self):
        """Test creating payload with custom fields"""
        custom_fields = {
            "priority": "critical",
            "assignee": "custom-team",
            "custom_field": "custom_value"
        }
        
        payload = self.injector.create_ticket_payload("A", custom_fields)
        
        ticket_data = payload["ticket_data"]
        self.assertEqual(ticket_data["priority"], "critical")  # Overridden
        self.assertEqual(ticket_data["assignee"], "custom-team")  # Overridden
        self.assertEqual(ticket_data["custom_field"], "custom_value")  # Added
        
        # Original fields should still exist
        self.assertEqual(ticket_data["type"], "bug")  # Original
        self.assertEqual(ticket_data["id"], "A")  # Original
    
    def test_create_ticket_payload_invalid_ticket(self):
        """Test creating payload for invalid ticket ID"""
        with self.assertRaises(ValueError) as context:
            self.injector.create_ticket_payload("INVALID")
        
        self.assertIn("Unknown ticket ID: INVALID", str(context.exception))
        self.assertIn("Available: ['A', 'B', 'F']", str(context.exception))
    
    @patch('scripts.day1_injector.requests.Session.post')
    def test_inject_ticket_success(self, mock_post):
        """Test successful ticket injection"""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "created",
            "row_id": "DAY1_A_1234567890",
            "message": "Ticket created successfully"
        }
        mock_post.return_value = mock_response
        
        result = self.injector.inject_ticket("A")
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["ticket_id"], "A")
        self.assertIn("DAY1_A_", result["row_id"])
        self.assertEqual(result["response"]["status"], "created")
        
        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        self.assertEqual(call_args[0][0], "http://test-council:8080/ledger/new")
        
        # Check payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["ticket_data"]["id"], "A")
        self.assertEqual(payload["row_type"], "ticket")
    
    @patch('scripts.day1_injector.requests.Session.post')
    def test_inject_ticket_api_failure(self, mock_post):
        """Test ticket injection with API failure"""
        # Mock API failure
        mock_post.side_effect = requests.exceptions.RequestException("Connection failed")
        
        result = self.injector.inject_ticket("A")
        
        # Verify failure result
        self.assertFalse(result["success"])
        self.assertEqual(result["ticket_id"], "A")
        self.assertEqual(result["error_type"], "api_request")
        self.assertIn("Connection failed", result["error"])
    
    @patch('scripts.day1_injector.requests.Session.post')
    def test_inject_ticket_http_error(self, mock_post):
        """Test ticket injection with HTTP error"""
        # Mock HTTP error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_post.return_value = mock_response
        
        result = self.injector.inject_ticket("A")
        
        # Verify failure result
        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "api_request")
        self.assertIn("500 Server Error", result["error"])
    
    @patch('scripts.day1_injector.requests.Session.post')
    def test_inject_multiple_tickets_success(self, mock_post):
        """Test injecting multiple tickets successfully"""
        # Mock successful responses
        def mock_response_generator(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            
            # Different response for each ticket
            payload = kwargs["json"]
            ticket_id = payload["ticket_data"]["id"]
            
            response.json.return_value = {
                "status": "created",
                "row_id": payload["row_id"],
                "ticket_id": ticket_id
            }
            return response
        
        mock_post.side_effect = mock_response_generator
        
        # Inject multiple tickets
        summary = self.injector.inject_multiple_tickets(["A", "B", "F"])
        
        # Verify summary
        self.assertEqual(summary["total_tickets"], 3)
        self.assertEqual(summary["successful"], 3)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["success_rate"], 100.0)
        
        # Verify results
        self.assertEqual(len(summary["results"]), 3)
        for result in summary["results"]:
            self.assertTrue(result["success"])
        
        # Verify API calls
        self.assertEqual(mock_post.call_count, 3)
    
    @patch('scripts.day1_injector.requests.Session.post')
    def test_inject_multiple_tickets_partial_failure(self, mock_post):
        """Test injecting multiple tickets with partial failure"""
        # Mock mixed responses
        def mock_response_generator(*args, **kwargs):
            payload = kwargs["json"]
            ticket_id = payload["ticket_data"]["id"]
            
            if ticket_id == "B":
                # Fail ticket B
                raise requests.exceptions.RequestException("API unavailable")
            else:
                # Success for others
                response = Mock()
                response.status_code = 200
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "status": "created",
                    "row_id": payload["row_id"],
                    "ticket_id": ticket_id
                }
                return response
        
        mock_post.side_effect = mock_response_generator
        
        # Inject tickets
        summary = self.injector.inject_multiple_tickets(["A", "B", "F"])
        
        # Verify summary
        self.assertEqual(summary["total_tickets"], 3)
        self.assertEqual(summary["successful"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertAlmostEqual(summary["success_rate"], 66.7, places=1)
        
        # Check individual results
        ticket_a_result = next(r for r in summary["results"] if r["ticket_id"] == "A")
        ticket_b_result = next(r for r in summary["results"] if r["ticket_id"] == "B")
        ticket_f_result = next(r for r in summary["results"] if r["ticket_id"] == "F")
        
        self.assertTrue(ticket_a_result["success"])
        self.assertFalse(ticket_b_result["success"])
        self.assertTrue(ticket_f_result["success"])
    
    @patch('scripts.day1_injector.requests.Session.get')
    def test_check_council_api_health_success(self, mock_get):
        """Test Council API health check success"""
        # Mock successful health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        is_healthy = self.injector.check_council_api_health()
        
        self.assertTrue(is_healthy)
        mock_get.assert_called_once_with("http://test-council:8080/health", timeout=10)
    
    @patch('scripts.day1_injector.requests.Session.get')
    def test_check_council_api_health_failure(self, mock_get):
        """Test Council API health check failure"""
        # Mock failed health response
        mock_response = Mock()
        mock_response.status_code = 503
        mock_get.return_value = mock_response
        
        is_healthy = self.injector.check_council_api_health()
        
        self.assertFalse(is_healthy)
    
    @patch('scripts.day1_injector.requests.Session.get')
    def test_check_council_api_health_exception(self, mock_get):
        """Test Council API health check with exception"""
        # Mock connection exception
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        is_healthy = self.injector.check_council_api_health()
        
        self.assertFalse(is_healthy)
    
    def test_check_builder_ack_metric(self):
        """Test Builder ACK metric check"""
        # This is currently a mock implementation
        result = self.injector.check_builder_ack_metric()
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)
    
    def test_verify_injection_success(self):
        """Test injection success verification"""
        # Mock successful results
        results = [
            {"success": True, "row_id": "DAY1_A_123", "ticket_id": "A"},
            {"success": True, "row_id": "DAY1_B_124", "ticket_id": "B"},
            {"success": False, "ticket_id": "F", "error": "API error"}
        ]
        
        with patch.object(self.injector, 'check_council_api_health', return_value=True):
            with patch.object(self.injector, 'check_builder_ack_metric', return_value=2.0):
                verification = self.injector.verify_injection_success(results)
        
        self.assertTrue(verification["api_health"])
        self.assertEqual(verification["builder_ack_metric"], 2.0)
        self.assertEqual(verification["successful_injections"], 2)
        self.assertEqual(verification["total_injections"], 3)
        self.assertEqual(len(verification["row_ids"]), 2)
        self.assertIn("DAY1_A_123", verification["row_ids"])
        self.assertIn("DAY1_B_124", verification["row_ids"])
    
    @patch('scripts.day1_injector.A2ABus')
    def test_a2a_event_publishing(self, mock_a2a_class):
        """Test A2A event publishing"""
        # Mock A2A bus
        mock_bus = Mock()
        mock_bus.pub.return_value = "stream-456"
        mock_a2a_class.return_value = mock_bus
        
        # Re-initialize injector with mocked A2A
        injector = Day1Injector()
        injector.a2a_bus = mock_bus
        
        # Test event publishing
        injector.publish_injection_event("TICKET_INJECTED", {"ticket_id": "A", "test": "data"})
        
        # Verify A2A event was published
        mock_bus.pub.assert_called_once()
        call_args = mock_bus.pub.call_args
        
        self.assertEqual(call_args[1]["row_id"], "DAY1_INJECT_TICKET_INJECTED")
        self.assertEqual(call_args[1]["event_type"], "TICKET_INJECTED")
        
        payload = call_args[1]["payload"]
        self.assertEqual(payload["event_type"], "TICKET_INJECTED")
        self.assertEqual(payload["injector_version"], "BC-140")
        self.assertEqual(payload["ticket_id"], "A")
        self.assertEqual(payload["test"], "data")
    
    def test_ticket_content_quality(self):
        """Test that ticket content is comprehensive and realistic"""
        # Test Bug A content
        bug_a = TICKET_TEMPLATES["A"]
        self.assertIn("memory leak", bug_a["title"].lower())
        self.assertIn("connection pooling", bug_a["description"].lower())
        self.assertIn("## Summary", bug_a["description"])
        self.assertIn("## Symptoms", bug_a["description"])
        self.assertIn("## Impact", bug_a["description"])
        self.assertIn("## Reproduction", bug_a["description"])
        self.assertGreater(bug_a["estimated_hours"], 8)  # Should be substantial bug
        
        # Test Bug B content
        bug_b = TICKET_TEMPLATES["B"]
        self.assertIn("redis", bug_b["title"].lower())
        self.assertIn("retry", bug_b["title"].lower())
        self.assertIn("backoff", bug_b["description"].lower())
        self.assertIn("thundering herd", bug_b["description"].lower())
        
        # Test Feature F content
        feature_f = TICKET_TEMPLATES["F"]
        self.assertIn("compression", feature_f["title"].lower())
        self.assertIn("A2A", feature_f["title"])
        self.assertIn("## Business Case", feature_f["description"])
        self.assertIn("## Acceptance Criteria", feature_f["description"])
        self.assertIn("## Implementation Plan", feature_f["description"])
        self.assertGreater(feature_f["estimated_hours"], 16)  # Should be substantial feature
    
    def test_payload_timestamps_format(self):
        """Test that timestamps are properly formatted"""
        payload = self.injector.create_ticket_payload("A")
        
        # Check timestamp format
        created_at = payload["created_at"]
        ticket_created_at = payload["ticket_data"]["created_at"]
        ticket_updated_at = payload["ticket_data"]["updated_at"]
        metadata_injected_at = payload["metadata"]["injected_at"]
        
        # All should be ISO format strings
        for timestamp in [created_at, ticket_created_at, ticket_updated_at, metadata_injected_at]:
            # Should be parseable as ISO datetime
            try:
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                self.fail(f"Invalid timestamp format: {timestamp}")
    
    def test_row_id_uniqueness(self):
        """Test that row IDs are unique"""
        # Create multiple payloads for same ticket
        payloads = []
        for _ in range(5):
            payload = self.injector.create_ticket_payload("A")
            payloads.append(payload)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Extract row IDs
        row_ids = [p["row_id"] for p in payloads]
        
        # All should be unique
        self.assertEqual(len(row_ids), len(set(row_ids)), "Row IDs should be unique")
        
        # All should follow expected pattern
        for row_id in row_ids:
            self.assertTrue(row_id.startswith("DAY1_A_"), f"Invalid row ID format: {row_id}")


class TestIntegrationDay1Injection(unittest.TestCase):
    """Integration tests for Day-1 injection workflow"""
    
    @patch('scripts.day1_injector.requests.Session.post')
    @patch('scripts.day1_injector.requests.Session.get')
    @patch('scripts.day1_injector.A2ABus')
    def test_end_to_end_injection_workflow(self, mock_a2a_class, mock_get, mock_post):
        """Test complete end-to-end injection workflow"""
        # Mock A2A bus
        mock_bus = Mock()
        mock_bus.pub.return_value = "stream-789"
        mock_a2a_class.return_value = mock_bus
        
        # Mock successful health check
        mock_health_response = Mock()
        mock_health_response.status_code = 200
        mock_get.return_value = mock_health_response
        
        # Mock successful injections
        def mock_injection_response(*args, **kwargs):
            response = Mock()
            response.status_code = 200
            response.raise_for_status.return_value = None
            
            payload = kwargs["json"]
            response.json.return_value = {
                "status": "created",
                "row_id": payload["row_id"],
                "ticket_id": payload["ticket_data"]["id"]
            }
            return response
        
        mock_post.side_effect = mock_injection_response
        
        # Initialize injector
        injector = Day1Injector()
        injector.a2a_bus = mock_bus
        
        # Run complete workflow
        health_ok = injector.check_council_api_health()
        self.assertTrue(health_ok)
        
        summary = injector.inject_multiple_tickets(["A", "B", "F"])
        
        verification = injector.verify_injection_success(summary["results"])
        
        # Verify workflow results
        self.assertEqual(summary["total_tickets"], 3)
        self.assertEqual(summary["successful"], 3)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["success_rate"], 100.0)
        
        self.assertTrue(verification["api_health"])
        self.assertEqual(verification["successful_injections"], 3)
        
        # Verify A2A events were published
        self.assertGreater(mock_bus.pub.call_count, 0)
        
        # Verify API calls
        self.assertEqual(mock_post.call_count, 3)  # One per ticket
        self.assertGreater(mock_get.call_count, 0)  # Health checks
    
    def test_ticket_template_consistency(self):
        """Test that all ticket templates are consistent"""
        for ticket_id, template in TICKET_TEMPLATES.items():
            with self.subTest(ticket_id=ticket_id):
                # All tickets should have meaningful descriptions
                self.assertGreater(len(template["description"]), 100, 
                                 f"Ticket {ticket_id} description too short")
                
                # All tickets should have realistic effort estimates
                self.assertGreater(template["estimated_hours"], 0, 
                                 f"Ticket {ticket_id} should have positive effort estimate")
                self.assertLess(template["estimated_hours"], 100, 
                               f"Ticket {ticket_id} effort estimate seems too high")
                
                # All tickets should have labels
                self.assertGreater(len(template["labels"]), 0, 
                                 f"Ticket {ticket_id} should have labels")
                
                # All tickets should have components
                self.assertGreater(len(template["components"]), 0, 
                                 f"Ticket {ticket_id} should have components")


if __name__ == '__main__':
    # Set test environment
    os.environ['COUNCIL_API_URL'] = 'http://test-council:8080'
    
    # Run tests
    unittest.main(verbosity=2) 