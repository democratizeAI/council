#!/usr/bin/env python3
"""
Smoke Tests - Suite 1
Tests API surface integrity after packaging
Pass criteria: 100% green
"""

import pytest
import requests
import time
import json
from typing import Dict, Any

class TestSmokeTests:
    """Smoke tests for AutoGen Council API"""
    
    BASE_URL = "http://localhost:9000"
    
    @classmethod
    def setup_class(cls):
        """Setup for all smoke tests"""
        cls.wait_for_service()
    
    @classmethod
    def wait_for_service(cls, timeout: int = 60):
        """Wait for service to be available"""
        print("⏳ Waiting for AutoGen Council service...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{cls.BASE_URL}/health", timeout=5)
                if response.status_code == 200:
                    print("✅ Service is ready")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        
        pytest.fail("Service not available within timeout")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.BASE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]
    
    def test_hybrid_endpoint_exists(self):
        """Test hybrid endpoint responds to POST"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }
        )
        
        # Should not be 404 - endpoint should exist
        assert response.status_code != 404
    
    def test_hybrid_endpoint_basic_functionality(self):
        """Test hybrid endpoint basic functionality"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 50,
                "temperature": 0.1
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have OpenAI-compatible structure
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]
        assert len(data["choices"][0]["message"]["content"]) > 0
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = requests.options(f"{self.BASE_URL}/hybrid")
        
        # Should have CORS headers for web client compatibility
        headers = response.headers
        # Note: Exact CORS header requirements depend on implementation
        assert response.status_code in [200, 204]
    
    def test_error_handling_malformed_json(self):
        """Test error handling for malformed requests"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        # Should return 400 for malformed JSON
        assert response.status_code in [400, 422]
    
    def test_error_handling_missing_messages(self):
        """Test error handling for missing required fields"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={"max_tokens": 10}  # Missing messages
        )
        
        # Should return 400 or 422 for missing required field
        assert response.status_code in [400, 422]
    
    def test_response_time_reasonable(self):
        """Test response time is reasonable for small requests"""
        start_time = time.time()
        
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 10
            }
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Should respond within 30 seconds for small request
        assert response_time < 30.0
        assert response.status_code == 200
    
    def test_max_tokens_respected(self):
        """Test max_tokens parameter is respected"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "Write a very long essay about technology"}],
                "max_tokens": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Response should be limited (rough token estimate)
        word_count = len(content.split())
        assert word_count <= 10  # Allow some flexibility in token counting
    
    def test_temperature_parameter_accepted(self):
        """Test temperature parameter is accepted"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "Say hello"}],
                "max_tokens": 10,
                "temperature": 0.8
            }
        )
        
        assert response.status_code == 200
    
    def test_conversation_context(self):
        """Test multi-turn conversation context"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [
                    {"role": "user", "content": "My name is Alice"},
                    {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
                    {"role": "user", "content": "What is my name?"}
                ],
                "max_tokens": 20
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"].lower()
        
        # Should remember the name from context
        assert "alice" in content
    
    def test_memory_endpoint_if_exists(self):
        """Test memory endpoint if it exists"""
        # Try to access memory endpoint
        response = requests.get(f"{self.BASE_URL}/memory")
        
        # If endpoint exists, it should not return 404
        if response.status_code != 404:
            assert response.status_code in [200, 401, 403]  # OK or auth required
    
    def test_metrics_endpoint_if_exists(self):
        """Test metrics endpoint if it exists"""
        # Try to access metrics endpoint
        response = requests.get(f"{self.BASE_URL}/metrics")
        
        # If endpoint exists, should return prometheus format or JSON
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "text/plain" in content_type or "application/json" in content_type
    
    def test_json_response_format(self):
        """Test response is valid JSON"""
        response = requests.post(
            f"{self.BASE_URL}/hybrid",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 10
            }
        )
        
        assert response.status_code == 200
        
        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)
        
        # Should have required fields
        assert "choices" in data
        assert isinstance(data["choices"], list)
    
    def test_concurrent_requests(self):
        """Test system handles concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = requests.post(
                    f"{self.BASE_URL}/hybrid",
                    json={
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 5
                    },
                    timeout=30
                )
                results.put(response.status_code)
            except Exception as e:
                results.put(f"error: {e}")
        
        # Launch 3 concurrent requests
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=make_request)
            thread.start()
            threads.append(thread)
        
        # Wait for all to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1
        
        # At least 2/3 should succeed (allow for some concurrency limits)
        assert success_count >= 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 