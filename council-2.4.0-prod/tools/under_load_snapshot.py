# -*- coding: utf-8 -*-
import time
import json
import psutil
import subprocess
import threading
from pathlib import Path

def run_gpu_monitor(duration=30, output_file="bench_snaps/nvidia_smi_snapshot.txt"):
    """Monitor GPU every 2 seconds for specified duration"""
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(f"=== GPU Monitoring for {duration}s ===\n")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            timestamp = time.strftime("%H:%M:%S")
            f.write(f"\n--- {timestamp} ---\n")
            
            try:
                result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    f.write(result.stdout)
                else:
                    f.write("nvidia-smi failed\n")
            except Exception as e:
                f.write(f"nvidia-smi error: {e}\n")
            
            f.flush()
            time.sleep(2)

def stress_system():
    """Create CPU load for realistic testing"""
    def cpu_stress():
        end_time = time.time() + 30
        while time.time() < end_time:
            # Simple CPU-intensive calculation
            sum(i*i for i in range(10000))
    
    # Start CPU stress threads
    threads = []
    for _ in range(psutil.cpu_count() // 2):  # Use half the cores
        t = threading.Thread(target=cpu_stress)
        t.start()
        threads.append(t)
    
    return threads

def capture_system_snapshot():
    """Capture system state during load"""
    snapshot = {
        "timestamp": time.time(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory": {
            "percent": psutil.virtual_memory().percent,
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "used_gb": round((psutil.virtual_memory().total - psutil.virtual_memory().available) / (1024**3), 2)
        }
    }
    
    # Try to get GPU info
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpus = []
            for line in lines:
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 4:
                        gpus.append({
                            "utilization_percent": int(parts[0]),
                            "memory_used_mb": int(parts[1]),
                            "memory_total_mb": int(parts[2]),
                            "temperature_c": int(parts[3])
                        })
            snapshot["gpus"] = gpus
    except Exception as e:
        snapshot["gpu_error"] = str(e)
    
    return snapshot

def main():
    print("🔥 Starting 30-second under-load snapshot...")
    
    # Start GPU monitoring in background
    gpu_monitor_thread = threading.Thread(target=run_gpu_monitor)
    gpu_monitor_thread.start()
    
    # Start CPU stress
    stress_threads = stress_system()
    
    # Capture snapshots every 5 seconds
    snapshots = []
    for i in range(6):  # 6 snapshots over 30 seconds
        snapshot = capture_system_snapshot()
        snapshots.append(snapshot)
        print(f"   📊 Snapshot {i+1}/6 captured")
        time.sleep(5)
    
    # Wait for all threads to complete
    gpu_monitor_thread.join()
    for t in stress_threads:
        t.join()
    
    # Save the snapshot data
    output_file = "bench_snaps/under_load_snapshot.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(snapshots, f, indent=2)
    
    print(f"\n✨ Under-load snapshot complete!")
    print(f"   📄 System data: {output_file}")
    print(f"   📄 GPU logs: bench_snaps/nvidia_smi_snapshot.txt")
    
    # Print summary
    if snapshots and "gpus" in snapshots[-1]:
        final_gpu = snapshots[-1]["gpus"][0]
        print(f"\n🎮 Final GPU state:")
        print(f"   🔥 Utilization: {final_gpu['utilization_percent']}%")
        print(f"   💾 VRAM: {final_gpu['memory_used_mb']}MB / {final_gpu['memory_total_mb']}MB")
        print(f"   🌡️ Temperature: {final_gpu['temperature_c']}°C")

if __name__ == "__main__":
    main() 