#!/usr/bin/env python3
"""
EMERGENCY SMOKE TEST - Simple validation of core functionality
"""

import os
import asyncio
import time
import sys

# Set environment for testing
os.environ['SWARM_COUNCIL_ENABLED'] = 'false'  # Disable council for speed
os.environ['SWARM_BUDGET'] = '10.00'

async def emergency_test():
    """Ultra-simple smoke test focusing on core issues"""
    print("🚨 EMERGENCY SMOKE TEST")
    print("=" * 30)
    
    try:
        sys.path.append('.')
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Very simple test cases
        simple_tests = [
            {
                "prompt": "hi",
                "target_latency": 5.0,  # More realistic for now
                "description": "Simple greeting"
            },
            {
                "prompt": "2+2",
                "target_latency": 5.0,
                "description": "Simple math"
            }
        ]
        
        success_count = 0
        
        for i, test in enumerate(simple_tests, 1):
            print(f"\n🧪 Test {i}: {test['description']}")
            print(f"   Query: '{test['prompt']}'")
            
            start_time = time.time()
            
            try:
                result = await router.route_query(test['prompt'])
                end_time = time.time()
                latency = end_time - start_time
                
                if result:
                    text = result.get('text', 'No response')
                    confidence = result.get('confidence', 0.0)
                    model = result.get('model', 'unknown')
                    
                    # Check for success criteria
                    has_response = len(text.strip()) > 0 and not text.startswith("SYSTEM:")
                    reasonable_latency = latency < test['target_latency']
                    reasonable_confidence = confidence > 0.2
                    
                    if has_response and reasonable_latency and reasonable_confidence:
                        success_count += 1
                        print(f"   ✅ PASSED")
                    else:
                        print(f"   ❌ FAILED")
                    
                    print(f"   ⏱️ Latency: {latency:.2f}s")
                    print(f"   📊 Confidence: {confidence:.2f}")
                    print(f"   🤖 Model: {model}")
                    print(f"   💬 Response: {text[:100]}...")
                    
                    # Check for specific issues
                    if text.startswith("SYSTEM:"):
                        print(f"   🚨 ISSUE: System prompt returned instead of response")
                    if latency > 10:
                        print(f"   🚨 ISSUE: Excessive latency")
                    if confidence < 0.2:
                        print(f"   🚨 ISSUE: Very low confidence")
                        
                else:
                    print(f"   ❌ FAILED - No result returned")
                    
            except Exception as e:
                print(f"   💥 ERROR: {e}")
        
        print(f"\n{'='*30}")
        print(f"Results: {success_count}/{len(simple_tests)} tests passed")
        
        if success_count == len(simple_tests):
            print("✅ Basic functionality working!")
        else:
            print("❌ Core issues detected:")
            print("   • Check GPU availability")
            print("   • Check model loading")
            print("   • Check token limits")
            print("   • Check confidence calculations")
        
        return success_count == len(simple_tests)
        
    except Exception as e:
        print(f"💥 Emergency test crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main emergency test runner"""
    print("🚨 EMERGENCY DIAGNOSTIC MODE")
    print("Testing core functionality only...")
    
    success = await emergency_test()
    
    if success:
        print(f"\n✅ CORE FUNCTIONALITY OK")
        print("Next steps:")
        print("1. Run full test suite")
        print("2. Check latency optimization")
        print("3. Validate memory system")
    else:
        print(f"\n❌ CORE ISSUES DETECTED")
        print("Priority fixes needed:")
        print("1. Fix model loading/generation")
        print("2. Fix response extraction")
        print("3. Fix confidence calculation")
        print("4. Check GPU utilization")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1) 