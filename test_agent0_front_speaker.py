#!/usr/bin/env python3
"""
Test Agent-0 Front-Speaker Implementation
Validates that Agent-0 speaks first with immediate responses and background refinement
"""

import asyncio
import time
import sys
import os

# Add router to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_agent0_front_speaker():
    """Test the new Agent-0 front-speaker routing"""
    print("🚀 Testing Agent-0 Front-Speaker Implementation")
    print("=" * 60)
    
    try:
        from router_cascade import RouterCascade
        
        # Initialize router
        router = RouterCascade()
        router.current_session_id = "test_session_123"
        
        # Test cases for different confidence scenarios
        test_cases = [
            {
                "name": "Simple Greeting (High Confidence Expected)",
                "prompt": "Hello there!",
                "expected_confidence": ">= 0.60",
                "expected_specialists": 0
            },
            {
                "name": "Math Question (Should Trigger Specialist)",
                "prompt": "What is 25 * 17?",
                "expected_confidence": "< 0.60",
                "expected_specialists": 1
            },
            {
                "name": "Code Question (Should Trigger Specialist)",
                "prompt": "Write a Python function to reverse a string",
                "expected_confidence": "< 0.60", 
                "expected_specialists": 1
            },
            {
                "name": "General Knowledge (May Trigger Specialist)",
                "prompt": "Explain quantum computing in simple terms",
                "expected_confidence": "varies",
                "expected_specialists": "0-1"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}: {test_case['name']}")
            print(f"📤 Prompt: '{test_case['prompt']}'")
            
            # Time the response
            start_time = time.time()
            
            try:
                result = await router.route_query(test_case['prompt'])
                
                latency = (time.time() - start_time) * 1000
                
                # Extract key metrics
                response_text = result.get("text", "")
                confidence = result.get("confidence", 0.0)
                agent0_first = result.get("agent0_first", False)
                refinement_available = result.get("refinement_available", False)
                specialists_used = result.get("specialists_used", [])
                refinement_task = result.get("refinement_task")
                
                print(f"✅ Agent-0 Response: {response_text[:100]}...")
                print(f"⏱️ Latency: {latency:.1f}ms")
                print(f"🎯 Confidence: {confidence:.3f}")
                print(f"🚀 Agent-0 First: {agent0_first}")
                print(f"⚙️ Refinement Available: {refinement_available}")
                print(f"👥 Specialists Used: {len(specialists_used)}")
                
                # If refinement is available, wait for it to complete
                if refinement_available and refinement_task:
                    print("⚙️ Waiting for background refinement...")
                    try:
                        refined_result = await asyncio.wait_for(refinement_task, timeout=10.0)
                        
                        refined_text = refined_result.get("text", "")
                        refinement_type = refined_result.get("refinement_type", "none")
                        final_specialists = refined_result.get("specialists_used", [])
                        
                        if refined_text != response_text:
                            print(f"✨ Refinement Complete: {refinement_type}")
                            print(f"📝 Refined Text: {refined_text[:100]}...")
                            print(f"👥 Final Specialists: {final_specialists}")
                        else:
                            print("📋 Refinement: No improvement needed")
                            
                    except asyncio.TimeoutError:
                        print("⏱️ Refinement timed out")
                    except Exception as e:
                        print(f"❌ Refinement error: {e}")
                
                # Validate expectations
                validation = {
                    "agent0_first": agent0_first,
                    "fast_response": latency < 1000,  # < 1s for Agent-0 draft
                    "has_response": len(response_text) > 0,
                    "confidence_reasonable": 0.0 <= confidence <= 1.0
                }
                
                results.append({
                    "test_name": test_case['name'],
                    "prompt": test_case['prompt'],
                    "latency_ms": latency,
                    "confidence": confidence,
                    "agent0_first": agent0_first,
                    "refinement_available": refinement_available,
                    "specialists_count": len(specialists_used),
                    "validation": validation,
                    "success": all(validation.values())
                })
                
                print(f"✅ Test Result: {'PASS' if results[-1]['success'] else 'FAIL'}")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                results.append({
                    "test_name": test_case['name'],
                    "error": str(e),
                    "success": False
                })
        
        # Summary
        print(f"\n📊 AGENT-0 FRONT-SPEAKER TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results if r.get('success', False))
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            print("✅ Agent-0 front-speaker implementation working correctly")
        else:
            print("⚠️ Some tests failed - check implementation")
        
        # Performance summary
        successful_results = [r for r in results if r.get('success', False)]
        if successful_results:
            avg_latency = sum(r['latency_ms'] for r in successful_results) / len(successful_results)
            avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
            
            print(f"\n📈 Performance Metrics:")
            print(f"   Average Agent-0 latency: {avg_latency:.1f}ms")
            print(f"   Average confidence: {avg_confidence:.3f}")
            print(f"   Fast responses (<1s): {sum(1 for r in successful_results if r['latency_ms'] < 1000)}/{len(successful_results)}")
        
        return passed == total
        
    except ImportError as e:
        print(f"❌ Failed to import router: {e}")
        return False
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

async def test_streaming_simulation():
    """Simulate streaming behavior"""
    print(f"\n🌊 STREAMING SIMULATION TEST")
    print("=" * 60)
    
    # This simulates what the streaming endpoint would do
    test_prompt = "Explain the benefits of renewable energy"
    
    print(f"📤 Streaming prompt: '{test_prompt}'")
    
    try:
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        router.current_session_id = "stream_test_456"
        
        # Simulate streaming flow
        print("1️⃣ Starting Agent-0 draft...")
        start_time = time.time()
        
        result = await router.route_query(test_prompt)
        
        draft_latency = (time.time() - start_time) * 1000
        
        agent0_text = result.get("text", "")
        confidence = result.get("confidence", 0.0)
        refinement_available = result.get("refinement_available", False)
        
        print(f"✅ Agent-0 draft ready: {draft_latency:.1f}ms")
        print(f"📝 Draft: {agent0_text}")
        print(f"🎯 Confidence: {confidence:.3f}")
        
        # Simulate word-by-word streaming
        words = agent0_text.split()
        print(f"\n2️⃣ Simulating word-by-word streaming ({len(words)} words):")
        
        streamed = ""
        for i, word in enumerate(words[:10]):  # First 10 words for demo
            if i > 0:
                streamed += " "
            streamed += word
            progress = (i + 1) / len(words)
            print(f"   Stream {i+1:2d}: {streamed}... ({progress*100:.0f}%)")
            await asyncio.sleep(0.05)  # Simulate streaming delay
        
        print(f"✅ Streaming simulation complete")
        
        if refinement_available:
            print(f"\n3️⃣ Background refinement would run here...")
        
        return True
        
    except Exception as e:
        print(f"❌ Streaming simulation failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Agent-0 Front-Speaker Test Suite")
    print("Testing the new instant response + background refinement approach")
    
    async def run_all_tests():
        # Test basic functionality
        basic_success = await test_agent0_front_speaker()
        
        # Test streaming simulation
        stream_success = await test_streaming_simulation()
        
        overall_success = basic_success and stream_success
        
        print(f"\n🏆 OVERALL TEST RESULT: {'SUCCESS' if overall_success else 'FAILURE'}")
        
        if overall_success:
            print("🎉 Agent-0 front-speaker implementation is ready!")
            print("✅ Instant responses with background refinement working")
        else:
            print("⚠️ Issues detected - please review implementation")
        
        return overall_success
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1) 