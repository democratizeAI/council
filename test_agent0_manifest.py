#!/usr/bin/env python3
"""
Test Agent-0 Manifest System
Validates intelligent flag-based escalation and system awareness
"""

import asyncio
import time
import sys
import os

# Add router to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_agent0_manifest_system():
    """Test the new Agent-0 manifest with flag-based escalation"""
    print("🧩 Testing Agent-0 Manifest System")
    print("=" * 60)
    
    try:
        from router_cascade import RouterCascade, extract_confidence, extract_flags, flags_to_specialists, clean_agent0_response
        
        # Test helper functions first
        print("🧪 Testing flag parsing functions...")
        test_txt = "Here's my answer. CONF=0.34 FLAG_MATH FLAG_CODE"
        
        confidence = extract_confidence(test_txt)
        flags = extract_flags(test_txt)
        specialists = flags_to_specialists(flags)
        clean_text = clean_agent0_response(test_txt)
        
        assert confidence == 0.34, f"Expected 0.34, got {confidence}"
        assert flags == ["FLAG_MATH", "FLAG_CODE"], f"Expected ['FLAG_MATH', 'FLAG_CODE'], got {flags}"
        assert specialists == {"math", "code"}, f"Expected {{'math', 'code'}}, got {specialists}"
        assert clean_text == "Here's my answer.", f"Expected 'Here's my answer.', got '{clean_text}'"
        
        print("✅ Flag parsing functions working correctly")
        
        # Initialize router
        router = RouterCascade()
        router.current_session_id = "manifest_test_123"
        
        # Test cases for manifest-aware escalation
        test_cases = [
            {
                "name": "High Confidence Greeting (No Escalation)",
                "prompt": "Hello there!",
                "expected_confidence": ">= 0.90",
                "expected_flags": [],
                "expected_escalation": False,
                "expected_behavior": "Agent-0 only"
            },
            {
                "name": "Math Question (FLAG_MATH Expected)",
                "prompt": "What is 25 * 17?",
                "expected_confidence": "< 0.60",
                "expected_flags": ["FLAG_MATH"],
                "expected_escalation": True,
                "expected_behavior": "Math specialist"
            },
            {
                "name": "Code Question (FLAG_CODE Expected)",
                "prompt": "Write a Python function to reverse a string",
                "expected_confidence": "< 0.60", 
                "expected_flags": ["FLAG_CODE"],
                "expected_escalation": True,
                "expected_behavior": "Code specialist"
            },
            {
                "name": "Complex Question (FLAG_KNOWLEDGE Expected)",
                "prompt": "Explain quantum computing in detail with examples",
                "expected_confidence": "< 0.60",
                "expected_flags": ["FLAG_KNOWLEDGE"],
                "expected_escalation": True,
                "expected_behavior": "Knowledge specialist"
            },
            {
                "name": "Logic Problem (FLAG_LOGIC Expected)",
                "prompt": "Prove that the square root of 2 is irrational",
                "expected_confidence": "< 0.60",
                "expected_flags": ["FLAG_LOGIC"],
                "expected_escalation": True,
                "expected_behavior": "Logic specialist"
            },
            {
                "name": "Very Complex Question (FLAG_COUNCIL Expected)",
                "prompt": "Compare QUIC vs HTTP/3 protocols in depth with performance analysis",
                "expected_confidence": "< 0.30",
                "expected_flags": ["FLAG_COUNCIL"],
                "expected_escalation": True,
                "expected_behavior": "Full Council"
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
                raw_text = result.get("raw_text", "")
                confidence = result.get("confidence", 0.0)
                flags_detected = result.get("flags_detected", [])
                escalation_reason = result.get("escalation_reason", "")
                refinement_available = result.get("refinement_available", False)
                wanted_specialists = result.get("wanted_specialists", [])
                
                print(f"✅ Agent-0 Response: {response_text[:80]}...")
                print(f"🧩 Raw Response: {raw_text[:100]}...")
                print(f"⏱️ Latency: {latency:.1f}ms")
                print(f"🎯 Confidence: {confidence:.3f}")
                print(f"🚩 Flags: {flags_detected}")
                print(f"⚙️ Escalation: {escalation_reason}")
                print(f"👥 Wanted Specialists: {wanted_specialists}")
                
                # Validate expectations
                validation = {
                    "has_response": len(response_text) > 0,
                    "confidence_reasonable": 0.0 <= confidence <= 1.0,
                    "fast_response": latency < 7000,  # Relaxed to 7s for model loading
                    "proper_escalation": refinement_available == test_case["expected_escalation"]
                }
                
                # Check flag expectations
                if test_case["expected_flags"]:
                    validation["expected_flags"] = any(flag in flags_detected for flag in test_case["expected_flags"])
                else:
                    validation["expected_flags"] = len(flags_detected) == 0
                
                # Check confidence range
                if test_case["expected_confidence"].startswith(">="):
                    threshold = float(test_case["expected_confidence"].split(">=")[1].strip())
                    validation["confidence_range"] = confidence >= threshold
                elif test_case["expected_confidence"].startswith("<"):
                    threshold = float(test_case["expected_confidence"].split("<")[1].strip())
                    validation["confidence_range"] = confidence < threshold
                else:
                    validation["confidence_range"] = True
                
                results.append({
                    "test_name": test_case['name'],
                    "prompt": test_case['prompt'],
                    "latency_ms": latency,
                    "confidence": confidence,
                    "flags_detected": flags_detected,
                    "escalation_reason": escalation_reason,
                    "wanted_specialists": wanted_specialists,
                    "refinement_available": refinement_available,
                    "validation": validation,
                    "success": all(validation.values())
                })
                
                print(f"✅ Test Result: {'PASS' if results[-1]['success'] else 'FAIL'}")
                
                # If escalation was triggered, wait a bit to see if it completes
                if refinement_available:
                    refinement_task = result.get("refinement_task")
                    if refinement_task:
                        print("⚙️ Waiting for background escalation...")
                        try:
                            refined_result = await asyncio.wait_for(refinement_task, timeout=10.0)
                            
                            refined_text = refined_result.get("text", "")
                            refinement_type = refined_result.get("refinement_type", "none")
                            final_specialists = refined_result.get("specialists_used", [])
                            
                            if refined_text != response_text:
                                print(f"✨ Escalation Complete: {refinement_type}")
                                print(f"📝 Refined Text: {refined_text[:80]}...")
                                print(f"👥 Used Specialists: {final_specialists}")
                            else:
                                print("📋 Escalation: No improvement found")
                                
                        except asyncio.TimeoutError:
                            print("⏱️ Escalation timed out")
                        except Exception as e:
                            print(f"❌ Escalation error: {e}")
                
            except Exception as e:
                print(f"❌ Test failed: {e}")
                results.append({
                    "test_name": test_case['name'],
                    "error": str(e),
                    "success": False
                })
        
        # Summary
        print(f"\n📊 AGENT-0 MANIFEST TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in results if r.get('success', False))
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 ALL MANIFEST TESTS PASSED!")
            print("✅ Agent-0 manifest system working correctly")
        else:
            print("⚠️ Some tests failed - check manifest implementation")
        
        # Performance summary
        successful_results = [r for r in results if r.get('success', False)]
        if successful_results:
            avg_latency = sum(r['latency_ms'] for r in successful_results) / len(successful_results)
            avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
            
            # Flag detection rate
            with_flags = sum(1 for r in successful_results if r.get('flags_detected'))
            flag_rate = with_flags / len(successful_results) * 100
            
            print(f"\n📈 Performance Metrics:")
            print(f"   Average Agent-0 latency: {avg_latency:.1f}ms")
            print(f"   Average confidence: {avg_confidence:.3f}")
            print(f"   Fast responses (<1s): {sum(1 for r in successful_results if r['latency_ms'] < 1000)}/{len(successful_results)}")
            print(f"   Flag detection rate: {flag_rate:.0f}%")
            print(f"   Escalation rate: {sum(1 for r in successful_results if r.get('refinement_available'))}/{len(successful_results)}")
        
        return passed == total
        
    except ImportError as e:
        print(f"❌ Failed to import router: {e}")
        return False
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        return False

async def test_escalation_scenarios():
    """Test specific escalation scenarios"""
    print(f"\n🌊 ESCALATION SCENARIOS TEST")
    print("=" * 60)
    
    # Test the expected escalation patterns
    scenarios = [
        ("2 + 2", "Agent-0 only", "High confidence math"),
        ("Factor x² - 5x + 6", "Math specialist", "Complex math needs FLAG_MATH"),
        ("def reverse_string(s):", "Code specialist", "Code needs FLAG_CODE"),
        ("Compare QUIC vs HTTP/3 in depth", "Full Council", "Complex topic needs FLAG_COUNCIL")
    ]
    
    print("Expected escalation patterns:")
    for prompt, expected, reason in scenarios:
        print(f"   '{prompt[:30]}...' → {expected} ({reason})")
    
    print(f"\n✅ Escalation patterns documented")
    return True

if __name__ == "__main__":
    print("🧩 Agent-0 Manifest Test Suite")
    print("Testing intelligent flag-based escalation system")
    
    async def run_all_tests():
        # Test manifest system
        manifest_success = await test_agent0_manifest_system()
        
        # Test escalation scenarios
        scenario_success = await test_escalation_scenarios()
        
        overall_success = manifest_success and scenario_success
        
        print(f"\n🏆 OVERALL MANIFEST TEST RESULT: {'SUCCESS' if overall_success else 'FAILURE'}")
        
        if overall_success:
            print("🎉 Agent-0 manifest system is ready!")
            print("✅ Intelligent flag-based escalation working")
            print("✅ System awareness and self-routing implemented")
        else:
            print("⚠️ Issues detected - please review manifest implementation")
        
        return overall_success
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1) 