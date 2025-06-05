#!/usr/bin/env python3
"""
Week 2-1: ExLlama V2 Performance Test
Locust load test for 8 VUs × 256-token prompts
Target: p95 ≤ 280ms (1080) / ≤ 120ms (4070), GPU util 45-60%
"""

from locust import HttpUser, task, between
import json
import time
import random

class SwarmUser(HttpUser):
    wait_time = between(0.5, 1.2)  # Realistic user think time
    
    def on_start(self):
        """Initialize test user session"""
        self.session_id = f"test_user_{random.randint(1000, 9999)}"
    
    @task(5)
    def simple_math(self):
        """Math queries to test specialist routing"""
        math_queries = [
            "Compute 123*456",
            "What is 89 + 234?", 
            "Calculate 15% of 250",
            "Solve: 2x + 5 = 17",
            "What's the square root of 144?"
        ]
        
        response = self.client.post(
            "/chat",
            json={
                "message": random.choice(math_queries),
                "session_id": self.session_id
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            latency = data.get("latency_ms", 0)
            
            # Week 2-1 performance targets
            if latency > 280:  # Conservative target for GTX 1080
                response.failure(f"Latency {latency}ms > 280ms target")
            else:
                response.success()
        else:
            response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def code_questions(self):
        """Code queries to test code specialist"""
        code_queries = [
            "Write a Python function to sort a list",
            "How do I read a file in Python?",
            "Explain list comprehensions",
            "What's the difference between == and is?",
            "Show me a simple for loop example"
        ]
        
        response = self.client.post(
            "/chat",
            json={
                "message": random.choice(code_queries),
                "session_id": self.session_id
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            latency = data.get("latency_ms", 0)
            
            if latency > 350:  # Code queries can be slightly slower
                response.failure(f"Code latency {latency}ms > 350ms")
            else:
                response.success()
        else:
            response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def general_queries(self):
        """General knowledge queries"""
        general_queries = [
            "What is the capital of France?",
            "Explain photosynthesis briefly",
            "Who wrote Romeo and Juliet?",
            "What causes seasons on Earth?",
            "How do airplanes fly?"
        ]
        
        response = self.client.post(
            "/chat",
            json={
                "message": random.choice(general_queries),
                "session_id": self.session_id
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            data = response.json()
            confidence = data.get("confidence", 0)
            
            # Ensure Week 1 confidence floor is working
            if confidence < 0.1:
                response.failure(f"Confidence {confidence} too low")
            else:
                response.success()
        else:
            response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Periodic health checks"""
        response = self.client.get("/health", catch_response=True)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                response.success()
            else:
                response.failure("API not healthy")
        else:
            response.failure(f"Health check failed: {response.status_code}")

if __name__ == "__main__":
    # Run with: locust -f tests/locust_perf.py --headless -u 8 -r 2 -t 3m --host http://localhost:8000
    print("🚀 Week 2-1 ExLlama V2 Performance Test")
    print("Target: p95 ≤ 280ms (GTX 1080) / ≤ 120ms (RTX 4070)")
    print("Expected GPU util: 45-60%")
    print("Run: locust -f tests/locust_perf.py --headless -u 8 -r 2 -t 3m --host http://localhost:8000") 