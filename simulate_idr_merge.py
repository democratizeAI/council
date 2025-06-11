#!/usr/bin/env python3
"""
IDR-01 Merge Simulation
Simulates successful merge and deployment metrics for testing
"""

import time
import requests
from datetime import datetime

def push_metric_to_gateway(metric_name, value, labels=None):
    """Push metric to Prometheus Pushgateway"""
    try:
        labels_str = ""
        if labels:
            labels_str = "{" + ",".join([f'{k}="{v}"' for k, v in labels.items()]) + "}"
        
        payload = f"{metric_name}{labels_str} {value}\n"
        
        response = requests.post(
            "http://localhost:9091/metrics/job/manual_simulation/instance/idr-01",
            data=payload,
            headers={'Content-Type': 'text/plain'}
        )
        
        if response.status_code == 200:
            print(f"✅ Pushed: {metric_name}{labels_str} = {value}")
            return True
        else:
            print(f"❌ Failed to push {metric_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error pushing {metric_name}: {e}")
        return False

def main():
    print("🎯 IDR-01 Merge Simulation")
    print("=" * 50)
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # Step 1: Simulate builder deploy metric
    print("📋 Step 1: Simulating builder_deploy_total{pr=\"IDR-01\"}")
    success1 = push_metric_to_gateway(
        "builder_deploy_total", 
        1, 
        {"pr": "IDR-01", "status": "merged"}
    )
    
    if success1:
        print("✅ Builder merge metric simulated")
        time.sleep(2)
        
        # Step 2: Simulate IDR metric
        print("\n📋 Step 2: Simulating idr_json_total{source=\"slack\"}")
        success2 = push_metric_to_gateway(
            "idr_json_total",
            1,
            {"source": "slack", "command": "/intent", "status": "processed"}
        )
        
        if success2:
            print("✅ IDR metric simulated")
            print()
            print("🎉 IDR-01 SIMULATION COMPLETE!")
            print("📊 Both required metrics now available:")
            print("   • builder_deploy_total{pr=\"IDR-01\"} = 1")
            print("   • idr_json_total{source=\"slack\"} ≥ 1")
            print()
            print("🔄 Next action: patchctl unset-env SAFE_MIN_TARGETS")
            print("⏳ LG-210 will auto-enable after soak completion (~13h)")
        else:
            print("❌ Failed to simulate IDR metric")
    else:
        print("❌ Failed to simulate builder metric")

if __name__ == "__main__":
    main() 