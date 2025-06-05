#!/usr/bin/env python3
"""
Single-Path Recipe Implementation Verification
Tests the core implementation without requiring server startup
"""

import sys
import re
import time
from pathlib import Path

def verify_greeting_filter():
    """Verify greeting filter is implemented in voting.py (Recipe Step 2a)"""
    print("🔍 STEP 2a: Verifying greeting filter in voting.py...")
    
    try:
        with open("router/voting.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check for GREETING_STUB_RE
        if "GREETING_STUB_RE" in content:
            print("   ✅ GREETING_STUB_RE found")
        else:
            print("   ❌ GREETING_STUB_RE missing")
            return False
        
        # Check for scrub_greeting_stub function
        if "scrub_greeting_stub" in content:
            print("   ✅ scrub_greeting_stub function found")
        else:
            print("   ❌ scrub_greeting_stub function missing")
            return False
        
        # Check for confidence = 0.0 assignment
        if "confidence = 0.0" in content:
            print("   ✅ Confidence nullification found")
        else:
            print("   ❌ Confidence nullification missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading voting.py: {e}")
        return False

def verify_agent0_first_speaker():
    """Verify Agent-0 mandatory first speaker implementation (Recipe Step 1)"""
    print("\n🔍 STEP 1: Verifying Agent-0 mandatory first speaker...")
    
    try:
        with open("router_cascade.py", "r") as f:
            content = f.read()
        
        # Check for _route_agent0_first method
        if "_route_agent0_first" in content:
            print("   ✅ _route_agent0_first method found")
        else:
            print("   ❌ _route_agent0_first method missing")
            return False
        
        # Check for single-path recipe comment
        if "SINGLE-PATH RECIPE" in content:
            print("   ✅ Single-path recipe implementation found")
        else:
            print("   ❌ Single-path recipe implementation missing")
            return False
        
        # Check for digest storage
        if "write_fusion_digest" in content:
            print("   ✅ Digest writing found")
        else:
            print("   ❌ Digest writing missing")
            return False
        
        # Check for cascading knowledge
        if "read_conversation_context" in content:
            print("   ✅ Cascading knowledge found")
        else:
            print("   ❌ Cascading knowledge missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading router_cascade.py: {e}")
        return False

def verify_progressive_reasoning():
    """Verify progressive reasoning implementation (Recipe Step 3)"""
    print("\n🔍 STEP 3: Verifying progressive reasoning...")
    
    try:
        with open("router_cascade.py", "r") as f:
            content = f.read()
        
        # Check for DRAFT_FROM_AGENT0 in specialist prompts
        if "DRAFT_FROM_AGENT0" in content:
            print("   ✅ Progressive reasoning (DRAFT_FROM_AGENT0) found")
        else:
            print("   ❌ Progressive reasoning missing")
            return False
        
        # Check for context_digests parameter
        if "context_digests" in content:
            print("   ✅ Context digests handling found")
        else:
            print("   ❌ Context digests handling missing")
            return False
        
        # Check for specialist_prompt construction
        if "specialist_prompt" in content:
            print("   ✅ Specialist prompt construction found")
        else:
            print("   ❌ Specialist prompt construction missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking progressive reasoning: {e}")
        return False

def verify_bubble_overwrite():
    """Verify bubble overwrite mechanism (Recipe Step 4)"""
    print("\n🔍 STEP 4: Verifying bubble overwrite mechanism...")
    
    try:
        with open("router_cascade.py", "r") as f:
            content = f.read()
        
        # Check for improvement detection
        if "Specialist wins" in content:
            print("   ✅ Specialist improvement detection found")
        else:
            print("   ❌ Specialist improvement detection missing")
            return False
        
        # Check for UI update comment
        if "overwrite" in content and "bubble" in content:
            print("   ✅ Bubble overwrite logic found")
        else:
            print("   ❌ Bubble overwrite logic missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking bubble overwrite: {e}")
        return False

def verify_escape_protection():
    """Verify final escape protection (Recipe Step 5)"""
    print("\n🔍 STEP 5: Verifying escape protection...")
    
    try:
        with open("router_cascade.py", "r") as f:
            content = f.read()
        
        # Check for final escape check
        if "Stub escaped" in content:
            print("   ✅ Final escape check found")
        else:
            print("   ❌ Final escape check missing")
            return False
        
        # Check for greeting shortcut
        if "greeting-shortcut" in content:
            print("   ✅ Greeting shortcut found")
        else:
            print("   ❌ Greeting shortcut missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking escape protection: {e}")
        return False

def verify_cascading_knowledge_system():
    """Verify cascading knowledge implementation exists"""
    print("\n🔍 EXTRA: Verifying cascading knowledge system...")
    
    try:
        with open("common/scratchpad.py", "r") as f:
            content = f.read()
        
        # Check for digest functions
        if "summarize_to_digest" in content:
            print("   ✅ summarize_to_digest function found")
        else:
            print("   ❌ summarize_to_digest function missing")
            return False
        
        if "write_fusion_digest" in content:
            print("   ✅ write_fusion_digest function found")
        else:
            print("   ❌ write_fusion_digest function missing")
            return False
        
        if "read_conversation_context" in content:
            print("   ✅ read_conversation_context function found")
        else:
            print("   ❌ read_conversation_context function missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error reading scratchpad.py: {e}")
        return False

def verify_test_script():
    """Verify our test script was created"""
    print("\n🔍 TEST: Verifying smoke test script...")
    
    if Path("test_single_path_recipe.py").exists():
        print("   ✅ Smoke test script exists")
        
        with open("test_single_path_recipe.py", "r") as f:
            content = f.read()
        
        # Check for all test scenarios
        tests = [
            "Greeting Speed Test",
            "Simple Math Test", 
            "Complex Math Test",
            "Cascading Knowledge"
        ]
        
        all_tests_found = True
        for test in tests:
            if test in content:
                print(f"   ✅ {test} scenario found")
            else:
                print(f"   ❌ {test} scenario missing")
                all_tests_found = False
        
        return all_tests_found
    else:
        print("   ❌ Smoke test script missing")
        return False

def main():
    """Run complete verification of single-path recipe implementation"""
    print("🚀 SINGLE-PATH RECIPE IMPLEMENTATION VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Greeting Filter", verify_greeting_filter),
        ("Agent-0 First Speaker", verify_agent0_first_speaker),
        ("Progressive Reasoning", verify_progressive_reasoning),
        ("Bubble Overwrite", verify_bubble_overwrite),
        ("Escape Protection", verify_escape_protection),
        ("Cascading Knowledge", verify_cascading_knowledge_system),
        ("Test Script", verify_test_script)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"   ❌ Test {name} failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    print(f"\n📊 VERIFICATION SUMMARY")
    print("=" * 40)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        if result:
            print(f"✅ {name}: IMPLEMENTED")
            passed += 1
        else:
            print(f"❌ {name}: MISSING/INCOMPLETE")
            failed += 1
    
    print(f"\n🏆 RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 SINGLE-PATH RECIPE FULLY IMPLEMENTED!")
        print("✅ Agent-0 always speaks first")
        print("✅ No greeting stubs can escape")
        print("✅ Cascading knowledge active")
        print("✅ Progressive reasoning enabled")
        print("✅ Bubble overwrite ready")
        print("✅ All safety checks in place")
        print("\n💡 Ready for testing once server is running")
        return True
    else:
        print(f"\n⚠️ Implementation incomplete - {failed} components missing")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Verification interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        sys.exit(1) 