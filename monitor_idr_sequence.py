#!/usr/bin/env python3
"""
IDR-01 Merge Sequence Monitor
Tracks the automated deployment pipeline post-emergency override
"""

import requests
import time
import json
from datetime import datetime

def check_prometheus_metric(metric_query):
    """Query Prometheus for a specific metric"""
    try:
        response = requests.get(f"http://localhost:9090/api/v1/query?query={metric_query}")
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('result', [])
        return []
    except Exception as e:
        return f"Error: {e}"

def check_targets_status():
    """Check current OPS board status"""
    try:
        response = requests.get("http://localhost:9090/api/v1/query?query=up")
        if response.status_code == 200:
            data = response.json()
            results = data['data']['result']
            up_count = sum(1 for r in results if r['value'][1] == '1')
            total = len(results)
            return f"{up_count}/{total}"
        return "Error"
    except:
        return "Error"

def check_agent_health():
    """Verify Agent-0 API is still healthy"""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            return "✅ Healthy"
        return f"❌ HTTP {response.status_code}"
    except:
        return "❌ Unreachable"

def main():
    """Monitor the IDR-01 sequence"""
    print("🔍 IDR-01 Merge Sequence Monitor")
    print("=" * 50)
    start_time = time.time()
    
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S UTC')}")
    print(f"🎯 Watching for: Builder-swarm merge (≤ 1 min)")
    print(f"📊 Then: idr_json_total metric (≤ 60s)")
    print()
    
    step1_completed = False
    step2_completed = False
    
    while time.time() - start_time < 600:  # 10 minute window
        elapsed = int(time.time() - start_time)
        
        # Check OPS board (should stay ≥ 19/39)
        targets_status = check_targets_status()
        
        # Check Agent-0 health
        agent_health = check_agent_health()
        
        # Check for builder deploy metric
        builder_metric = check_prometheus_metric('builder_deploy_total{pr="IDR-01"}')
        
        # Check for IDR metric
        idr_metric = check_prometheus_metric('idr_json_total{source="slack"}')
        
        print(f"\r⏱️  T+{elapsed:3d}s | Targets: {targets_status} | Agent-0: {agent_health}", end="")
        
        # Step 1: Check for merge completion
        if not step1_completed and builder_metric and len(builder_metric) > 0:
            print(f"\n✅ STEP 1: Builder merge detected! (T+{elapsed}s)")
            step1_completed = True
            
        # Step 2: Check for IDR metric
        if step1_completed and not step2_completed and idr_metric and len(idr_metric) > 0:
            value = float(idr_metric[0]['value'][1])
            if value >= 1:
                print(f"\n✅ STEP 2: idr_json_total ≥ 1 confirmed! (T+{elapsed}s)")
                step2_completed = True
                break
        
        time.sleep(5)  # Check every 5 seconds
    
    print("\n" + "=" * 50)
    if step1_completed and step2_completed:
        print("🎉 IDR-01 SEQUENCE COMPLETE!")
        print("✅ Merge successful")
        print("✅ Canary deployment validated") 
        print("🔜 Ready for LG-210 after soak completion")
    else:
        print("⏳ Sequence in progress...")
        if not step1_completed:
            print("⏰ Waiting for Builder-swarm merge...")
        elif not step2_completed:
            print("⏰ Waiting for idr_json_total metric...")
    
    print(f"\n📋 Final Status:")
    print(f"   Targets: {check_targets_status()}")
    print(f"   Agent-0: {check_agent_health()}")
    print(f"   Runtime: {int(time.time() - start_time)}s")

if __name__ == "__main__":
    main() 