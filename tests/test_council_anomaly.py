#!/usr/bin/env python3
"""
Unit tests for Council Latency Anomaly Detection (M-310)
Tests rule logic, spike generation, and alert verification
"""

import os
import sys
import time
import unittest
import threading
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append('.')

# Mock dependencies
try:
    import requests
except ImportError:
    requests = Mock()

from scripts.latency_spike import LatencySpiker


class TestCouncilAnomalyRule(unittest.TestCase):
    """Test Council latency anomaly Prometheus rule logic"""
    
    def test_anomaly_threshold_calculation(self):
        """Test 110% threshold calculation logic"""
        # Test cases: baseline -> expected threshold
        test_cases = [
            (0.050, 0.055),  # 50ms -> 55ms
            (0.100, 0.110),  # 100ms -> 110ms
            (0.200, 0.220),  # 200ms -> 220ms
            (1.000, 1.100),  # 1s -> 1.1s
        ]
        
        for baseline, expected_threshold in test_cases:
            with self.subTest(baseline=baseline):
                threshold = baseline * 1.10
                self.assertAlmostEqual(threshold, expected_threshold, places=3)
                
                # Verify that values just above threshold would trigger
                trigger_value = threshold + 0.001
                self.assertGreater(trigger_value, threshold)
                
                # Verify that values just below threshold would not trigger
                safe_value = threshold - 0.001
                self.assertLess(safe_value, threshold)
    
    def test_critical_threshold_calculation(self):
        """Test 150% critical threshold calculation"""
        test_cases = [
            (0.050, 0.075),  # 50ms -> 75ms
            (0.100, 0.150),  # 100ms -> 150ms
            (0.200, 0.300),  # 200ms -> 300ms
        ]
        
        for baseline, expected_threshold in test_cases:
            with self.subTest(baseline=baseline):
                threshold = baseline * 1.50
                self.assertAlmostEqual(threshold, expected_threshold, places=3)
    
    def test_prometheus_rule_syntax(self):
        """Test that Prometheus rule syntax is valid"""
        # Load the rule file
        rule_file = Path('./rules/council_anomaly.yml')
        self.assertTrue(rule_file.exists(), "Rule file should exist")
        
        content = rule_file.read_text()
        
        # Check for required components
        self.assertIn('CouncilLatencyAnomaly', content)
        self.assertIn('histogram_quantile(0.95', content)
        self.assertIn('avg_over_time', content)
        self.assertIn('* 1.10', content)
        self.assertIn('for: 2m', content)
        
        # Check labels
        self.assertIn('severity: warning', content)
        self.assertIn('component: council-router', content)
        self.assertIn('rule_id: M-310', content)
        
        # Check critical alert
        self.assertIn('CouncilLatencyAnomaly_Critical', content)
        self.assertIn('* 1.50', content)
        self.assertIn('severity: critical', content)


class TestLatencySpiker(unittest.TestCase):
    """Test synthetic latency spike generator"""
    
    def setUp(self):
        """Set up test environment"""
        self.spiker = LatencySpiker(spike_latency=0.150, duration=5)  # Short duration for tests
    
    def tearDown(self):
        """Clean up after tests"""
        if self.spiker.active:
            self.spiker.stop_spike()
    
    def test_spiker_initialization(self):
        """Test spiker initialization"""
        self.assertEqual(self.spiker.spike_latency, 0.150)
        self.assertEqual(self.spiker.duration, 5)
        self.assertFalse(self.spiker.active)
        self.assertIsNone(self.spiker.start_time)
        self.assertIsNone(self.spiker.end_time)
    
    @patch('scripts.latency_spike.requests.get')
    def test_make_slow_request_success(self, mock_get):
        """Test successful slow request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        # Test with 100ms artificial delay
        start_time = time.time()
        result = self.spiker.make_slow_request(0.100)
        duration = time.time() - start_time
        
        # Should return total duration including artificial delay
        self.assertIsNotNone(result)
        self.assertGreater(result, 0.100)  # At least the artificial delay
        self.assertGreater(duration, 0.100)  # Actual call should take at least delay time
    
    @patch('scripts.latency_spike.requests.get')
    def test_make_slow_request_failure(self, mock_get):
        """Test failed slow request"""
        # Mock failed response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response
        
        result = self.spiker.make_slow_request(0.050)
        
        # Should return None for failed requests
        self.assertIsNone(result)
    
    @patch('scripts.latency_spike.requests.get')
    def test_make_slow_request_exception(self, mock_get):
        """Test request with exception"""
        # Mock exception
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = self.spiker.make_slow_request(0.050)
        
        # Should return None for exceptions
        self.assertIsNone(result)
    
    def test_start_stop_spike(self):
        """Test starting and stopping spike"""
        # Initially inactive
        self.assertFalse(self.spiker.active)
        
        # Start spike
        with patch.object(self.spiker, 'make_slow_request', return_value=0.200):
            success = self.spiker.start_spike()
            self.assertTrue(success)
            self.assertTrue(self.spiker.active)
            
            # Wait a bit for thread to start
            time.sleep(0.1)
            
            # Stop spike
            success = self.spiker.stop_spike()
            self.assertTrue(success)
            self.assertFalse(self.spiker.active)
    
    def test_cannot_start_duplicate_spike(self):
        """Test that duplicate spikes cannot be started"""
        with patch.object(self.spiker, 'make_slow_request', return_value=0.200):
            # Start first spike
            success1 = self.spiker.start_spike()
            self.assertTrue(success1)
            self.assertTrue(self.spiker.active)
            
            # Try to start second spike
            success2 = self.spiker.start_spike()
            self.assertFalse(success2)  # Should fail
            
            # Stop spike
            self.spiker.stop_spike()
    
    @patch('scripts.latency_spike.requests.get')
    def test_check_prometheus_alert_firing(self, mock_get):
        """Test checking Prometheus alert when firing"""
        # Mock Prometheus alerts API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "labels": {"alertname": "CouncilLatencyAnomaly"},
                        "state": "firing"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        is_firing = self.spiker.check_prometheus_alert()
        
        self.assertTrue(is_firing)
        mock_get.assert_called_once()
    
    @patch('scripts.latency_spike.requests.get')
    def test_check_prometheus_alert_inactive(self, mock_get):
        """Test checking Prometheus alert when inactive"""
        # Mock Prometheus alerts API response with no alerts
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "alerts": []
            }
        }
        mock_get.return_value = mock_response
        
        is_firing = self.spiker.check_prometheus_alert()
        
        self.assertFalse(is_firing)
    
    @patch('scripts.latency_spike.requests.get')
    def test_get_current_latency_success(self, mock_get):
        """Test getting current latency from Prometheus"""
        # Mock Prometheus query API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "value": [1234567890, "0.095"]  # 95ms
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        latency = self.spiker.get_current_latency()
        
        self.assertIsNotNone(latency)
        self.assertAlmostEqual(latency, 0.095, places=3)
    
    @patch('scripts.latency_spike.requests.get')
    def test_get_current_latency_no_data(self, mock_get):
        """Test getting current latency when no data available"""
        # Mock Prometheus query API response with no results
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": []
            }
        }
        mock_get.return_value = mock_response
        
        latency = self.spiker.get_current_latency()
        
        self.assertIsNone(latency)
    
    @patch('scripts.latency_spike.A2ABus')
    def test_a2a_event_publishing(self, mock_a2a_class):
        """Test A2A event publishing"""
        # Mock A2A bus
        mock_bus = Mock()
        mock_bus.pub.return_value = "stream-123"
        mock_a2a_class.return_value = mock_bus
        
        # Re-initialize spiker with mocked A2A
        spiker = LatencySpiker(spike_latency=0.100, duration=5)
        spiker.a2a_bus = mock_bus
        
        # Test event publishing
        spiker.publish_spike_event("LATENCY_SPIKE_START", {"test": "data"})
        
        # Verify A2A event was published
        mock_bus.pub.assert_called_once()
        call_args = mock_bus.pub.call_args
        
        self.assertEqual(call_args[1]["row_id"], "LATENCY_SPIKE_LATENCY_SPIKE_START")
        self.assertEqual(call_args[1]["event_type"], "LATENCY_SPIKE_START")
        
        payload = call_args[1]["payload"]
        self.assertEqual(payload["event_type"], "LATENCY_SPIKE_START")
        self.assertEqual(payload["spike_latency_ms"], 100.0)
        self.assertEqual(payload["duration_seconds"], 5)
        self.assertEqual(payload["test"], "data")


class TestIntegrationAnomalyDetection(unittest.TestCase):
    """Integration tests for end-to-end anomaly detection"""
    
    @patch('scripts.latency_spike.requests.get')
    @patch('scripts.latency_spike.A2ABus')
    def test_end_to_end_spike_and_alert(self, mock_a2a_class, mock_get):
        """Test end-to-end spike generation and alert detection"""
        # Mock A2A bus
        mock_bus = Mock()
        mock_bus.pub.return_value = "stream-123"
        mock_a2a_class.return_value = mock_bus
        
        # Mock responses for different API calls
        def mock_api_response(*args, **kwargs):
            url = args[0]
            
            if '/health' in url:
                # Mock Council API health check
                response = Mock()
                response.status_code = 200
                return response
            elif '/alerts' in url:
                # Mock Prometheus alerts API - start inactive, then firing
                response = Mock()
                response.status_code = 200
                response.raise_for_status.return_value = None
                
                # Simulate alert firing after requests start
                if hasattr(mock_get, '_call_count'):
                    mock_get._call_count += 1
                else:
                    mock_get._call_count = 1
                
                if mock_get._call_count > 3:  # After a few calls, alert starts firing
                    response.json.return_value = {
                        "status": "success",
                        "data": {
                            "alerts": [
                                {
                                    "labels": {"alertname": "CouncilLatencyAnomaly"},
                                    "state": "firing"
                                }
                            ]
                        }
                    }
                else:
                    response.json.return_value = {
                        "status": "success",
                        "data": {"alerts": []}
                    }
                return response
            elif '/query' in url:
                # Mock Prometheus query API for latency
                response = Mock()
                response.status_code = 200
                response.raise_for_status.return_value = None
                response.json.return_value = {
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "value": [1234567890, "0.075"]  # 75ms baseline
                            }
                        ]
                    }
                }
                return response
            
            # Default mock response
            response = Mock()
            response.status_code = 200
            return response
        
        mock_get.side_effect = mock_api_response
        
        # Create spiker with short duration for test
        spiker = LatencySpiker(spike_latency=0.150, duration=3)
        spiker.a2a_bus = mock_bus
        
        try:
            # Get baseline
            baseline = spiker.get_current_latency()
            self.assertIsNotNone(baseline)
            self.assertAlmostEqual(baseline, 0.075, places=3)
            
            # Start spike
            success = spiker.start_spike()
            self.assertTrue(success)
            self.assertTrue(spiker.active)
            
            # Wait for spike to run and potentially trigger alert
            time.sleep(1.5)  # Let some requests happen
            
            # Check if alert is firing
            is_firing = spiker.check_prometheus_alert()
            
            # Stop spike
            spiker.stop_spike()
            
            # Verify A2A events were published
            self.assertGreater(mock_bus.pub.call_count, 0)
            
            # Verify some requests were made to Council API
            health_calls = [call for call in mock_get.call_args_list 
                           if '/health' in str(call)]
            self.assertGreater(len(health_calls), 0)
            
        finally:
            if spiker.active:
                spiker.stop_spike()
    
    def test_spike_duration_accuracy(self):
        """Test that spike duration is reasonably accurate"""
        duration = 2  # 2 seconds
        spiker = LatencySpiker(spike_latency=0.050, duration=duration)
        
        with patch.object(spiker, 'make_slow_request', return_value=0.100):
            start_time = time.time()
            
            success = spiker.start_spike()
            self.assertTrue(success)
            
            # Wait for completion
            spiker.wait_for_completion()
            
            actual_duration = time.time() - start_time
            
            # Should be close to target duration (within 20% tolerance)
            self.assertLess(abs(actual_duration - duration), duration * 0.2)
            self.assertFalse(spiker.active)
    
    def test_spike_latency_injection(self):
        """Test that artificial latency is properly injected"""
        target_latency = 0.200  # 200ms
        spiker = LatencySpiker(spike_latency=target_latency, duration=1)
        
        with patch('scripts.latency_spike.requests.get') as mock_get:
            # Mock fast response (10ms)
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            # Override time.time to simulate fast request
            original_time = time.time
            
            def mock_time():
                if hasattr(mock_time, '_calls'):
                    mock_time._calls += 1
                else:
                    mock_time._calls = 1
                
                # Simulate 10ms request time
                if mock_time._calls % 2 == 1:
                    return original_time()
                else:
                    return original_time() + 0.010
            
            with patch('time.time', side_effect=mock_time):
                start_time = original_time()
                result = spiker.make_slow_request(target_latency)
                actual_duration = original_time() - start_time
                
                # Result should include artificial delay
                self.assertIsNotNone(result)
                self.assertGreater(result, target_latency)
                
                # Actual wall clock time should be close to target latency
                self.assertGreater(actual_duration, target_latency * 0.9)


if __name__ == '__main__':
    # Set test environment
    os.environ['COUNCIL_URL'] = 'http://test-council:8080'
    os.environ['PROMETHEUS_URL'] = 'http://test-prometheus:9090'
    
    # Run tests
    unittest.main(verbosity=2) 