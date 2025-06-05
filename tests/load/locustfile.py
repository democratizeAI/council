#!/usr/bin/env python3
"""
AutoGen Council Load Testing with Locust
=======================================

Stress test configuration:
- 50 concurrent users  
- 10 users/second spawn rate
- 5 minute test duration
- Target: p95 < 2000ms, error rate < 2%

Usage:
    locust -f locustfile.py --headless -u50 -r10 -t5m --host http://localhost:9000
"""

import random
import json
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner

class AutoGenCouncilUser(HttpUser):
    """Simulates realistic AutoGen Council usage patterns"""
    
    wait_time = between(1, 3)  # 1-3 seconds between requests
    
    def on_start(self):
        """Initialize user session"""
        self.session_id = f"load_test_{random.randint(1000, 9999)}"
        self.conversation_context = []
        
    @task(10)  # 50% of traffic
    def simple_greeting(self):
        """Test basic greeting/health responses"""
        queries = [
            "hello", "hi there", "how are you?", 
            "what can you help me with?", "good morning"
        ]
        
        self.make_request({
            "query": random.choice(queries),
            "session_id": self.session_id
        }, "greeting")
    
    @task(8)  # 40% of traffic  
    def math_specialist_query(self):
        """Test math specialist with varying complexity"""
        math_queries = [
            "What is 2 + 2?",
            "Factor x^2 - 5x + 6", 
            "Solve the equation 3x + 7 = 22",
            "What's the derivative of x^3 + 2x^2 - 5x + 1?",
            "Calculate the area of a circle with radius 5",
            "Simplify (x^2 - 4)/(x - 2)",
            "Find the integral of sin(x)",
            "What's 15% of 240?"
        ]
        
        self.make_request({
            "query": random.choice(math_queries),
            "session_id": self.session_id,
            "specialist_hint": "math"
        }, "math")
    
    @task(6)  # 30% of traffic
    def code_specialist_query(self):
        """Test code specialist requests"""
        code_queries = [
            "Write a Python function to reverse a string",
            "How do I sort a list in Python?", 
            "Explain what a for loop does",
            "Write a simple calculator in Python",
            "How to read a file in Python?",
            "What's the difference between lists and tuples?",
            "Write a function to find the factorial of a number",
            "How do I handle exceptions in Python?"
        ]
        
        self.make_request({
            "query": random.choice(code_queries), 
            "session_id": self.session_id,
            "specialist_hint": "code"
        }, "code")
    
    @task(4)  # 20% of traffic
    def knowledge_specialist_query(self):
        """Test knowledge specialist requests"""
        knowledge_queries = [
            "What is machine learning?",
            "Explain quantum computing",
            "Who invented the telephone?",
            "What causes climate change?", 
            "How does photosynthesis work?",
            "What is the capital of Australia?",
            "Explain the theory of relativity",
            "What are the benefits of renewable energy?"
        ]
        
        self.make_request({
            "query": random.choice(knowledge_queries),
            "session_id": self.session_id, 
            "specialist_hint": "knowledge"
        }, "knowledge")
    
    @task(3)  # 15% of traffic
    def logic_specialist_query(self):
        """Test logic and reasoning specialist"""
        logic_queries = [
            "If all birds can fly and penguins are birds, can penguins fly?",
            "Solve this riddle: What has keys but no locks?",
            "What's wrong with this argument: All cats are mammals, Fluffy is a mammal, therefore Fluffy is a cat?",
            "If it's raining, then the ground is wet. The ground is wet. Is it raining?",
            "Complete the pattern: 2, 4, 8, 16, ?",
            "What's the logical fallacy in 'Everyone I know likes pizza, so everyone in the world likes pizza'?",
            "If A > B and B > C, what can we conclude about A and C?",
            "Explain why correlation doesn't imply causation"
        ]
        
        self.make_request({
            "query": random.choice(logic_queries),
            "session_id": self.session_id,
            "specialist_hint": "logic" 
        }, "logic")
    
    @task(2)  # 10% of traffic
    def multi_turn_conversation(self):
        """Test conversation context and memory"""
        if len(self.conversation_context) == 0:
            # Start conversation
            query = "My bike is turquoise. What color is my bike?"
            self.conversation_context.append(query)
        elif len(self.conversation_context) == 1:
            # Follow up
            query = "What did I just tell you about my bike?"
            self.conversation_context.append(query)
        else:
            # Reset conversation
            self.conversation_context = []
            query = "Let's start over. Tell me about artificial intelligence."
            
        self.make_request({
            "query": query,
            "session_id": self.session_id,
            "context": self.conversation_context[-3:]  # Last 3 messages
        }, "conversation")
    
    @task(1)  # 5% of traffic - stress test
    def complex_query(self):
        """Test complex queries that exercise multiple specialists"""
        complex_queries = [
            "Write a Python function to calculate compound interest, then use it to find the value of $1000 invested at 5% for 10 years",
            "Explain machine learning and write code to implement a simple linear regression",
            "What is calculus and show me how to find the derivative of a polynomial function in Python",
            "Compare different sorting algorithms and implement quicksort in Python with mathematical analysis of time complexity"
        ]
        
        self.make_request({
            "query": random.choice(complex_queries),
            "session_id": self.session_id,
            "require_specialist": True
        }, "complex")
    
    def make_request(self, payload: dict, request_type: str):
        """Make request with error handling and metrics"""
        start_time = time.time()
        
        try:
            with self.client.post(
                "/hybrid",
                json=payload,
                headers={"Content-Type": "application/json"},
                catch_response=True
            ) as response:
                
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        # Check for stub responses
                        if "response" in data:
                            response_text = data["response"].lower()
                            if any(stub in response_text for stub in ["unsure", "template", "i don't", "error"]):
                                response.failure(f"Stub response detected: {response_text[:100]}")
                            else:
                                response.success()
                        else:
                            response.failure("Invalid response format")
                            
                    except json.JSONDecodeError:
                        response.failure("Invalid JSON response")
                        
                elif response.status_code == 422:
                    response.failure("Request validation error (422)")
                    
                elif response.status_code >= 500:
                    response.failure(f"Server error ({response.status_code})")
                    
                else:
                    response.failure(f"Unexpected status code: {response.status_code}")
                
                # Log slow responses
                if response_time > 2000:
                    print(f"SLOW RESPONSE: {request_type} took {response_time:.0f}ms")
                    
        except Exception as e:
            print(f"REQUEST EXCEPTION: {request_type} - {str(e)}")

class HealthCheckUser(HttpUser):
    """Dedicated health check user for monitoring"""
    
    wait_time = between(5, 10)  # Less frequent health checks
    weight = 1  # Lower weight
    
    @task
    def health_check(self):
        """Monitor system health during load test"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")

# Event handlers for load test monitoring
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Monitor request performance"""
    if response_time > 2000:  # Log requests over 2 seconds
        print(f"PERFORMANCE ALERT: {name} took {response_time:.0f}ms")

@events.test_start.add_listener  
def on_test_start(environment, **kwargs):
    """Initialize load test"""
    print("🚀 AutoGen Council Load Test Starting")
    print(f"Target: {environment.host}")
    print("Performance targets:")
    print("  • P95 latency < 2000ms")
    print("  • Error rate < 2%")
    print("  • No stub responses")
    print("=" * 50)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate load test report"""
    print("=" * 50)
    print("🏁 AutoGen Council Load Test Complete")
    
    stats = environment.stats
    
    print(f"📊 Performance Summary:")
    print(f"  • Total requests: {stats.total.num_requests}")
    print(f"  • Failed requests: {stats.total.num_failures}")
    print(f"  • Error rate: {stats.total.fail_ratio:.2%}")
    print(f"  • Average response time: {stats.total.avg_response_time:.0f}ms")
    print(f"  • P50 response time: {stats.total.get_response_time_percentile(0.5):.0f}ms")
    print(f"  • P95 response time: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  • P99 response time: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    print(f"  • RPS: {stats.total.current_rps:.1f}")
    
    # Performance assertions
    p95_time = stats.total.get_response_time_percentile(0.95)
    error_rate = stats.total.fail_ratio
    
    print(f"\n🎯 Performance Targets:")
    print(f"  • P95 < 2000ms: {'✅ PASS' if p95_time < 2000 else '❌ FAIL'} ({p95_time:.0f}ms)")
    print(f"  • Error rate < 2%: {'✅ PASS' if error_rate < 0.02 else '❌ FAIL'} ({error_rate:.2%})")
    
    if p95_time < 2000 and error_rate < 0.02:
        print("\n🎉 LOAD TEST PASSED - System ready for production!")
    else:
        print("\n⚠️ LOAD TEST FAILED - Performance tuning needed")

# Run configuration
if __name__ == "__main__":
    print("Run with: locust -f locustfile.py --headless -u50 -r10 -t5m --host http://localhost:9000") 