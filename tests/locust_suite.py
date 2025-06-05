#!/usr/bin/env python3
"""
Locust Load Testing Suite - Suite 4
Load/burst testing for AutoGen Council API
Pass criteria: Error rate < 0.1%, GPU util ≥ 50%, util dip < 35%
"""

import json
import random
import time
from locust import HttpUser, task, between, events

class AutoGenCouncilUser(HttpUser):
    """Simulates a user interacting with AutoGen Council"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Initialize user session"""
        self.conversation_history = []
        self.test_prompts = [
            "Explain machine learning in simple terms",
            "Write a Python function to sort a list",
            "What are the benefits of cloud computing?",
            "How does neural network training work?",
            "Describe the principles of software architecture",
            "What is the difference between AI and ML?",
            "Explain REST API design best practices",
            "How do databases ensure data consistency?",
            "What are microservices and their advantages?",
            "Describe the software development lifecycle"
        ]
    
    @task(10)
    def simple_chat(self):
        """Simple single-turn chat request"""
        prompt = random.choice(self.test_prompts)
        
        response = self.client.post("/hybrid", 
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.7
            },
            name="simple_chat"
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if len(content) > 10:  # Reasonable response
                        return
                # Mark as failure if response is invalid
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="simple_chat",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Invalid response format"
                )
            except json.JSONDecodeError:
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="simple_chat",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Invalid JSON response"
                )
    
    @task(5)
    def conversation_with_memory(self):
        """Multi-turn conversation to test memory"""
        if len(self.conversation_history) == 0:
            # Start new conversation
            initial_prompt = "My name is TestUser and I'm interested in AI"
            messages = [{"role": "user", "content": initial_prompt}]
        else:
            # Continue conversation
            follow_up_prompts = [
                "What did I just tell you about myself?",
                "Can you remember my name?",
                "What topic am I interested in?",
                "Tell me more about that topic"
            ]
            follow_up = random.choice(follow_up_prompts)
            messages = self.conversation_history + [{"role": "user", "content": follow_up}]
        
        response = self.client.post("/hybrid",
            json={
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.5
            },
            name="conversation_memory"
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    assistant_response = data["choices"][0]["message"]["content"]
                    
                    # Update conversation history (keep last 4 turns)
                    self.conversation_history = messages + [{"role": "assistant", "content": assistant_response}]
                    if len(self.conversation_history) > 8:  # 4 turns = 8 messages
                        self.conversation_history = self.conversation_history[-8:]
                    
                    return
                        
                # Mark as failure if response is invalid
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="conversation_memory",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Invalid response format"
                )
            except json.JSONDecodeError:
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="conversation_memory",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Invalid JSON response"
                )
    
    @task(3)
    def long_context_request(self):
        """Test with longer context to stress memory and processing"""
        long_prompt = """
        I'm working on a complex software project that involves multiple components:
        1. A React frontend with TypeScript
        2. A Node.js backend with Express
        3. A PostgreSQL database
        4. Redis for caching
        5. Docker for containerization
        
        The system needs to handle user authentication, real-time messaging, 
        file uploads, and data analytics. I'm particularly concerned about 
        scalability and security best practices.
        
        Can you provide a comprehensive architectural overview and 
        recommendations for this system?
        """
        
        response = self.client.post("/hybrid",
            json={
                "messages": [{"role": "user", "content": long_prompt}],
                "max_tokens": 300,
                "temperature": 0.6
            },
            name="long_context"
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if len(content) > 50:  # Reasonable response to complex prompt
                        return
                
                # Mark as failure if response is too short for complex prompt
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="long_context",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Response too short for complex prompt"
                )
            except json.JSONDecodeError:
                self.environment.events.request_failure.fire(
                    request_type="POST",
                    name="long_context",
                    response_time=response.elapsed.total_seconds() * 1000,
                    response_length=len(response.content),
                    exception="Invalid JSON response"
                )
    
    @task(2)
    def health_check(self):
        """Periodic health check"""
        self.client.get("/health", name="health_check")
    
    @task(1)
    def metrics_check(self):
        """Check metrics endpoint if available"""
        response = self.client.get("/metrics", name="metrics_check", catch_response=True)
        
        if response.status_code == 404:
            # Metrics endpoint might not exist, don't count as failure
            response.success()

class BurstTestUser(HttpUser):
    """High-frequency burst testing user"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times for burst testing
    
    def on_start(self):
        """Initialize burst test user"""
        self.quick_prompts = [
            "Hello",
            "Hi there",
            "How are you?",
            "Test",
            "Quick question",
            "Help me",
            "Thanks",
            "Yes",
            "No",
            "OK"
        ]
    
    @task
    def quick_burst_request(self):
        """Quick requests to test burst handling"""
        prompt = random.choice(self.quick_prompts)
        
        self.client.post("/hybrid",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 20,
                "temperature": 0.1
            },
            name="burst_request"
        )

# Custom event handlers for detailed metrics
@events.request_success.add_listener
def on_request_success(request_type, name, response_time, response_length, **kwargs):
    """Track successful requests"""
    if response_time > 5000:  # Log slow requests (>5s)
        print(f"SLOW REQUEST: {name} took {response_time:.2f}ms")

@events.request_failure.add_listener
def on_request_failure(request_type, name, response_time, response_length, exception, **kwargs):
    """Track failed requests"""
    print(f"FAILED REQUEST: {name} - {exception}")

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Generate final report on test completion"""
    stats = environment.stats
    
    print("\n" + "="*60)
    print("LOAD TEST COMPLETION REPORT")
    print("="*60)
    
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    
    if total_requests > 0:
        error_rate = (total_failures / total_requests) * 100
        avg_response_time = stats.total.avg_response_time
        
        print(f"Total Requests: {total_requests}")
        print(f"Total Failures: {total_failures}")
        print(f"Error Rate: {error_rate:.2f}%")
        print(f"Average Response Time: {avg_response_time:.2f}ms")
        print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        
        # Pass criteria evaluation
        print("\n" + "="*30)
        print("PASS CRITERIA EVALUATION")
        print("="*30)
        
        error_rate_pass = error_rate < 0.1
        response_time_pass = avg_response_time < 2000  # 2s average
        
        print(f"Error Rate < 0.1%: {'✅ PASS' if error_rate_pass else '❌ FAIL'} ({error_rate:.2f}%)")
        print(f"Avg Response < 2s: {'✅ PASS' if response_time_pass else '❌ FAIL'} ({avg_response_time:.2f}ms)")
        
        overall_pass = error_rate_pass and response_time_pass
        print(f"\nOverall Load Test: {'✅ PASS' if overall_pass else '❌ FAIL'}")
        
        # Note about GPU utilization (needs external monitoring)
        print("\nNote: GPU utilization (≥50%) and util dip (<35%) must be")
        print("      verified through Grafana monitoring during the test.")
    
    print("="*60) 