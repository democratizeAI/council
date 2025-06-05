#!/usr/bin/env python3
"""
Test script for preference model training pipeline.
Validates dataset, model config, and training setup.
"""

import json
import os
import sys
from pathlib import Path

def test_dataset():
    """Test that merged preference dataset is valid."""
    dataset_path = "data/merged_prefs_20250605.jsonl"
    
    if not os.path.exists(dataset_path):
        print(f"❌ Dataset not found: {dataset_path}")
        return False
    
    try:
        pairs = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    data = json.loads(line)
                    
                    # Validate schema
                    required_keys = ['prompt', 'chosen', 'rejected']
                    if not all(k in data for k in required_keys):
                        print(f"❌ Line {line_num}: Missing required keys {required_keys}")
                        return False
                    
                    pairs.append(data)
        
        print(f"✅ Dataset valid: {len(pairs)} preference pairs")
        
        # Show sample
        if pairs:
            sample = pairs[0]
            print(f"📝 Sample pair:")
            print(f"   Prompt: {sample['prompt'][:50]}...")
            print(f"   Chosen: {sample['chosen'][:50]}...")
            print(f"   Rejected: {sample['rejected'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Dataset validation failed: {e}")
        return False

def test_model_config():
    """Test model configuration."""
    config_path = "config/models.yaml"
    
    if not os.path.exists(config_path):
        print(f"❌ Model config not found: {config_path}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check for preference model
        models = config.get('models', [])
        pref_models = [m for m in models if m.get('role') == 'preference']
        
        if not pref_models:
            print("❌ No preference models found in config")
            return False
        
        pref_model = pref_models[0]
        print(f"✅ Preference model configured:")
        print(f"   Name: {pref_model['name']}")
        print(f"   Path: {pref_model['path']}")
        print(f"   VRAM: {pref_model['vram_mb']}MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Model config validation failed: {e}")
        return False

def test_training_script():
    """Test training script exists and is executable."""
    script_path = "scripts/train_lora.sh"
    
    if not os.path.exists(script_path):
        print(f"❌ Training script not found: {script_path}")
        return False
    
    # Check if script has execution content
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'train_preference_lora.py' not in content:
        print("❌ Training script missing core functionality")
        return False
    
    print("✅ Training script configured")
    return True

def test_api_endpoint():
    """Test reward API endpoint file."""
    api_path = "app/router/reward.py"
    
    if not os.path.exists(api_path):
        print(f"❌ Reward API not found: {api_path}")
        return False
    
    with open(api_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_elements = [
        '@router.post("/score"',
        'ScoreRequest', 
        'ScoreResponse',
        'load_preference_model'
    ]
    
    for element in required_elements:
        if element not in content:
            print(f"❌ API missing element: {element}")
            return False
    
    print("✅ Reward API endpoint configured")
    return True

def test_environment():
    """Test scheduler environment configuration."""
    env_path = "config/scheduler.env"
    
    if not os.path.exists(env_path):
        print(f"❌ Scheduler config not found: {env_path}")
        return False
    
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_vars = [
        'PREF_HEAD_LORA_PATH',
        'PREF_DATA_PATH', 
        'PREF_FINE_TUNE_CRON'
    ]
    
    for var in required_vars:
        if var not in content:
            print(f"❌ Environment missing variable: {var}")
            return False
    
    print("✅ Scheduler environment configured")
    return True

def main():
    """Run all tests."""
    print("🧪 Testing Preference Model Pipeline")
    print("=" * 50)
    
    tests = [
        ("Dataset Validation", test_dataset),
        ("Model Configuration", test_model_config),
        ("Training Script", test_training_script),
        ("API Endpoint", test_api_endpoint),
        ("Environment Config", test_environment)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"   ⚠️  Test failed")
    
    print("\n" + "=" * 50)
    print(f"🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Preference model ready for training.")
        print("💡 Next steps:")
        print("   1. Run training: bash scripts/train_lora.sh --base phi2-2.7b --data data/merged_prefs_20250605.jsonl --output models/lora_pref_phi2_20250605")
        print("   2. Test API endpoint: curl -X POST /reward/score")
        print("   3. Monitor training: check Grafana dashboard")
        return 0
    else:
        print("❌ Some tests failed. Please fix issues before training.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 