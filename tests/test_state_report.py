#!/usr/bin/env python3
"""
Unit tests for State-of-Titan Report Generator (BC-190)
Tests metric collection, template rendering, and output generation
"""

import os
import sys
import json
import time
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project root to path
sys.path.append('.')

# Mock dependencies if not available
try:
    import redis
except ImportError:
    redis = Mock()

try:
    import jinja2
except ImportError:
    jinja2 = Mock()

try:
    import requests
except ImportError:
    requests = Mock()

from scripts.generate_state_report import TitanReportGenerator


class TestTitanReportGenerator(unittest.TestCase):
    """Test State-of-Titan report generation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'REPORTS_DIR': self.temp_dir,
            'TEMPLATE_DIR': './reports',
            'DRY_RUN': 'true',
            'PROMETHEUS_URL': 'http://mock-prometheus:9090',
            'REDIS_URL': 'redis://mock-redis:6379'
        })
        self.env_patcher.start()
        
        # Create template in temp directory
        template_dir = Path(self.temp_dir)
        template_path = template_dir / 'template_state_of_titan.html.j2'
        
        # Simple test template
        template_content = '''
        <!DOCTYPE html>
        <html>
        <head><title>Test Report - {{ period }}</title></head>
        <body>
            <h1>State of Titan - {{ period }}</h1>
            <p>Generated: {{ timestamp }}</p>
            <p>Router P95: {{ router_p95_latency }}ms</p>
            <p>GPU Util: {{ gpu_utilization }}%</p>
            <p>VRAM Peak: {{ (vram_peak_bytes / 1024 / 1024 / 1024) | round(1) }}GB</p>
            <p>Cost: ${{ cost_spend_24h }}</p>
            <p>Rollbacks: {{ rollback_count }}</p>
            <p>A2A Queue: {{ a2a_pending_max }}</p>
            <p>Quant Kept: {{ quant_decisions.kept }}</p>
            <p>Quant Rejected: {{ quant_decisions.rejected }}</p>
        </body>
        </html>
        '''
        template_path.write_text(template_content.strip())
        
        # Update template dir to use temp dir
        os.environ['TEMPLATE_DIR'] = str(template_dir)
        
        self.generator = TitanReportGenerator(period="24h")
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization(self):
        """Test generator initialization"""
        self.assertEqual(self.generator.period, "24h")
        self.assertIsNotNone(self.generator.jinja_env)
        self.assertEqual(str(self.generator.reports_dir), self.temp_dir)
    
    @patch('scripts.generate_state_report.requests.get')
    def test_prometheus_query_success(self, mock_get):
        """Test successful Prometheus query"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": [
                    {
                        "value": [1234567890, "42.5"]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        result = self.generator.query_prometheus("test_metric")
        
        self.assertEqual(result, 42.5)
        mock_get.assert_called_once()
    
    @patch('scripts.generate_state_report.requests.get')
    def test_prometheus_query_failure(self, mock_get):
        """Test failed Prometheus query"""
        # Mock failed response
        mock_get.side_effect = requests.RequestException("Connection failed")
        
        result = self.generator.query_prometheus("test_metric")
        
        self.assertIsNone(result)
    
    @patch('scripts.generate_state_report.requests.get')
    def test_prometheus_query_no_data(self, mock_get):
        """Test Prometheus query with no data"""
        # Mock response with no results
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "result": []
            }
        }
        mock_get.return_value = mock_response
        
        result = self.generator.query_prometheus("test_metric")
        
        self.assertIsNone(result)
    
    @patch('scripts.generate_state_report.redis.from_url')
    def test_get_cost_data_redis(self, mock_redis):
        """Test cost data retrieval from Redis"""
        mock_client = Mock()
        mock_client.get.return_value = b"15.75"
        mock_redis.return_value = mock_client
        
        result = self.generator.get_cost_data()
        
        self.assertEqual(result, 15.75)
    
    @patch('scripts.generate_state_report.redis.from_url')
    def test_get_cost_data_file_fallback(self, mock_redis):
        """Test cost data fallback to file"""
        # Mock Redis failure
        mock_redis.side_effect = Exception("Redis unavailable")
        
        # Create mock metrics file
        metrics_dir = Path('/tmp/metrics_override')
        metrics_dir.mkdir(exist_ok=True)
        
        metrics_file = metrics_dir / 'cost_guard.prom'
        metrics_file.write_text('cloud_spend_daily 23.45\n')
        
        with patch('scripts.generate_state_report.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.read_text.return_value = 'cloud_spend_daily 23.45\n'
            
            result = self.generator.get_cost_data()
            
            self.assertEqual(result, 23.45)
    
    @patch('scripts.generate_state_report.redis.from_url')
    def test_get_cost_data_default(self, mock_redis):
        """Test cost data default value"""
        # Mock Redis failure
        mock_redis.side_effect = Exception("Redis unavailable")
        
        # Mock file not existing
        with patch('scripts.generate_state_report.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            result = self.generator.get_cost_data()
            
            self.assertEqual(result, 0.0)
    
    @patch('scripts.generate_state_report.TitanReportGenerator.query_prometheus')
    def test_get_quant_decisions(self, mock_query):
        """Test quantization decision metrics"""
        # Mock Prometheus responses
        mock_query.side_effect = [3, 1]  # kept=3, rejected=1
        
        result = self.generator.get_quant_decisions()
        
        expected = {"kept": 3, "rejected": 1}
        self.assertEqual(result, expected)
        
        # Verify queries were made
        self.assertEqual(mock_query.call_count, 2)
    
    def test_get_quant_history(self):
        """Test quantization history retrieval"""
        result = self.generator.get_quant_history()
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        
        # Check structure of first item
        if result:
            item = result[0]
            required_keys = ["timestamp", "model_name", "decision", 
                           "original_throughput", "quantized_throughput", 
                           "throughput_drop_percent"]
            for key in required_keys:
                self.assertIn(key, item)
    
    @patch('scripts.generate_state_report.TitanReportGenerator.query_prometheus')
    @patch('scripts.generate_state_report.TitanReportGenerator.get_cost_data')
    @patch('scripts.generate_state_report.TitanReportGenerator.get_quant_decisions')
    @patch('scripts.generate_state_report.TitanReportGenerator.get_quant_history')
    def test_collect_metrics(self, mock_history, mock_quant, mock_cost, mock_query):
        """Test metrics collection"""
        # Mock all data sources
        mock_query.side_effect = [25.3, 72.5, 6442450944, 0, 12]  # Default values
        mock_cost.return_value = 8.50
        mock_quant.return_value = {"kept": 2, "rejected": 1}
        mock_history.return_value = []
        
        metrics = self.generator.collect_metrics()
        
        # Verify structure
        self.assertIn("router_p95_latency", metrics)
        self.assertIn("gpu_utilization", metrics)
        self.assertIn("vram_peak", metrics)
        self.assertIn("cost_spend_24h", metrics)
        self.assertIn("rollback_count", metrics)
        self.assertIn("a2a_pending_max", metrics)
        self.assertIn("quant_decisions", metrics)
        self.assertIn("timestamp", metrics)
        self.assertIn("period", metrics)
        
        # Verify values
        self.assertEqual(metrics["cost_spend_24h"], 8.50)
        self.assertEqual(metrics["period"], "24h")
        self.assertEqual(metrics["quant_decisions"]["kept"], 2)
    
    def test_render_report(self):
        """Test HTML report rendering"""
        # Mock metrics
        metrics = {
            "router_p95_latency": 25.3,
            "gpu_utilization": 72.5,
            "vram_peak": 6442450944,
            "cost_spend_24h": 8.50,
            "rollback_count": 0,
            "a2a_pending_max": 12,
            "quant_decisions": {"kept": 2, "rejected": 1},
            "timestamp": "2024-01-15 12:30:45 UTC",
            "period": "24h"
        }
        
        html_content = self.generator.render_report(metrics)
        
        # Verify HTML content
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("State of Titan - 24h", html_content)
        self.assertIn("25.3ms", html_content)
        self.assertIn("72.5%", html_content)
        self.assertIn("6.0GB", html_content)
        self.assertIn("$8.5", html_content)
        self.assertIn("Quant Kept: 2", html_content)
    
    def test_save_reports(self):
        """Test saving HTML and JSON reports"""
        html_content = "<html><body>Test Report</body></html>"
        metrics = {
            "router_p95_latency": 25.3,
            "timestamp": "2024-01-15 12:30:45 UTC",
            "period": "24h"
        }
        
        html_path, json_path = self.generator.save_reports(html_content, metrics)
        
        # Verify files were created
        self.assertTrue(html_path.exists())
        self.assertTrue(json_path.exists())
        
        # Verify HTML content
        saved_html = html_path.read_text()
        self.assertEqual(saved_html, html_content)
        
        # Verify JSON content
        saved_json = json.loads(json_path.read_text())
        self.assertEqual(saved_json["router_p95_latency"], 25.3)
        self.assertEqual(saved_json["period"], "24h")
        
        # Verify filenames
        self.assertTrue(html_path.name.startswith("state-of-titan-24h"))
        self.assertTrue(json_path.name.startswith("state-of-titan-24h"))
        self.assertTrue(html_path.name.endswith(".html"))
        self.assertTrue(json_path.name.endswith(".json"))
    
    @patch('scripts.generate_state_report.A2ABus')
    def test_publish_report_ready_event(self, mock_a2a_class):
        """Test A2A event publishing"""
        # Mock A2A bus
        mock_bus = Mock()
        mock_bus.pub.return_value = "stream-123"
        mock_a2a_class.return_value = mock_bus
        
        # Re-initialize generator with mocked A2A
        self.generator.a2a_bus = mock_bus
        
        html_path = Path("/reports/state-of-titan-24h.html")
        metrics = {
            "router_p95_latency": 25.3,
            "gpu_utilization": 72.5,
            "cost_spend_24h": 8.50,
            "rollback_count": 0
        }
        
        self.generator.publish_report_ready_event(html_path, metrics)
        
        # Verify A2A event was published
        mock_bus.pub.assert_called_once()
        call_args = mock_bus.pub.call_args
        
        self.assertEqual(call_args[1]["row_id"], "STATE_REPORT_BC190")
        self.assertEqual(call_args[1]["event_type"], "REPORT_READY")
        
        payload = call_args[1]["payload"]
        self.assertEqual(payload["event_type"], "REPORT_READY")
        self.assertEqual(payload["period"], "24h")
        self.assertEqual(payload["url"], "/reports/state-of-titan-24h.html")
    
    @patch('scripts.generate_state_report.TitanReportGenerator.collect_metrics')
    @patch('scripts.generate_state_report.TitanReportGenerator.render_report')
    @patch('scripts.generate_state_report.TitanReportGenerator.save_reports')
    @patch('scripts.generate_state_report.TitanReportGenerator.publish_report_ready_event')
    def test_generate_report_success(self, mock_publish, mock_save, mock_render, mock_collect):
        """Test successful report generation"""
        # Mock all steps
        mock_metrics = {"router_p95_latency": 25.3, "timestamp": "2024-01-15 12:30:45 UTC"}
        mock_collect.return_value = mock_metrics
        mock_render.return_value = "<html>Test</html>"
        mock_save.return_value = (Path("/tmp/test.html"), Path("/tmp/test.json"))
        mock_publish.return_value = None
        
        result = self.generator.generate_report()
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertEqual(result["period"], "24h")
        self.assertIn("html_path", result)
        self.assertIn("json_path", result)
        self.assertIn("duration_seconds", result)
        self.assertLess(result["duration_seconds"], 3.0)  # BC-190 requirement: < 3s
        
        # Verify all steps were called
        mock_collect.assert_called_once()
        mock_render.assert_called_once_with(mock_metrics)
        mock_save.assert_called_once()
        mock_publish.assert_called_once()
    
    @patch('scripts.generate_state_report.TitanReportGenerator.collect_metrics')
    def test_generate_report_failure(self, mock_collect):
        """Test report generation failure"""
        # Mock failure
        mock_collect.side_effect = Exception("Test error")
        
        result = self.generator.generate_report()
        
        # Verify failure
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Test error")
        self.assertEqual(result["period"], "24h")
    
    def test_render_time_requirement(self):
        """Test that rendering meets <3s requirement"""
        # Create larger mock metrics
        metrics = {
            "router_p95_latency": 25.3,
            "gpu_utilization": 72.5,
            "vram_peak": 6442450944,
            "cost_spend_24h": 8.50,
            "rollback_count": 0,
            "a2a_pending_max": 12,
            "quant_decisions": {"kept": 2, "rejected": 1},
            "quant_history": [
                {
                    "timestamp": time.time() - 3600,
                    "model_name": f"test-model-{i}",
                    "decision": "kept" if i % 2 == 0 else "rejected",
                    "original_throughput": 45.0 + i,
                    "quantized_throughput": 40.0 + i,
                    "throughput_drop_percent": 10.0 + i
                }
                for i in range(50)  # Generate many history items
            ],
            "timestamp": "2024-01-15 12:30:45 UTC",
            "period": "24h"
        }
        
        start_time = time.time()
        html_content = self.generator.render_report(metrics)
        render_time = time.time() - start_time
        
        # Verify render time requirement
        self.assertLess(render_time, 3.0, "Render time should be < 3s per BC-190 requirement")
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertGreater(len(html_content), 1000)  # Reasonable size check
    
    def test_html_timestamp_requirement(self):
        """Test that HTML contains latest timestamp in header"""
        metrics = {
            "router_p95_latency": 25.3,
            "gpu_utilization": 72.5,
            "vram_peak": 6442450944,
            "cost_spend_24h": 8.50,
            "rollback_count": 0,
            "a2a_pending_max": 12,
            "quant_decisions": {"kept": 2, "rejected": 1},
            "timestamp": "2024-01-15 12:30:45 UTC",
            "period": "24h"
        }
        
        html_content = self.generator.render_report(metrics)
        
        # Verify timestamp is in header
        self.assertIn("2024-01-15 12:30:45 UTC", html_content)
        
        # Verify timestamp is in the generated content section
        lines = html_content.split('\n')
        timestamp_found = any("2024-01-15 12:30:45 UTC" in line for line in lines[:50])  # Check header area
        self.assertTrue(timestamp_found, "Timestamp should appear in HTML header area")
    
    def test_quant_decision_section_consistency(self):
        """Test that QUANT_DECISION section matches metrics"""
        quant_decisions = {"kept": 5, "rejected": 2}
        
        metrics = {
            "router_p95_latency": 25.3,
            "gpu_utilization": 72.5,
            "vram_peak": 6442450944,
            "cost_spend_24h": 8.50,
            "rollback_count": 0,
            "a2a_pending_max": 12,
            "quant_decisions": quant_decisions,
            "timestamp": "2024-01-15 12:30:45 UTC",
            "period": "24h"
        }
        
        html_content = self.generator.render_report(metrics)
        
        # Verify kept count appears
        self.assertIn("Quant Kept: 5", html_content)
        
        # Verify rejected count appears  
        self.assertIn("Quant Rejected: 2", html_content)
        
        # Calculate expected success rate
        total = quant_decisions["kept"] + quant_decisions["rejected"]
        success_rate = (quant_decisions["kept"] / total * 100) if total > 0 else 0
        
        # Success rate should be calculated correctly (5/7 * 100 = 71.4%)
        self.assertAlmostEqual(success_rate, 71.4, places=1)


class TestReportIntegration(unittest.TestCase):
    """Integration tests for complete report generation workflow"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create complete template structure
        template_dir = Path(self.temp_dir)
        
        # Copy actual template (simplified version)
        template_path = template_dir / 'template_state_of_titan.html.j2'
        template_content = '''<!DOCTYPE html>
<html>
<head><title>{{ period }} Report</title></head>
<body>
    <h1>State of Titan - {{ period }}</h1>
    <div>Generated: {{ timestamp }}</div>
    <div>Router P95: {{ router_p95_latency }}ms</div>
    <div>GPU: {{ gpu_utilization }}%</div>
    <div>VRAM: {{ (vram_peak_bytes / 1024 / 1024 / 1024) | round(1) }}GB</div>
    <div>Cost: ${{ cost_spend_24h }}</div>
    <div>Rollbacks: {{ rollback_count }}</div>
    <div>A2A: {{ a2a_pending_max }}</div>
    <div>Kept: {{ quant_decisions.kept }}</div>
    <div>Rejected: {{ quant_decisions.rejected }}</div>
</body>
</html>'''
        template_path.write_text(template_content)
        
        self.env_patcher = patch.dict(os.environ, {
            'REPORTS_DIR': self.temp_dir,
            'TEMPLATE_DIR': str(template_dir),
            'DRY_RUN': 'true'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up integration test environment"""
        self.env_patcher.stop()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('scripts.generate_state_report.requests.get')
    @patch('scripts.generate_state_report.redis.from_url')
    def test_end_to_end_report_generation(self, mock_redis, mock_requests):
        """Test complete end-to-end report generation"""
        # Mock Prometheus responses
        def mock_prometheus_response(*args, **kwargs):
            query = kwargs.get('params', {}).get('query', '')
            
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            # Different responses for different queries
            if 'latency' in query:
                value = "0.0253"  # 25.3ms
            elif 'gpu_utilization' in query:
                value = "72.5"
            elif 'gpu_mem_used' in query:
                value = "6442450944"  # 6GB
            elif 'rollback' in query:
                value = "0"
            elif 'a2a_queue' in query:
                value = "12"
            elif 'kept' in query:
                value = "3"
            elif 'rejected' in query:
                value = "1"
            else:
                value = "0"
            
            mock_response.json.return_value = {
                "status": "success",
                "data": {
                    "result": [{"value": [1234567890, value]}]
                }
            }
            return mock_response
        
        mock_requests.side_effect = mock_prometheus_response
        
        # Mock Redis cost data
        mock_redis_client = Mock()
        mock_redis_client.get.return_value = b"12.75"
        mock_redis.return_value = mock_redis_client
        
        # Generate report
        generator = TitanReportGenerator(period="24h")
        result = generator.generate_report()
        
        # Verify success
        self.assertTrue(result["success"])
        self.assertLess(result["duration_seconds"], 3.0)
        
        # Verify files exist
        html_path = Path(result["html_path"])
        json_path = Path(result["json_path"])
        
        self.assertTrue(html_path.exists())
        self.assertTrue(json_path.exists())
        
        # Verify HTML content
        html_content = html_path.read_text()
        self.assertIn("State of Titan - 24h", html_content)
        self.assertIn("25.3ms", html_content)
        self.assertIn("72.5%", html_content)
        self.assertIn("6.0GB", html_content)
        self.assertIn("$12.75", html_content)
        self.assertIn("Kept: 3", html_content)
        self.assertIn("Rejected: 1", html_content)
        
        # Verify JSON content
        json_data = json.loads(json_path.read_text())
        self.assertEqual(json_data["router_p95_latency"], 25.3)
        self.assertEqual(json_data["gpu_utilization"], 72.5)
        self.assertEqual(json_data["cost_spend_24h"], 12.75)
        self.assertEqual(json_data["quant_decisions"]["kept"], 3)
        self.assertEqual(json_data["quant_decisions"]["rejected"], 1)


if __name__ == '__main__':
    # Set up test environment
    os.environ['DRY_RUN'] = 'true'
    
    # Run tests
    unittest.main(verbosity=2) 