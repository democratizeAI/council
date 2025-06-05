#!/usr/bin/env python3
"""
🏆 Titanic Gauntlet v2.6.0 - Docker Edition
Comprehensive evaluation suite for Council API running in containers
"""
import os
import sys
import json
import time
import requests
import argparse
from datetime import datetime
from pathlib import Path

class TitanicGauntletDocker:
    """Docker-compatible Titanic Gauntlet runner"""
    
    def __init__(self, council_url="http://localhost:9000", budget=10.0):
        self.council_url = council_url
        self.budget = budget
        self.results = {
            "metadata": {
                "version": "2.6.0",
                "timestamp": datetime.now().isoformat(),
                "council_url": council_url,
                "budget_limit": budget
            },
            "metrics": {},
            "tests": []
        }
        
    def check_council_health(self):
        """Verify Council API is responsive"""
        try:
            response = requests.get(f"{self.council_url}/health", timeout=10)
            if response.status_code == 200:
                print("✅ Council API health check passed")
                return True
            else:
                print(f"❌ Council API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Council API unreachable: {e}")
            return False
    
    def run_micro_suite(self):
        """Fast 50-prompt micro suite (≈3 min)"""
        print("🚀 Running Micro Suite (50 prompts)")
        print("=" * 50)
        
        # Micro test prompts - core functionality
        micro_prompts = [
            "What is 2 + 2?",
            "Write a Python function to calculate factorial",
            "Explain what Docker containers are",
            "How do you reverse a string in Python?",
            "What is the capital of France?",
        ] * 10  # 50 total prompts
        
        return self._run_prompt_suite(micro_prompts, "micro")
    
    def run_full_titanic(self):
        """Full 380-prompt Titanic suite (≈25 min)"""
        print("🏆 Running Full Titanic Gauntlet (380 prompts)")
        print("=" * 50)
        
        # Generate comprehensive test suite
        prompts = self._generate_titanic_prompts()
        return self._run_prompt_suite(prompts, "full_titanic")
    
    def _generate_titanic_prompts(self):
        """Generate the full 380-prompt test suite"""
        prompts = []
        
        # Math problems (80 prompts)
        math_prompts = [
            f"Calculate {i} * {j} + {k}" for i in range(10, 20) 
            for j in range(2, 6) for k in range(1, 3)
        ]
        prompts.extend(math_prompts[:80])
        
        # Code generation (100 prompts)
        code_prompts = [
            "Write a Python function to sort a list",
            "Create a REST API endpoint in FastAPI",
            "Implement binary search in Python",
            "Write a SQL query to find duplicates",
            "Create a React component for a button",
        ] * 20
        prompts.extend(code_prompts)
        
        # Logic puzzles (50 prompts)
        logic_prompts = [
            "If all roses are flowers and some flowers fade quickly, what can we conclude?",
            "A train travels 60 mph for 2 hours. How far does it go?",
            "You have 3 boxes, one contains apples. How do you find it with minimum questions?",
        ] * 17  # ~50 prompts
        prompts.extend(logic_prompts[:50])
        
        # Knowledge questions (150 prompts)
        knowledge_prompts = [
            "What is the capital of Australia?",
            "Who invented the telephone?",
            "What year did World War II end?",
            "Explain photosynthesis briefly",
            "What is the largest planet in our solar system?",
        ] * 30
        prompts.extend(knowledge_prompts)
        
        return prompts[:380]  # Ensure exactly 380 prompts
    
    def _run_prompt_suite(self, prompts, suite_name):
        """Run a suite of prompts and collect metrics"""
        start_time = time.time()
        total_cost = 0
        successful_requests = 0
        failed_requests = 0
        latencies = []
        
        print(f"📊 Testing {len(prompts)} prompts...")
        
        for i, prompt in enumerate(prompts):
            if total_cost >= self.budget:
                print(f"💰 Budget limit reached (${total_cost:.2f}), stopping early")
                break
                
            try:
                # Time the request
                request_start = time.time()
                
                response = requests.post(
                    f"{self.council_url}/hybrid",
                    json={"prompt": prompt},
                    timeout=30
                )
                
                request_time = (time.time() - request_start) * 1000  # ms
                latencies.append(request_time)
                
                if response.status_code == 200:
                    successful_requests += 1
                    # Estimate cost (mock for now)
                    estimated_cost = 0.02  # $0.02 per request estimate
                    total_cost += estimated_cost
                    
                    result = {
                        "prompt": prompt,
                        "response": response.json(),
                        "latency_ms": request_time,
                        "status": "success",
                        "cost": estimated_cost
                    }
                else:
                    failed_requests += 1
                    result = {
                        "prompt": prompt,
                        "response": None,
                        "latency_ms": request_time,
                        "status": "failed",
                        "error": response.text
                    }
                
                self.results["tests"].append(result)
                
                # Progress indicator
                if (i + 1) % 50 == 0:
                    success_rate = (successful_requests / (i + 1)) * 100
                    avg_latency = sum(latencies) / len(latencies)
                    print(f"   Progress: {i + 1}/{len(prompts)} | "
                          f"Success: {success_rate:.1f}% | "
                          f"Avg Latency: {avg_latency:.0f}ms | "
                          f"Cost: ${total_cost:.2f}")
                
            except Exception as e:
                failed_requests += 1
                print(f"❌ Request {i + 1} failed: {e}")
                continue
        
        # Calculate final metrics
        total_time = time.time() - start_time
        total_requests = successful_requests + failed_requests
        
        metrics = {
            "suite_name": suite_name,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            "total_cost": total_cost,
            "total_time_seconds": total_time,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0
        }
        
        self.results["metrics"] = metrics
        return metrics
    
    def generate_report(self, output_file=None):
        """Generate comprehensive test report"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
            output_file = f"reports/titanic_{self.results['metrics']['suite_name']}_{timestamp}.json"
        
        # Ensure reports directory exists
        Path("reports").mkdir(exist_ok=True)
        
        # Write detailed JSON report
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        metrics = self.results["metrics"]
        print("\n🏆 TITANIC GAUNTLET RESULTS")
        print("=" * 50)
        print(f"Suite: {metrics['suite_name']}")
        print(f"Total Requests: {metrics['total_requests']}")
        print(f"Success Rate: {metrics['success_rate']:.1f}%")
        print(f"P95 Latency: {metrics['p95_latency_ms']:.0f}ms")
        print(f"Total Cost: ${metrics['total_cost']:.2f}")
        print(f"Total Time: {metrics['total_time_seconds']:.0f}s")
        print(f"Report saved: {output_file}")
        
        # Pass/Fail Gates
        self._check_pass_gates(metrics)
        
        return output_file
    
    def _check_pass_gates(self, metrics):
        """Check if results meet pass gates"""
        print(f"\n🚦 PASS GATES")
        print("=" * 30)
        
        if metrics["suite_name"] == "micro":
            gates = {
                "success_rate": (95, "≥ 95%"),
                "p95_latency_ms": (200, "≤ 200ms"),
                "total_cost": (0.15, "≤ $0.15")
            }
        else:  # full_titanic
            gates = {
                "success_rate": (92, "≥ 92%"),
                "p95_latency_ms": (200, "≤ 200ms"),
                "total_cost": (7.0, "≤ $7.00")
            }
        
        all_passed = True
        
        for metric, (threshold, description) in gates.items():
            value = metrics[metric]
            
            if metric in ["success_rate"]:
                passed = value >= threshold
            else:  # latency, cost
                passed = value <= threshold
            
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{metric}: {value:.2f} ({description}) - {status}")
            
            if not passed:
                all_passed = False
        
        print(f"\n🎯 Overall: {'✅ ALL GATES PASSED' if all_passed else '❌ SOME GATES FAILED'}")

def main():
    parser = argparse.ArgumentParser(description="Titanic Gauntlet v2.6.0 - Docker Edition")
    parser.add_argument("--suite", choices=["micro", "full"], default="micro", 
                      help="Test suite to run")
    parser.add_argument("--budget", type=float, default=10.0, 
                      help="Budget limit in USD")
    parser.add_argument("--council-url", default="http://localhost:9000",
                      help="Council API URL")
    parser.add_argument("--report", help="Output report file")
    
    args = parser.parse_args()
    
    print(f"🏆 Titanic Gauntlet v2.6.0 - Docker Edition")
    print(f"Council URL: {args.council_url}")
    print(f"Budget: ${args.budget}")
    print(f"Suite: {args.suite}")
    print()
    
    gauntlet = TitanicGauntletDocker(args.council_url, args.budget)
    
    # Health check first
    if not gauntlet.check_council_health():
        print("❌ Council API health check failed. Is the container running?")
        print("Try: docker-compose up -d council-api")
        sys.exit(1)
    
    # Run the selected suite
    if args.suite == "micro":
        metrics = gauntlet.run_micro_suite()
    else:
        metrics = gauntlet.run_full_titanic()
    
    # Generate report
    report_file = gauntlet.generate_report(args.report)
    
    print(f"\n📊 Prometheus Metrics:")
    print(f"swarm_titanic_requests_total: {metrics['total_requests']}")
    print(f"swarm_council_cost_dollars_total: {metrics['total_cost']:.2f}")
    print(f"swarm_p95_latency_ms: {metrics['p95_latency_ms']:.0f}")

if __name__ == "__main__":
    main() 