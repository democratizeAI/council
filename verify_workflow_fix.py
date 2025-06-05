#!/usr/bin/env python3
"""
Workflow Fix Verification Script
Confirms upload-artifact@v4 fixes are properly applied
"""

import re
import os

def check_workflow_fixes():
    """Verify workflow files have been fixed"""
    
    workflow_files = [
        '.github/workflows/soak-test.yml',
        '.github/workflows/nightly-graduation.yml'
    ]
    
    print("🔍 Verifying GitHub Actions Workflow Fixes...")
    print("=" * 50)
    
    all_fixed = True
    
    for file_path in workflow_files:
        if not os.path.exists(file_path):
            print(f"❌ {file_path}: File not found")
            all_fixed = False
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for old v3 usage
        v3_matches = re.findall(r'actions/upload-artifact@v3', content)
        v4_matches = re.findall(r'actions/upload-artifact@v4', content)
        
        print(f"\n📄 {file_path}:")
        print(f"   Old @v3 usage: {len(v3_matches)} instances")
        print(f"   New @v4 usage: {len(v4_matches)} instances")
        
        if len(v3_matches) > 0:
            print(f"   ❌ Still contains deprecated @v3!")
            all_fixed = False
        elif len(v4_matches) > 0:
            print(f"   ✅ Updated to @v4")
        else:
            print(f"   ℹ️ No upload-artifact actions found")
    
    print(f"\n🎯 Overall Status:")
    if all_fixed:
        print("✅ All workflows fixed - upload-artifact@v4 applied")
        print("🚀 Workflows should now pass on GitHub Actions")
    else:
        print("❌ Some workflows still need fixes")
        
    return all_fixed

def check_soak_test_health():
    """Quick check that soak test is still running"""
    try:
        import requests
        
        main_r = requests.get('http://localhost:8000/healthz', timeout=3)
        canary_r = requests.get('http://localhost:8001/healthz', timeout=3)
        
        print(f"\n🔍 Soak Test Health Check:")
        print(f"   Main API: {'✅ OK' if main_r.status_code == 200 else '❌ DOWN'}")
        print(f"   Canary API: {'✅ OK' if canary_r.status_code == 200 else '❌ DOWN'}")
        
        return main_r.status_code == 200 and canary_r.status_code == 200
        
    except Exception as e:
        print(f"\n🔍 Soak Test Health Check:")
        print(f"   ❌ Connection failed: {e}")
        return False

def main():
    print("🚀 GitHub Actions Workflow Fix Verification")
    print("=" * 50)
    
    workflow_fixed = check_workflow_fixes()
    soak_healthy = check_soak_test_health()
    
    print(f"\n📊 Summary:")
    print(f"   Workflow Fixes: {'✅ APPLIED' if workflow_fixed else '❌ INCOMPLETE'}")
    print(f"   Soak Test: {'✅ HEALTHY' if soak_healthy else '❌ UNHEALTHY'}")
    
    if workflow_fixed and soak_healthy:
        print(f"\n🎉 SUCCESS: Workflows triggered and soak test continues!")
        print(f"   - GitHub Actions should now pass with @v4")
        print(f"   - No disruption to 48-hour soak test")
        return True
    else:
        print(f"\n⚠️ Check GitHub Actions status for remaining issues")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1) 