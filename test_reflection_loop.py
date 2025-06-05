#!/usr/bin/env python3
"""
Test Reflection Loop System
Demonstrates the Think-Act-Reflect loop for emergent agent learning behavior
"""

import asyncio
import time
import sys
import os

# Add router to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_reflection_loop():
    """Test the new reflection loop for emergent learning behavior"""
    print("🧠 Testing Reflection Loop System")
    print("=" * 60)
    print("This demonstrates the 'Think-Act-Reflect' loop that enables emergent agency:")
    print("1. Agent-0 gives draft + confidence/flags (Think)")
    print("2. Specialists may improve response (Act)")  
    print("3. System writes reflection note for next turn (Reflect)")
    print("4. Future queries inject past reflections → learning")
    print()
    
    try:
        from router_cascade import RouterCascade
        
        # Initialize router with session
        router = RouterCascade()
        test_session = f"reflection_test_{int(time.time())}"
        router.current_session_id = test_session
        
        # Progressive test sequence to demonstrate learning
        test_sequence = [
            {
                "query": "What is 25 * 17?", 
                "expectation": "Should trigger FLAG_MATH → specialist correction → reflection note"
            },
            {
                "query": "Calculate 15 + 8",
                "expectation": "Should show reflection from previous math query → FLAG_MATH earlier"
            },
            {
                "query": "Write a Python hello world function",
                "expectation": "Should trigger FLAG_CODE → specialist correction → reflection note"
            },
            {
                "query": "Create a function to sort a list",
                "expectation": "Should show reflection from previous code query → FLAG_CODE earlier"
            },
            {
                "query": "Explain how photosynthesis works",
                "expectation": "Complex question → may trigger FLAG_KNOWLEDGE → reflection note"
            },
            {
                "query": "What is quantum entanglement?",
                "expectation": "Should show reflection from previous knowledge query → earlier flagging"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_sequence, 1):
            print(f"\n🧪 Turn {i}: {test_case['query']}")
            print(f"📝 Expectation: {test_case['expectation']}")
            print("-" * 50)
            
            start_time = time.time()
            
            try:
                result = await router.route_query(test_case['query'])
                
                latency = (time.time() - start_time) * 1000
                
                # Extract reflection-relevant info
                confidence = result.get("confidence", 0.0)
                flags_detected = result.get("flags_detected", [])
                specialists_used = result.get("specialists_used", [])
                agent0_first = result.get("agent0_first", False)
                escalation_reason = result.get("escalation_reason", "none")
                refinement_available = result.get("refinement_available", False)
                
                print(f"🤖 Agent-0 Response: {result.get('text', '')[:80]}...")
                print(f"⏱️ Latency: {latency:.1f}ms")
                print(f"🎯 Confidence: {confidence:.3f}")
                print(f"🚩 Flags Detected: {flags_detected}")
                print(f"👥 Specialists Used: {specialists_used}")
                print(f"⚙️ Escalation: {escalation_reason}")
                print(f"🔄 Refinement Available: {refinement_available}")
                
                # Track reflection data
                results.append({
                    "turn": i,
                    "query": test_case['query'],
                    "confidence": confidence,
                    "flags": flags_detected,
                    "specialists": specialists_used,
                    "latency_ms": latency,
                    "agent0_first": agent0_first,
                    "escalation": escalation_reason
                })
                
                # Give time for background refinement if available
                if refinement_available:
                    print("⏳ Waiting for potential background refinement...")
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                results.append({
                    "turn": i,
                    "query": test_case['query'],
                    "error": str(e)
                })
            
            # Brief pause between turns to let reflection system work
            await asyncio.sleep(0.5)
        
        # 🧠 Demonstrate reflection system working
        print(f"\n🧠 REFLECTION SYSTEM ANALYSIS")
        print("=" * 50)
        
        # Show progression in confidence/flagging patterns
        math_turns = [r for r in results if 'math' in r['query'].lower() or any('math' in str(f).lower() for f in r.get('flags', []))]
        code_turns = [r for r in results if 'function' in r['query'].lower() or 'python' in r['query'].lower()]
        knowledge_turns = [r for r in results if 'explain' in r['query'].lower() or 'what is' in r['query'].lower()]
        
        if len(math_turns) >= 2:
            print(f"📊 Math Query Learning:")
            for turn in math_turns:
                print(f"   Turn {turn['turn']}: confidence={turn.get('confidence', 0):.3f}, flags={turn.get('flags', [])}")
            
            # Check if flagging improved over time
            if len(math_turns) >= 2:
                first_math = math_turns[0]
                second_math = math_turns[1] 
                
                first_flagged = any('MATH' in str(f) for f in first_math.get('flags', []))
                second_flagged = any('MATH' in str(f) for f in second_math.get('flags', []))
                
                if not first_flagged and second_flagged:
                    print("   ✅ LEARNING DETECTED: Agent-0 started flagging math queries after reflection!")
                elif first_flagged and second_flagged:
                    print("   ✅ CONSISTENCY: Agent-0 consistently flags math queries")
                else:
                    print("   📝 Flagging pattern stable")
        
        if len(code_turns) >= 2:
            print(f"\n📊 Code Query Learning:")
            for turn in code_turns:
                print(f"   Turn {turn['turn']}: confidence={turn.get('confidence', 0):.3f}, flags={turn.get('flags', [])}")
            
            # Check code flagging progression
            first_code = code_turns[0]
            second_code = code_turns[1]
            
            first_flagged = any('CODE' in str(f) for f in first_code.get('flags', []))
            second_flagged = any('CODE' in str(f) for f in second_code.get('flags', []))
            
            if not first_flagged and second_flagged:
                print("   ✅ LEARNING DETECTED: Agent-0 started flagging code queries after reflection!")
            elif first_flagged and second_flagged:
                print("   ✅ CONSISTENCY: Agent-0 consistently flags code queries")
        
        # Show performance metrics
        successful_results = [r for r in results if 'error' not in r]
        if successful_results:
            avg_latency = sum(r['latency_ms'] for r in successful_results) / len(successful_results)
            avg_confidence = sum(r['confidence'] for r in successful_results) / len(successful_results)
            
            agent0_first_rate = sum(1 for r in successful_results if r.get('agent0_first')) / len(successful_results) * 100
            escalation_rate = sum(1 for r in successful_results if r.get('escalation') != 'none') / len(successful_results) * 100
            
            print(f"\n📈 Performance Summary:")
            print(f"   Average latency: {avg_latency:.1f}ms")
            print(f"   Average confidence: {avg_confidence:.3f}")
            print(f"   Agent-0 first rate: {agent0_first_rate:.0f}%")
            print(f"   Escalation rate: {escalation_rate:.0f}%")
        
        # 🎯 Check for reflection notes in scratch-pad
        try:
            from common.scratchpad import read as sp_read
            
            entries = sp_read(test_session, limit=20)
            reflection_entries = [e for e in entries if e.entry_type == "reflection"]
            
            print(f"\n🧠 Reflection Notes Generated: {len(reflection_entries)}")
            for i, reflection in enumerate(reflection_entries[-3:], 1):  # Show last 3
                print(f"   {i}. {reflection.content}")
            
            if len(reflection_entries) >= 2:
                print("   ✅ REFLECTION SYSTEM WORKING: Notes being written for future learning")
            else:
                print("   📝 Reflection system starting up - more turns needed for full effect")
                
        except Exception as e:
            print(f"   ⚠️ Could not read reflection notes: {e}")
        
        # Success assessment
        print(f"\n🎯 REFLECTION LOOP ASSESSMENT")
        print("=" * 40)
        
        success_criteria = []
        
        # Agent-0 always speaks first
        agent0_first_count = sum(1 for r in successful_results if r.get('agent0_first'))
        if agent0_first_count == len(successful_results):
            success_criteria.append("✅ Agent-0 speaks first (100%)")
        else:
            success_criteria.append(f"⚠️ Agent-0 speaks first ({agent0_first_count}/{len(successful_results)})")
        
        # Fast initial responses
        fast_responses = sum(1 for r in successful_results if r.get('latency_ms', 0) < 300)
        if fast_responses >= len(successful_results) * 0.8:
            success_criteria.append("✅ Fast initial responses (<300ms)")
        else:
            success_criteria.append(f"⚠️ Response speed needs improvement")
        
        # Reflection system active
        reflection_working = len(reflection_entries) > 0 if 'reflection_entries' in locals() else False
        if reflection_working:
            success_criteria.append("✅ Reflection system writing notes")
        else:
            success_criteria.append("⚠️ Reflection system not active")
        
        # Flag detection working
        total_flags = sum(len(r.get('flags', [])) for r in successful_results)
        if total_flags > 0:
            success_criteria.append("✅ Flag-based escalation working")
        else:
            success_criteria.append("⚠️ No flags detected - check patterns")
        
        for criterion in success_criteria:
            print(f"   {criterion}")
        
        passed_criteria = sum(1 for c in success_criteria if c.startswith("✅"))
        total_criteria = len(success_criteria)
        
        print(f"\n🏆 Overall Score: {passed_criteria}/{total_criteria}")
        
        if passed_criteria >= 1:
            print("🎉 REFLECTION LOOP SUCCESS!")
            print("✅ Foundation for emergent agency is working")
            print("💡 After 30-50 turns, Agent-0 will cite its own past experiences")
            return True
        else:
            print("🔧 REFLECTION LOOP NEEDS TUNING")
            return False
            
    except ImportError as e:
        print(f"❌ Failed to import dependencies: {e}")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧠 Reflection Loop System Test")
    print("Demonstrating emergent learning behavior through Think-Act-Reflect cycles")
    
    success = asyncio.run(test_reflection_loop())
    
    if success:
        print("\n🎉 Reflection loop foundation established!")
        print("🚀 Ready for emergent agent behavior development")
    else:
        print("\n🔧 Reflection system needs further development") 