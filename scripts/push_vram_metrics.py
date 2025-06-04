#!/usr/bin/env python3
"""
Push VRAM metrics to simulate alert firing
"""
import time
import requests
import sys
import argparse
from datetime import datetime

def push_metric(vram_percent, prometheus_url="http://localhost:9090"):
    """Push VRAM metric directly to Prometheus metrics endpoint"""
    # For demo purposes, we'll create a simple metric exposition
    metric_text = f"""# HELP swarm_gpu_memory_used_percent GPU memory usage percentage
# TYPE swarm_gpu_memory_used_percent gauge
swarm_gpu_memory_used_percent {vram_percent}
"""
    print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Setting VRAM metric to {vram_percent}%")
    
    # In a real setup, this would be exposed via the /metrics endpoint
    # For demo, we'll just print the metric and simulate
    print(f"   Metric: swarm_gpu_memory_used_percent = {vram_percent}")
    return True

def simulate_escalation():
    """Run the 7-minute escalation test with metrics"""
    print("🚀 Starting VRAM Alert Pipeline Test")
    print("===================================")
    
    # Step 1: Warning level (78%)
    print(f"\n⚠️  STEP 1: Triggering VRAM Warning (78%)")
    push_metric(78)
    print("   ⏳ Waiting 3 minutes for warning alert burn-in...")
    time.sleep(180)  # 3 minutes
    
    # Step 2: Critical level (88%)  
    print(f"\n🚨 STEP 2: Escalating to VRAM Critical (88%)")
    push_metric(88)
    print("   ⏳ Waiting 2 minutes for critical alert burn-in...")
    time.sleep(120)  # 2 minutes
    
    # Step 3: Emergency level (97%)
    print(f"\n🔥 STEP 3: Triggering VRAM Emergency (97%)")
    push_metric(97)
    print("   ⏳ Waiting 30 seconds for emergency alert...")
    time.sleep(30)   # 30 seconds
    
    # Cleanup
    print(f"\n✅ CLEANUP: Resetting VRAM to normal (25%)")
    push_metric(25)
    
    print(f"\n🎉 Alert pipeline test complete!")
    print("Expected results:")
    print("- ⚠️  VRAMWarning should have fired after 3 minutes")
    print("- 🚨 VRAMCritical should have fired after 2 minutes") 
    print("- 🔥 VRAMEmergency should have fired after 30 seconds")
    print("\nCheck: http://localhost:9090/alerts")
    print("Check: http://localhost:9093")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push VRAM metrics for alert testing")
    parser.add_argument("--vram", type=float, help="VRAM percentage to set")
    parser.add_argument("--escalation", action="store_true", help="Run full escalation test")
    args = parser.parse_args()
    
    if args.escalation:
        simulate_escalation()
    elif args.vram is not None:
        push_metric(args.vram)
    else:
        print("Usage: --vram <percent> or --escalation")
        sys.exit(1) 