#!/usr/bin/env python3
"""Capture performance baseline metrics for CI regression testing"""

import argparse
import json
import time
import requests
from datetime import datetime
from typing import Dict, Any

def get_metrics_from_server() -> Dict[str, float]:
    """Fetch current metrics from Prometheus endpoint"""
    try:
        response = requests.get("http://127.0.0.1:8000/metrics", timeout=10)
        response.raise_for_status()
        
        metrics = {}
        for line in response.text.split('\n'):
            if line.startswith('swarm_router_request_latency_count'):
                metrics['total_requests'] = float(line.split()[1])
            elif line.startswith('swarm_router_request_latency_sum'):
                metrics['total_latency_seconds'] = float(line.split()[1])
            elif line.startswith('swarm_vram_used_bytes'):
                # Sum all VRAM usage
                vram_bytes = float(line.split()[1])
                metrics['total_vram_bytes'] = metrics.get('total_vram_bytes', 0) + vram_bytes
        
        # Calculate derived metrics
        if metrics.get('total_requests', 0) > 0:
            metrics['avg_latency_ms'] = (metrics['total_latency_seconds'] / metrics['total_requests']) * 1000
        
        metrics['total_vram_mb'] = metrics.get('total_vram_bytes', 0) / (1024 * 1024)
        
        return metrics
        
    except Exception as e:
        print(f"❌ Failed to fetch metrics: {e}")
        return {}

def capture_baseline(latency_ms: float, vram_mb: float, qps: float) -> Dict[str, Any]:
    """Capture current baseline performance"""
    
    print("🎯 Capturing SwarmAI Performance Baseline")
    print("=" * 50)
    
    # Get live metrics from server
    live_metrics = get_metrics_from_server()
    
    # Create baseline document
    baseline = {
        "metadata": {
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "version": "v0.4.0",
            "description": "First prod-grade release: real transformers, 0 fragmentation @ 70+ QPS",
            "gpu_profile": "rtx_4070",
            "models_loaded": 9
        },
        "performance_thresholds": {
            "max_latency_ms": latency_ms,
            "max_vram_mb": vram_mb,
            "target_qps": qps,
            "max_fragmentation_events": 0,
            "max_failure_rate_percent": 0.1
        },
        "live_measurements": live_metrics,
        "quality_gates": {
            "vram_utilization_percent": (live_metrics.get('total_vram_mb', 0) / vram_mb) * 100 if vram_mb > 0 else 0,
            "avg_latency_ms": live_metrics.get('avg_latency_ms', 0),
            "total_requests_processed": live_metrics.get('total_requests', 0)
        }
    }
    
    # Display summary
    print(f"📊 Live Performance Metrics:")
    print(f"   • Total Requests: {baseline['live_measurements'].get('total_requests', 0):,.0f}")
    print(f"   • Average Latency: {baseline['live_measurements'].get('avg_latency_ms', 0):.1f}ms")
    print(f"   • VRAM Usage: {baseline['live_measurements'].get('total_vram_mb', 0):.0f}MB / {vram_mb}MB")
    print(f"   • VRAM Utilization: {baseline['quality_gates']['vram_utilization_percent']:.1f}%")
    
    print(f"\n🎯 Baseline Thresholds Set:")
    print(f"   • Max Latency: {latency_ms}ms")
    print(f"   • Max VRAM: {vram_mb}MB")
    print(f"   • Target QPS: {qps}")
    print(f"   • Max Fragmentation Events: 0")
    
    return baseline

def save_baseline(baseline: Dict[str, Any], output_file: str = "swarm_baseline.json"):
    """Save baseline to file"""
    try:
        with open(output_file, 'w') as f:
            json.dump(baseline, f, indent=2)
        print(f"\n✅ Baseline saved to {output_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to save baseline: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Capture SwarmAI performance baseline")
    parser.add_argument("--latency_ms", type=float, default=100, 
                       help="Maximum acceptable latency in milliseconds")
    parser.add_argument("--vram_mb", type=float, default=10500,
                       help="Maximum VRAM usage in MB")
    parser.add_argument("--qps", type=float, default=75,
                       help="Target QPS for load testing")
    parser.add_argument("--output", type=str, default="swarm_baseline.json",
                       help="Output file for baseline")
    
    args = parser.parse_args()
    
    # Capture baseline
    baseline = capture_baseline(args.latency_ms, args.vram_mb, args.qps)
    
    # Save to file
    if save_baseline(baseline, args.output):
        print(f"\n🏆 Baseline capture complete!")
        print(f"   Use this file in CI to prevent performance regressions.")
        print(f"   Next: git add {args.output} && git commit -m 'Lock baseline performance'")
    else:
        exit(1)

if __name__ == "__main__":
    main() 