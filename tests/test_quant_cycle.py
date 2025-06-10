#!/usr/bin/env python3
"""
Unit tests for Quantization Cycle (BC-180)
Tests the complete quantization workflow with mock models
"""

import unittest
import tempfile
import shutil
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import time

# Test imports
import sys
sys.path.append('.')


class TestQuantizationCycle(unittest.TestCase):
    """Test quantization cycle functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="quant_test_"))
        self.model_dir = self.test_dir / "models"
        self.model_dir.mkdir()
        
        # Set environment for testing
        os.environ['MODEL_DIR'] = str(self.model_dir)
        os.environ['DRY_RUN'] = 'true'
        os.environ['THROUGHPUT_DROP_THRESHOLD'] = '0.12'
        
        # Create mock model file
        self.mock_model = self.model_dir / "test_model.gguf"
        self.mock_model.write_text("mock model content" * 1000)
        
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
        
        # Clean up environment
        for key in ['MODEL_DIR', 'DRY_RUN', 'THROUGHPUT_DROP_THRESHOLD']:
            if key in os.environ:
                del os.environ[key]
    
    def test_import_quantization_cycle(self):
        """Test that we can import the quantization cycle module"""
        try:
            from scripts.quant_cycle import QuantizationCycle
            self.assertTrue(True, "Successfully imported QuantizationCycle")
        except ImportError as e:
            self.fail(f"Failed to import QuantizationCycle: {e}")
    
    @patch('scripts.quant_cycle.A2ABus')
    def test_quantization_cycle_initialization(self, mock_a2a):
        """Test QuantizationCycle initialization"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test_model") as cycle:
            self.assertEqual(cycle.model_name, "test_model")
            self.assertTrue(cycle.model_dir.exists())
            self.assertTrue(cycle.work_dir.exists())
    
    def test_find_source_model(self):
        """Test finding source model"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Should find our mock model
            source_model = cycle.find_source_model()
            self.assertIsNotNone(source_model)
            self.assertEqual(source_model.name, "test_model.gguf")
            
        # Test with no models
        self.mock_model.unlink()
        with QuantizationCycle("test") as cycle:
            source_model = cycle.find_source_model()
            self.assertIsNone(source_model)
    
    def test_clone_model_weights(self):
        """Test cloning model weights"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            cloned_path = cycle.clone_model_weights(self.mock_model)
            
            self.assertTrue(cloned_path.exists())
            self.assertEqual(cloned_path.parent, cycle.work_dir)
            self.assertEqual(cloned_path.name, self.mock_model.name)
    
    def test_quantize_model(self):
        """Test model quantization"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            cloned_path = cycle.clone_model_weights(self.mock_model)
            quantized_path = cycle.quantize_model(cloned_path, "Q2_K")
            
            self.assertTrue(quantized_path.exists())
            self.assertIn("q2_k", quantized_path.name.lower())
    
    def test_benchmark_model(self):
        """Test model benchmarking"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            cloned_path = cycle.clone_model_weights(self.mock_model)
            throughput = cycle.benchmark_model(cloned_path, "test")
            
            self.assertIsInstance(throughput, float)
            self.assertGreater(throughput, 0)
    
    def test_make_decision_keep(self):
        """Test decision making - keep case"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Small throughput drop (within threshold)
            decision = cycle.make_decision(100.0, 92.0)  # 8% drop
            self.assertEqual(decision, "kept")
    
    def test_make_decision_reject(self):
        """Test decision making - reject case"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Large throughput drop (exceeds threshold)
            decision = cycle.make_decision(100.0, 80.0)  # 20% drop
            self.assertEqual(decision, "rejected")
    
    def test_get_model_format(self):
        """Test model format detection"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Test different formats
            self.assertEqual(cycle.get_model_format(Path("model_q2_k.gguf")), "Q2_K")
            self.assertEqual(cycle.get_model_format(Path("model_q4_k_m.gguf")), "Q4_K_M")
            self.assertEqual(cycle.get_model_format(Path("model.gguf")), "F16")
    
    def test_estimate_throughput(self):
        """Test throughput estimation"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Test with different sized models
            throughput = cycle.estimate_throughput(self.mock_model)
            self.assertIsInstance(throughput, float)
            self.assertGreater(throughput, 0)
    
    @patch('scripts.quant_cycle.A2ABus')
    def test_publish_decision_event(self, mock_a2a_class):
        """Test A2A event publishing"""
        from scripts.quant_cycle import QuantizationCycle
        
        # Mock A2A bus instance
        mock_bus = MagicMock()
        mock_bus.pub.return_value = "test-stream-id"
        mock_a2a_class.return_value = mock_bus
        
        with QuantizationCycle("test") as cycle:
            metrics = {
                "original_throughput": 100.0,
                "quantized_throughput": 90.0,
                "throughput_drop_percent": 10.0,
                "source_format": "F16",
                "target_format": "Q2_K"
            }
            
            cycle.publish_decision_event("kept", metrics)
            
            # Verify A2A event was published
            mock_bus.pub.assert_called_once()
            call_args = mock_bus.pub.call_args
            
            self.assertEqual(call_args[1]['row_id'], "QUANT_CYCLE_BC180")
            self.assertEqual(call_args[1]['event_type'], "QUANT_DECISION")
            
            payload = call_args[1]['payload']
            self.assertEqual(payload['event_type'], "QUANT_DECISION")
            self.assertEqual(payload['decision'], "kept")
            self.assertEqual(payload['cycle_version'], "BC-180")
    
    @patch('scripts.quant_cycle.push_to_gateway')
    def test_push_metrics(self, mock_push):
        """Test Prometheus metrics pushing"""
        from scripts.quant_cycle import QuantizationCycle
        
        # Temporarily disable dry run for this test
        os.environ['DRY_RUN'] = 'false'
        
        try:
            with QuantizationCycle("test") as cycle:
                cycle.push_metrics()
                mock_push.assert_called_once()
        finally:
            os.environ['DRY_RUN'] = 'true'
    
    @patch('scripts.quant_cycle.A2ABus')
    def test_complete_cycle_success(self, mock_a2a_class):
        """Test complete quantization cycle - success case"""
        from scripts.quant_cycle import QuantizationCycle
        
        # Mock A2A bus
        mock_bus = MagicMock()
        mock_bus.pub.return_value = "test-stream-id"
        mock_a2a_class.return_value = mock_bus
        
        with QuantizationCycle("test") as cycle:
            result = cycle.run_cycle()
            
            self.assertTrue(result["success"])
            self.assertIn("decision", result)
            self.assertIn(result["decision"], ["kept", "rejected"])
            self.assertIn("duration_seconds", result)
            self.assertIn("metrics", result)
            
            # Verify A2A event was published
            mock_bus.pub.assert_called_once()
    
    def test_complete_cycle_no_model(self):
        """Test complete cycle with no source model"""
        from scripts.quant_cycle import QuantizationCycle
        
        # Remove mock model
        self.mock_model.unlink()
        
        with QuantizationCycle("test") as cycle:
            result = cycle.run_cycle()
            
            self.assertFalse(result["success"])
            self.assertIn("error", result)
    
    @patch('scripts.quant_cycle.quant_cycle_decision')
    @patch('scripts.quant_cycle.quant_cycle_throughput')
    @patch('scripts.quant_cycle.quant_cycle_duration')
    def test_metrics_recording(self, mock_duration, mock_throughput, mock_decision):
        """Test that Prometheus metrics are recorded correctly"""
        from scripts.quant_cycle import QuantizationCycle
        
        with QuantizationCycle("test") as cycle:
            # Test duration metric
            cycle.clone_model_weights(self.mock_model)
            mock_duration.labels.assert_called()
            
            # Test throughput metric
            cycle.benchmark_model(self.mock_model, "test")
            mock_throughput.labels.assert_called()
    
    def test_cleanup(self):
        """Test cleanup functionality"""
        from scripts.quant_cycle import QuantizationCycle
        
        cycle = QuantizationCycle("test")
        work_dir = cycle.work_dir
        
        self.assertTrue(work_dir.exists())
        
        cycle.cleanup()
        
        self.assertFalse(work_dir.exists())


class TestQuantCycleScript(unittest.TestCase):
    """Test the quantization cycle script interface"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="quant_script_test_"))
        self.model_dir = self.test_dir / "models"
        self.model_dir.mkdir()
        
        # Create mock model
        mock_model = self.model_dir / "tiny_model.gguf"
        mock_model.write_text("tiny mock model")
        
        # Set environment
        os.environ['MODEL_DIR'] = str(self.model_dir)
        os.environ['DRY_RUN'] = 'true'
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)
        
        for key in ['MODEL_DIR', 'DRY_RUN']:
            if key in os.environ:
                del os.environ[key]
    
    @patch('scripts.quant_cycle.QuantizationCycle')
    def test_main_function_success(self, mock_cycle_class):
        """Test main function with successful cycle"""
        from scripts.quant_cycle import main
        
        # Mock successful cycle
        mock_cycle = MagicMock()
        mock_cycle.run_cycle.return_value = {
            "success": True,
            "decision": "kept",
            "duration_seconds": 45.2
        }
        mock_cycle_class.return_value.__enter__.return_value = mock_cycle
        
        # Test that main completes without exception
        try:
            with patch('sys.argv', ['quant_cycle.py', '--dry-run']):
                main()
        except SystemExit as e:
            self.assertEqual(e.code, 0)  # Should exit with success
    
    @patch('scripts.quant_cycle.QuantizationCycle')
    def test_main_function_failure(self, mock_cycle_class):
        """Test main function with failed cycle"""
        from scripts.quant_cycle import main
        
        # Mock failed cycle
        mock_cycle = MagicMock()
        mock_cycle.run_cycle.return_value = {
            "success": False,
            "error": "Test failure"
        }
        mock_cycle_class.return_value.__enter__.return_value = mock_cycle
        
        # Test that main exits with error
        try:
            with patch('sys.argv', ['quant_cycle.py', '--dry-run']):
                main()
        except SystemExit as e:
            self.assertEqual(e.code, 1)  # Should exit with error


class TestQuantCycleIntegration(unittest.TestCase):
    """Integration tests for quantization cycle"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix="quant_integration_"))
        self.model_dir = self.test_dir / "models"
        self.model_dir.mkdir()
        
        # Create a larger mock model file
        mock_model = self.model_dir / "integration_test.gguf"
        with open(mock_model, 'wb') as f:
            f.write(b"Mock GGUF model content " * 50000)  # ~1MB file
        
        os.environ['MODEL_DIR'] = str(self.model_dir)
        os.environ['DRY_RUN'] = 'true'
    
    def tearDown(self):
        """Clean up integration test"""
        shutil.rmtree(self.test_dir)
        
        for key in ['MODEL_DIR', 'DRY_RUN']:
            if key in os.environ:
                del os.environ[key]
    
    @patch('scripts.quant_cycle.A2ABus')
    def test_end_to_end_quantization(self, mock_a2a_class):
        """Test complete end-to-end quantization cycle"""
        from scripts.quant_cycle import QuantizationCycle
        
        # Mock A2A bus
        mock_bus = MagicMock()
        mock_bus.pub.return_value = "integration-test-stream"
        mock_a2a_class.return_value = mock_bus
        
        with QuantizationCycle("integration_test") as cycle:
            start_time = time.time()
            result = cycle.run_cycle()
            duration = time.time() - start_time
            
            # Verify successful completion
            self.assertTrue(result["success"])
            self.assertIn(result["decision"], ["kept", "rejected"])
            self.assertLess(duration, 60)  # Should complete within 1 minute in dry run
            
            # Verify metrics
            self.assertIn("metrics", result)
            metrics = result["metrics"]
            self.assertIn("original_throughput", metrics)
            self.assertIn("quantized_throughput", metrics)
            self.assertIn("throughput_drop_percent", metrics)
            
            # Verify A2A event
            mock_bus.pub.assert_called_once()
            event_call = mock_bus.pub.call_args
            self.assertEqual(event_call[1]['event_type'], "QUANT_DECISION")


def run_quant_cycle_tests():
    """Run all quantization cycle tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestQuantizationCycle,
        TestQuantCycleScript,
        TestQuantCycleIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestClass(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful()
    }


if __name__ == "__main__":
    print("🧪 Running Quantization Cycle Tests (BC-180)")
    print("=" * 50)
    
    results = run_quant_cycle_tests()
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results:")
    print(f"   Tests run: {results['tests_run']}")
    print(f"   Failures: {results['failures']}")
    print(f"   Errors: {results['errors']}")
    print(f"   Success: {'✅' if results['success'] else '❌'}")
    
    if results['success']:
        print("\n🎉 All quantization cycle tests passed!")
        print("   ✅ Cycle initialization working")
        print("   ✅ Model quantization logic verified") 
        print("   ✅ Decision making tested")
        print("   ✅ A2A event publishing confirmed")
        print("   ✅ Metrics recording validated")
    else:
        print("\n❌ Some tests failed - check output above")
        exit(1) 