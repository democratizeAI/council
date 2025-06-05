#!/usr/bin/env python3
"""
Phase 3 GPU Clock Locking for Consistent Performance
Locks GPU clocks for stable 45%+ utilization
"""

import subprocess
import time
import sys

def check_nvidia_smi():
    """Check if nvidia-smi is available"""
    try:
        result = subprocess.run(['nvidia-smi', '--version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def get_gpu_info():
    """Get current GPU information"""
    try:
        result = subprocess.run([
            'nvidia-smi', 
            '--query-gpu=name,temperature.gpu,power.draw,clocks.gr,clocks.mem,persistence_mode',
            '--format=csv,noheader,nounits'
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            if len(parts) >= 6:
                return {
                    'name': parts[0],
                    'temperature': parts[1],
                    'power': parts[2],
                    'gpu_clock': parts[3],
                    'mem_clock': parts[4],
                    'persistence': parts[5]
                }
    except Exception as e:
        print(f"❌ Failed to get GPU info: {e}")
    
    return None

def set_persistence_mode():
    """Enable persistence mode for stable performance"""
    print("🔧 Enabling persistence mode...")
    try:
        result = subprocess.run(['nvidia-smi', '-pm', '1'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Persistence mode enabled")
            return True
        else:
            print(f"⚠️ Persistence mode failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Persistence mode error: {e}")
        return False

def lock_gpu_clocks():
    """Lock GPU clocks for Phase 3 performance"""
    print("🚀 Locking GPU clocks for Phase 3 optimization...")
    
    # RTX 4070 optimal clock ranges (adjust for your card)
    gpu_min_clock = 2100  # MHz
    gpu_max_clock = 2700  # MHz
    
    try:
        # Lock GPU clocks
        cmd = ['nvidia-smi', '-lgc', f'{gpu_min_clock},{gpu_max_clock}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ GPU clocks locked: {gpu_min_clock}-{gpu_max_clock} MHz")
            return True
        else:
            print(f"⚠️ Clock locking failed: {result.stderr}")
            print("💡 Note: Administrator privileges may be required")
            return False
            
    except Exception as e:
        print(f"❌ Clock locking error: {e}")
        return False

def reset_gpu_clocks():
    """Reset GPU clocks to default"""
    print("🔄 Resetting GPU clocks to default...")
    try:
        result = subprocess.run(['nvidia-smi', '-rgc'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ GPU clocks reset to default")
            return True
        else:
            print(f"⚠️ Clock reset failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Clock reset error: {e}")
        return False

def monitor_gpu_performance(duration=30):
    """Monitor GPU performance for Phase 3 validation"""
    print(f"📊 Monitoring GPU performance for {duration}s...")
    
    utilizations = []
    temperatures = []
    power_draws = []
    
    start_time = time.time()
    
    while time.time() - start_time < duration:
        try:
            result = subprocess.run([
                'nvidia-smi',
                '--query-gpu=utilization.gpu,temperature.gpu,power.draw',
                '--format=csv,noheader,nounits'
            ], capture_output=True, text=True, timeout=2)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 3:
                    util = float(parts[0])
                    temp = float(parts[1]) 
                    power = float(parts[2])
                    
                    utilizations.append(util)
                    temperatures.append(temp)
                    power_draws.append(power)
                    
                    print(f"   📊 GPU: {util}% util, {temp}°C, {power}W")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   ⚠️ Monitoring error: {e}")
            break
    
    if utilizations:
        avg_util = sum(utilizations) / len(utilizations)
        max_util = max(utilizations)
        avg_temp = sum(temperatures) / len(temperatures)
        avg_power = sum(power_draws) / len(power_draws)
        
        print(f"\n📊 MONITORING RESULTS:")
        print(f"   Average utilization: {avg_util:.1f}%")
        print(f"   Peak utilization: {max_util:.1f}%")
        print(f"   Average temperature: {avg_temp:.1f}°C")
        print(f"   Average power draw: {avg_power:.1f}W")
        
        # Phase 3 targets
        util_target = avg_util >= 45.0
        temp_safe = avg_temp <= 80.0
        
        print(f"\n🎯 PHASE 3 GPU TARGETS:")
        print(f"   {'✅' if util_target else '❌'} Utilization ≥ 45%: {avg_util:.1f}%")
        print(f"   {'✅' if temp_safe else '❌'} Temperature ≤ 80°C: {avg_temp:.1f}°C")
        
        return util_target and temp_safe
    
    return False

def main():
    """Main Phase 3 GPU optimization routine"""
    print("🚀 PHASE 3: GPU CLOCK OPTIMIZATION")
    print("=" * 40)
    
    # Check prerequisites
    if not check_nvidia_smi():
        print("❌ nvidia-smi not available")
        return False
    
    # Get initial GPU info
    gpu_info = get_gpu_info()
    if gpu_info:
        print(f"🔍 GPU: {gpu_info['name']}")
        print(f"   Current: {gpu_info['gpu_clock']} MHz GPU, {gpu_info['mem_clock']} MHz Mem")
        print(f"   Status: {gpu_info['temperature']}°C, {gpu_info['power']}W")
    
    try:
        # Enable persistence mode
        set_persistence_mode()
        
        # Lock clocks for performance
        clock_success = lock_gpu_clocks()
        
        if clock_success:
            print("\n🧪 Testing optimized performance...")
            time.sleep(5)  # Let settings stabilize
            
            # Monitor performance
            performance_good = monitor_gpu_performance(30)
            
            if performance_good:
                print("\n🎉 Phase 3 GPU optimization successful!")
                print("✅ GPU ready for vLLM high-performance workload")
                return True
            else:
                print("\n🟡 Performance below Phase 3 targets")
                return False
        
        else:
            print("\n⚠️ Clock locking failed - proceeding with default clocks")
            print("💡 Run as Administrator for clock control")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        return False
    finally:
        # Optional: Reset clocks on exit (comment out to keep locked)
        # print("\n🔄 Resetting GPU clocks...")
        # reset_gpu_clocks()
        pass

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 GPU optimized for Phase 3 vLLM deployment!")
        sys.exit(0)
    else:
        print("\n⚠️ GPU optimization had issues")
        sys.exit(1) 