#!/usr/bin/env python3
"""
🔧 HASHLIB FIX TESTS
==================

Tests for the specialist sandbox hashlib fix that resolves:
"[ERROR] math_specialist: Math specialist failed: name 'hashlib' is not defined"

This regression occurred because specialists' execution environment
didn't have access to essential stdlib modules like hashlib.
"""

import pytest
import sys
import builtins
from unittest.mock import patch
from router.specialist_sandbox_fix import (
    SpecialistSandbox, 
    get_specialist_sandbox,
    fix_specialist_imports,
    test_specialist_environment
)

class TestHashlibFix:
    """Test hashlib availability in specialist execution environment"""
    
    def test_sandbox_has_hashlib(self):
        """Test that sandbox environment has hashlib available"""
        sandbox = SpecialistSandbox()
        
        # Should have hashlib in globals
        assert 'hashlib' in sandbox.globals
        assert sandbox.globals['hashlib'] is not None
        
        # Should be able to use hashlib
        result = sandbox.evaluate_expression("hashlib.md5(b'test').hexdigest()")
        assert result == "098f6bcd4621d373cade4e832627b4f6"
    
    def test_sandbox_has_md5_function(self):
        """Test that sandbox has convenient md5 function"""
        sandbox = SpecialistSandbox()
        
        # Should have md5 function
        assert 'md5' in sandbox.globals
        
        # Should work with string input
        result = sandbox.evaluate_expression("md5('test')")
        assert result == "098f6bcd4621d373cade4e832627b4f6"
    
    def test_sandbox_has_essential_modules(self):
        """Test that sandbox has all essential modules specialists need"""
        sandbox = SpecialistSandbox()
        
        essential_modules = ['hashlib', 'math', 're', 'json', 'time', 'os', 'sys']
        
        for module in essential_modules:
            assert module in sandbox.globals, f"Missing essential module: {module}"
            assert sandbox.globals[module] is not None
    
    def test_sandbox_math_functions(self):
        """Test that math functions work in sandbox (math specialist needs these)"""
        sandbox = SpecialistSandbox()
        
        test_cases = [
            ("math.sqrt(16)", 4.0),
            ("sqrt(25)", 5.0),  # Shortcut function
            ("math.pi > 3", True),
            ("sin(0)", 0.0),
        ]
        
        for expression, expected in test_cases:
            result = sandbox.evaluate_expression(expression)
            if isinstance(expected, float):
                assert abs(result - expected) < 0.001, f"Failed: {expression}"
            else:
                assert result == expected, f"Failed: {expression}"
    
    def test_sandbox_code_execution(self):
        """Test that code execution works with hashlib (code specialist needs this)"""
        sandbox = SpecialistSandbox()
        
        code = """
import hashlib
result = hashlib.sha256('hello world'.encode()).hexdigest()
"""
        
        local_vars = {}
        sandbox.execute_code(code, local_vars)
        
        assert 'result' in local_vars
        assert local_vars['result'] == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    
    def test_global_import_fix(self):
        """Test that fix_specialist_imports() makes hashlib globally available"""
        # Save original state
        original_hashlib = getattr(builtins, 'hashlib', None)
        original_md5 = getattr(builtins, 'md5', None)
        
        try:
            # Remove hashlib if present
            if hasattr(builtins, 'hashlib'):
                delattr(builtins, 'hashlib')
            if hasattr(builtins, 'md5'):
                delattr(builtins, 'md5')
            
            # Apply fix
            fix_specialist_imports()
            
            # Should now be available globally
            assert hasattr(builtins, 'hashlib')
            assert hasattr(builtins, 'md5')
            
            # Should work
            import hashlib
            result = hashlib.md5(b'test').hexdigest()
            assert result == "098f6bcd4621d373cade4e832627b4f6"
            
        finally:
            # Restore original state
            if original_hashlib is not None:
                builtins.hashlib = original_hashlib
            elif hasattr(builtins, 'hashlib'):
                delattr(builtins, 'hashlib')
                
            if original_md5 is not None:
                builtins.md5 = original_md5
            elif hasattr(builtins, 'md5'):
                delattr(builtins, 'md5')
    
    def test_specialist_environment_comprehensive(self):
        """Test the comprehensive environment test function"""
        results = test_specialist_environment()
        
        # Should have multiple test results
        assert len(results) > 0
        
        # All tests should pass
        for result in results:
            assert result['success'], f"Failed test: {result['expression']} - {result['actual']}"
    
    @patch('router.voting.SpecialistRunner')
    def test_hashlib_error_scenario(self, mock_specialist_runner):
        """Test the scenario that caused the original error"""
        # Simulate the original error
        mock_specialist_runner.return_value._run_math.side_effect = Exception("name 'hashlib' is not defined")
        
        # After applying our fix, this should not happen
        sandbox = get_specialist_sandbox()
        
        # Should be able to execute code that uses hashlib
        code = """
# This is what specialists typically do
entry_id = hashlib.md5(f"math_cache_{prompt}_{timestamp}".encode()).hexdigest()[:12]
result = f"Answer with ID: {entry_id}"
"""
        
        local_vars = {
            'prompt': 'What is 2+2?',
            'timestamp': '1234567890'
        }
        
        # Should not raise "name 'hashlib' is not defined"
        sandbox.execute_code(code, local_vars)
        assert 'result' in local_vars
        assert 'Answer with ID:' in local_vars['result']
    
    def test_scratchpad_compatibility(self):
        """Test that fix is compatible with scratchpad system"""
        # The scratchpad system is one of the main users of hashlib
        sandbox = get_specialist_sandbox()
        
        # Simulate scratchpad entry creation (from common/scratchpad.py line 146)
        code = """
import time
entry_id = hashlib.md5(f"session_123_agent0_{time.time()}".encode()).hexdigest()[:12]
"""
        
        local_vars = {}
        sandbox.execute_code(code, local_vars)
        
        assert 'entry_id' in local_vars
        assert len(local_vars['entry_id']) == 12  # Should be 12 chars as per scratchpad

if __name__ == "__main__":
    # Run the tests
    test_fix = TestHashlibFix()
    
    print("🔧 HASHLIB FIX TESTS")
    print("=" * 50)
    
    tests = [
        test_fix.test_sandbox_has_hashlib,
        test_fix.test_sandbox_has_md5_function,
        test_fix.test_sandbox_has_essential_modules,
        test_fix.test_sandbox_math_functions,
        test_fix.test_sandbox_code_execution,
        test_fix.test_global_import_fix,
        test_fix.test_specialist_environment_comprehensive,
        test_fix.test_scratchpad_compatibility,
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: {e}")
    
    print(f"\n📊 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ Hashlib fix is working correctly!")
        print("🚀 Specialists should now have access to all required modules")
    else:
        print("❌ Some tests failed - hashlib fix needs attention") 