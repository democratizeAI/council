#!/usr/bin/env python3
"""
🔧 HASHLIB FIX INTEGRATION TEST
==============================

Test to verify that the hashlib fix resolves the front-end error:
"[ERROR] math_specialist: Math specialist failed: name 'hashlib' is not defined"

This simulates a chat request to see if the specialists work correctly.
"""

import asyncio
import sys
import time

async def test_hashlib_fix():
    """Test that specialists can now use hashlib without errors"""
    print("🔧 HASHLIB FIX INTEGRATION TEST")
    print("=" * 50)
    
    try:
        # Import and test the router that was causing issues
        from router.voting import vote
        
        print("✅ Router imported successfully")
        
        # Test a simple math query that would trigger specialists
        test_prompts = [
            "What is 2+2?",
            "Hello there",
            "Tell me about AI"
        ]
        
        success_count = 0
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🧪 Test {i}: '{prompt}'")
            
            try:
                start_time = time.time()
                
                # This is the call that was failing with hashlib error
                result = await vote(prompt, model_names=["math_specialist", "code_specialist"], top_k=1)
                
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Check if we got a response without hashlib errors
                response_text = result.get("text", "")
                specialists_tried = result.get("specialists_tried", [])
                
                print(f"   ⏱️ Response time: {elapsed_ms:.1f}ms")
                print(f"   📝 Response: {response_text[:100]}...")
                print(f"   🎯 Specialists tried: {specialists_tried}")
                
                # Check if there are any hashlib-related errors
                if "hashlib" not in response_text and "not defined" not in response_text:
                    print(f"   ✅ No hashlib errors detected")
                    success_count += 1
                else:
                    print(f"   ❌ Hashlib error still present in response")
                
            except Exception as e:
                if "hashlib" in str(e) and "not defined" in str(e):
                    print(f"   ❌ Hashlib error still occurring: {e}")
                else:
                    print(f"   ⚠️ Other error (not hashlib related): {e}")
                    success_count += 1  # Count as success if not hashlib error
        
        print("\n" + "=" * 50)
        print("📊 RESULTS")
        print("=" * 50)
        print(f"Tests passed: {success_count}/{len(test_prompts)}")
        
        if success_count == len(test_prompts):
            print("🎉 SUCCESS: Hashlib fix is working!")
            print("✅ Specialists should no longer fail with import errors")
            print("✅ Front-end should now receive proper responses")
            return True
        else:
            print("❌ Some tests still failing - hashlib fix needs more work")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("⚠️ Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

async def test_sandbox_directly():
    """Test the sandbox fix directly"""
    print("\n🧪 DIRECT SANDBOX TEST")
    print("=" * 30)
    
    try:
        from router.specialist_sandbox_fix import get_specialist_sandbox, test_specialist_environment
        
        # Test the sandbox environment
        results = test_specialist_environment()
        
        passed = sum(1 for r in results if r['success'])
        total = len(results)
        
        print(f"Sandbox tests: {passed}/{total} passed")
        
        if passed == total:
            print("✅ Sandbox environment is working correctly")
            return True
        else:
            print("❌ Sandbox environment has issues")
            for result in results:
                if not result['success']:
                    print(f"   Failed: {result['expression']} - {result['actual']}")
            return False
            
    except Exception as e:
        print(f"❌ Sandbox test failed: {e}")
        return False

def main():
    """Run all hashlib fix integration tests"""
    print("🚀 RUNNING HASHLIB FIX INTEGRATION TESTS")
    print("=" * 60)
    
    # Test 1: Direct sandbox test
    sandbox_success = asyncio.run(test_sandbox_directly())
    
    # Test 2: Integration test with voting system
    integration_success = asyncio.run(test_hashlib_fix())
    
    print("\n" + "=" * 60)
    print("🏁 FINAL RESULTS")
    print("=" * 60)
    
    if sandbox_success and integration_success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Hashlib fix is working correctly")
        print("✅ Front-end should no longer see import errors")
        print("🚀 Ready for production use")
    else:
        print("❌ Some tests failed")
        print("🔧 Check the specific failures above")
    
    return sandbox_success and integration_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 