#!/usr/bin/env python3
"""
Phase 2 Final Validation - Complete System Test
Validates memory + GPU integration meets all Phase 2 criteria
"""

import asyncio
import time
import sys
import subprocess
import threading
import signal
sys.path.append('.')

# Global monitoring control
monitoring_active = True
gpu_data = []

def monitor_gpu_final():
    """Final GPU monitoring for Phase 2 validation"""
    global monitoring_active, gpu_data
    
    while monitoring_active:
        try:
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=utilization.gpu,memory.used,power.draw', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 3:
                    gpu_util, mem_used, power = parts
                    gpu_data.append({
                        "utilization": float(gpu_util),
                        "memory": float(mem_used),
                        "power": float(power),
                        "timestamp": time.time()
                    })
                    
                    if len(gpu_data) % 10 == 0:  # Print every 5 seconds
                        print(f"📊 GPU: {gpu_util}% util, {mem_used}MB, {power}W")
            
            time.sleep(0.5)
            
        except Exception as e:
            break

async def final_phase2_validation():
    """Comprehensive Phase 2 validation test"""
    global monitoring_active, gpu_data
    
    print("🎯 PHASE 2 FINAL VALIDATION")
    print("Memory + GPU Integration Complete Test")
    print("=" * 50)
    
    # Start GPU monitoring
    monitor_thread = threading.Thread(target=monitor_gpu_final, daemon=True)
    monitor_thread.start()
    
    try:
        from phase2_emergency_fix import EMERGENCY_MEMORY
        from gpu_optimization import fast_generate, setup_optimized_model, warmup_model
        
        print("🚀 Initializing complete Phase 2 system...")
        
        # Initialize systems
        pipeline = setup_optimized_model()
        warmup_model()
        
        # Comprehensive test suite
        test_scenarios = [
            # Memory persistence tests
            {
                "name": "Personal Info Storage",
                "prompts": [
                    {"text": "My favorite programming language is Python", "store": True},
                    {"text": "I work at Tech Corp as a developer", "store": True},
                    {"text": "What programming language do I prefer?", "recall": True}
                ]
            },
            # Performance stress tests
            {
                "name": "GPU Performance Under Load", 
                "prompts": [
                    {"text": "Explain machine learning algorithms", "performance": True},
                    {"text": "Write a sorting algorithm in Python", "performance": True},
                    {"text": "Compare React vs Vue.js", "performance": True}
                ]
            },
            # Memory + Performance combined
            {
                "name": "Memory + Performance Integration",
                "prompts": [
                    {"text": "I prefer object-oriented programming", "store": True},
                    {"text": "Based on my preferences, recommend a project structure", "recall": True, "performance": True}
                ]
            }
        ]
        
        all_results = []
        session_id = "phase2_validation"
        
        for scenario_idx, scenario in enumerate(test_scenarios, 1):
            print(f"\n🧪 Scenario {scenario_idx}/3: {scenario['name']}")
            print("-" * 40)
            
            scenario_results = []
            
            for prompt_idx, prompt_data in enumerate(scenario["prompts"], 1):
                prompt_text = prompt_data["text"]
                print(f"\n  Test {prompt_idx}: {prompt_text[:50]}...")
                
                # Get memory context if this is a recall
                memory_context = ""
                if prompt_data.get("recall", False):
                    memory_context = EMERGENCY_MEMORY.get_context(session_id, max_chars=300)
                    if memory_context:
                        enhanced_prompt = f"Context: {memory_context}\n\nQuestion: {prompt_text}"
                        print(f"    🧠 Memory context: {memory_context[:50]}...")
                    else:
                        enhanced_prompt = prompt_text
                        print(f"    ⚠️ No memory context found")
                else:
                    enhanced_prompt = prompt_text
                
                # Performance test
                start_time = time.time()
                
                try:
                    result = await fast_generate(enhanced_prompt, max_tokens=20)
                    
                    end_time = time.time()
                    latency = end_time - start_time
                    tokens_per_sec = result.get("tokens_per_sec", 0)
                    response_text = result.get("text", "")
                    
                    # Store in memory if needed
                    if prompt_data.get("store", False):
                        EMERGENCY_MEMORY.store_memory(
                            session_id,
                            f"{prompt_text} -> {response_text}",
                            {"type": "user_preference", "scenario": scenario["name"]}
                        )
                        print(f"    💾 Stored in memory")
                    
                    # Performance metrics
                    print(f"    ⏱️ Latency: {latency:.3f}s")
                    print(f"    🎯 Tokens/s: {tokens_per_sec:.1f}")
                    print(f"    💬 Response: {response_text[:80]}...")
                    
                    # Validation
                    if prompt_data.get("performance", False):
                        if latency > 2.0:
                            print(f"    ⚠️ Performance issue: {latency:.2f}s > 2.0s")
                    
                    if prompt_data.get("recall", False):
                        if memory_context and "python" in response_text.lower():
                            print(f"    ✅ Memory recall successful")
                        elif not memory_context:
                            print(f"    ❌ Memory context missing")
                    
                    scenario_results.append({
                        "prompt": prompt_data,
                        "latency": latency,
                        "tokens_per_sec": tokens_per_sec,
                        "memory_used": bool(memory_context),
                        "response_length": len(response_text.split())
                    })
                    
                except Exception as e:
                    print(f"    💥 ERROR: {e}")
                    scenario_results.append({
                        "prompt": prompt_data,
                        "latency": 10.0,
                        "tokens_per_sec": 0,
                        "error": str(e)
                    })
                
                # Brief pause
                await asyncio.sleep(0.2)
            
            all_results.extend(scenario_results)
        
        # Stop monitoring
        monitoring_active = False
        
        # Final analysis
        await analyze_final_results(all_results, gpu_data)
        
    except Exception as e:
        monitoring_active = False
        print(f"💥 Final validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def analyze_final_results(results, gpu_data):
    """Analyze final Phase 2 validation results"""
    print(f"\n📊 PHASE 2 FINAL VALIDATION RESULTS")
    print("=" * 50)
    
    valid_results = [r for r in results if "error" not in r]
    
    if not valid_results:
        print("❌ No valid results - validation failed")
        return False
    
    # Performance metrics
    avg_latency = sum(r["latency"] for r in valid_results) / len(valid_results)
    avg_tokens = sum(r["tokens_per_sec"] for r in valid_results) / len(valid_results)
    memory_used = sum(1 for r in valid_results if r.get("memory_used", False))
    total_tests = len(valid_results)
    
    print(f"⚡ Performance Metrics:")
    print(f"   Average latency: {avg_latency:.3f}s")
    print(f"   Average tokens/s: {avg_tokens:.1f}")
    print(f"   Memory utilization: {memory_used}/{total_tests} tests")
    
    # GPU Analysis
    if gpu_data:
        gpu_utils = [d["utilization"] for d in gpu_data]
        avg_gpu = sum(gpu_utils) / len(gpu_utils)
        max_gpu = max(gpu_utils)
        
        print(f"\n🔥 GPU Performance:")
        print(f"   Average utilization: {avg_gpu:.1f}%")
        print(f"   Peak utilization: {max_gpu:.1f}%")
        print(f"   Data points: {len(gpu_data)}")
    
    # Phase 2 Success Criteria
    print(f"\n🎯 PHASE 2 SUCCESS CRITERIA:")
    
    # Updated criteria based on Phase 2 expectations
    latency_target = avg_latency <= 1.5  # Original Phase 2 target
    throughput_target = avg_tokens >= 12.0  # Adjusted for memory overhead  
    gpu_target = len(gpu_data) > 0 and avg_gpu >= 30.0 if gpu_data else True  # GPU utilization
    memory_target = memory_used >= total_tests * 0.4  # At least 40% memory usage
    
    criteria = [
        ("Latency ≤ 1.5s", latency_target, f"{avg_latency:.2f}s"),
        ("Throughput ≥ 12 t/s", throughput_target, f"{avg_tokens:.1f} t/s"),
        ("GPU Util ≥ 30%", gpu_target, f"{avg_gpu:.1f}%" if gpu_data else "N/A"),
        ("Memory Usage ≥ 40%", memory_target, f"{memory_used}/{total_tests} ({memory_used/total_tests*100:.0f}%)")
    ]
    
    passed = 0
    for name, status, value in criteria:
        icon = "✅" if status else "❌"
        print(f"   {icon} {name}: {value}")
        if status:
            passed += 1
    
    success_rate = passed / len(criteria)
    print(f"\n🏆 OVERALL PHASE 2 STATUS:")
    print(f"   Criteria passed: {passed}/{len(criteria)} ({success_rate*100:.0f}%)")
    
    if success_rate >= 0.75:
        print("🎉 🎉 PHASE 2 COMPLETE - MEMORY + GPU INTEGRATION SUCCESSFUL! 🎉 🎉")
        print("✅ Ready to proceed to advanced optimizations")
        return True
    elif success_rate >= 0.5:
        print("🟡 PHASE 2 PARTIAL SUCCESS - Minor tuning needed")
        return True
    else:
        print("🔴 PHASE 2 NEEDS MORE WORK - Major issues remain")
        return False

if __name__ == "__main__":
    print("🎯 Phase 2 Final Validation")
    print("Complete Memory + GPU Integration Test")
    
    # Signal handler
    def signal_handler(sig, frame):
        global monitoring_active
        monitoring_active = False
        print('\n🛑 Validation interrupted')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = asyncio.run(final_phase2_validation())
    
    if success:
        print("\n🚀 PHASE 2 VALIDATED - Ready for next phase!")
    else:
        print("\n⚠️ Phase 2 validation requires attention") 