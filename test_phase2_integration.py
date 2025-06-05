#!/usr/bin/env python3
"""
Phase 2 Integration Test - GPU Performance + Memory System
Validates that memory re-integration preserves Phase 1 GPU optimizations
"""

import asyncio
import time
import sys
import subprocess
import threading
import signal
import json
sys.path.append('.')

# Global monitoring control
monitoring_active = True
test_results = {
    "gpu_utilization": [],
    "tokens_per_sec": [],
    "memory_hits": 0,
    "memory_writes": 0,
    "latencies": []
}

def monitor_gpu_phase2():
    """Enhanced GPU monitoring for Phase 2"""
    global monitoring_active, test_results
    
    while monitoring_active:
        try:
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 4:
                    gpu_util, mem_used, power, temp = parts
                    test_results["gpu_utilization"].append(float(gpu_util))
                    print(f"📊 GPU: {gpu_util}% util, {mem_used}MB, {power}W, {temp}°C")
            
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ GPU monitoring error: {e}")
            break

async def test_memory_and_gpu_integration():
    """Test memory system integration while preserving GPU performance"""
    global monitoring_active, test_results
    
    print("🚀 Phase 2 Integration Test: Memory + GPU")
    print("=" * 60)
    
    # Start GPU monitoring
    monitor_thread = threading.Thread(target=monitor_gpu_phase2, daemon=True)
    monitor_thread.start()
    
    try:
        from router_cascade import RouterCascade
        
        print("🧠 Initializing RouterCascade with memory enabled...")
        router = RouterCascade()
        
        # Wait a moment for initialization
        await asyncio.sleep(1.0)
        
        print("🔍 Testing memory persistence and GPU performance...")
        
        # Test sequence designed to validate memory + performance
        test_sequence = [
            # Memory seeding phase
            {"prompt": "My favorite color is blue", "expected_tokens": 5, "memory_seed": True},
            {"prompt": "I work as a software engineer", "expected_tokens": 8, "memory_seed": True}, 
            {"prompt": "My hobby is reading science fiction", "expected_tokens": 10, "memory_seed": True},
            
            # Memory recall phase (should hit cache and maintain GPU performance)
            {"prompt": "What is my favorite color?", "expected_tokens": 15, "memory_recall": True},
            {"prompt": "What do I do for work?", "expected_tokens": 15, "memory_recall": True},
            {"prompt": "What are my hobbies?", "expected_tokens": 15, "memory_recall": True},
            
            # Complex reasoning phase (should trigger higher GPU utilization)
            {"prompt": "Compare bubble sort vs quicksort algorithms", "expected_tokens": 20, "complex": True},
            {"prompt": "Explain quantum computing principles", "expected_tokens": 25, "complex": True},
        ]
        
        total_start = time.time()
        
        for i, test in enumerate(test_sequence, 1):
            print(f"\n🧪 Test {i}/{len(test_sequence)}: {test['prompt'][:50]}...")
            
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    router.route_query(test['prompt']),
                    timeout=10.0
                )
                
                end_time = time.time()
                latency = end_time - start_time
                
                # Extract performance metrics
                tokens_per_sec = result.get("tokens_per_sec", 0)
                if tokens_per_sec == 0:
                    # Estimate if not provided
                    response_length = len(result.get("text", "").split())
                    tokens_per_sec = response_length / latency if latency > 0 else 0
                
                test_results["tokens_per_sec"].append(tokens_per_sec)
                test_results["latencies"].append(latency)
                
                # Track memory operations
                if result.get("memory_context_used", False):
                    test_results["memory_hits"] += 1
                if "memory" in str(result.get("model", "")):
                    test_results["memory_writes"] += 1
                
                print(f"   ⏱️ Latency: {latency:.3f}s")
                print(f"   🎯 Tokens/s: {tokens_per_sec:.1f}")
                print(f"   🧠 Memory used: {result.get('memory_context_used', False)}")
                print(f"   💬 Response: {result.get('text', '')[:80]}...")
                
                # Performance validation
                if test.get("complex", False):
                    if tokens_per_sec < 10:
                        print("   ⚠️ WARNING: Low tokens/s for complex query")
                elif test.get("memory_recall", False):
                    if latency > 2.0:
                        print("   ⚠️ WARNING: High latency for memory recall")
                
                # Brief pause between tests
                await asyncio.sleep(0.3)
                
            except asyncio.TimeoutError:
                print(f"   🚨 TIMEOUT after 10s")
                test_results["latencies"].append(10.0)
            except Exception as e:
                print(f"   💥 ERROR: {e}")
                test_results["latencies"].append(5.0)
        
        total_time = time.time() - total_start
        
        # Stop monitoring
        monitoring_active = False
        
        # Calculate final metrics
        await analyze_phase2_results(total_time)
        
    except Exception as e:
        monitoring_active = False
        print(f"💥 Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def analyze_phase2_results(total_time):
    """Analyze Phase 2 test results against targets"""
    global test_results
    
    print(f"\n📊 PHASE 2 RESULTS ANALYSIS")
    print("=" * 40)
    
    # GPU Performance Analysis
    gpu_utils = test_results["gpu_utilization"]
    if gpu_utils:
        avg_gpu = sum(gpu_utils) / len(gpu_utils)
        max_gpu = max(gpu_utils)
        min_gpu = min(gpu_utils)
        
        print(f"🔥 GPU Utilization:")
        print(f"   Average: {avg_gpu:.1f}% (target: ≥35%)")
        print(f"   Peak: {max_gpu:.1f}%")
        print(f"   Min: {min_gpu:.1f}%")
        
        gpu_target_met = avg_gpu >= 35.0
        print(f"   Status: {'✅ TARGET MET' if gpu_target_met else '❌ BELOW TARGET'}")
    
    # Throughput Analysis
    tokens_per_sec = test_results["tokens_per_sec"]
    if tokens_per_sec:
        avg_tokens = sum(tokens_per_sec) / len(tokens_per_sec)
        
        print(f"\n🎯 Throughput:")
        print(f"   Average: {avg_tokens:.1f} tokens/s (target: ≥25)")
        
        throughput_target_met = avg_tokens >= 25.0
        print(f"   Status: {'✅ TARGET MET' if throughput_target_met else '❌ BELOW TARGET'}")
    
    # Latency Analysis
    latencies = test_results["latencies"]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print(f"\n⚡ Latency:")
        print(f"   Average: {avg_latency:.3f}s (target: ≤1.5s)")
        print(f"   P95: {max_latency:.3f}s")
        
        latency_target_met = avg_latency <= 1.5
        print(f"   Status: {'✅ TARGET MET' if latency_target_met else '❌ ABOVE TARGET'}")
    
    # Memory System Analysis
    print(f"\n🧠 Memory System:")
    print(f"   Memory hits: {test_results['memory_hits']}")
    print(f"   Memory writes: {test_results['memory_writes']}")
    print(f"   Total time: {total_time:.2f}s")
    
    # Overall Phase 2 Assessment
    targets_met = []
    if gpu_utils:
        targets_met.append(avg_gpu >= 35.0)
    if tokens_per_sec:
        targets_met.append(avg_tokens >= 25.0)
    if latencies:
        targets_met.append(avg_latency <= 1.5)
    
    success_rate = sum(targets_met) / len(targets_met) if targets_met else 0
    
    print(f"\n🎯 PHASE 2 OVERALL STATUS:")
    print(f"   Targets met: {sum(targets_met)}/{len(targets_met)} ({success_rate*100:.1f}%)")
    
    if success_rate >= 0.8:
        print("🎉 🎉 PHASE 2 SUCCESS: Memory + GPU integration complete! 🎉 🎉")
        return True
    elif success_rate >= 0.6:
        print("🟡 PHASE 2 PARTIAL: Some optimization needed")
        return False
    else:
        print("🔴 PHASE 2 ISSUES: Significant problems detected")
        return False

if __name__ == "__main__":
    print("🚀 Phase 2 Integration Test")
    print("Testing Memory System + GPU Performance")
    
    # Set up signal handler
    def signal_handler(sig, frame):
        global monitoring_active
        monitoring_active = False
        print('\n🛑 Test interrupted')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = asyncio.run(test_memory_and_gpu_integration())
    
    if success:
        print("\n✅ Ready to proceed to performance optimization phase")
    else:
        print("\n⚠️ Phase 2 integration needs attention") 