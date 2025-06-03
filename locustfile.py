# -*- coding: utf-8 -*-
"""
Locust load testing for SwarmAI FastAPI router
Tests the /orchestrate endpoint with realistic payloads
"""

from locust import task, HttpUser, between
import random

class SwarmUser(HttpUser):
    # Target the real FastAPI server
    host = "http://127.0.0.1:8000"
    
    # Realistic wait times between requests
    wait_time = between(0.01, 0.05)
    
    # Available models (matching what's loaded)
    available_models = [
        "tinyllama_1b",
        "mistral_0.5b", 
        "qwen2_0.5b",
        "safety_guard_0.3b",
        "phi2_2.7b",
        "codellama_0.7b",
        "math_specialist_0.8b",
        "openchat_3.5_0.4b",
        "mistral_7b_instruct"
    ]
    
    # Test prompts by category
    test_prompts = {
        "math": [
            "What is 2 + 2?",
            "Calculate the square root of 144",
            "Solve for x: 2x + 5 = 15"
        ],
        "code": [
            "Write a Python function to reverse a string",
            "Explain what a binary search tree is",
            "How do you implement a quicksort algorithm?"
        ],
        "general": [
            "Explain E=mc^2 in one sentence",
            "What is the capital of France?",
            "Tell me about photosynthesis"
        ]
    }
    
    @task(3)
    def test_math_routing(self):
        """Test routing to math specialist"""
        prompt = random.choice(self.test_prompts["math"])
        self.client.post("/orchestrate", 
                        json={
                            "prompt": prompt,
                            "route": ["math_specialist_0.8b"]
                        })
    
    @task(3)
    def test_code_routing(self):
        """Test routing to code specialist"""
        prompt = random.choice(self.test_prompts["code"])
        self.client.post("/orchestrate",
                        json={
                            "prompt": prompt, 
                            "route": ["codellama_0.7b"]
                        })
    
    @task(2)
    def test_general_routing(self):
        """Test routing to general models"""
        prompt = random.choice(self.test_prompts["general"])
        model = random.choice(["mistral_7b_instruct", "openchat_3.5_0.4b"])
        self.client.post("/orchestrate",
                        json={
                            "prompt": prompt,
                            "route": [model]
                        })
    
    @task(1)
    def test_multi_model_routing(self):
        """Test routing with multiple model options"""
        prompt = random.choice(self.test_prompts["general"])
        models = random.sample(self.available_models, k=random.randint(2, 4))
        self.client.post("/orchestrate",
                        json={
                            "prompt": prompt,
                            "route": models
                        })
    
    @task(1)
    def test_health_check(self):
        """Test health endpoint"""
        self.client.get("/health")
    
    @task(1) 
    def test_models_list(self):
        """Test models listing endpoint"""
        self.client.get("/models")
