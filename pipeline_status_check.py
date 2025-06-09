#!/usr/bin/env python3
"""
Autonomous Pipeline Status Verification
=======================================
"""

import os

def check_pipeline_status():
    """Check all autonomous pipeline components"""
    print("🎯 AUTONOMOUS PIPELINE STATUS CHECK")
    print("=" * 50)
    
    checks = [
        ("Autonomous Flag", "guardian_autonomous.flag", "System autonomy enabled"),
        ("Ledger Ready", "BUILDER_LEDGER_v10.4.md", "Build tracking active"),
        ("SBOM Security", ".github/workflows/sbom.yml", "Vulnerability scanning"),
        ("Docs Brain", "docs/guidebook", "Documentation system"),
        ("Protocol V1", "OPUS_PROTOCOL_V1.1.md", "UI-Ease Sprint protocol"),
        ("Protocol V2", "OPUS_PROTOCOL_V2.md", "Slack Command protocol"),
        ("Security Checklist", "slack_security_checklist.md", "Slack security guide"),
        ("Reality Check", "AUTONOMOUS_REALITY_CHECK.md", "System validation"),
    ]
    
    all_good = True
    
    for name, path, description in checks:
        exists = os.path.exists(path)
        status = "✅ ACTIVE" if exists else "❌ Missing"
        print(f"{status:<12} | {name:<20} | {description}")
        if not exists:
            all_good = False
    
    print()
    print("🔍 CORE SYSTEM VALIDATION:")
    print("=" * 50)
    
    # Check if we can import key modules
    try:
        from router.voting import vote
        print("✅ READY      | Router Voting System  | Core decision engine")
    except Exception as e:
        print(f"❌ ERROR      | Router Voting System  | {str(e)[:40]}...")
        all_good = False
    
    try:
        import asyncio
        print("✅ READY      | Async Support         | Parallel execution")
    except Exception:
        print("❌ ERROR      | Async Support         | Cannot import asyncio")
        all_good = False
    
    # Check directory structure
    dirs_to_check = [
        "docs/guidebook",
        "docs/ledger", 
        "docs/audit",
        ".github/workflows"
    ]
    
    for directory in dirs_to_check:
        if os.path.exists(directory):
            print(f"✅ READY      | {directory:<20} | Directory structure")
        else:
            print(f"❌ MISSING    | {directory:<20} | Directory structure")
            all_good = False
    
    print()
    if all_good:
        print("🚀 PIPELINE STATUS: FULLY OPERATIONAL")
        print("📜 Ready for Opus Protocol V2 execution!")
        print("🎯 All systems green for Slack integration!")
    else:
        print("⚠️ PIPELINE STATUS: NEEDS ATTENTION")
        print("📋 Some components missing - check above")
    
    return all_good

if __name__ == "__main__":
    status = check_pipeline_status()
    exit(0 if status else 1) 