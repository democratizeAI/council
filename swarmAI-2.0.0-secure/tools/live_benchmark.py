# -*- coding: utf-8 -*-
import time
import json
import psutil
from pathlib import Path

def capture_metrics():
    return {
        "timestamp": time.time(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
    }

def main():
    duration = 90
    capture_interval = 2
    output_file = "bench_snaps/live_bench.json"
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    metrics_list = []
    
    while time.time() - start_time < duration:
        metrics = capture_metrics()
        metrics_list.append(metrics)
        time.sleep(capture_interval)
    
    with open(output_file, 'w') as f:
        json.dump(metrics_list, f, indent=2)
        print(f"\n✨  Wrote {output_file}")

if __name__ == "__main__":
    main() 