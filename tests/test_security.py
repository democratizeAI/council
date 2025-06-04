"""Security tests for sandbox execution system"""
import pytest
import time
import os
from pathlib import Path

# Skip all tests if Firejail is not available
pytestmark = pytest.mark.skipif(
    not Path("/usr/bin/firejail").exists() and not Path("/bin/firejail").exists(),
    reason="Firejail not available - expected on Windows/development"
)

from sandbox_exec import exec_safe


class TestSandboxSecurity:
    """Test security isolation and resource limits"""
    
    def test_basic_execution(self):
        """Test basic code execution works"""
        result = exec_safe("print('hello sandbox')")
        assert result["stdout"] == "hello sandbox"
        assert result["stderr"] == ""
        assert result["elapsed_ms"] > 0
    
    def test_math_calculation(self):
        """Test mathematical computations"""
        result = exec_safe("print(sum(range(100)))")
        assert result["stdout"] == "4950"
        assert result["elapsed_ms"] < 1000  # Should be fast
    
    def test_network_isolation(self):
        """Test that network access is blocked"""
        code = """
import socket
try:
    socket.create_connection(('8.8.8.8', 53), timeout=1)
    print('FAIL: Network accessible')
except:
    print('PASS: Network blocked')
"""
        result = exec_safe(code)
        assert "PASS: Network blocked" in result["stdout"]
    
    def test_filesystem_isolation(self):
        """Test that filesystem is private"""
        code = """
import os
try:
    files = os.listdir('/home')
    print(f'FAIL: Can access /home: {files}')
except:
    print('PASS: Filesystem isolated')
"""
        result = exec_safe(code)
        assert "PASS: Filesystem isolated" in result["stdout"]
    
    def test_timeout_protection(self):
        """Test that infinite loops are killed"""
        code = """
import time
time.sleep(10)  # Should timeout before completing
print('FAIL: Timeout not enforced')
"""
        with pytest.raises(RuntimeError, match="timed out"):
            exec_safe(code)
    
    def test_dangerous_imports_blocked(self):
        """Test that dangerous operations fail safely"""
        dangerous_code = """
import subprocess
subprocess.run(['rm', '-rf', '/tmp/test'], capture_output=True)
print('DANGER: File operations succeeded')
"""
        # Should either fail due to isolation or missing commands
        try:
            result = exec_safe(dangerous_code)
            # If it runs, should not affect host filesystem
            assert "DANGER" not in result["stdout"]
        except RuntimeError:
            # Expected - dangerous operations should fail
            pass
    
    def test_resource_limits(self):
        """Test CPU and memory limits"""
        code = """
# Try to consume CPU
import time
start = time.time()
count = 0
while time.time() - start < 3:  # Try for 3 seconds
    count += 1
print(f'Completed {count} iterations')
"""
        result = exec_safe(code)
        # Should complete but with reasonable resource usage
        assert "Completed" in result["stdout"]
        assert result["elapsed_ms"] < 6000  # Should not take too long
    
    def test_output_size_limit(self):
        """Test that large outputs are handled"""
        code = """
# Try to generate large output
for i in range(10000):
    print(f'Line {i}: ' + 'x' * 100)
"""
        # Should either complete with truncated output or fail gracefully
        try:
            result = exec_safe(code)
            # If it completes, output should be reasonable
            assert len(result["stdout"]) < 1024 * 1024  # Less than 1MB
        except RuntimeError:
            # Expected - large output should be limited
            pass


class TestSandboxPerformance:
    """Test performance characteristics"""
    
    def test_execution_latency(self):
        """Test that execution is reasonably fast"""
        start = time.perf_counter()
        result = exec_safe("print(42)")
        end = time.perf_counter()
        
        assert result["stdout"] == "42"
        assert result["elapsed_ms"] < 500  # Should be under 500ms
        assert (end - start) < 1.0  # Total time under 1 second
    
    def test_multiple_executions(self):
        """Test multiple rapid executions"""
        results = []
        for i in range(5):
            result = exec_safe(f"print({i * 10})")
            results.append(result)
        
        # All should succeed
        assert len(results) == 5
        assert all(r["stdout"] == str(i * 10) for i, r in enumerate(results))
        
        # Average latency should be reasonable
        avg_latency = sum(r["elapsed_ms"] for r in results) / len(results)
        assert avg_latency < 200  # Average under 200ms


class TestErrorHandling:
    """Test error conditions"""
    
    def test_syntax_error_handling(self):
        """Test syntax errors are reported"""
        with pytest.raises(RuntimeError):
            exec_safe("print('unclosed string")
    
    def test_runtime_error_handling(self):
        """Test runtime errors are reported"""
        with pytest.raises(RuntimeError):
            exec_safe("raise ValueError('test error')")
    
    def test_empty_code_handling(self):
        """Test empty code execution"""
        result = exec_safe("")
        assert result["stdout"] == ""
        assert result["stderr"] == ""


class TestPrometheusMetrics:
    """Test metrics collection"""
    
    def test_metrics_recorded(self):
        """Test that Prometheus metrics are recorded"""
        from prometheus_client import REGISTRY
        
        # Execute some code to generate metrics
        exec_safe("print('metrics test')")
        
        # Check that our metrics exist
        metric_names = [m.name for m in REGISTRY.collect()]
        assert "swarm_exec_latency_seconds" in metric_names
        assert "swarm_exec_fail_total" in metric_names


if __name__ == "__main__":
    # Quick smoke test
    if Path("/usr/bin/firejail").exists():
        print("🛡️ Running security smoke test...")
        test = TestSandboxSecurity()
        test.test_basic_execution()
        test.test_math_calculation()
        print("✅ Basic security tests passed!")
    else:
        print("⚠️ Firejail not found - tests would be skipped") 