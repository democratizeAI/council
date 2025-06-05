#!/usr/bin/env python3
"""
48-Hour Soak Test Readiness Check
Validates all gates are green for soak test initiation
"""

import requests
import json
import os
import time
from datetime import datetime

def check_api_health():
    """Check API health and metrics"""
    print("🔍 Checking API Health...")
    
    try:
        # Main API
        r = requests.get("http://localhost:8000/healthz", timeout=5)
        if r.status_code == 200:
            print("  ✅ Main API healthy")
        else:
            print(f"  ❌ Main API unhealthy: {r.status_code}")
            return False
        
        # Canary API  
        r = requests.get("http://localhost:8001/healthz", timeout=5)
        if r.status_code == 200:
            print("  ✅ Canary API healthy")
        else:
            print(f"  ❌ Canary API unhealthy: {r.status_code}")
            return False
        
        # Metrics exposure
        r = requests.get("http://localhost:8000/metrics", timeout=5)
        if r.status_code == 200 and "swarm_api_request_duration_seconds" in r.text:
            print("  ✅ Metrics exposed correctly")
            return True
        else:
            print("  ❌ Metrics not properly exposed")
            return False
            
    except Exception as e:
        print(f"  ❌ API check failed: {e}")
        return False

def check_training_status():
    """Check training completion"""
    print("🧠 Checking Training Status...")
    
    # Reward model
    try:
        with open('logs/training/reward_v1_training_log.json', 'r') as f:
            reward_log = json.load(f)
        
        if reward_log.get('target_reached') and reward_log.get('final_accuracy', 0) >= 0.65:
            print(f"  ✅ Reward model: {reward_log['final_accuracy']:.4f} ≥ 0.65")
        else:
            print(f"  ❌ Reward model not ready")
            return False
            
    except FileNotFoundError:
        print("  ❌ Reward model training log not found")
        return False
    
    # RL-LoRA
    try:
        log_files = [f for f in os.listdir('logs/training') if f.startswith('rl_lora_') and f.endswith('_log.json')]
        if log_files:
            latest_log = max(log_files, key=lambda f: os.path.getmtime(f'logs/training/{f}'))
            with open(f'logs/training/{latest_log}', 'r') as f:
                rl_log = json.load(f)
            
            if rl_log.get('training_completed') and rl_log.get('reward_trend') in ['flat', 'up']:
                print(f"  ✅ RL-LoRA: {rl_log['final_reward']:.4f} ({rl_log['reward_trend']} trend)")
                return True
            else:
                print("  ❌ RL-LoRA not ready")
                return False
        else:
            print("  ❌ RL-LoRA training log not found")
            return False
            
    except Exception as e:
        print(f"  ❌ RL-LoRA check failed: {e}")
        return False

def check_gdpr_lineage():
    """Check GDPR purge and lineage"""
    print("🗑️ Checking GDPR & Lineage...")
    
    # GDPR purge metrics
    try:
        with open('metrics/snapshot_prune.prom', 'r') as f:
            content = f.read()
        
        if 'snapshot_pruned_total' in content:
            # Extract the count
            for line in content.split('\n'):
                if line.startswith('snapshot_pruned_total'):
                    count = line.split()[-1]
                    print(f"  ✅ GDPR purge: snapshot_pruned_total {count}")
                    break
        else:
            print("  ❌ GDPR metrics not found")
            return False
            
    except FileNotFoundError:
        print("  ❌ GDPR metrics file not found")
        return False
    
    # Lineage timestamp
    try:
        with open('metrics/lineage.prom', 'r') as f:
            content = f.read()
        
        if 'lineage_last_push_timestamp_seconds' in content:
            print("  ✅ Lineage: timestamp updated")
            return True
        else:
            print("  ❌ Lineage timestamp not found")
            return False
            
    except FileNotFoundError:
        print("  ❌ Lineage metrics file not found")
        return False

def check_monitoring_ready():
    """Check monitoring system readiness"""
    print("📊 Checking Monitoring...")
    
    # Check if alert rules exist
    if os.path.exists('monitoring/soak_alerts.yml'):
        print("  ✅ Soak test alerts configured")
    else:
        print("  ❌ Soak test alerts not found")
        return False
    
    # Check dashboard exists
    if os.path.exists('monitoring/grafana/dashboards/fastapi-soak.json'):
        print("  ✅ Grafana dashboard ready")
        return True
    else:
        print("  ❌ Grafana dashboard not found")
        return False

def main():
    print("🎯 48-Hour Soak Test Readiness Check")
    print("=" * 50)
    print(f"🕒 Check time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    gates = []
    
    # Gate checks
    gates.append(("API Health & Metrics", check_api_health()))
    gates.append(("Training Completion", check_training_status()))
    gates.append(("GDPR & Lineage", check_gdpr_lineage()))
    gates.append(("Monitoring Ready", check_monitoring_ready()))
    
    print("\n🚦 Gate Status Summary:")
    print("-" * 30)
    
    all_green = True
    for gate_name, status in gates:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {gate_name}")
        if not status:
            all_green = False
    
    print("\n🎭 Final Status:")
    if all_green:
        print("🟢 ALL GATES GREEN - Ready for 48-hour soak!")
        print("🚀 You can now start the soak test")
        print("📈 Monitor the live dashboard for:")
        print("   • p95 latency ≤ 200ms")
        print("   • 5xx rate ≤ 0.5%")
        print("   • VRAM < 10.5GB")
        print("   • All training metrics stable")
        return True
    else:
        print("🔴 Some gates are RED - Fix issues before soak")
        print("❌ Do NOT start 48-hour soak until all gates are green")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 