#!/usr/bin/env python3
"""Direct GPU utilization test with real-time monitoring"""

import asyncio
import time
import sys
import subprocess
import threading
import signal
sys.path.append('.')

# Global variable to control monitoring
monitoring_active = True

def monitor_gpu_during_test():
    """Monitor GPU utilization during generation in real-time"""
    global monitoring_active
    print("📊 Starting real-time GPU monitoring...")
    
    try:
        while monitoring_active:
            result = subprocess.run([
                'nvidia-smi', 
                '--query-gpu=utilization.gpu,memory.used,power.draw', 
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 3:
                    gpu_util, mem_used, power = parts
                    print(f"📊 GPU: {gpu_util}% util, {mem_used}MB mem, {power}W")
            
            time.sleep(0.5)  # Check every 500ms
            
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ GPU monitoring error: {e}")

async def test_gpu_utilization():
    """Test GPU utilization with real-time monitoring"""
    global monitoring_active
    
    print('🔬 GPU Utilization Test with Real-time Monitoring...')
    
    # Start monitoring in background
    monitor_thread = threading.Thread(target=monitor_gpu_during_test, daemon=True)
    monitor_thread.start()
    
    try:
        from gpu_optimization import fast_generate, setup_optimized_model, warmup_model
        
        print("🚀 Setting up optimized model...")
        pipeline = setup_optimized_model()
        
        print("🔥 Warming up model...")
        warmup_model()
        
        print('\n📋 Testing GPU utilization during generation...')
        print("🔍 Watch for GPU utilization spikes above 40%...")
        
        # Multiple test runs to see sustained performance
        test_prompts = [
            "Write a hello world function",
            "What is 2+2?", 
            "Explain Python loops",
            "Create a simple class"
        ]
        
        total_tokens = 0
        total_time = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🧪 Test {i}/4: {prompt}")
            
            start = time.time()
            result = await fast_generate(prompt, max_tokens=15)  # Shorter for speed
            end = time.time()
            
            latency = end - start
            tokens_per_sec = result.get("tokens_per_sec", 0)
            
            total_tokens += result.get("output_length", 0)
            total_time += latency
            
            print(f"   ⏱️ Latency: {latency:.3f}s")
            print(f"   🎯 Tokens/s: {tokens_per_sec:.1f}")
            print(f"   💬 Response: {result.get('text', '')[:60]}...")
            
            # Brief pause between tests
            await asyncio.sleep(0.5)
        
        # Stop monitoring
        monitoring_active = False
        
        # Calculate averages
        avg_latency = total_time / len(test_prompts)
        avg_tokens_per_sec = total_tokens / total_time if total_time > 0 else 0
        
        print(f'\n📊 FINAL RESULTS:')
        print(f'   Average latency: {avg_latency:.3f}s')
        print(f'   Average tokens/s: {avg_tokens_per_sec:.1f}')
        print(f'   Total tokens: {total_tokens}')
        print(f'   Total time: {total_time:.3f}s')
        
        # Performance assessment
        if avg_tokens_per_sec >= 45:
            print('🎉 🎉 PHASE 1 COMPLETE: TARGET ACHIEVED! 🎉 🎉')
        elif avg_tokens_per_sec >= 30:
            print('🟡 CLOSE: 67% of target achieved')
        elif avg_tokens_per_sec >= 20:
            print('🟡 PROGRESS: 44% of target achieved')  
        else:
            print('🔴 SIGNIFICANT OPTIMIZATION STILL NEEDED')
            
        return avg_tokens_per_sec
        
    except Exception as e:
        monitoring_active = False
        print(f'💥 ERROR: {e}')
        import traceback
        traceback.print_exc()
        return 0

async def check_baseline():
    """Quick baseline check"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,power.draw', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            if len(parts) >= 3:
                mem_used, gpu_util, power = parts
                print(f'📊 Baseline GPU Status:')
                print(f'   Memory: {mem_used}MB')
                print(f'   Utilization: {gpu_util}%')
                print(f'   Power: {power}W')
                
    except Exception as e:
        print(f'❌ Baseline check failed: {e}')

if __name__ == "__main__":
    print("🚀 Phase 1 GPU Optimization - COMPREHENSIVE TEST")
    print("=" * 60)
    
    # Set up signal handler for clean exit
    def signal_handler(sig, frame):
        global monitoring_active
        monitoring_active = False
        print('\n🛑 Test interrupted by user')
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    asyncio.run(check_baseline())
    print()
    result = asyncio.run(test_gpu_utilization())
    
    print(f"\n🎯 Final Performance: {result:.1f} tokens/s")
    print("Monitor output above to see if GPU utilization exceeded 40% during generation") 