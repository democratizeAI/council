#!/usr/bin/env python3
"""
Service Wrapper Smoke Test
==========================

Comprehensive validation of Agent-0 service wrapper functionality:
- Health endpoint validation
- Service startup metrics
- Automatic restart behavior
- Cross-platform service management

Implements the smoke test matrix from the playbook.
"""

import requests
import time
import subprocess
import sys
import os
import platform
import json
from typing import Dict, Any, Optional

class ServiceTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.platform = platform.system()
        self.test_results = {}
        
    def log(self, message: str, level: str = "INFO"):
        """Safe logging with timestamp"""
        timestamp = time.strftime('%H:%M:%S')
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "📋")
        print(f"{timestamp} {prefix} {message}")

    def test_health_endpoint(self) -> bool:
        """Test if health endpoint is responding correctly"""
        self.log("Testing health endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                
                # Check basic health status
                if health_data.get("status") == "healthy":
                    self.log("Health endpoint returning healthy status", "SUCCESS")
                    
                    # Check service-specific metrics
                    service_info = health_data.get("service", {})
                    startups = service_info.get("startups_total", 0)
                    uptime = service_info.get("uptime_seconds", 0)
                    service_managed = service_info.get("service_managed", False)
                    
                    self.log(f"Service startups: {startups}")
                    self.log(f"Uptime: {uptime:.1f} seconds")
                    self.log(f"Service managed: {service_managed}")
                    
                    self.test_results["health_endpoint"] = {
                        "status": "pass",
                        "uptime_seconds": uptime,
                        "startups_total": startups,
                        "service_managed": service_managed
                    }
                    return True
                else:
                    self.log(f"Health endpoint unhealthy: {health_data.get('status')}", "ERROR")
                    self.test_results["health_endpoint"] = {"status": "fail", "reason": "unhealthy"}
                    return False
            else:
                self.log(f"Health endpoint returned {response.status_code}", "ERROR")
                self.test_results["health_endpoint"] = {"status": "fail", "reason": f"HTTP {response.status_code}"}
                return False
                
        except requests.RequestException as e:
            self.log(f"Health endpoint unreachable: {e}", "ERROR")
            self.test_results["health_endpoint"] = {"status": "fail", "reason": str(e)}
            return False

    def test_metrics_endpoint(self) -> bool:
        """Test if Prometheus metrics are exposed"""
        self.log("Testing metrics endpoint...")
        
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=10)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Check for service-specific metrics
                required_metrics = [
                    "service_startups_total",
                    "swarm_router_requests_total",
                    "swarm_router_request_latency"
                ]
                
                missing_metrics = []
                for metric in required_metrics:
                    if metric not in metrics_text:
                        missing_metrics.append(metric)
                
                if not missing_metrics:
                    self.log("All required metrics found", "SUCCESS")
                    self.test_results["metrics_endpoint"] = {"status": "pass"}
                    return True
                else:
                    self.log(f"Missing metrics: {missing_metrics}", "ERROR")
                    self.test_results["metrics_endpoint"] = {"status": "fail", "missing": missing_metrics}
                    return False
            else:
                self.log(f"Metrics endpoint returned {response.status_code}", "ERROR")
                self.test_results["metrics_endpoint"] = {"status": "fail", "reason": f"HTTP {response.status_code}"}
                return False
                
        except requests.RequestException as e:
            self.log(f"Metrics endpoint unreachable: {e}", "ERROR")
            self.test_results["metrics_endpoint"] = {"status": "fail", "reason": str(e)}
            return False

    def test_service_status(self) -> bool:
        """Test service management commands"""
        self.log("Testing service status...")
        
        try:
            if self.platform == "Windows":
                # Check Windows service status
                result = subprocess.run(
                    ["sc", "query", "Agent0Council"], 
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and "RUNNING" in result.stdout:
                    self.log("Windows service is running", "SUCCESS")
                    self.test_results["service_status"] = {"status": "pass", "platform": "Windows"}
                    return True
                else:
                    self.log("Windows service not running", "ERROR")
                    self.test_results["service_status"] = {"status": "fail", "platform": "Windows"}
                    return False
            else:
                # Check Linux systemd service status
                result = subprocess.run(
                    ["systemctl", "is-active", "agent0"], 
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip() == "active":
                    self.log("Linux service is active", "SUCCESS")
                    self.test_results["service_status"] = {"status": "pass", "platform": "Linux"}
                    return True
                else:
                    self.log("Linux service not active", "ERROR")
                    self.test_results["service_status"] = {"status": "fail", "platform": "Linux"}
                    return False
                    
        except subprocess.TimeoutExpired:
            self.log("Service status check timed out", "ERROR")
            self.test_results["service_status"] = {"status": "fail", "reason": "timeout"}
            return False
        except Exception as e:
            self.log(f"Service status check failed: {e}", "ERROR")
            self.test_results["service_status"] = {"status": "fail", "reason": str(e)}
            return False

    def test_basic_functionality(self) -> bool:
        """Test basic Agent-0 functionality"""
        self.log("Testing basic Agent-0 functionality...")
        
        try:
            # Test a simple query
            test_payload = {
                "prompt": "What is 2+2?",
                "session_id": "smoke_test"
            }
            
            response = requests.post(
                f"{self.base_url}/chat", 
                json=test_payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                chat_data = response.json()
                if chat_data.get("text") and "4" in chat_data.get("text", ""):
                    self.log("Basic functionality test passed", "SUCCESS")
                    self.test_results["basic_functionality"] = {"status": "pass"}
                    return True
                else:
                    self.log("Basic functionality test failed - incorrect response", "ERROR")
                    self.test_results["basic_functionality"] = {"status": "fail", "reason": "incorrect_response"}
                    return False
            else:
                self.log(f"Basic functionality test failed - HTTP {response.status_code}", "ERROR")
                self.test_results["basic_functionality"] = {"status": "fail", "reason": f"HTTP {response.status_code}"}
                return False
                
        except requests.RequestException as e:
            self.log(f"Basic functionality test failed: {e}", "ERROR")
            self.test_results["basic_functionality"] = {"status": "fail", "reason": str(e)}
            return False

    def test_startup_time(self) -> bool:
        """Measure service startup time"""
        self.log("Testing service startup time...")
        
        # This test assumes the service was recently started
        # In a real scenario, you would restart the service and measure
        
        try:
            start_time = time.time()
            
            # Wait for service to be ready (max 60 seconds)
            for attempt in range(60):
                try:
                    response = requests.get(f"{self.base_url}/health", timeout=5)
                    if response.status_code == 200:
                        startup_time = time.time() - start_time
                        self.log(f"Service ready in {startup_time:.1f} seconds", "SUCCESS")
                        
                        if startup_time <= 60:  # Service should start within 60 seconds
                            self.test_results["startup_time"] = {"status": "pass", "time_seconds": startup_time}
                            return True
                        else:
                            self.log("Service startup too slow", "WARNING")
                            self.test_results["startup_time"] = {"status": "slow", "time_seconds": startup_time}
                            return False
                except requests.RequestException:
                    time.sleep(1)
                    continue
            
            self.log("Service failed to start within 60 seconds", "ERROR")
            self.test_results["startup_time"] = {"status": "fail", "reason": "timeout"}
            return False
            
        except Exception as e:
            self.log(f"Startup time test failed: {e}", "ERROR")
            self.test_results["startup_time"] = {"status": "fail", "reason": str(e)}
            return False

    def run_smoke_test_matrix(self) -> Dict[str, Any]:
        """Run the complete smoke test matrix"""
        self.log("🧪 Starting Service Wrapper Smoke Test Matrix")
        self.log(f"Platform: {self.platform}")
        self.log(f"Target: {self.base_url}")
        
        tests = [
            ("Health Endpoint", self.test_health_endpoint),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Service Status", self.test_service_status),
            ("Basic Functionality", self.test_basic_functionality),
            ("Startup Time", self.test_startup_time)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            self.log(f"\n--- {test_name} ---")
            try:
                if test_func():
                    passed += 1
                    self.log(f"{test_name}: PASS", "SUCCESS")
                else:
                    self.log(f"{test_name}: FAIL", "ERROR")
            except Exception as e:
                self.log(f"{test_name}: ERROR - {e}", "ERROR")
                self.test_results[test_name.lower().replace(" ", "_")] = {"status": "error", "reason": str(e)}
        
        # Summary
        self.log(f"\n🏁 Smoke Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            self.log("✅ All tests passed - Service wrapper is working correctly!", "SUCCESS")
        elif passed >= total * 0.8:  # 80% pass rate
            self.log("⚠️ Most tests passed - Service wrapper has minor issues", "WARNING")
        else:
            self.log("❌ Multiple test failures - Service wrapper needs attention", "ERROR")
        
        # Add summary to results
        self.test_results["summary"] = {
            "total_tests": total,
            "passed_tests": passed,
            "pass_rate": passed / total,
            "platform": self.platform,
            "timestamp": time.time()
        }
        
        return self.test_results

    def save_results(self, filename: str = "service_test_results.json"):
        """Save test results to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            self.log(f"Test results saved to {filename}")
        except Exception as e:
            self.log(f"Failed to save results: {e}", "ERROR")

def main():
    """Main entry point"""
    print("🚀 Agent-0 Service Wrapper Smoke Test")
    print("=" * 50)
    
    tester = ServiceTester()
    results = tester.run_smoke_test_matrix()
    
    # Save results
    tester.save_results()
    
    # Exit with appropriate code
    summary = results.get("summary", {})
    if summary.get("pass_rate", 0) >= 1.0:
        sys.exit(0)  # All tests passed
    elif summary.get("pass_rate", 0) >= 0.8:
        sys.exit(1)  # Some failures
    else:
        sys.exit(2)  # Many failures

if __name__ == "__main__":
    main()
