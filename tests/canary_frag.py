#!/usr/bin/env python3
"""
Fragmentation Canary - CUDA Memory Stress Test
Hits mistral_7b_instruct at 100 QPS for 90s to detect memory fragmentation events.
"""

import locust
import os
import time
import json
from locust import HttpUser, task, between

class SwarmLoadUser(HttpUser):
    """Load user that hits the swarm API for CUDA fragmentation testing"""
    wait_time = between(0.01, 0.02)  # 100 QPS targeting
    
    def on_start(self):
        """Initialize user session"""
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "FragmentationCanary/1.0"
        }
    
    @task(10)
    def test_mistral_inference(self):
        """Primary load test - hit mistral_7b_instruct repeatedly"""
        payload = {
            "prompt": "Write a simple Python function to calculate fibonacci:",
            "model": "mistral_7b_instruct",
            "max_tokens": 64,
            "temperature": 0.0
        }
        
        with self.client.post("/generate", 
                             json=payload, 
                             headers=self.headers,
                             timeout=10,
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "generated_text" in result:
                        response.success()
                    else:
                        response.failure(f"Missing generated_text in response: {result}")
                except json.JSONDecodeError as e:
                    response.failure(f"Invalid JSON response: {e}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")
    
    @task(5)
    def test_math_specialist(self):
        """Secondary load - math specialist to create mixed allocation patterns"""
        payload = {
            "prompt": "What is 12 * 15?",
            "model": "math_specialist", 
            "max_tokens": 32,
            "temperature": 0.0
        }
        
        with self.client.post("/generate",
                             json=payload,
                             headers=self.headers,
                             timeout=5,
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2) 
    def test_code_specialist(self):
        """Tertiary load - code specialist for large allocations"""
        payload = {
            "prompt": "def sort_list(items):",
            "model": "code_specialist",
            "max_tokens": 128,
            "temperature": 0.0
        }
        
        with self.client.post("/generate",
                             json=payload, 
                             headers=self.headers,
                             timeout=8,
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

# Entry point for command line execution
if __name__ == "__main__":
    print("🧪 CUDA Fragmentation Canary Test")
    print("=" * 50)
    print("Target: 100 QPS for 90 seconds")
    print("Models: mistral_7b_instruct (primary), math_specialist, code_specialist")
    print("Goal: Detect CUDA memory fragmentation events")
    print("=" * 50)
    
    # Run with locust programmatically if needed
    # This allows direct execution for CI integration
    import subprocess
    import sys
    
    cmd = [
        "locust",
        "-f", __file__,
        "--headless",
        "-u", "100",        # 100 users
        "-r", "20",         # Spawn rate 20 users/sec
        "-t", "90s",        # Run for 90 seconds
        "--host", "http://localhost:8000"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    
    sys.exit(result.returncode) 