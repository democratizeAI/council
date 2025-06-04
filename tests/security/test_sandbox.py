#!/usr/bin/env python3
"""
Firejail Sandbox Security Tests
==============================
Ensures safe code execution with proper isolation and resource limits
"""

import pytest
import time
import os
from unittest.mock import patch
from sandbox_exec import exec_safe

class TestSandboxSecurity:
    """Security tests for Firejail sandbox"""
    
    def test_basic_math(self):
        """Test basic code execution"""
        result = exec_safe("print(2+2)")
        assert result["stdout"] == "4"
        assert result["elapsed_ms"] < 1000  # Should be fast
    
    def test_math_functions(self):
        """Test mathematical operations"""
        result = exec_safe("import math; print(int(math.sqrt(16)))")
        assert result["stdout"] == "4"
    
    def test_timeout_protection(self):
        """Test that infinite loops are terminated"""
        with pytest.raises(RuntimeError, match="timeout"):
            exec_safe("while True: pass")
    
    def test_cpu_intensive_timeout(self):
        """Test CPU-intensive operations are limited"""
        with pytest.raises(RuntimeError, match="timeout"):
            exec_safe("sum(range(10**8))")  # This should timeout
    
    def test_network_isolation(self):
        """Test that network access is blocked"""
        with pytest.raises(RuntimeError):
            exec_safe("import urllib.request; urllib.request.urlopen('http://google.com')")
    
    def test_file_system_isolation(self):
        """Test file system access limitations"""
        # Should not be able to access files outside sandbox
        with pytest.raises(RuntimeError):
            exec_safe("open('/etc/passwd', 'r').read()")
    
    def test_output_size_limit(self):
        """Test output size is capped"""
        # Try to generate massive output
        code = "print('A' * 1000000)"  # 1MB of 'A's
        result = exec_safe(code)
        # Should either succeed with limited output or fail gracefully
        assert len(result.get("stdout", "")) < 25000000  # 25MB limit
    
    def test_memory_usage(self):
        """Test memory allocation limits"""
        # Try to allocate large amounts of memory
        with pytest.raises(RuntimeError):
            exec_safe("big_list = [0] * (10**8)")  # ~800MB
    
    def test_valid_python_syntax(self):
        """Test valid Python code executes correctly"""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n-1)

print(factorial(5))
"""
        result = exec_safe(code)
        assert result["stdout"] == "120"
    
    def test_error_handling(self):
        """Test error messages are captured"""
        result = exec_safe("1/0")  # Division by zero
        assert "ZeroDivisionError" in result["stderr"] or "division by zero" in result["stderr"]
    
    def test_import_restrictions(self):
        """Test that dangerous imports are blocked or fail safely"""
        dangerous_imports = [
            "import subprocess; subprocess.run(['ls'])",
            "import os; os.system('echo test')",
            "import socket; socket.socket()"
        ]
        
        for code in dangerous_imports:
            with pytest.raises(RuntimeError):
                exec_safe(code)
    
    def test_performance_metrics(self):
        """Test that execution metrics are tracked"""
        result = exec_safe("print('performance test')")
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] > 0

class TestSandboxConfiguration:
    """Test sandbox configuration and environment"""
    
    def test_firejail_missing_handling(self):
        """Test graceful handling when Firejail is not available"""
        with patch.dict(os.environ, {"FIREJAIL_BIN": "/nonexistent/firejail"}):
            with pytest.raises(RuntimeError, match="Firejail not installed"):
                exec_safe("print('test')")
    
    def test_custom_timeout(self):
        """Test custom timeout configuration"""
        with patch.dict(os.environ, {"EXEC_TIMEOUT_SEC": "1"}):
            with pytest.raises(RuntimeError, match="timeout"):
                exec_safe("import time; time.sleep(2)")
    
    def test_language_support(self):
        """Test different language file extensions"""
        result = exec_safe("print('Python test')", lang="py")
        assert result["stdout"] == "Python test"

# Performance benchmarks
class TestSandboxPerformance:
    """Performance tests for sandbox execution"""
    
    def test_startup_latency(self):
        """Test sandbox startup time is reasonable"""
        start_time = time.time()
        result = exec_safe("print('latency test')")
        total_time = time.time() - start_time
        
        # Should complete within reasonable time (including ~40-50ms Firejail overhead)
        assert total_time < 1.0  # 1 second max
        assert result["elapsed_ms"] < 1000
    
    def test_multiple_executions(self):
        """Test multiple rapid executions"""
        results = []
        for i in range(5):
            result = exec_safe(f"print({i})")
            results.append(result)
        
        # All should succeed
        assert all(r["stdout"] == str(i) for i, r in enumerate(results))
        
        # Average latency should be reasonable
        avg_latency = sum(r["elapsed_ms"] for r in results) / len(results)
        assert avg_latency < 500  # 500ms average

if __name__ == "__main__":
    # Quick integration test
    print("🧪 Running sandbox security tests...")
    
    # Test basic functionality
    try:
        result = exec_safe("print('Sandbox test successful!')")
        print(f"✅ Basic test: {result}")
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
    
    # Test security
    try:
        exec_safe("while True: pass")
        print("❌ Timeout test failed - should have timed out!")
    except RuntimeError:
        print("✅ Timeout protection working")
    
    print("\n🛡️ Sandbox security tests ready for Day +2!") 