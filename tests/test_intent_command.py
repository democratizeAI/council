#!/usr/bin/env python3
"""
Unit tests for /intent Slack command (IDR-01)
Tests intent processing, IDA integration, and A2A bus PR creation
"""

import os
import sys
import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.append('.')

from app.slack.commands.intent import IntentProcessor, handle_intent_command


class TestIntentCommand(unittest.TestCase):
    """Test /intent Slack command functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.processor = IntentProcessor()
        self.test_user_id = "U12345TEST"
        self.test_channel_id = "C67890TEST"
        self.test_intent = "Add authentication to the API endpoints"
    
    def test_initialization(self):
        """Test IntentProcessor initialization"""
        self.assertEqual(self.processor.ida_url, "http://ida-service:8080")
        self.assertEqual(self.processor.council_url, "http://council-api:8000")
        self.assertEqual(self.processor.ledger_endpoint, "http://council-api:8000/ledger/new")
    
    @patch('requests.post')
    def test_ida_service_success(self, mock_post):
        """Test successful IDA service call"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ticket_type": "feature",
            "priority": "medium", 
            "title": "Add authentication to API endpoints",
            "ida_available": True
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.processor.call_ida_service(self.test_intent, self.test_user_id)
        
        self.assertEqual(result['ticket_type'], 'feature')
        self.assertTrue(result['ida_available'])
    
    @patch('requests.post')
    def test_ida_service_fallback(self, mock_post):
        """Test fallback parsing when IDA service fails"""
        # Mock IDA service failure
        mock_post.side_effect = Exception("IDA service unavailable")
        
        result = self.processor.call_ida_service("Fix critical bug in payment system", self.test_user_id)
        
        # Verify fallback parsing
        self.assertEqual(result['ticket_type'], 'bug')
        self.assertEqual(result['priority'], 'high')
        self.assertFalse(result['ida_available'])
        self.assertIn("Fix critical bug in payment system", result['title'])
    
    def test_fallback_intent_parsing_bug(self):
        """Test fallback parsing for bug keywords"""
        result = self.processor._fallback_intent_parsing("Error in user authentication", self.test_user_id)
        
        self.assertEqual(result['ticket_type'], 'bug')
        self.assertEqual(result['priority'], 'high')
        self.assertEqual(result['title'], 'Error in user authentication')
        self.assertFalse(result['ida_available'])
    
    def test_fallback_intent_parsing_feature(self):
        """Test fallback parsing for feature keywords"""
        result = self.processor._fallback_intent_parsing("Add new dashboard feature", self.test_user_id)
        
        self.assertEqual(result['ticket_type'], 'feature')
        self.assertEqual(result['priority'], 'medium')
        self.assertEqual(result['title'], 'Add new dashboard feature')
        self.assertFalse(result['ida_available'])
    
    def test_fallback_intent_parsing_task(self):
        """Test fallback parsing for generic tasks"""
        result = self.processor._fallback_intent_parsing("Update documentation", self.test_user_id)
        
        self.assertEqual(result['ticket_type'], 'task')
        self.assertEqual(result['priority'], 'medium')
        self.assertEqual(result['title'], 'Update documentation')
        self.assertFalse(result['ida_available'])
    
    @patch('requests.post')
    def test_post_to_ledger_creates_pr_trigger(self, mock_post):
        """Test that ledger posting creates proper structure for Builder-swarm PR generation"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "status": "created",
            "pr_scaffold_trigger": True
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        ida_result = {
            "ticket_type": "feature",
            "priority": "high",
            "title": "Implement CI/CD pipeline"
        }
        
        result = self.processor.post_to_ledger(ida_result, self.test_user_id)
        
        # Verify ledger call structure supports Builder-swarm
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['metadata']['source'], 'slack-intent-command')
        self.assertEqual(payload['metadata']['version'], 'IDR-01')
        self.assertEqual(payload['row_type'], 'ticket')
        
        # Verify PR scaffold trigger
        self.assertTrue(result.get('pr_scaffold_trigger', False))
    
    @patch('app.slack.commands.intent.IntentProcessor.call_ida_service')
    @patch('app.slack.commands.intent.IntentProcessor.post_to_ledger')
    def test_full_a2a_workflow(self, mock_post_ledger, mock_call_ida):
        """Test complete A2A workflow from intent to PR creation"""
        # Mock IDA response
        mock_ida_result = {
            "ticket_type": "feature",
            "priority": "high",
            "title": "Add API authentication",
            "ida_available": True
        }
        mock_call_ida.return_value = mock_ida_result
        
        # Mock ledger response with PR trigger
        mock_ledger_result = {
            "status": "created",
            "row_id": "INTENT_123456",
            "pr_scaffold_trigger": True
        }
        mock_post_ledger.return_value = mock_ledger_result
        
        result = handle_intent_command(self.test_intent, self.test_user_id, "C12345")
        
        # Verify successful workflow
        self.assertEqual(result['response_type'], 'ephemeral')
        self.assertIn('Intent processed successfully', result['text'])
        self.assertIn('Builder-swarm will automatically scaffold PR', result['text'])
        self.assertIn('CI will run security + arch checks', result['text'])
    
    @patch('app.slack.commands.intent.IntentProcessor.call_ida_service')
    @patch('app.slack.commands.intent.IntentProcessor.post_to_ledger')
    def test_handle_intent_command_success(self, mock_post_ledger, mock_call_ida):
        """Test successful intent command handling"""
        # Mock IDA result
        mock_ida_result = {
            "ticket_type": "feature",
            "priority": "high",
            "title": "Add authentication to API endpoints",
            "description": "Implement OAuth2 authentication",
            "estimated_hours": 16,
            "ida_available": True
        }
        mock_call_ida.return_value = mock_ida_result
        
        # Mock ledger result
        mock_ledger_result = {"status": "created", "row_id": "INTENT_123456"}
        mock_post_ledger.return_value = mock_ledger_result
        
        result = handle_intent_command(self.test_intent, self.test_user_id, self.test_channel_id)
        
        # Verify calls
        mock_call_ida.assert_called_once_with(self.test_intent, self.test_user_id)
        mock_post_ledger.assert_called_once_with(mock_ida_result, self.test_user_id)
        
        # Verify response
        self.assertEqual(result['response_type'], 'ephemeral')
        self.assertIn('Intent processed successfully', result['text'])
        self.assertIn('Feature', result['text'])
        self.assertIn('High', result['text'])
        self.assertIn('✅ Available', result['text'])  # IDA service status
    
    @patch('app.slack.commands.intent.IntentProcessor.call_ida_service')
    @patch('app.slack.commands.intent.IntentProcessor.post_to_ledger')
    def test_handle_intent_command_ida_fallback(self, mock_post_ledger, mock_call_ida):
        """Test intent command with IDA fallback"""
        # Mock IDA fallback result
        mock_ida_result = {
            "ticket_type": "bug",
            "priority": "high",
            "title": "Critical error in payment processing",
            "description": "Critical error in payment processing",
            "ida_available": False
        }
        mock_call_ida.return_value = mock_ida_result
        
        # Mock ledger result
        mock_ledger_result = {"status": "created", "row_id": "INTENT_789012"}
        mock_post_ledger.return_value = mock_ledger_result
        
        result = handle_intent_command("Critical error in payment processing", self.test_user_id, self.test_channel_id)
        
        # Verify response indicates fallback mode
        self.assertEqual(result['response_type'], 'ephemeral')
        self.assertIn('Intent processed successfully', result['text'])
        self.assertIn('⚠️ Fallback mode', result['text'])  # IDA service status
    
    @patch('app.slack.commands.intent.IntentProcessor.call_ida_service')
    def test_handle_intent_command_failure(self, mock_call_ida):
        """Test intent command handling failure"""
        # Mock exception
        mock_call_ida.side_effect = Exception("Service unavailable")
        
        result = handle_intent_command(self.test_intent, self.test_user_id, self.test_channel_id)
        
        # Verify error response
        self.assertEqual(result['response_type'], 'ephemeral')
        self.assertIn('Intent processing failed', result['text'])
        self.assertIn('Service unavailable', result['text'])
    
    def test_row_id_generation(self):
        """Test unique row ID generation"""
        import time
        
        # Test multiple calls generate unique IDs
        ida_result = {"ticket_type": "task", "priority": "medium", "title": "Test"}
        
        with patch('time.time', return_value=1234567890):
            with patch('requests.post') as mock_post:
                mock_post.return_value.json.return_value = {"status": "created"}
                mock_post.return_value.raise_for_status.return_value = None
                
                self.processor.post_to_ledger(ida_result, "USER1")
                self.processor.post_to_ledger(ida_result, "USER2")
                
                # Verify different row IDs for different users
                call1_payload = mock_post.call_args_list[0][1]['json']
                call2_payload = mock_post.call_args_list[1][1]['json']
                
                self.assertNotEqual(call1_payload['row_id'], call2_payload['row_id'])
                self.assertIn('USER1', call1_payload['row_id'])
                self.assertIn('USER2', call2_payload['row_id'])


class TestA2AIntegration(unittest.TestCase):
    """Test A2A bus integration and PR creation verification"""
    
    def setUp(self):
        """Set up A2A test environment"""
        self.test_user_id = "U12345A2A"
        self.test_intent = "Create automated backup system"
    
    @patch('app.slack.commands.intent.IntentProcessor.call_ida_service')
    @patch('app.slack.commands.intent.IntentProcessor.post_to_ledger')
    def test_a2a_event_flow_simulation(self, mock_post_ledger, mock_call_ida):
        """Test that intent command triggers A2A events for PR creation"""
        # Mock successful processing
        mock_ida_result = {
            "ticket_type": "feature",
            "priority": "medium",
            "title": "Create automated backup system",
            "ida_available": True
        }
        mock_call_ida.return_value = mock_ida_result
        
        mock_ledger_result = {
            "status": "created",
            "row_id": f"INTENT_{self.test_user_id}_1234567890"
        }
        mock_post_ledger.return_value = mock_ledger_result
        
        # Execute intent command
        result = handle_intent_command(self.test_intent, self.test_user_id, "C12345")
        
        # Verify successful processing (A2A events would be published in real implementation)
        self.assertEqual(result['response_type'], 'ephemeral')
        self.assertIn('Intent processed successfully', result['text'])
        self.assertIn('Builder-swarm will automatically scaffold PR', result['text'])
        
        # Verify ledger payload contains A2A-compatible structure
        call_args = mock_post_ledger.call_args[0]
        ida_result, user_id = call_args
        self.assertEqual(user_id, self.test_user_id)
        self.assertEqual(ida_result['ticket_type'], 'feature')
    
    def test_pr_creation_workflow_verification(self):
        """Test that the intent command creates proper structure for PR generation"""
        processor = IntentProcessor()
        
        # Mock successful ledger posting
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                "status": "created",
                "row_id": "INTENT_USER_123",
                "pr_scaffold_trigger": True  # Simulated Builder-swarm trigger
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            ida_result = {
                "ticket_type": "feature",
                "priority": "high",
                "title": "Implement CI/CD pipeline",
                "description": "Setup automated deployment pipeline",
                "labels": ["devops", "automation"]
            }
            
            result = processor.post_to_ledger(ida_result, "TESTUSER")
            
            # Verify the ledger payload structure supports PR scaffolding
            payload = mock_post.call_args[1]['json']
            
            # Check metadata for Builder-swarm compatibility
            self.assertEqual(payload['metadata']['source'], 'slack-intent-command')
            self.assertEqual(payload['metadata']['version'], 'IDR-01')
            self.assertEqual(payload['row_type'], 'ticket')
            
            # Check ticket data structure
            ticket_data = payload['ticket_data']
            self.assertEqual(ticket_data['ticket_type'], 'feature')
            self.assertEqual(ticket_data['priority'], 'high')
            self.assertIn('Implement CI/CD pipeline', ticket_data['title'])
            
            # Verify Builder-swarm trigger in response
            self.assertTrue(result.get('pr_scaffold_trigger', False))


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2) 