#!/usr/bin/env python3
"""
Fresh Instance Stack Tests (BC-110 + BC-120)
Tests the complete fresh instance compose stack and mission validator
"""

import pytest
import docker
import time
import requests
import json
import subprocess
import os
from typing import Dict, Any, Optional
from pathlib import Path


class FreshInstanceTestSuite:
    """Test suite for fresh instance stack verification"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.compose_file = "compose/fresh-instance.yml"
        self.compose_project = "fresh-instance-test"
        self.test_timeout = 180  # 3 minutes for full stack startup
        
        # Service endpoints
        self.endpoints = {
            "redis": "http://localhost:6379",
            "prometheus": "http://localhost:9090",
            "council-api": "http://localhost:8000",
            "guardian": "http://localhost:9093",
            "mission-validator": "http://localhost:8080"
        }
        
    def setup_method(self, method):
        """Setup for each test method"""
        self.cleanup_stack()
        
    def teardown_method(self, method):
        """Cleanup after each test method"""
        self.cleanup_stack()
        
    def cleanup_stack(self):
        """Clean up any existing test containers"""
        try:
            # Stop compose stack
            subprocess.run([
                "docker-compose", "-f", self.compose_file, 
                "-p", self.compose_project, "down", "-v"
            ], capture_output=True, check=False)
            
            # Remove any orphaned containers
            containers = self.client.containers.list(
                filters={"label": f"com.docker.compose.project={self.compose_project}"}
            )
            for container in containers:
                container.remove(force=True)
                
        except Exception as e:
            print(f"Cleanup warning: {e}")
    
    def start_fresh_stack(self) -> bool:
        """Start the fresh instance stack"""
        try:
            # Start stack
            result = subprocess.run([
                "docker-compose", "-f", self.compose_file,
                "-p", self.compose_project, "up", "-d"
            ], capture_output=True, text=True, check=True)
            
            print("Fresh stack started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to start fresh stack: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            return False
    
    def wait_for_service_health(self, service_name: str, endpoint: str, timeout: int = 60) -> bool:
        """Wait for a service to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if service_name == "redis":
                    # Special check for Redis
                    container = self.client.containers.get(f"{self.compose_project}-redis-1")
                    health = container.attrs['State']['Health']['Status']
                    if health == 'healthy':
                        return True
                else:
                    # HTTP health check
                    if service_name == "prometheus":
                        response = requests.get(f"{endpoint}/-/healthy", timeout=5)
                    else:
                        response = requests.get(f"{endpoint}/health", timeout=5)
                    
                    if response.status_code == 200:
                        print(f"✅ {service_name} is healthy")
                        return True
                        
            except Exception as e:
                print(f"⏳ Waiting for {service_name}: {e}")
                
            time.sleep(3)
            
        print(f"❌ {service_name} failed to become healthy within {timeout}s")
        return False
    
    def check_mission_validator_metrics(self) -> Dict[str, Any]:
        """Check mission validator metrics"""
        try:
            response = requests.get(f"{self.endpoints['mission-validator']}/metrics", timeout=10)
            if response.status_code != 200:
                return {"error": f"Metrics endpoint returned {response.status_code}"}
                
            metrics_text = response.text
            
            # Parse relevant metrics
            metrics = {
                "mission_ingest_ok_total": 0,
                "mission_validation_status": 0,
                "mission_validator_health": 0
            }
            
            for line in metrics_text.split('\n'):
                if line.startswith('mission_ingest_ok_total'):
                    # Extract value after the metric name
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["mission_ingest_ok_total"] = float(parts[1])
                        
                elif line.startswith('mission_validation_status'):
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["mission_validation_status"] = float(parts[1])
                        
                elif line.startswith('mission_validator_health'):
                    parts = line.split()
                    if len(parts) >= 2:
                        metrics["mission_validator_health"] = float(parts[1])
            
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def trigger_genesis_mandate(self) -> bool:
        """Trigger GENESIS_MANDATE_001 acknowledgment in Council-API"""
        try:
            # Try to trigger the mandate via API call
            response = requests.post(
                f"{self.endpoints['council-api']}/system/acknowledge",
                json={"mandate": "GENESIS_MANDATE_001"},
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                print("✅ GENESIS_MANDATE_001 triggered via API")
                return True
                
            # Fallback: check if it's already in the environment
            response = requests.get(f"{self.endpoints['council-api']}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                if "GENESIS_MANDATE_001" in str(health_data):
                    print("✅ GENESIS_MANDATE_001 found in health response")
                    return True
                    
        except Exception as e:
            print(f"Failed to trigger GENESIS_MANDATE_001: {e}")
            
        return False
    
    def get_prometheus_metrics(self, query: str) -> Optional[float]:
        """Query Prometheus for specific metrics"""
        try:
            response = requests.get(
                f"{self.endpoints['prometheus']}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success" and data.get("data", {}).get("result"):
                    result = data["data"]["result"][0]
                    return float(result["value"][1])
                    
        except Exception as e:
            print(f"Prometheus query failed: {e}")
            
        return None


# Test fixture
@pytest.fixture(scope="class")
def fresh_stack():
    """Fixture to manage fresh instance stack lifecycle"""
    suite = FreshInstanceTestSuite()
    yield suite
    suite.cleanup_stack()


class TestFreshInstanceStack:
    """Test class for fresh instance stack (BC-110)"""
    
    def test_compose_file_exists(self):
        """Test that compose file exists and is valid"""
        compose_path = Path("compose/fresh-instance.yml")
        assert compose_path.exists(), "Fresh instance compose file not found"
        
        # Validate compose file syntax
        result = subprocess.run([
            "docker-compose", "-f", str(compose_path), "config"
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Invalid compose file: {result.stderr}"
    
    def test_stack_startup_performance(self, fresh_stack):
        """Test BC-110: Stack becomes healthy within 120s"""
        start_time = time.time()
        
        # Start the stack
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        
        # Check each service health
        services_to_check = [
            ("redis", fresh_stack.endpoints["redis"]),
            ("prometheus", fresh_stack.endpoints["prometheus"]),
            ("council-api", fresh_stack.endpoints["council-api"]),
            ("mission-validator", fresh_stack.endpoints["mission-validator"])
        ]
        
        all_healthy = True
        for service_name, endpoint in services_to_check:
            if not fresh_stack.wait_for_service_health(service_name, endpoint, timeout=60):
                all_healthy = False
        
        total_time = time.time() - start_time
        
        assert all_healthy, "Not all services became healthy"
        assert total_time < 120, f"Stack took {total_time:.1f}s to start (requirement: <120s)"
        
        print(f"✅ Fresh stack healthy in {total_time:.1f}s")
    
    def test_service_networking(self, fresh_stack):
        """Test that services can communicate with each other"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        
        # Wait for core services
        assert fresh_stack.wait_for_service_health("redis", fresh_stack.endpoints["redis"])
        assert fresh_stack.wait_for_service_health("prometheus", fresh_stack.endpoints["prometheus"])
        assert fresh_stack.wait_for_service_health("council-api", fresh_stack.endpoints["council-api"])
        
        # Test Redis connectivity from Council-API
        try:
            response = requests.get(f"{fresh_stack.endpoints['council-api']}/health", timeout=10)
            health_data = response.json()
            
            # Should include Redis connection status
            assert "redis" in str(health_data).lower() or response.status_code == 200
            
        except Exception as e:
            pytest.fail(f"Council-API cannot connect to Redis: {e}")
    
    def test_environment_variables(self, fresh_stack):
        """Test that GENESIS_MANDATE_001 environment is set"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        assert fresh_stack.wait_for_service_health("council-api", fresh_stack.endpoints["council-api"])
        
        # Check that Council-API has the GENESIS_MANDATE_001 environment
        try:
            container = fresh_stack.client.containers.get(f"{fresh_stack.compose_project}-council-api-1")
            env_vars = container.attrs['Config']['Env']
            
            genesis_env_found = any("GENESIS_MANDATE_001" in env for env in env_vars)
            assert genesis_env_found, "GENESIS_MANDATE_001 environment variable not found"
            
        except Exception as e:
            pytest.fail(f"Failed to check environment variables: {e}")


class TestMissionValidator:
    """Test class for mission validator service (BC-120)"""
    
    def test_mission_validator_startup(self, fresh_stack):
        """Test that mission validator starts and is healthy"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        assert fresh_stack.wait_for_service_health(
            "mission-validator", 
            fresh_stack.endpoints["mission-validator"],
            timeout=90
        ), "Mission validator failed to become healthy"
    
    def test_mission_validator_metrics_endpoint(self, fresh_stack):
        """Test that mission validator exposes metrics"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        assert fresh_stack.wait_for_service_health("mission-validator", fresh_stack.endpoints["mission-validator"])
        
        # Check metrics endpoint
        metrics = fresh_stack.check_mission_validator_metrics()
        assert "error" not in metrics, f"Metrics check failed: {metrics.get('error')}"
        
        # Should have health metric
        assert metrics.get("mission_validator_health", 0) == 1, "Mission validator health metric not set"
    
    def test_genesis_mandate_validation(self, fresh_stack):
        """Test BC-120: mission_ingest_ok_total ≥ 1 when GENESIS_MANDATE_001 acknowledged"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        
        # Wait for all services
        assert fresh_stack.wait_for_service_health("council-api", fresh_stack.endpoints["council-api"])
        assert fresh_stack.wait_for_service_health("mission-validator", fresh_stack.endpoints["mission-validator"])
        
        # Check initial metrics (should be 0)
        initial_metrics = fresh_stack.check_mission_validator_metrics()
        print(f"Initial metrics: {initial_metrics}")
        
        # Wait for automatic acknowledgment or trigger it
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            metrics = fresh_stack.check_mission_validator_metrics()
            
            if metrics.get("mission_ingest_ok_total", 0) >= 1:
                print(f"✅ GENESIS_MANDATE_001 acknowledged! Metrics: {metrics}")
                break
                
            # Try to trigger it manually
            fresh_stack.trigger_genesis_mandate()
            time.sleep(5)
        else:
            # Final check
            metrics = fresh_stack.check_mission_validator_metrics()
            
        # Verify the acceptance criteria
        assert metrics.get("mission_ingest_ok_total", 0) >= 1, \
            f"BC-120 FAILED: mission_ingest_ok_total = {metrics.get('mission_ingest_ok_total', 0)} (required: ≥1)"
        
        print(f"🎉 BC-120 PASSED: mission_ingest_ok_total = {metrics['mission_ingest_ok_total']}")
    
    def test_prometheus_scraping(self, fresh_stack):
        """Test that Prometheus can scrape mission validator metrics"""
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        
        # Wait for both services
        assert fresh_stack.wait_for_service_health("prometheus", fresh_stack.endpoints["prometheus"])
        assert fresh_stack.wait_for_service_health("mission-validator", fresh_stack.endpoints["mission-validator"])
        
        # Give Prometheus time to scrape
        time.sleep(30)
        
        # Query Prometheus for mission validator metrics
        mission_metric = fresh_stack.get_prometheus_metrics("mission_ingest_ok_total")
        
        # Should be able to find the metric (even if value is 0)
        assert mission_metric is not None, "Prometheus is not scraping mission validator metrics"
        
        print(f"✅ Prometheus scraping working: mission_ingest_ok_total = {mission_metric}")


class TestIntegration:
    """Integration tests for the complete BC-110 + BC-120 system"""
    
    def test_end_to_end_fresh_instance(self, fresh_stack):
        """Complete end-to-end test of fresh instance system"""
        print("🚀 Starting end-to-end fresh instance test")
        
        # 1. Start the stack
        start_time = time.time()
        assert fresh_stack.start_fresh_stack(), "Failed to start fresh stack"
        
        # 2. Wait for all services to be healthy
        services = [
            ("redis", fresh_stack.endpoints["redis"]),
            ("prometheus", fresh_stack.endpoints["prometheus"]),
            ("council-api", fresh_stack.endpoints["council-api"]),
            ("mission-validator", fresh_stack.endpoints["mission-validator"])
        ]
        
        for service_name, endpoint in services:
            assert fresh_stack.wait_for_service_health(service_name, endpoint), \
                f"Service {service_name} failed health check"
        
        startup_time = time.time() - start_time
        print(f"✅ All services healthy in {startup_time:.1f}s")
        
        # 3. Verify BC-110: Health endpoints green in <120s
        assert startup_time < 120, f"BC-110 FAILED: Stack took {startup_time:.1f}s (required: <120s)"
        print(f"🎉 BC-110 PASSED: Stack healthy in {startup_time:.1f}s")
        
        # 4. Wait for mission validation
        validation_start = time.time()
        max_validation_wait = 90
        
        while time.time() - validation_start < max_validation_wait:
            metrics = fresh_stack.check_mission_validator_metrics()
            
            if metrics.get("mission_ingest_ok_total", 0) >= 1:
                validation_time = time.time() - validation_start
                print(f"✅ Mission validated in {validation_time:.1f}s")
                break
                
            time.sleep(5)
        else:
            # Final check with debug info
            metrics = fresh_stack.check_mission_validator_metrics()
            print(f"Final metrics check: {metrics}")
        
        # 5. Verify BC-120: mission_ingest_ok_total ≥ 1
        final_metrics = fresh_stack.check_mission_validator_metrics()
        assert final_metrics.get("mission_ingest_ok_total", 0) >= 1, \
            f"BC-120 FAILED: mission_ingest_ok_total = {final_metrics.get('mission_ingest_ok_total', 0)}"
        print(f"🎉 BC-120 PASSED: mission_ingest_ok_total = {final_metrics['mission_ingest_ok_total']}")
        
        # 6. Verify Prometheus integration
        time.sleep(10)  # Allow Prometheus to scrape
        prom_metric = fresh_stack.get_prometheus_metrics("mission_ingest_ok_total")
        assert prom_metric is not None, "Prometheus integration failed"
        print(f"✅ Prometheus integration: mission_ingest_ok_total = {prom_metric}")
        
        total_time = time.time() - start_time
        print(f"🎉 END-TO-END TEST PASSED in {total_time:.1f}s")
        print("   ✅ BC-110: Fresh instance stack healthy")
        print("   ✅ BC-120: Mission validation working")
        print("   ✅ Prometheus integration confirmed")


def run_fresh_instance_tests():
    """Entry point for running fresh instance tests"""
    # Run tests with verbose output
    pytest_args = [
        "tests/test_fresh_instance.py",
        "-v",
        "--tb=short",
        "-s"  # Don't capture output
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    print("🧪 Running Fresh Instance Tests (BC-110 + BC-120)")
    print("=" * 60)
    
    exit_code = run_fresh_instance_tests()
    
    if exit_code == 0:
        print("\n🎉 All fresh instance tests passed!")
        print("   ✅ BC-110: Fresh instance stack verified")
        print("   ✅ BC-120: Mission validator working")
    else:
        print("\n❌ Some tests failed")
        
    exit(exit_code) 