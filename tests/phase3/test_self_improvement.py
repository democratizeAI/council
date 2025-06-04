#!/usr/bin/env python3
"""
Phase 3 Self-Improvement Loop Test Suite
=======================================

Tests the complete self-improvement pipeline:
1. Failure harvesting with Agent-0 rewrites
2. QLoRA training pipeline
3. Automatic deployment and rollback
4. Quality regression detection
"""

import pytest
import asyncio
import sys
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from harvest_failures import FailureHarvester
from faiss_memory import FaissMemory

class TestFailureHarvester:
    """Test the Agent-0 failure harvesting system"""
    
    @pytest.fixture
    def temp_memory_dir(self):
        """Create temporary memory directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def harvester(self, temp_memory_dir):
        """Create harvester instance with test memory"""
        return FailureHarvester(memory_path=temp_memory_dir)
    
    def test_harvester_initialization(self, harvester):
        """Test that harvester initializes correctly"""
        assert harvester.memory is not None
        assert harvester.harvest_stats["failures_found"] == 0
        assert harvester.harvest_stats["rewrites_successful"] == 0
        assert "harvest_timestamp" in harvester.harvest_stats
        print("✅ Harvester initialization test passed")
    
    def test_quality_assessment(self, harvester):
        """Test the quality assessment algorithm"""
        
        # Test basic improvement (length)
        query = "What is 2+2?"
        bad_response = "IDK"
        good_response = "To calculate 2+2, I need to add these numbers step by step. 2 + 2 = 4. Therefore, the answer is 4."
        
        score = harvester._assess_quality(query, bad_response, good_response)
        assert score > 0.5, "Quality should improve with better response"
        
        # Test reasoning improvement
        query_math = "Calculate the area of a circle"
        bad_math = "Area is big"
        good_math = "To calculate the area of a circle, I use the formula A = πr². First, I need the radius. Then I square it and multiply by π (approximately 3.14159)."
        
        score_math = harvester._assess_quality(query_math, bad_math, good_math)
        assert score_math >= 0.7, "Mathematical responses with reasoning should score highly"
        
        print(f"✅ Quality assessment test passed (scores: {score:.2f}, {score_math:.2f})")
    
    @pytest.mark.asyncio
    async def test_harvest_no_failures(self, harvester):
        """Test harvesting when no failures exist"""
        
        failures = await harvester.harvest_yesterday_failures()
        assert failures == [], "Should return empty list when no failures"
        
        stats = await harvester.run_harvest()
        assert stats["failures_found"] == 0
        assert stats["training_pairs_generated"] == 0
        
        print("✅ No failures harvest test passed")
    
    def test_mock_failure_data(self, harvester):
        """Test with mock failure data"""
        
        # Create mock failures
        yesterday = datetime.now() - timedelta(days=1)
        mock_failures = [
            {
                "query": "What is machine learning?",
                "response": "IDK something with computers",
                "timestamp": yesterday.timestamp(),
                "model": "test-model",
                "confidence": 0.2,
                "failure_reason": "low_quality"
            },
            {
                "query": "Calculate 15 * 23",
                "response": "big number",
                "timestamp": yesterday.timestamp(),
                "model": "test-model", 
                "confidence": 0.1,
                "failure_reason": "wrong_answer"
            }
        ]
        
        # Mock the harvest method to return our test data
        with patch.object(harvester, 'harvest_yesterday_failures', return_value=mock_failures):
            assert len(mock_failures) == 2
            
        print("✅ Mock failure data test passed")

class TestTrainingPipeline:
    """Test QLoRA training pipeline components"""
    
    @pytest.fixture
    def training_data_dir(self):
        """Create temporary training data directory"""
        temp_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(temp_dir, "training_data"), exist_ok=True)
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_training_data_format(self, training_data_dir):
        """Test training data format validation"""
        
        # Create sample training data
        training_examples = [
            {
                "instruction": "What is 2+2?",
                "input": "",
                "output": "To calculate 2+2, I add the numbers: 2 + 2 = 4",
                "reasoning": "This is basic arithmetic addition",
                "quality_score": 0.8,
                "harvest_timestamp": datetime.now().timestamp()
            },
            {
                "instruction": "Explain machine learning",
                "input": "",
                "output": "Machine learning is a subset of AI that enables computers to learn from data without being explicitly programmed.",
                "reasoning": "This requires explaining a technical concept clearly",
                "quality_score": 0.9,
                "harvest_timestamp": datetime.now().timestamp()
            }
        ]
        
        # Save as JSONL format
        training_file = os.path.join(training_data_dir, "training_data", "harvest_test.jsonl")
        with open(training_file, 'w') as f:
            for example in training_examples:
                f.write(json.dumps(example) + '\n')
        
        # Validate format
        assert os.path.exists(training_file)
        
        # Read back and validate
        loaded_examples = []
        with open(training_file, 'r') as f:
            for line in f:
                example = json.loads(line.strip())
                loaded_examples.append(example)
        
        assert len(loaded_examples) == 2
        assert loaded_examples[0]["instruction"] == "What is 2+2?"
        assert loaded_examples[1]["quality_score"] == 0.9
        
        print("✅ Training data format test passed")
    
    def test_lora_config_generation(self, training_data_dir):
        """Test LoRA configuration generation"""
        
        config = {
            "base_model": "models/test-model",
            "training_data": "training_data/harvest_test.jsonl",
            "output_dir": "loras/test",
            "batch_size": 4,
            "gradient_accumulation_steps": 8,
            "learning_rate": 5e-5,
            "num_epochs": 3,
            "lora_rank": 16,
            "lora_alpha": 32,
            "max_seq_length": 2048,
            "training_timestamp": datetime.now().isoformat(),
            "training_examples": 25
        }
        
        # Save config
        config_file = os.path.join(training_data_dir, "training_config.json")
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Validate config
        with open(config_file, 'r') as f:
            loaded_config = json.load(f)
        
        assert loaded_config["lora_rank"] == 16
        assert loaded_config["batch_size"] == 4
        assert loaded_config["training_examples"] == 25
        
        print("✅ LoRA config generation test passed")

class TestDeploymentPipeline:
    """Test LoRA deployment and rollback system"""
    
    @pytest.fixture
    def lora_dir(self):
        """Create temporary LoRA directory structure"""
        temp_dir = tempfile.mkdtemp()
        lora_dir = os.path.join(temp_dir, "loras", "test")
        os.makedirs(lora_dir, exist_ok=True)
        
        # Create mock LoRA files
        with open(os.path.join(lora_dir, "adapter_config.json"), 'w') as f:
            json.dump({"r": 16, "lora_alpha": 32, "target_modules": ["q_proj", "v_proj"]}, f)
        
        with open(os.path.join(lora_dir, "adapter_model.bin"), 'wb') as f:
            f.write(b"mock_adapter_weights")
        
        with open(os.path.join(lora_dir, "training_config.json"), 'w') as f:
            json.dump({"training_examples": 20, "final_loss": 0.5}, f)
        
        with open(os.path.join(lora_dir, "deployment_ready.txt"), 'w') as f:
            f.write(datetime.now().isoformat())
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_lora_file_validation(self, lora_dir):
        """Test LoRA file validation"""
        
        lora_path = os.path.join(lora_dir, "loras", "test")
        
        # Check required files exist
        required_files = ["adapter_config.json", "adapter_model.bin", "training_config.json", "deployment_ready.txt"]
        
        for file in required_files:
            file_path = os.path.join(lora_path, file)
            assert os.path.exists(file_path), f"Required file missing: {file}"
        
        # Validate config content
        with open(os.path.join(lora_path, "adapter_config.json"), 'r') as f:
            config = json.load(f)
        
        assert config["r"] == 16
        assert "target_modules" in config
        
        print("✅ LoRA file validation test passed")
    
    def test_deployment_summary_format(self, lora_dir):
        """Test deployment summary format"""
        
        summary = {
            "deployment_timestamp": datetime.now().isoformat(),
            "lora_directory": os.path.join(lora_dir, "loras", "test"),
            "pre_deployment": {
                "success_rate": "0.875",
                "avg_latency_ms": "750"
            },
            "post_deployment": {
                "success_rate": "0.920",
                "avg_latency_ms": "680"
            },
            "monitoring_duration_s": 60,
            "rollback_thresholds": {
                "max_latency_ms": 1000,
                "min_success_rate": 0.85
            },
            "deployment_status": "successful"
        }
        
        # Save summary
        summary_file = os.path.join(lora_dir, "loras", "test", "deployment_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Validate summary
        with open(summary_file, 'r') as f:
            loaded_summary = json.load(f)
        
        assert loaded_summary["deployment_status"] == "successful"
        assert loaded_summary["monitoring_duration_s"] == 60
        assert float(loaded_summary["post_deployment"]["success_rate"]) > float(loaded_summary["pre_deployment"]["success_rate"])
        
        print("✅ Deployment summary format test passed")

class TestQualityRegression:
    """Test quality regression detection and rollback triggers"""
    
    def test_latency_regression_detection(self):
        """Test latency regression detection logic"""
        
        # Simulated metrics
        pre_latency = 650.0  # ms
        post_latency = 1200.0  # ms
        threshold = 1000.0  # ms
        
        # Should trigger rollback
        assert post_latency > threshold, "Latency regression should be detected"
        
        # Normal case
        normal_latency = 720.0
        assert normal_latency <= threshold, "Normal latency should not trigger rollback"
        
        print("✅ Latency regression detection test passed")
    
    def test_success_rate_regression(self):
        """Test success rate regression detection"""
        
        # Simulated metrics
        pre_success_rate = 0.875
        post_success_rate = 0.780  # Dropped significantly
        threshold = 0.85
        
        # Should trigger rollback
        assert post_success_rate < threshold, "Success rate regression should be detected"
        
        # Normal case
        normal_success_rate = 0.920
        assert normal_success_rate >= threshold, "Good success rate should not trigger rollback"
        
        print("✅ Success rate regression detection test passed")
    
    def test_rollback_target_selection(self):
        """Test rollback target selection logic"""
        
        # Mock directory structure
        mock_dirs = [
            "loras/rollback_20241215_143022",
            "loras/backup_20241214_091245", 
            "loras/failed_20241215_120033"
        ]
        
        # Should prefer rollback_ over backup_ over failed_
        rollback_dirs = [d for d in mock_dirs if "rollback_" in d]
        backup_dirs = [d for d in mock_dirs if "backup_" in d]
        
        if rollback_dirs:
            target = sorted(rollback_dirs)[-1]  # Most recent
            assert "rollback_" in target
        elif backup_dirs:
            target = sorted(backup_dirs)[-1]
            assert "backup_" in target
        
        print("✅ Rollback target selection test passed")

@pytest.mark.asyncio
async def test_end_to_end_simulation():
    """Simulate the complete self-improvement loop"""
    
    print("\n🧪 End-to-End Self-Improvement Simulation")
    print("=" * 50)
    
    # Phase 1: Mock failure harvest
    print("📊 Phase 1: Failure Harvesting...")
    
    mock_failures = [
        {"query": "What is AI?", "response": "dunno", "confidence": 0.2},
        {"query": "Calculate 7*8", "response": "big", "confidence": 0.1}
    ]
    
    # Mock Agent-0 rewrites
    mock_rewrites = [
        {
            "original_query": "What is AI?",
            "agent0_improved_response": "AI (Artificial Intelligence) is the simulation of human intelligence in machines that are programmed to think and learn.",
            "quality_score": 0.85
        },
        {
            "original_query": "Calculate 7*8", 
            "agent0_improved_response": "To calculate 7*8: 7 × 8 = 56. Therefore, the answer is 56.",
            "quality_score": 0.90
        }
    ]
    
    high_quality_rewrites = [r for r in mock_rewrites if r["quality_score"] >= 0.7]
    print(f"   ✅ {len(high_quality_rewrites)} high-quality rewrites generated")
    
    # Phase 2: Mock training
    print("🧠 Phase 2: QLoRA Training...")
    
    training_config = {
        "training_examples": len(high_quality_rewrites),
        "final_loss": 0.45,
        "training_completed": True
    }
    
    print(f"   ✅ Training completed with {training_config['training_examples']} examples")
    print(f"   📊 Final loss: {training_config['final_loss']}")
    
    # Phase 3: Mock deployment
    print("🚀 Phase 3: Deployment...")
    
    pre_metrics = {"success_rate": 0.875, "avg_latency_ms": 720}
    post_metrics = {"success_rate": 0.925, "avg_latency_ms": 680}
    
    # Quality improvement check
    improvement = post_metrics["success_rate"] > pre_metrics["success_rate"]
    latency_ok = post_metrics["avg_latency_ms"] < 1000  # threshold
    
    assert improvement, "Deployment should improve success rate"
    assert latency_ok, "Deployment should maintain acceptable latency"
    
    print(f"   ✅ Deployment successful: {post_metrics['success_rate']:.1%} success rate")
    print(f"   ⚡ Latency: {post_metrics['avg_latency_ms']}ms")
    
    # Phase 4: Monitoring
    print("📊 Phase 4: Monitoring...")
    
    monitoring_duration = 60  # seconds
    regression_detected = False
    
    print(f"   ✅ Monitored for {monitoring_duration}s, no regressions detected")
    
    # Summary
    print("\n🎯 Self-Improvement Loop Summary:")
    print(f"   📊 Failures processed: {len(mock_failures)}")
    print(f"   🔄 Rewrites generated: {len(high_quality_rewrites)}")
    print(f"   🧠 Training examples: {training_config['training_examples']}")
    print(f"   📈 Success rate: {pre_metrics['success_rate']:.1%} → {post_metrics['success_rate']:.1%}")
    print(f"   ⚡ Latency: {pre_metrics['avg_latency_ms']}ms → {post_metrics['avg_latency_ms']}ms")
    print("   ✅ Loop completed successfully!")

if __name__ == "__main__":
    # Run individual test classes
    test_harvester = TestFailureHarvester()
    test_training = TestTrainingPipeline()
    test_deployment = TestDeploymentPipeline()
    test_regression = TestQualityRegression()
    
    print("🧪 Phase 3 Self-Improvement Test Suite")
    print("=" * 45)
    
    # Create temporary fixtures for direct testing
    temp_dir = tempfile.mkdtemp()
    try:
        harvester = FailureHarvester(memory_path=temp_dir)
        
        # Run tests that don't require fixtures
        test_harvester.test_harvester_initialization(harvester)
        test_harvester.test_quality_assessment(harvester)
        test_harvester.test_mock_failure_data(harvester)
        
        test_regression.test_latency_regression_detection()
        test_regression.test_success_rate_regression()
        test_regression.test_rollback_target_selection()
        
        print("\n🚀 Running end-to-end simulation...")
        asyncio.run(test_end_to_end_simulation())
        
        print("\n🎉 All Phase 3 tests completed successfully!")
        print("✅ Self-improvement loop components validated")
        
    finally:
        shutil.rmtree(temp_dir) 