"""
🧪 End-to-End Smoke Test
Validates core functionality: FastAPI startup, basic math, streaming, health
Target: "2 + 2 ?" → "4" in ≤ 300ms
"""

import pytest
import asyncio
import time
import httpx
import json
from fastapi.testclient import TestClient
import threading
import uvicorn
from unittest.mock import patch

# Import the main app
import sys
sys.path.append('../')
from main import app

class TestE2ESmoke:
    """End-to-end smoke tests for production readiness"""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)
    
    def test_basic_math_latency(self, client):
        """
        Core smoke test: 2 + 2 → 4 in ≤ 300ms
        This validates the entire pipeline end-to-end
        """
        start_time = time.time()
        
        response = client.post("/orchestrate", json={
            "prompt": "What is 2 + 2?",
            "route": "math"
        })
        
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000
        
        # Assertions
        assert response.status_code == 200
        assert latency_ms <= 300, f"Response took {latency_ms:.1f}ms (>300ms threshold)"
        
        response_data = response.json()
        assert "response" in response_data
        
        # Validate the response contains "4"
        response_text = response_data["response"].lower()
        assert "4" in response_text, f"Expected '4' in response, got: {response_text}"
        
        print(f"✅ Math test passed in {latency_ms:.1f}ms")
    
    def test_health_endpoints(self, client):
        """Validate all health endpoints respond quickly"""
        endpoints = [
            "/health",
            "/stream/health", 
            "/metrics"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            latency_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200, f"{endpoint} returned {response.status_code}"
            assert latency_ms <= 100, f"{endpoint} took {latency_ms:.1f}ms (>100ms threshold)"
            
            print(f"✅ {endpoint} healthy in {latency_ms:.1f}ms")
    
    def test_streaming_response(self, client):
        """Test streaming endpoint functionality"""
        response = client.post("/stream/completions", json={
            "prompt": "Count to 3",
            "stream": True
        })
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        
        # Validate SSE format
        content = response.content.decode()
        assert "data:" in content
        assert "[DONE]" in content
        
        print("✅ Streaming response working")
    
    def test_ensemble_routing(self, client):
        """Test ensemble routing with different prompts"""
        test_cases = [
            {"prompt": "Solve: x + 5 = 10", "route": "math"},
            {"prompt": "Write a haiku", "route": "creative"},
            {"prompt": "Debug this Python code", "route": "code"}
        ]
        
        for case in test_cases:
            start_time = time.time()
            response = client.post("/orchestrate", json=case)
            latency_ms = (time.time() - start_time) * 1000
            
            assert response.status_code == 200
            assert latency_ms <= 500, f"Route {case['route']} took {latency_ms:.1f}ms"
            
            response_data = response.json()
            assert "response" in response_data
            assert len(response_data["response"]) > 0
            
            print(f"✅ Route {case['route']} working in {latency_ms:.1f}ms")
    
    def test_cost_tracking(self, client):
        """Validate cost tracking metrics work"""
        # Make a request that should increment cost
        response = client.post("/orchestrate", json={
            "prompt": "Simple test",
            "route": "opus"
        })
        
        assert response.status_code == 200
        
        # Check metrics endpoint includes cost data
        metrics_response = client.get("/metrics")
        assert metrics_response.status_code == 200
        
        metrics_text = metrics_response.text
        assert "cost_usd_total" in metrics_text
        
        print("✅ Cost tracking active")
    
    def test_error_handling(self, client):
        """Test graceful error handling"""
        # Invalid JSON
        response = client.post("/orchestrate", 
                             content="invalid json",
                             headers={"content-type": "application/json"})
        assert response.status_code == 422  # Validation error
        
        # Missing required fields
        response = client.post("/orchestrate", json={})
        assert response.status_code in [400, 422]
        
        print("✅ Error handling working")
    
    def test_concurrent_requests(self, client):
        """Test system handles concurrent load"""
        import concurrent.futures
        
        def make_request():
            return client.post("/orchestrate", json={
                "prompt": "Quick test",
                "route": "default"
            })
        
        # Test 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]
            total_time = time.time() - start_time
        
        # All should succeed
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 8, f"Only {success_count}/10 requests succeeded"
        
        # Should handle load efficiently
        avg_time_per_request = total_time / 10
        assert avg_time_per_request <= 1.0, f"Average {avg_time_per_request:.2f}s per request"
        
        print(f"✅ Concurrent load test: {success_count}/10 success in {total_time:.2f}s")

# Standalone test runner for CI
if __name__ == "__main__":
    print("🧪 Running E2E Smoke Tests")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--durations=10"
    ])
    
    if exit_code == 0:
        print("🎉 All smoke tests passed!")
    else:
        print("❌ Some smoke tests failed")
        
    exit(exit_code)

# Performance benchmark mode
def run_performance_benchmark():
    """Extended performance testing"""
    client = TestClient(app)
    
    print("🏃 Running performance benchmark...")
    
    # Warmup
    for _ in range(5):
        client.post("/orchestrate", json={"prompt": "warmup", "route": "default"})
    
    # Benchmark
    latencies = []
    for i in range(100):
        start = time.time()
        response = client.post("/orchestrate", json={
            "prompt": f"Benchmark test {i}",
            "route": "default"
        })
        end = time.time()
        
        if response.status_code == 200:
            latencies.append((end - start) * 1000)
    
    # Stats
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
        
        print(f"📊 Performance Results:")
        print(f"   Average latency: {avg_latency:.1f}ms")
        print(f"   P95 latency: {p95_latency:.1f}ms")
        print(f"   Success rate: {len(latencies)}/100")
        
        # Success criteria
        assert avg_latency <= 200, f"Average latency {avg_latency:.1f}ms > 200ms"
        assert p95_latency <= 500, f"P95 latency {p95_latency:.1f}ms > 500ms"
        
        print("✅ Performance benchmark passed!")

# CLI interface
if __name__ == "__main__" and len(sys.argv) > 1:
    if sys.argv[1] == "bench":
        run_performance_benchmark()
    elif sys.argv[1] == "smoke":
        pytest.main([__file__ + "::TestE2ESmoke::test_basic_math_latency", "-v"])
    else:
        print("Usage: python test_e2e_smoke.py [smoke|bench]") 