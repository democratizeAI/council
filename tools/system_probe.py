# -*- coding: utf-8 -*-
import json
import psutil
import platform
import subprocess
from pathlib import Path

def get_gpu_info():
    """Get GPU information using nvidia-smi if available"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpus = []
            for line in lines:
                if line.strip():
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 5:
                        gpus.append({
                            "name": parts[0],
                            "memory_total_mb": int(parts[1]),
                            "memory_free_mb": int(parts[2]),
                            "utilization_percent": int(parts[3]),
                            "temperature_c": int(parts[4])
                        })
            return gpus
    except Exception as e:
        print(f"GPU info unavailable: {e}")
    return []

def get_system_info():
    info = {
        "platform": platform.system(),
        "cpu": {
            "cores": psutil.cpu_count(),
            "physical_cores": psutil.cpu_count(logical=False),
            "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
        },
        "memory": {
            "total_bytes": psutil.virtual_memory().total,
            "available_bytes": psutil.virtual_memory().available,
            "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "available_gb": round(psutil.virtual_memory().available / (1024**3), 2)
        },
        "gpus": get_gpu_info()
    }
    return info

def main():
    output_file = "swarm_system_report.json"
    info = get_system_info()
    
    with open(output_file, 'w') as f:
        json.dump(info, f, indent=2)
        
    print(f"\n✨ Fresh system probe written to {output_file}")
    
    # Print summary
    if info["gpus"]:
        for i, gpu in enumerate(info["gpus"]):
            vram_used = gpu["memory_total_mb"] - gpu["memory_free_mb"]
            print(f"🎮 GPU {i}: {gpu['name']}")
            print(f"   💾 VRAM: {gpu['memory_total_mb']}MB total, {gpu['memory_free_mb']}MB free ({vram_used}MB used)")
            print(f"   🔥 Load: {gpu['utilization_percent']}%, Temp: {gpu['temperature_c']}°C")
    
    print(f"🧠 CPU: {info['cpu']['cores']} cores")
    print(f"💽 RAM: {info['memory']['total_gb']}GB total, {info['memory']['available_gb']}GB available")

if __name__ == "__main__":
    main() 