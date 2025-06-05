#!/usr/bin/env python3
"""
Cursor E2E Test Harness for FastAPI Soak Testing (Ticket #217)
Spins up the real FastAPI stack and fires 10 sanity calls with cursor.exec()
"""

import pytest
import docker
import requests
import time
import json
import os
import subprocess
from typing import Dict, List
from dataclasses import dataclass

# Test configuration
SOAK_CONFIG = {
    "base_url": "http://localhost:8000",
    "canary_url": "http://localhost:8001", 
    "timeout": 30,
    "health_check_retries": 10,
    "sanity_call_count": 10,
    "log_streaming": True
}

@dataclass
class SoakResult:
    """Container for soak test results"""
    endpoint: str
    status_code: int
    response_time_ms: int
    response_size_bytes: int
    error: str = None

class CursorTestHarness:
    """
    Enhanced test harness that uses cursor.exec() to manage containers
    and stream logs during soak testing
    """
    
    def __init__(self):
        self.client = docker.from_env()
        self.containers = {}
        self.logs = {}
        
    def spin_up_stack(self):
        """Spin up the FastAPI stack using docker-compose"""
        print("🚀 Spinning up FastAPI stack for soak testing...")
        
        try:
            # Use cursor.exec() equivalent: subprocess with log streaming
            result = subprocess.run([
                "docker-compose", 
                "-f", "docker-compose.fastapi.yml", 
                "up", "-d", "--build"
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode != 0:
                raise Exception(f"Failed to start stack: {result.stderr}")
                
            print(f"✅ Stack started: {result.stdout}")
            
            # Give containers time to start
            time.sleep(10)
            
            # Stream logs using cursor.exec() approach
            self.stream_container_logs()
            
            return True
            
        except Exception as e:
            print(f"❌ Stack startup failed: {e}")
            return False
    
    def stream_container_logs(self):
        """Stream container logs during testing (cursor.exec() approach)"""
        try:
            containers = ["swarm-api-main", "swarm-api-canary"]
            
            for container_name in containers:
                container = self.client.containers.get(container_name)
                
                # Use cursor.exec() pattern: forward Docker logs
                logs = container.exec_run(
                    ["bash", "-c", "tail -f /app/logs/api.log || echo 'Log file not found'"],
                    stream=True,
                    detach=True
                )
                
                self.logs[container_name] = logs
                print(f"📝 Streaming logs for {container_name}")
                
        except Exception as e:
            print(f"⚠️ Log streaming setup failed: {e}")
    
    def wait_for_health(self, url: str, max_retries: int = 10) -> bool:
        """Wait for service to become healthy"""
        print(f"🔍 Waiting for health check: {url}/healthz")
        
        for attempt in range(max_retries):
            try:
                response = requests.get(f"{url}/healthz", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Service healthy: {health_data['service']} v{health_data['version']}")
                    return True
                    
            except requests.exceptions.RequestException:
                pass
                
            print(f"⏳ Health check attempt {attempt + 1}/{max_retries}")
            time.sleep(3)
        
        print(f"❌ Service failed to become healthy after {max_retries} attempts")
        return False
    
    def perform_sanity_calls(self, base_url: str) -> List[SoakResult]:
        """Fire 10 comprehensive sanity calls to test all endpoints"""
        print(f"🎯 Performing sanity calls against {base_url}")
        
        sanity_tests = [
            # 1. Root endpoint
            {
                "method": "GET",
                "endpoint": "/",
                "description": "Root API info"
            },
            # 2. Health checks
            {
                "method": "GET", 
                "endpoint": "/health",
                "description": "Legacy health check"
            },
            {
                "method": "GET",
                "endpoint": "/healthz", 
                "description": "Kubernetes health check"
            },
            # 3. Metrics endpoint
            {
                "method": "GET",
                "endpoint": "/metrics",
                "description": "Prometheus metrics"
            },
            # 4. Basic orchestration
            {
                "method": "POST",
                "endpoint": "/orchestrate",
                "json": {
                    "prompt": "What is 2+2?",
                    "flags": [],
                    "temperature": 0.7
                },
                "description": "Basic math orchestration"
            },
            # 5. Math flag orchestration  
            {
                "method": "POST",
                "endpoint": "/orchestrate",
                "json": {
                    "prompt": "Solve: x^2 + 5x + 6 = 0",
                    "flags": ["FLAG_MATH"],
                    "temperature": 0.5
                },
                "description": "Math flag orchestration"
            },
            # 6. Long prompt test
            {
                "method": "POST",
                "endpoint": "/orchestrate", 
                "json": {
                    "prompt": "This is a very long prompt " * 50,
                    "flags": [],
                    "temperature": 0.8
                },
                "description": "Long prompt orchestration"
            },
            # 7. LoRA reload
            {
                "method": "POST",
                "endpoint": "/admin/reload",
                "json": {"lora": "models/math_adapter.bin"},
                "description": "LoRA model reload"
            },
            # 8. Soak test probe
            {
                "method": "POST",
                "endpoint": "/orchestrate",
                "json": {
                    "prompt": "test soak endpoint functionality",
                    "flags": ["FLAG_TEST"],
                    "temperature": 0.9
                },
                "description": "Soak test probe"
            },
            # 9. Error handling test
            {
                "method": "POST", 
                "endpoint": "/test/error",
                "description": "Intentional 5xx error test",
                "expect_error": True
            }
        ]
        
        results = []
        
        for i, test in enumerate(sanity_tests[:SOAK_CONFIG["sanity_call_count"]], 1):
            print(f"🔬 Sanity call {i}/10: {test['description']}")
            
            start_time = time.time()
            
            try:
                # Prepare request
                url = f"{base_url}{test['endpoint']}"
                method = test['method'].lower()
                kwargs = {
                    "timeout": SOAK_CONFIG["timeout"],
                    "headers": {"Content-Type": "application/json"}
                }
                
                if 'json' in test:
                    kwargs['json'] = test['json']
                
                # Make request
                response = getattr(requests, method)(url, **kwargs)
                
                response_time_ms = int((time.time() - start_time) * 1000)
                response_size = len(response.content)
                
                # Check if error was expected
                if test.get('expect_error', False):
                    if response.status_code >= 500:
                        print(f"✅ Expected error received: {response.status_code}")
                    else:
                        print(f"⚠️ Expected error but got: {response.status_code}")
                else:
                    response.raise_for_status()
                    print(f"✅ Success: {response.status_code} in {response_time_ms}ms")
                
                results.append(SoakResult(
                    endpoint=test['endpoint'],
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    response_size_bytes=response_size
                ))
                
            except Exception as e:
                print(f"❌ Failed: {e}")
                results.append(SoakResult(
                    endpoint=test['endpoint'],
                    status_code=0,
                    response_time_ms=0,
                    response_size_bytes=0,
                    error=str(e)
                ))
            
            # Small delay between calls
            time.sleep(0.5)
        
        return results
    
    def collect_metrics(self, base_url: str) -> Dict:
        """Collect final metrics after soak testing"""
        try:
            response = requests.get(f"{base_url}/metrics", timeout=10)
            metrics_text = response.text
            
            # Parse key metrics
            metrics = {
                "requests_total": 0,
                "errors_5xx": 0,
                "avg_duration": 0
            }
            
            for line in metrics_text.split('\n'):
                if 'swarm_api_requests_total' in line and 'status="200"' in line:
                    metrics["requests_total"] += float(line.split()[-1])
                elif 'swarm_api_5xx_total' in line:
                    metrics["errors_5xx"] += float(line.split()[-1])
            
            return metrics
            
        except Exception as e:
            print(f"⚠️ Metrics collection failed: {e}")
            return {}
    
    def tear_down_stack(self):
        """Clean up containers after testing"""
        print("🧹 Tearing down FastAPI stack...")
        
        try:
            result = subprocess.run([
                "docker-compose",
                "-f", "docker-compose.fastapi.yml", 
                "down", "-v"
            ], capture_output=True, text=True)
            
            print(f"✅ Stack torn down: {result.stdout}")
            
        except Exception as e:
            print(f"⚠️ Teardown warning: {e}")

# Pytest fixtures and tests
@pytest.fixture(scope="module")
def cursor_harness():
    """Setup and teardown the cursor test harness"""
    harness = CursorTestHarness()
    
    # Setup
    if not harness.spin_up_stack():
        pytest.fail("Failed to spin up FastAPI stack")
    
    yield harness
    
    # Teardown
    harness.tear_down_stack()

def test_api_health_checks(cursor_harness):
    """Test that all services become healthy"""
    main_healthy = cursor_harness.wait_for_health(SOAK_CONFIG["base_url"])
    canary_healthy = cursor_harness.wait_for_health(SOAK_CONFIG["canary_url"])
    
    assert main_healthy, "Main API service failed health check"
    assert canary_healthy, "Canary API service failed health check"

def test_main_api_sanity_calls(cursor_harness):
    """Test main API with 10 sanity calls"""
    results = cursor_harness.perform_sanity_calls(SOAK_CONFIG["base_url"])
    
    # Analyze results
    successful_calls = [r for r in results if r.error is None and r.status_code < 400]
    error_calls = [r for r in results if r.error is not None]
    expected_errors = [r for r in results if r.status_code >= 500 and '/test/error' in r.endpoint]
    
    print(f"\n📊 Sanity Test Results:")
    print(f"   ✅ Successful: {len(successful_calls)}")
    print(f"   ❌ Errors: {len(error_calls)}")
    print(f"   🧪 Expected errors: {len(expected_errors)}")
    
    # Calculate average response time
    valid_times = [r.response_time_ms for r in results if r.response_time_ms > 0]
    avg_response_time = sum(valid_times) / len(valid_times) if valid_times else 0
    
    print(f"   ⏱️ Average response time: {avg_response_time:.1f}ms")
    
    # Assertions
    assert len(successful_calls) >= 8, f"Expected at least 8 successful calls, got {len(successful_calls)}"
    assert avg_response_time <= 200, f"Average response time {avg_response_time}ms exceeds 200ms threshold"

def test_canary_api_basic_health(cursor_harness):
    """Test canary API basic functionality"""
    results = cursor_harness.perform_sanity_calls(SOAK_CONFIG["canary_url"])
    
    successful_calls = [r for r in results if r.error is None and r.status_code < 400]
    
    assert len(successful_calls) >= 6, f"Canary API failed basic sanity tests: {len(successful_calls)}/10"

def test_prometheus_metrics_collection(cursor_harness):
    """Test that metrics are properly collected"""
    metrics = cursor_harness.collect_metrics(SOAK_CONFIG["base_url"])
    
    assert metrics.get("requests_total", 0) > 0, "No requests recorded in metrics"
    print(f"📈 Collected {metrics.get('requests_total')} total requests")

if __name__ == "__main__":
    # Allow running directly for development
    harness = CursorTestHarness()
    
    try:
        if harness.spin_up_stack():
            if harness.wait_for_health(SOAK_CONFIG["base_url"]):
                results = harness.perform_sanity_calls(SOAK_CONFIG["base_url"])
                print(f"\n🎯 Direct run completed with {len(results)} calls")
            else:
                print("❌ Health checks failed")
        else:
            print("❌ Stack startup failed")
    finally:
        harness.tear_down_stack() 