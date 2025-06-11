#!/usr/bin/env python3
"""
IDR-01 Focused 2-Minute Watch
Monitors specific signals with action triggers
"""

import requests
import time
from datetime import datetime

def check_metric(metric_query):
    """Query Prometheus for specific metric"""
    try:
        response = requests.get(f"http://localhost:9090/api/v1/query?query={metric_query}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', {}).get('result', [])
            if results:
                return float(results[0]['value'][1])
        return 0
    except:
        return 0

def main():
    print("🎯 IDR-01 Focused 2-Minute Watch")
    print("=" * 50)
    start_time = time.time()
    
    builder_deploy_detected = False
    idr_metric_achieved = False
    
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print("🔍 Watching for:")
    print("   1. builder_deploy_total{pr=\"IDR-01\"} increment")
    print("   2. idr_json_total{source=\"slack\"} ≥ 1")
    print()
    
    while time.time() - start_time < 120:  # 2 minute window
        elapsed = int(time.time() - start_time)
        
        # Check builder deploy metric
        builder_metric = check_metric('builder_deploy_total{pr="IDR-01"}')
        
        # Check IDR metric  
        idr_metric = check_metric('idr_json_total{source="slack"}')
        
        print(f"\r⏱️  T+{elapsed:3d}s | builder_deploy: {builder_metric} | idr_total: {idr_metric}", end="", flush=True)
        
        # Signal 1: Builder deploy
        if not builder_deploy_detected and builder_metric > 0:
            print(f"\n✅ SIGNAL 1: builder_deploy_total detected! (T+{elapsed}s)")
            print("   📱 Slack #builder-alerts should show merge confirmation")
            builder_deploy_detected = True
            
        # Signal 2: IDR metric
        if not idr_metric_achieved and idr_metric >= 1:
            print(f"\n✅ SIGNAL 2: idr_json_total ≥ 1 achieved! (T+{elapsed}s)")
            print("   🎉 Canary deployment validated")
            idr_metric_achieved = True
            break
            
        time.sleep(3)  # Check every 3 seconds
    
    elapsed = int(time.time() - start_time)
    print(f"\n\n{'='*50}")
    print(f"⏰ Watch Complete: {elapsed}s elapsed")
    
    if builder_deploy_detected and idr_metric_achieved:
        print("🎉 SUCCESS: Both signals confirmed!")
        print("📋 Next action: patchctl unset-env SAFE_MIN_TARGETS")
        print("⏳ LG-210 will auto-enable after soak completion")
    elif not builder_deploy_detected:
        print("⚠️  MISSING: builder_deploy_total{pr=\"IDR-01\"}")
        print("💡 Manual nudge: builderctl trigger-poll")
        print("💡 Alt: gh pr label builder/IDR-01-intent-agent autonomous")
    elif not idr_metric_achieved:
        print("⚠️  MISSING: idr_json_total{source=\"slack\"} ≥ 1")
        print("💡 Manual trigger: Send /intent command in Slack")
    
    print(f"\n📊 Final values:")
    print(f"   builder_deploy_total: {check_metric('builder_deploy_total{pr=\"IDR-01\"}')}")
    print(f"   idr_json_total: {check_metric('idr_json_total{source=\"slack\"}')}")

if __name__ == "__main__":
    main() 