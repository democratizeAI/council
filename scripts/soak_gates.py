#!/usr/bin/env python3
"""
🚪 Soak-Gates Helper (Ticket #224)
Evaluates soak test gates using PromQL expressions with offset comparisons
"""

import requests
import sys
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SoakGate:
    """Represents a soak test gate with PromQL expression and threshold"""
    name: str
    query: str
    threshold: float
    comparison: str  # ">", "<", ">=", "<="
    description: str
    critical: bool = False

class SoakGatesHelper:
    """Helper for evaluating soak test gates using Prometheus queries"""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url.rstrip('/')
        self.gates = self._define_gates()
    
    def _define_gates(self) -> List[SoakGate]:
        """Define all soak test gates with PromQL expressions"""
        return [
            # Performance Gates
            SoakGate(
                name="p95_latency",
                query='histogram_quantile(0.95, swarm_api_request_duration_seconds_bucket{method="POST",route="/orchestrate"})',
                threshold=500.0,  # 500ms
                comparison="<",
                description="P95 latency must stay under 500ms",
                critical=True
            ),
            
            SoakGate(
                name="error_rate",
                query='rate(swarm_api_5xx_total[5m]) * 100',
                threshold=1.0,  # 1%
                comparison="<",
                description="5xx error rate must stay under 1%",
                critical=True
            ),
            
            # Resource Gates
            SoakGate(
                name="gpu_memory",
                query='swarm_api_gpu_memory_mb{gpu="0"}',
                threshold=10240.0,  # 10GB
                comparison="<",
                description="GPU memory usage must stay under 10GB",
                critical=True
            ),
            
            SoakGate(
                name="system_memory",
                query='swarm_api_memory_usage_bytes / 1024 / 1024',
                threshold=8192.0,  # 8GB
                comparison="<",
                description="System memory usage must stay under 8GB"
            ),
            
            # Throughput Gates
            SoakGate(
                name="request_rate",
                query='rate(swarm_api_requests_total[5m])',
                threshold=10.0,  # 10 RPS minimum
                comparison=">",
                description="Request rate must maintain at least 10 RPS"
            ),
            
            SoakGate(
                name="canary_traffic",
                query='rate(swarm_api_canary_traffic_total[5m])',
                threshold=0.5,  # 0.5 RPS minimum
                comparison=">",
                description="Canary traffic must maintain at least 0.5 RPS"
            ),
            
            # RL/Training Gates (with offset comparison as per feedback)
            SoakGate(
                name="rl_reward_progress",
                query='rl_lora_last_reward offset 0 >= rl_lora_last_reward offset 1h',
                threshold=1.0,  # Boolean result (1 = true, 0 = false)
                comparison=">=",
                description="RL reward must not decrease over 1 hour window"
            ),
            
            SoakGate(
                name="training_convergence",
                query='rate(training_steps_total[10m])',
                threshold=0.1,  # 0.1 steps/sec minimum
                comparison=">",
                description="Training must maintain convergence progress"
            ),
            
            # Infrastructure Gates
            SoakGate(
                name="redis_connections",
                query='redis_connected_clients',
                threshold=100.0,  # 100 connections max
                comparison="<",
                description="Redis connections must stay under 100"
            ),
            
            SoakGate(
                name="disk_usage",
                query='(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"} * 100',
                threshold=80.0,  # 80% max
                comparison="<",
                description="Disk usage must stay under 80%"
            )
        ]
    
    def query_prometheus(self, query: str) -> Optional[float]:
        """Execute PromQL query and return first sample value"""
        try:
            url = f"{self.prometheus_url}/api/v1/query"
            params = {"query": query}
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data["status"] != "success":
                print(f"❌ Query failed: {data.get('error', 'Unknown error')}")
                return None
            
            result = data["data"]["result"]
            if not result:
                print(f"⚠️  No data returned for query: {query}")
                return None
            
            # Grab first sample as per feedback
            first_sample = result[0]
            value = float(first_sample["value"][1])
            
            return value
            
        except requests.RequestException as e:
            print(f"❌ Prometheus request failed: {e}")
            return None
        except (KeyError, ValueError, IndexError) as e:
            print(f"❌ Failed to parse Prometheus response: {e}")
            return None
    
    def evaluate_gate(self, gate: SoakGate) -> Tuple[bool, str, Optional[float]]:
        """Evaluate a single soak gate"""
        value = self.query_prometheus(gate.query)
        
        if value is None:
            return False, f"❌ Failed to query {gate.name}", None
        
        # Evaluate comparison
        if gate.comparison == ">":
            passed = value > gate.threshold
        elif gate.comparison == "<":
            passed = value < gate.threshold
        elif gate.comparison == ">=":
            passed = value >= gate.threshold
        elif gate.comparison == "<=":
            passed = value <= gate.threshold
        else:
            return False, f"❌ Invalid comparison operator: {gate.comparison}", value
        
        # Format result
        status = "✅" if passed else "❌"
        critical_marker = " [CRITICAL]" if gate.critical and not passed else ""
        
        result = f"{status} {gate.name}: {value:.2f} {gate.comparison} {gate.threshold} - {gate.description}{critical_marker}"
        
        return passed, result, value
    
    def evaluate_all_gates(self) -> Dict[str, any]:
        """Evaluate all soak gates and return comprehensive results"""
        results = {
            "timestamp": time.time(),
            "gates": [],
            "summary": {
                "total": len(self.gates),
                "passed": 0,
                "failed": 0,
                "critical_failed": 0
            }
        }
        
        print(f"🚪 Evaluating {len(self.gates)} soak gates...")
        print("=" * 60)
        
        for gate in self.gates:
            passed, message, value = self.evaluate_gate(gate)
            
            gate_result = {
                "name": gate.name,
                "passed": passed,
                "value": value,
                "threshold": gate.threshold,
                "comparison": gate.comparison,
                "critical": gate.critical,
                "description": gate.description,
                "message": message
            }
            
            results["gates"].append(gate_result)
            print(message)
            
            # Update summary
            if passed:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
                if gate.critical:
                    results["summary"]["critical_failed"] += 1
        
        print("=" * 60)
        
        # Overall status
        critical_failures = results["summary"]["critical_failed"]
        total_failures = results["summary"]["failed"]
        
        if critical_failures > 0:
            status = "🔴 CRITICAL FAILURES"
            results["overall_status"] = "critical_failure"
        elif total_failures > 0:
            status = "🟡 SOME FAILURES"
            results["overall_status"] = "warning"
        else:
            status = "🟢 ALL GATES PASSED"
            results["overall_status"] = "success"
        
        print(f"{status}: {results['summary']['passed']}/{results['summary']['total']} gates passed")
        
        if critical_failures > 0:
            print(f"🚨 {critical_failures} CRITICAL gate(s) failed - soak test should be stopped!")
            results["action"] = "stop_soak"
        elif total_failures > 0:
            print(f"⚠️  {total_failures} gate(s) failed - monitor closely")
            results["action"] = "monitor"
        else:
            print("✅ All gates passed - soak test is healthy")
            results["action"] = "continue"
        
        return results
    
    def watch_gates(self, interval: int = 60, max_duration: int = 3600):
        """Continuously monitor soak gates"""
        print(f"👀 Starting continuous gate monitoring (interval: {interval}s, max: {max_duration}s)")
        
        start_time = time.time()
        iteration = 0
        
        try:
            while time.time() - start_time < max_duration:
                iteration += 1
                print(f"\n🔄 Gate check #{iteration} ({time.strftime('%H:%M:%S')})")
                
                results = self.evaluate_all_gates()
                
                # Stop on critical failures
                if results["overall_status"] == "critical_failure":
                    print("\n🛑 STOPPING: Critical gate failures detected!")
                    return False
                
                time.sleep(interval)
            
            print(f"\n⏰ Monitoring completed after {max_duration}s")
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            return True

def main():
    """CLI interface for soak gates helper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Soak test gates helper")
    parser.add_argument("--prometheus", default="http://localhost:9090", 
                       help="Prometheus URL")
    parser.add_argument("--watch", action="store_true", 
                       help="Continuous monitoring mode")
    parser.add_argument("--interval", type=int, default=60,
                       help="Watch interval in seconds")
    parser.add_argument("--duration", type=int, default=3600,
                       help="Max watch duration in seconds")
    parser.add_argument("--json", action="store_true",
                       help="Output results as JSON")
    
    args = parser.parse_args()
    
    helper = SoakGatesHelper(args.prometheus)
    
    if args.watch:
        success = helper.watch_gates(args.interval, args.duration)
        sys.exit(0 if success else 1)
    else:
        results = helper.evaluate_all_gates()
        
        if args.json:
            print(json.dumps(results, indent=2))
        
        # Exit with appropriate code
        if results["overall_status"] == "critical_failure":
            sys.exit(2)  # Critical failure
        elif results["overall_status"] == "warning":
            sys.exit(1)  # Warning
        else:
            sys.exit(0)  # Success

if __name__ == "__main__":
    main() 