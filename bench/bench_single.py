#!/usr/bin/env python3
"""
Single-Shot Performance Benchmark - Suite 3
Validates raw tokens/s & latency performance after cold boot
Pass criteria: ≥17 t/s, p95 ≤ 800ms
"""

import argparse
import asyncio
import json
import time
import statistics
import requests
from typing import List, Dict, Any

class SingleShotBenchmark:
    """Single-shot performance benchmark for AutoGen Council"""
    
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url
        self.results = []
        
    def wait_for_service(self, timeout: int = 60) -> bool:
        """Wait for service to be ready"""
        print("⏳ Waiting for AutoGen Council to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Service is ready")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        print("❌ Service not ready within timeout")
        return False
    
    def generate_test_prompts(self, num_prompts: int = 10) -> List[str]:
        """Generate diverse test prompts for benchmarking"""
        prompts = [
            "Write a Python function to calculate fibonacci numbers",
            "Explain the concept of machine learning in simple terms",
            "What are the benefits of renewable energy sources?",
            "How does photosynthesis work in plants?",
            "Describe the principles of quantum computing",
            "What is the difference between AI and machine learning?",
            "Explain how neural networks process information",
            "What are the main causes of climate change?",
            "How do computers understand human language?",
            "Describe the process of software development",
            "What is the role of databases in modern applications?",
            "How does encryption protect digital communications?",
            "Explain the concept of cloud computing",
            "What are the fundamentals of web development?",
            "How do operating systems manage computer resources?"
        ]
        
        # Cycle through prompts to get requested number
        return [prompts[i % len(prompts)] for i in range(num_prompts)]
    
    async def run_single_request(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Run a single performance test request"""
        start_time = time.time()
        
        try:
            # Use the existing hybrid endpoint
            response = requests.post(
                f"{self.base_url}/hybrid",
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            end_time = time.time()
            latency = end_time - start_time
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Estimate tokens (rough approximation)
                tokens_generated = len(response_text.split())
                tokens_per_sec = tokens_generated / latency if latency > 0 else 0
                
                return {
                    "success": True,
                    "latency": latency,
                    "tokens_generated": tokens_generated,
                    "tokens_per_sec": tokens_per_sec,
                    "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                    "response_length": len(response_text),
                    "status_code": response.status_code
                }
            else:
                return {
                    "success": False,
                    "latency": latency,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt
                }
                
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "latency": end_time - start_time,
                "error": str(e),
                "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt
            }
    
    async def run_benchmark(self, num_requests: int = 10, max_tokens: int = 256) -> Dict[str, Any]:
        """Run the complete single-shot benchmark"""
        print(f"🚀 Starting single-shot benchmark with {num_requests} requests, {max_tokens} max tokens")
        
        # Wait for service
        if not self.wait_for_service():
            return {"error": "Service not available"}
        
        # Generate test prompts
        prompts = self.generate_test_prompts(num_requests)
        
        # Run requests sequentially (single-shot, not concurrent)
        results = []
        for i, prompt in enumerate(prompts, 1):
            print(f"📤 Request {i}/{num_requests}: {prompt[:30]}...")
            
            result = await self.run_single_request(prompt, max_tokens)
            results.append(result)
            
            if result["success"]:
                print(f"   ✅ {result['latency']:.3f}s, {result['tokens_per_sec']:.1f} t/s")
            else:
                print(f"   ❌ Failed: {result['error']}")
            
            # Brief pause between requests
            await asyncio.sleep(0.5)
        
        # Analyze results
        return self.analyze_results(results, max_tokens)
    
    def analyze_results(self, results: List[Dict], max_tokens: int) -> Dict[str, Any]:
        """Analyze benchmark results against pass criteria"""
        successful_results = [r for r in results if r["success"]]
        
        if not successful_results:
            return {
                "success": False,
                "error": "No successful requests",
                "total_requests": len(results),
                "successful_requests": 0
            }
        
        # Extract metrics
        latencies = [r["latency"] for r in successful_results]
        tokens_per_sec = [r["tokens_per_sec"] for r in successful_results]
        
        # Calculate statistics
        avg_latency = statistics.mean(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 5 else max(latencies)
        avg_tokens_per_sec = statistics.mean(tokens_per_sec)
        
        # Pass criteria evaluation
        tokens_pass = avg_tokens_per_sec >= 17.0  # ≥17 t/s
        latency_pass = p95_latency <= 0.8  # p95 ≤ 800ms
        success_rate = len(successful_results) / len(results)
        success_rate_pass = success_rate >= 0.95  # ≥95% success rate
        
        overall_pass = tokens_pass and latency_pass and success_rate_pass
        
        return {
            "success": True,
            "overall_pass": overall_pass,
            "timestamp": time.time(),
            "config": {
                "max_tokens": max_tokens,
                "total_requests": len(results),
                "successful_requests": len(successful_results)
            },
            "metrics": {
                "avg_latency": avg_latency,
                "p95_latency": p95_latency,
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "avg_tokens_per_sec": avg_tokens_per_sec,
                "max_tokens_per_sec": max(tokens_per_sec),
                "success_rate": success_rate
            },
            "pass_criteria": {
                "tokens_per_sec": {
                    "target": 17.0,
                    "actual": avg_tokens_per_sec,
                    "pass": tokens_pass
                },
                "p95_latency": {
                    "target": 0.8,
                    "actual": p95_latency,
                    "pass": latency_pass
                },
                "success_rate": {
                    "target": 0.95,
                    "actual": success_rate,
                    "pass": success_rate_pass
                }
            },
            "raw_results": results
        }

def main():
    parser = argparse.ArgumentParser(description="Single-shot performance benchmark")
    parser.add_argument("--tokens", type=int, default=256, help="Maximum tokens per request")
    parser.add_argument("--requests", type=int, default=10, help="Number of test requests")
    parser.add_argument("--url", default="http://localhost:9000", help="AutoGen Council base URL")
    parser.add_argument("--output", help="Output file for results (JSON)")
    
    args = parser.parse_args()
    
    # Run benchmark
    benchmark = SingleShotBenchmark(args.url)
    results = asyncio.run(benchmark.run_benchmark(args.requests, args.tokens))
    
    # Print summary
    if results.get("success") and "metrics" in results:
        metrics = results["metrics"]
        pass_criteria = results["pass_criteria"]
        
        print(f"\n📊 SINGLE-SHOT PERFORMANCE BENCHMARK RESULTS")
        print("=" * 60)
        print(f"🎯 Performance Metrics:")
        print(f"   Average latency: {metrics['avg_latency']:.3f}s")
        print(f"   P95 latency: {metrics['p95_latency']:.3f}s")
        print(f"   Average tokens/s: {metrics['avg_tokens_per_sec']:.1f}")
        print(f"   Peak tokens/s: {metrics['max_tokens_per_sec']:.1f}")
        print(f"   Success rate: {metrics['success_rate']:.1%}")
        
        print(f"\n🎯 Pass Criteria:")
        for criterion, data in pass_criteria.items():
            status = "✅" if data["pass"] else "❌"
            print(f"   {status} {criterion}: {data['actual']:.3f} (target: {data['target']:.3f})")
        
        overall_status = "✅ PASS" if results["overall_pass"] else "❌ FAIL"
        print(f"\n🏆 Overall Result: {overall_status}")
        
    else:
        print(f"❌ Benchmark failed: {results.get('error', 'Unknown error')}")
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📄 Results saved to {args.output}")
    
    # Exit with appropriate code
    exit_code = 0 if results.get("overall_pass", False) else 1
    exit(exit_code)

if __name__ == "__main__":
    main() 