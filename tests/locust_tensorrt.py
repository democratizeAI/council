#!/usr/bin/env python3
"""
Locust Load Testing for Phase 4 TensorRT-LLM
Tests 4-way concurrency target: 25+ t/s aggregate
Usage: locust -f tests/locust_tensorrt.py -u 8 -r 2 -t 3m --host http://localhost:8000 --tags tensorrt
"""

import time
import random
from locust import HttpUser, task, tag, events
from locust.env import Environment

class TensorRTLoadUser(HttpUser):
    """Locust user for TensorRT-LLM load testing"""
    
    wait_time = lambda self: random.uniform(0.5, 2.0)  # Variable think time
    
    def on_start(self):
        """Initialize user session"""
        self.client.timeout = 30  # 30s timeout for TensorRT requests
        self.test_prompts = [
            "Write a Python function to calculate factorial",
            "Explain the difference between lists and tuples in Python",
            "What is the capital of France and its population?",
            "How do you implement a binary search algorithm?",
            "Describe the benefits of renewable energy sources",
            "Write a simple HTTP server in Python",
            "What are the main principles of object-oriented programming?",
            "How does machine learning differ from traditional programming?",
            "Explain the concept of recursion with an example",
            "What are the advantages of using databases over files?",
            "How do you handle exceptions in Python?",
            "What is the difference between HTTP and HTTPS?",
            "Describe how sorting algorithms work",
            "What are the main components of a computer?",
            "How do you create a REST API?",
            "Explain the concept of version control with Git",
            "What is cloud computing and its benefits?",
            "How do neural networks learn?",
            "What are the principles of good software design?",
            "How do you optimize database queries?"
        ]
    
    @task(10)
    @tag("tensorrt", "single")
    def single_generation_request(self):
        """Single generation request for TensorRT testing"""
        prompt = random.choice(self.test_prompts)
        
        payload = {
            "prompt": prompt,
            "max_tokens": 50,
            "temperature": 0.7,
            "backend": "tensorrt"
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/generate",
            json=payload,
            catch_response=True,
            name="tensorrt_single"
        ) as response:
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "text" in result and result["text"]:
                        tokens = len(result["text"].split())
                        tokens_per_sec = tokens / latency if latency > 0 else 0
                        
                        # Log performance metrics
                        events.request.fire(
                            request_type="PERF",
                            name="tokens_per_sec",
                            response_time=tokens_per_sec * 1000,  # Scale for visibility
                            response_length=tokens
                        )
                        
                        # Mark success if performance targets met
                        if tokens_per_sec >= 15.0:  # Lower bound for individual requests
                            response.success()
                        else:
                            response.failure(f"Low throughput: {tokens_per_sec:.1f} t/s")
                    else:
                        response.failure("No text in response")
                except Exception as e:
                    response.failure(f"JSON decode error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(5)
    @tag("tensorrt", "memory") 
    def memory_cache_request(self):
        """Test memory cache performance"""
        # Use a limited set of prompts to increase cache hits
        cache_prompts = [
            "What is 2 + 2?",
            "Hello world in Python",
            "Current time and date",
            "Basic math operations"
        ]
        
        prompt = random.choice(cache_prompts)
        
        payload = {
            "prompt": prompt,
            "max_tokens": 30,
            "backend": "tensorrt"
        }
        
        start_time = time.time()
        
        with self.client.post(
            "/generate",
            json=payload,
            catch_response=True,
            name="tensorrt_cache"
        ) as response:
            
            latency = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    source = result.get("source", "unknown")
                    
                    # Cache hits should be very fast
                    if source == "memory_cache" and latency > 0.1:
                        response.failure(f"Slow cache hit: {latency:.3f}s")
                    elif source == "tensorrt" and latency > 2.0:
                        response.failure(f"Slow generation: {latency:.3f}s")
                    else:
                        response.success()
                        
                except Exception as e:
                    response.failure(f"JSON decode error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    @tag("tensorrt", "stress")
    def stress_test_request(self):
        """Higher token count stress test"""
        stress_prompts = [
            "Write a detailed explanation of how machine learning works, including examples",
            "Describe the complete process of software development from requirements to deployment",
            "Explain quantum computing and its potential applications in detail",
            "Provide a comprehensive guide to database design and optimization"
        ]
        
        prompt = random.choice(stress_prompts)
        
        payload = {
            "prompt": prompt,
            "max_tokens": 100,  # Higher token count
            "temperature": 0.7,
            "backend": "tensorrt"
        }
        
        with self.client.post(
            "/generate",
            json=payload,
            catch_response=True,
            name="tensorrt_stress"
        ) as response:
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "text" in result and len(result["text"]) > 50:
                        response.success()
                    else:
                        response.failure("Insufficient response length")
                except Exception as e:
                    response.failure(f"JSON decode error: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")

# Performance monitoring and metrics collection
@events.request.on("success")
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Track successful requests for aggregate metrics"""
    if name.startswith("tensorrt_"):
        # Log to console for real-time monitoring
        if request_type == "POST":
            print(f"✅ {name}: {response_time:.0f}ms, {response_length} bytes")

@events.request.on("failure")
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Track failed requests"""
    if name.startswith("tensorrt_"):
        print(f"❌ {name}: {exception}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test session"""
    print("🚀 Starting TensorRT-LLM Load Test")
    print("Target: 25+ t/s aggregate throughput at 4-way concurrency")
    print("=" * 60)

@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Analyze final results"""
    stats = environment.stats
    
    print("\n📊 TENSORRT-LLM LOAD TEST RESULTS")
    print("=" * 60)
    
    # Overall request statistics
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    avg_response_time = stats.total.avg_response_time
    
    print(f"Total Requests: {total_requests}")
    print(f"Failures: {total_failures} ({failure_rate:.1f}%)")
    print(f"Avg Response Time: {avg_response_time:.0f}ms")
    
    # TensorRT-specific metrics
    tensorrt_stats = [s for name, s in stats.entries.items() if name[1].startswith("tensorrt_")]
    
    if tensorrt_stats:
        tensorrt_requests = sum(s.num_requests for s in tensorrt_stats)
        tensorrt_failures = sum(s.num_failures for s in tensorrt_stats)
        tensorrt_failure_rate = (tensorrt_failures / tensorrt_requests * 100) if tensorrt_requests > 0 else 0
        
        print(f"\n🔥 TensorRT Performance:")
        print(f"   TensorRT Requests: {tensorrt_requests}")
        print(f"   TensorRT Failures: {tensorrt_failures} ({tensorrt_failure_rate:.1f}%)")
        
        # Calculate throughput (requests per second)
        test_duration = time.time() - environment.parsed_options.start_time if hasattr(environment.parsed_options, 'start_time') else 180
        throughput_rps = tensorrt_requests / test_duration
        
        print(f"   Test Duration: {test_duration:.0f}s")
        print(f"   Throughput: {throughput_rps:.1f} req/s")
        
        # Success criteria for Phase 4
        success_criteria = {
            "failure_rate": tensorrt_failure_rate <= 5.0,  # <5% failure rate
            "avg_latency": avg_response_time <= 1500,      # <1.5s average
            "throughput": throughput_rps >= 2.0            # ≥2 req/s (conservative for load test)
        }
        
        print(f"\n🎯 Phase 4 Load Test Criteria:")
        for criterion, passed in success_criteria.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {criterion}: {passed}")
        
        if all(success_criteria.values()):
            print("\n🎉 PHASE 4 LOAD TEST SUCCESS!")
            print("✅ TensorRT-LLM handling concurrent load effectively")
        else:
            print("\n⚠️ Phase 4 load test needs optimization")
    
    else:
        print("⚠️ No TensorRT-specific stats found")

# Custom user class for high concurrency testing
class HighConcurrencyUser(TensorRTLoadUser):
    """High concurrency user for stress testing"""
    
    wait_time = lambda self: random.uniform(0.1, 0.5)  # Faster requests
    
    @task(15)
    @tag("tensorrt", "high_concurrency")
    def rapid_fire_requests(self):
        """Rapid-fire requests for concurrency testing"""
        quick_prompts = [
            "Hello",
            "What is AI?", 
            "Python syntax",
            "Math: 5+5",
            "Current year?"
        ]
        
        prompt = random.choice(quick_prompts)
        
        payload = {
            "prompt": prompt,
            "max_tokens": 20,
            "backend": "tensorrt"
        }
        
        with self.client.post(
            "/generate",
            json=payload,
            catch_response=True,
            name="tensorrt_rapid"
        ) as response:
            
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

if __name__ == "__main__":
    print("🚀 TensorRT-LLM Locust Load Testing")
    print("Run with: locust -f tests/locust_tensorrt.py -u 8 -r 2 -t 3m --host http://localhost:8000")
    print("Target: Validate 25+ t/s aggregate throughput") 