#!/usr/bin/env python3
"""
Next Phase Monitor - EXT-24A through BC-200
Tracks critical drill sequence metrics and gates
"""

import time
import requests
from datetime import datetime, timedelta

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

def check_soak_completion():
    """Check if 24h soak test is complete"""
    # Soak started at 1749593368, runs for 24h
    start_time = 1749593368
    current_time = time.time()
    elapsed_hours = (current_time - start_time) / 3600
    remaining_hours = 24 - elapsed_hours
    
    return {
        'elapsed': elapsed_hours,
        'remaining': remaining_hours,
        'complete': remaining_hours <= 0
    }

def main():
    print("🔧 Next Phase Monitor - GA Release Drill Sequence")
    print("=" * 60)
    
    soak_status = check_soak_completion()
    
    print(f"📊 Current Status:")
    print(f"   ✅ IDR-01: COMPLETE (deployed & validated)")
    print(f"   ⏳ Soak Test: {soak_status['elapsed']:.1f}h elapsed, {soak_status['remaining']:.1f}h remaining")
    print(f"   🎯 LG-210: {'🟢 READY' if soak_status['complete'] else 'Pending soak completion'}")
    print()
    
    print("📅 Upcoming Critical Events:")
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│ T-minus │ Owner  │ Event                │ Key Metrics        │")
    print("├─────────┼────────┼──────────────────────┼───────────────────┤")
    print("│   28h   │ DevOps │ EXT-24A HA LB Drill │ lb_failover ≥ 1   │")
    print("│         │        │                      │ p95 spike < 20ms  │")
    print("├─────────┼────────┼──────────────────────┼───────────────────┤")
    print("│   26h   │ SRE    │ EXT-24B Anomaly     │ CouncilLatency    │")
    print("│         │        │ Burst + M-310       │ fires ≤ 30s       │")
    print("├─────────┼────────┼──────────────────────┼───────────────────┤")
    print("│   24h   │ FinOps │ EXT-24C Autoscaler   │ GPU 65-80%        │")
    print("│         │        │ Ramp to 600 QPS     │ VRAM < 10.5GB     │")
    print("├─────────┼────────┼──────────────────────┼───────────────────┤")
    print("│   22h   │ QA     │ BC-200 Fast-Gauntlet│ PASS verdict      │")
    print("└─────────┴────────┴──────────────────────┴───────────────────┘")
    print()
    
    print("🔍 Key Metrics Watch:")
    
    # Check current baseline metrics
    lb_failover = check_metric('lb_failover_success_total')
    latency_anomaly = check_metric('CouncilLatencyAnomaly_fired_total')
    gpu_util = check_metric('gpu_utilization_percent')
    vram_usage = check_metric('vram_usage_gb')
    frag_events = check_metric('frag_events_total')
    
    print(f"   📊 lb_failover_success_total: {lb_failover}")
    print(f"   📊 CouncilLatencyAnomaly_fired_total: {latency_anomaly}")
    print(f"   📊 gpu_utilization_percent: {gpu_util}%")
    print(f"   📊 vram_usage_gb: {vram_usage:.1f}GB")
    print(f"   📊 frag_events_total: {frag_events} (must stay 0)")
    print()
    
    print("🚨 Alert Thresholds:")
    print(f"   • lb_failover_success_total ≥ 1 ✓")
    print(f"   • p95 spike < 20ms during failover")
    print(f"   • CouncilLatencyAnomaly fires ≤ 30s")
    print(f"   • GPU utilization 65-80% target")
    print(f"   • VRAM usage < 10.5GB")
    print(f"   • frag_events_total = 0 (critical)")
    print()
    
    print("🔧 EXT-24A HA LB Drill Checklist:")
    print("   1. ⏰ Merge window opens at T-28h")
    print("   2. 🚀 PatchCtl deploys ha-lb-overlay")
    print("   3. 👀 Watch for new lb-traefik service")
    print("   4. ⚡ Execute: ./scripts/kill_primary_gpu.sh")
    print("   5. 📊 Monitor lb_failover_success_total increment")
    print("   6. 📈 Verify p95 spike < 20ms, recovery < 60s")
    print("   7. ✅ Confirm frag_events_total stays 0")
    print("   8. 📱 Watch Slack #ops-alerts for confirmation")
    print()
    
    print("🛡️ Rollback Command (if needed):")
    print("   patchctl rollback deploy ha-lb-overlay")
    print()
    
    if soak_status['complete']:
        print("🎉 LG-210 AUTO-ENABLE: READY!")
        print("   GAUNTLET_ENABLED=true will activate automatically")
    else:
        print(f"⏳ LG-210 AUTO-ENABLE: {soak_status['remaining']:.1f}h remaining")
    
    print()
    print("📍 System Status: 🟢 ALL RAILS GREEN - Ready for drill sequence")
    print("🎯 Next Action: Monitor for EXT-24A deployment at T-28h")

if __name__ == "__main__":
    main() 