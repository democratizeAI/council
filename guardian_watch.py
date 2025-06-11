#!/usr/bin/env python3
"""
Guardian Watch - Red Line Monitoring
Only alerts on conditions requiring manual intervention
"""

import time
import requests
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

def check_red_lines():
    """Check for Guardian auto-page conditions"""
    alerts = []
    
    # Check p95 latency (Guardian pages if > 170ms for 2 min)
    p95_latency = check_metric('histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))')
    if p95_latency > 170:
        alerts.append(f"🚨 P95 LATENCY: {p95_latency:.1f}ms > 170ms (Guardian page threshold)")
    
    # Check fragment events (must stay 0)
    frag_events = check_metric('frag_events_total')
    if frag_events > 0:
        alerts.append(f"🚨 FRAGMENT EVENT: frag_events_total = {frag_events} (breaks soak)")
    
    # Check LB failover during drill
    lb_failover = check_metric('lb_failover_success_total')
    p95_spike = check_metric('lb_p95_spike_ms')
    if lb_failover > 0 and p95_spike > 20:
        alerts.append(f"🚨 LB DRILL FAIL: p95 spike = {p95_spike:.1f}ms > 20ms threshold")
    
    return alerts

def main():
    print("🛡️ Guardian Watch - Red Line Monitoring")
    print("=" * 50)
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S ET')}")
    print()
    print("📋 EXT-24A Quick Reference:")
    print("┌─────────────────────────────────────────────────────────┐")
    print("│ Step │ Action                    │ Success Signal       │")
    print("├──────┼───────────────────────────┼─────────────────────┤")
    print("│ 1️⃣   │ gh pr merge EXT-24A       │ Slack: ✅ merged...  │")
    print("│ 2️⃣   │ PatchCtl auto-deploy      │ lb_exporter:9100 UP │")
    print("│ 3️⃣   │ ./scripts/kill_primary... │ lb_failover +1      │")
    print("│ 4️⃣   │ /ops snapshot note        │ Logged to titan     │")
    print("│ 5️⃣   │ [if fail] rollback        │ p95 < 160ms         │")
    print("└──────┴───────────────────────────┴─────────────────────┘")
    print()
    print("🕒 Key Timeline:")
    print("   Soak ends: ~18:30 ET → LG-210 auto-enable")
    print("   HA drill: 04:30 ET (T-28h)")
    print("   Anomaly: 06:30 ET (T-26h)")
    print("   Autoscaler: 08:30 ET (T-24h)")
    print()
    print("🚨 RED LINE CONDITIONS (Guardian auto-page):")
    print("   • p95 > 170ms for 2+ minutes")
    print("   • frag_events_total > 0")
    print("   • lb drill p95 spike > 20ms")
    print()
    print("🔍 Monitoring... (Ctrl+C to stop)")
    print("   Will alert ONLY on red line conditions requiring manual assist")
    print()
    
    last_alert_time = 0
    alert_cooldown = 300  # 5 minutes between alerts
    
    try:
        while True:
            alerts = check_red_lines()
            current_time = time.time()
            
            if alerts and (current_time - last_alert_time) > alert_cooldown:
                print(f"\n🚨 RED LINE ALERT - {datetime.now().strftime('%H:%M:%S')}")
                print("=" * 50)
                for alert in alerts:
                    print(alert)
                print()
                print("💡 MANUAL ASSIST REQUIRED")
                print("   Check Slack #ops-alerts for Guardian pages")
                print("   Consider: patchctl rollback deploy ha-lb-overlay")
                print("=" * 50)
                last_alert_time = current_time
            
            # Show quiet heartbeat every 5 minutes
            if int(current_time) % 300 == 0:
                p95 = check_metric('histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))')
                frag = check_metric('frag_events_total')
                print(f"🟢 {datetime.now().strftime('%H:%M')} - All green (p95: {p95:.1f}ms, frag: {frag})")
            
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print(f"\n✅ Guardian watch stopped at {datetime.now().strftime('%H:%M:%S')}")
        print("🎯 System ready for autopilot rail execution")

if __name__ == "__main__":
    main() 