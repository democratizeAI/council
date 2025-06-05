#!/usr/bin/env python3
"""
Training Progress Checker (Supporting script)
Checks status of reward model and RL-LoRA training
"""

import json
import os
import time
from datetime import datetime

def check_reward_model_status():
    """Check reward model training status"""
    try:
        with open('logs/training/reward_v1_training_log.json', 'r') as f:
            log = json.load(f)
        
        status = "✅ PASSED" if log.get('target_reached') else "❌ FAILED"
        accuracy = log.get('final_accuracy', 0)
        
        print(f"📊 Reward Model: {status}")
        print(f"   Accuracy: {accuracy:.4f} (target: 0.65)")
        print(f"   Epochs: {log.get('epochs_trained', 'N/A')}")
        
        return log.get('target_reached', False)
        
    except FileNotFoundError:
        print("📊 Reward Model: ⏳ NOT STARTED")
        return False

def check_rl_lora_status():
    """Check RL-LoRA training status"""
    try:
        # Find the most recent RL-LoRA log
        log_files = [f for f in os.listdir('logs/training') if f.startswith('rl_lora_') and f.endswith('_log.json')]
        
        if not log_files:
            print("🔗 RL-LoRA: ⏳ NOT STARTED")
            return False
        
        # Get the most recent log
        latest_log = max(log_files, key=lambda f: os.path.getmtime(f'logs/training/{f}'))
        
        with open(f'logs/training/{latest_log}', 'r') as f:
            log = json.load(f)
        
        status = "✅ PASSED" if log.get('training_completed') else "❌ FAILED"
        reward = log.get('final_reward', 0)
        trend = log.get('reward_trend', 'unknown')
        
        print(f"🔗 RL-LoRA: {status}")
        print(f"   Final Reward: {reward:.4f}")
        print(f"   Trend: {trend}")
        print(f"   Commit: {log.get('commit_sha', 'N/A')[:8]}")
        
        return log.get('training_completed', False)
        
    except (FileNotFoundError, json.JSONDecodeError):
        print("🔗 RL-LoRA: ⏳ NOT STARTED")
        return False

def main():
    print("🎯 Training Progress Dashboard")
    print("=" * 40)
    
    reward_ok = check_reward_model_status()
    rl_lora_ok = check_rl_lora_status()
    
    print("\n📈 Overall Status:")
    if reward_ok and rl_lora_ok:
        print("   ✅ ALL TRAINING COMPLETE - Ready for 48h soak!")
    elif reward_ok:
        print("   🟡 Reward model ready, RL-LoRA pending")
    else:
        print("   ⏳ Training in progress...")
    
    print(f"\n🕒 Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main() 