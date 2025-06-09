#!/usr/bin/env python3
"""
Council Smoke Test - 40 VU Load Test
Tests the council-api /council endpoint with realistic prompts
Target: p95 < 300ms, queue depth < 10, no Guardian restarts
"""

from locust import task, HttpUser, between
import random
import json

class CouncilUser(HttpUser):
    # Target the council-api service
    host = "http://localhost:9000"
    
    # Realistic wait times for deliberation processes
    wait_time = between(1, 3)  # Council deliberations take time
    
    # Test prompts for Council - varied complexity
    test_prompts = [
        {
            "prompt": "Explain quantum computing in simple terms",
            "max_tokens": 150,
            "temperature": 0.7
        },
        {
            "prompt": "Write a Python function to calculate fibonacci numbers",
            "max_tokens": 200,
            "temperature": 0.3
        },
        {
            "prompt": "What are the benefits of renewable energy?",
            "max_tokens": 180,
            "temperature": 0.5
        },
        {
            "prompt": "Solve this math problem: If a train travels 60 mph for 2.5 hours, how far does it go?",
            "max_tokens": 100,
            "temperature": 0.1
        },
        {
            "prompt": "Describe the water cycle",
            "max_tokens": 160,
            "temperature": 0.6
        }
    ]
    
    @task(5)
    def test_council_deliberation(self):
        """Test Council deliberation with random prompt"""
        prompt_data = random.choice(self.test_prompts)
        
        with self.client.post("/council", 
                            json=prompt_data,
                            headers={"Content-Type": "application/json"},
                            catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "text" in data:
                        response.success()
                    else:
                        response.failure("No text field in JSON")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(2)
    def test_health_endpoint(self):
        """Test health endpoint for service availability"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Service not healthy")
                except json.JSONDecodeError:
                    response.failure("Invalid health response")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def test_council_status_endpoint(self):
        """Test council status endpoint for monitoring"""
        with self.client.get("/council/status", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "council_enabled" in data:
                        response.success()
                    else:
                        response.failure("Council status data missing")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"Council status endpoint failed: {response.status_code}")

    def on_start(self):
        """Called when user starts - optional warm-up"""
        # Quick health check before starting load test
        self.client.get("/health") 