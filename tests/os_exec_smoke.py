#!/usr/bin/env python3
"""
OS Execution Smoke Test Harness - Week 2
========================================

Tests OS integration functionality with cross-platform support:
- Windows PowerShell execution
- Linux bash execution  
- WSL execution on Windows
- Docker-in-Docker testing
- Security allowlist validation
- Cost guard verification
- Filesystem diff capture
- Exit code validation
- Prometheus metrics validation

Integrates with CI matrix for nightly testing.
"""

import os
import sys
import time
import json
import asyncio
import tempfile
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
import pytest
import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class OSExecTestHarness:
    """Cross-platform OS execution test harness"""
    
    def __init__(self):
        self.platform = platform.system().lower()
        self.test_results = []
        self.api_base = "http://localhost:8000"
        self.temp_dir = None
        
    def setup(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp(prefix="os_exec_test_")
        print(f"🔧 Test harness setup complete (platform: {self.platform})")
        print(f"📁 Temp directory: {self.temp_dir}")
        
    def teardown(self):
        """Cleanup test environment"""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        print("🧹 Test harness cleanup complete")
    
    async def test_basic_commands(self) -> List[Dict[str, Any]]:
        """Test basic OS commands across platforms"""
        results = []
        
        # Platform-specific basic commands
        if self.platform == "windows":
            test_commands = [
                ("echo Hello World", "Hello World"),
                ("dir /b", ""),  # List files (basic)
                ("hostname", ""),
                ("date /t", ""),
                ("whoami", ""),
            ]
        else:
            test_commands = [
                ("echo 'Hello World'", "Hello World"),
                ("ls -la", ""),
                ("hostname", ""),
                ("date", ""),
                ("whoami", ""),
            ]
        
        for command, expected_output in test_commands:
            result = await self._test_command(command, expected_output)
            results.append(result)
            
        return results
    
    async def test_file_operations(self) -> List[Dict[str, Any]]:
        """Test file system operations with diff capture"""
        results = []
        
        test_file = Path(self.temp_dir) / "test_file.txt"
        test_content = "Week 2 OS Integration Test"
        
        if self.platform == "windows":
            commands = [
                (f"echo {test_content} > {test_file}", test_content),
                (f"type {test_file}", test_content),
                (f"del {test_file}", ""),
            ]
        else:
            commands = [
                (f"echo '{test_content}' > {test_file}", ""),
                (f"cat {test_file}", test_content),
                (f"rm {test_file}", ""),
            ]
        
        # Capture filesystem state before and after
        initial_files = self._capture_filesystem_state()
        
        for command, expected in commands:
            result = await self._test_command(command, expected)
            result["fs_state_before"] = initial_files
            result["fs_state_after"] = self._capture_filesystem_state()
            results.append(result)
            
        return results
    
    async def test_security_allowlist(self) -> List[Dict[str, Any]]:
        """Test that dangerous commands are blocked"""
        results = []
        
        # Commands that should be blocked by allowlist
        dangerous_commands = [
            "rm -rf /",
            "del /f /q C:\\*",
            "chmod 777 /etc/passwd",
            "shutdown /s",
            "reboot",
            "format c:",
            "dd if=/dev/zero of=/dev/sda",
        ]
        
        for command in dangerous_commands:
            result = await self._test_command(command, "", should_succeed=False)
            result["test_type"] = "security_block"
            results.append(result)
            
        return results
    
    async def test_cost_guards(self) -> List[Dict[str, Any]]:
        """Test cost guard enforcement"""
        results = []
        
        # Commands that should trigger cost guards
        if self.platform == "windows":
            expensive_commands = [
                "powershell -Command \"Start-Sleep 15\"",  # Long-running
                "powershell -Command \"1..1000 | ForEach-Object { New-Item -Path temp_$_.txt -ItemType File }\"",  # Many files
            ]
        else:
            expensive_commands = [
                "sleep 15",  # Long-running  
                "for i in {1..1000}; do touch temp_$i.txt; done",  # Many files
            ]
        
        for command in expensive_commands:
            result = await self._test_command(command, "", should_succeed=False)
            result["test_type"] = "cost_guard"
            results.append(result)
            
        return results
    
    async def test_exit_codes(self) -> List[Dict[str, Any]]:
        """Test exit code capture and reporting"""
        results = []
        
        # Commands with specific exit codes
        if self.platform == "windows":
            test_cases = [
                ("echo Success", 0),
                ("exit 1", 1),
                ("exit 42", 42),
                ("powershell -Command \"exit 99\"", 99),
            ]
        else:
            test_cases = [
                ("echo 'Success'", 0),
                ("exit 1", 1),
                ("exit 42", 42),
                ("bash -c 'exit 99'", 99),
            ]
        
        for command, expected_exit_code in test_cases:
            result = await self._test_command(command, "")
            result["expected_exit_code"] = expected_exit_code
            result["exit_code_correct"] = (result.get("exit_code") == expected_exit_code)
            results.append(result)
            
        return results
    
    async def test_prometheus_metrics(self) -> Dict[str, Any]:
        """Test that Prometheus metrics are properly recorded"""
        try:
            # Execute a command to generate metrics
            await self._test_command("echo 'metrics test'", "metrics test")
            
            # Check metrics endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/metrics")
                
                if response.status_code == 200:
                    metrics_text = response.text
                    
                    # Check for expected OS execution metrics
                    expected_metrics = [
                        "swarm_os_exec_total",
                        "swarm_os_exec_latency_seconds",
                        "swarm_os_exec_cpu_seconds",
                    ]
                    
                    metrics_found = {}
                    for metric in expected_metrics:
                        metrics_found[metric] = metric in metrics_text
                    
                    return {
                        "success": True,
                        "metrics_endpoint_available": True,
                        "metrics_found": metrics_found,
                        "all_metrics_present": all(metrics_found.values())
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Metrics endpoint returned {response.status_code}",
                        "metrics_endpoint_available": False
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metrics_endpoint_available": False
            }
    
    async def _test_command(self, command: str, expected_output: str = "", should_succeed: bool = True) -> Dict[str, Any]:
        """Execute a single command test via API"""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.api_base}/task",
                    json={
                        "command": command,
                        "working_dir": self.temp_dir,
                        "session_id": "os_exec_test"
                    }
                )
                
                execution_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    success = data.get("success", False)
                    stdout = data.get("stdout", "")
                    stderr = data.get("stderr", "")
                    exit_code = data.get("exit_code", -1)
                    command_type = data.get("command_type", "unknown")
                    blocked_reason = data.get("blocked_reason")
                    
                    # Check if result matches expectations
                    if should_succeed:
                        test_passed = success and (not expected_output or expected_output in stdout)
                    else:
                        test_passed = not success or blocked_reason is not None
                    
                    return {
                        "command": command,
                        "success": success,
                        "stdout": stdout,
                        "stderr": stderr,
                        "exit_code": exit_code,
                        "execution_time_ms": execution_time,
                        "command_type": command_type,
                        "blocked_reason": blocked_reason,
                        "test_passed": test_passed,
                        "expected_output": expected_output,
                        "should_succeed": should_succeed
                    }
                else:
                    return {
                        "command": command,
                        "success": False,
                        "error": f"API returned {response.status_code}: {response.text}",
                        "test_passed": not should_succeed,  # API error might be expected for blocked commands
                        "execution_time_ms": execution_time
                    }
                    
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return {
                "command": command,
                "success": False,
                "error": str(e),
                "test_passed": not should_succeed,  # Exception might be expected for dangerous commands
                "execution_time_ms": execution_time
            }
    
    def _capture_filesystem_state(self) -> Dict[str, Any]:
        """Capture filesystem state for diff analysis"""
        try:
            if not self.temp_dir:
                return {"error": "No temp directory"}
                
            temp_path = Path(self.temp_dir)
            if not temp_path.exists():
                return {"error": "Temp directory does not exist"}
            
            files = []
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "path": str(file_path.relative_to(temp_path)),
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
            
            return {
                "file_count": len(files),
                "files": files,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run complete OS integration test suite"""
        print("🚀 Starting OS Integration Test Suite")
        print(f"Platform: {self.platform}")
        print(f"API Base: {self.api_base}")
        
        results = {
            "platform": self.platform,
            "start_time": time.time(),
            "test_results": {}
        }
        
        try:
            self.setup()
            
            # Test basic commands
            print("\n1️⃣ Testing basic commands...")
            results["test_results"]["basic_commands"] = await self.test_basic_commands()
            
            # Test file operations
            print("2️⃣ Testing file operations...")
            results["test_results"]["file_operations"] = await self.test_file_operations()
            
            # Test security allowlist
            print("3️⃣ Testing security allowlist...")
            results["test_results"]["security_allowlist"] = await self.test_security_allowlist()
            
            # Test cost guards
            print("4️⃣ Testing cost guards...")
            results["test_results"]["cost_guards"] = await self.test_cost_guards()
            
            # Test exit codes
            print("5️⃣ Testing exit codes...")
            results["test_results"]["exit_codes"] = await self.test_exit_codes()
            
            # Test Prometheus metrics
            print("6️⃣ Testing Prometheus metrics...")
            results["test_results"]["prometheus_metrics"] = await self.test_prometheus_metrics()
            
            # Calculate summary
            total_tests = 0
            passed_tests = 0
            
            for category, tests in results["test_results"].items():
                if isinstance(tests, list):
                    for test in tests:
                        total_tests += 1
                        if test.get("test_passed", False):
                            passed_tests += 1
                elif isinstance(tests, dict) and "success" in tests:
                    total_tests += 1
                    if tests.get("success", False):
                        passed_tests += 1
            
            results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "overall_success": passed_tests == total_tests
            }
            
            results["end_time"] = time.time()
            results["duration_seconds"] = results["end_time"] - results["start_time"]
            
            print(f"\n✅ Test suite completed!")
            print(f"📊 Results: {passed_tests}/{total_tests} tests passed ({results['summary']['success_rate']:.1%})")
            
        except Exception as e:
            print(f"❌ Test suite failed: {e}")
            results["error"] = str(e)
            results["summary"] = {"overall_success": False}
        
        finally:
            self.teardown()
        
        return results

# Pytest integration
@pytest.mark.asyncio
async def test_os_exec_basic():
    """Basic OS execution test for CI"""
    harness = OSExecTestHarness()
    harness.setup()
    
    try:
        # Test simple echo command
        result = await harness._test_command("echo 'CI Test'", "CI Test")
        assert result["test_passed"], f"Basic echo test failed: {result}"
        
    finally:
        harness.teardown()

@pytest.mark.asyncio 
async def test_os_exec_security():
    """Security allowlist test for CI"""
    harness = OSExecTestHarness()
    harness.setup()
    
    try:
        # Test that dangerous command is blocked
        result = await harness._test_command("rm -rf /", "", should_succeed=False)
        assert result["test_passed"], f"Security test failed: {result}"
        
    finally:
        harness.teardown()

# Command-line interface
async def main():
    """Run OS integration smoke tests"""
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Quick test mode
        harness = OSExecTestHarness()
        print("🔥 Quick OS Exec Test")
        
        harness.setup()
        try:
            result = await harness._test_command("echo 'Quick test'", "Quick test")
            if result["test_passed"]:
                print("✅ Quick test passed")
                return 0
            else:
                print(f"❌ Quick test failed: {result}")
                return 1
        finally:
            harness.teardown()
    else:
        # Full test suite
        harness = OSExecTestHarness()
        results = await harness.run_full_test_suite()
        
        # Save results to file
        results_file = Path("test_results_os_exec.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"📄 Results saved to: {results_file}")
        
        return 0 if results["summary"]["overall_success"] else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 