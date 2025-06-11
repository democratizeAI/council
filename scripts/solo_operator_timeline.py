#!/usr/bin/env python3
"""
Solo Operator Timeline Monitor
Tracks remaining tasks before soak completion and freeze lift
"""

import time
from datetime import datetime, timedelta

def get_current_time():
    return datetime.now()

def print_timeline():
    current = get_current_time()
    
    print("🎯 SOLO OPERATOR TIMELINE - PRE-FREEZE COMPLETION")
    print("=" * 60)
    print(f"📅 Current Time: {current.strftime('%H:%M ET')}")
    print()
    
    # Calculate soak completion (1.2h from 16:54 = ~18:05)
    soak_completion = datetime.now().replace(hour=18, minute=5, second=0, microsecond=0)
    if current.date() < soak_completion.date():
        soak_completion = soak_completion + timedelta(days=1)
    
    time_to_soak = soak_completion - current
    
    print(f"⏳ Soak Completion: ~{soak_completion.strftime('%H:%M ET')} ({time_to_soak.total_seconds()/3600:.1f}h remaining)")
    print(f"🚀 Freeze Lift: 18:30 ET (Auto-execution)")
    print()
    
    # Task timeline
    tasks = [
        ("≈08:55", "Warm Slack slash-cmd", "/intent ping in prod Slack"),
        ("09:00", "Smoke-test /intent", "create ticket flow"),
        ("09:05", "Check stub adoption", "curl metrics endpoint"),
        ("09:30", "Verify QA-302 auto-merge", "gh pr view status"),
        ("12:55", "Prep BC-130 tail script", "./scripts/tail_bc130.sh"),
        ("13:00", "Watch BC-130 auto-PR", "council_smoke_pass_total"),
        ("13:10", "Tag pre-unfreeze state", "git tag v0.1-pre-unfreeze"),
        ("~18:05", "🎉 SOAK COMPLETE", "LG-210 AUTO-ENABLE activates"),
        ("18:29", "Guardian board check", "./scripts/quick_health.sh"),
        ("18:30", "🚀 FREEZE LIFTS", "Auto-merge sequence begins")
    ]
    
    print("📋 REMAINING TASK SCHEDULE:")
    print("┌────────┬─────────────────────────┬─────────────────────────┐")
    print("│  Time  │         Task            │        Action           │")
    print("├────────┼─────────────────────────┼─────────────────────────┤")
    
    for time_str, task, action in tasks:
        status = "⏳" if "18:" in time_str else "⏸️"
        print(f"│ {time_str:6} │ {status} {task:20} │ {action:22} │")
    
    print("└────────┴─────────────────────────┴─────────────────────────┘")
    print()
    
    print("🛡️ ROLLBACK COMMANDS (keep handy for post-18:30):")
    print("• Φ-3 GPU pin: docker compose restart phi3_vllm:prev")
    print("• Council-api: gh pr revert feature/council-api-v2-phi3 --auto")
    print("• Φ-3-mini pod: gh pr revert spec-714-phi3mini-pod --auto")
    print()
    
    print("🎯 NEXT IMMEDIATE ACTION:")
    if current.hour < 9:
        print("⏸️ STANDBY - Wait for 08:55 ET to warm Slack slash-cmd")
    elif current.hour == 9 and current.minute < 5:
        print("🔥 EXECUTE - Send /intent ping in prod Slack now!")
    elif current.hour == 9 and current.minute < 30:
        print("🔍 CHECK - Verify stub adoption metrics")
    elif current.hour < 13:
        print("⏸️ STANDBY - Monitor QA-302 auto-merge status")
    elif current.hour < 18:
        print("⏸️ STANDBY - Prepare for BC-130 and final checks")
    else:
        print("🚀 FINAL PHASE - Soak completion imminent!")

if __name__ == "__main__":
    print_timeline() 