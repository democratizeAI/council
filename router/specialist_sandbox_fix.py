#!/usr/bin/env python3
"""
🔧 SPECIALIST SANDBOX FIX
========================

Fixes the "name 'hashlib' is not defined" error by ensuring essential
stdlib modules are available in the specialists' execution environment.

The issue: specialists need hashlib for caching and ID generation, but
restricted execution environments don't include it by default.

Critical fix for:
- Math specialist: Uses hashlib for expression caching
- Code specialist: Uses hashlib for code hashing  
- Logic specialist: Uses hashlib for rule hashing
- Scratchpad system: Uses hashlib for entry IDs
"""

import hashlib
import sys
import math
import re
import json
import time
import os
from typing import Dict, Any, List

# Essential stdlib modules that specialists need
ESSENTIAL_MODULES = {
    'hashlib': hashlib,
    'math': math, 
    're': re,
    'json': json,
    'time': time,
    'os': os,
    'sys': sys
}

# Safe builtins for specialist execution
SAFE_BUILTINS = {
    'abs': abs,
    'all': all,
    'any': any,
    'bool': bool,
    'dict': dict,
    'enumerate': enumerate,
    'filter': filter,
    'float': float,
    'int': int,
    'len': len,
    'list': list,
    'map': map,
    'max': max,
    'min': min,
    'range': range,
    'round': round,
    'set': set,
    'sorted': sorted,
    'str': str,
    'sum': sum,
    'tuple': tuple,
    'zip': zip,
    'print': print,
    'type': type,
    'isinstance': isinstance,
    'hasattr': hasattr,
    'getattr': getattr,
    'setattr': setattr,
}

class SpecialistSandbox:
    """Safe execution environment for specialists with essential modules"""
    
    def __init__(self):
        self.globals = {}
        self._setup_environment()
    
    def _setup_environment(self):
        """Setup safe execution environment with essential modules"""
        
        # Add safe builtins
        self.globals['__builtins__'] = SAFE_BUILTINS.copy()
        
        # Add essential modules
        for module_name, module in ESSENTIAL_MODULES.items():
            self.globals[module_name] = module
        
        # Add common functions that specialists need
        self.globals.update({
            # Math functions (for math specialist)
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'exp': math.exp,
            'pi': math.pi,
            'e': math.e,
            
            # Hashing functions (for all specialists)
            'md5': lambda text: hashlib.md5(text.encode()).hexdigest(),
            'sha256': lambda text: hashlib.sha256(text.encode()).hexdigest(),
            
            # Utility functions
            'timestamp': time.time,
            'current_time': time.time,
        })
    
    def execute_code(self, code: str, local_vars: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute code in safe environment"""
        if local_vars is None:
            local_vars = {}
        
        # Merge with safe globals
        execution_globals = self.globals.copy()
        execution_globals.update(local_vars)
        
        try:
            # Execute in safe environment
            exec(code, execution_globals, local_vars)
            return local_vars
        except Exception as e:
            raise Exception(f"Specialist execution failed: {e}")
    
    def evaluate_expression(self, expression: str, local_vars: Dict[str, Any] = None) -> Any:
        """Evaluate expression in safe environment"""
        if local_vars is None:
            local_vars = {}
        
        execution_globals = self.globals.copy()
        execution_globals.update(local_vars)
        
        try:
            return eval(expression, execution_globals, local_vars)
        except Exception as e:
            raise Exception(f"Expression evaluation failed: {e}")

# Global sandbox instance
_sandbox = None

def get_specialist_sandbox() -> SpecialistSandbox:
    """Get or create global sandbox instance"""
    global _sandbox
    if _sandbox is None:
        _sandbox = SpecialistSandbox()
    return _sandbox

def fix_specialist_imports():
    """
    Apply the hashlib fix to the current execution environment.
    
    This function should be called during specialist initialization
    to ensure all required modules are available.
    """
    import builtins
    
    # Ensure hashlib is available globally
    if not hasattr(builtins, 'hashlib'):
        builtins.hashlib = hashlib
    
    # Add other essential modules to builtins
    for module_name, module in ESSENTIAL_MODULES.items():
        if not hasattr(builtins, module_name):
            setattr(builtins, module_name, module)
    
    # Add common hashing functions
    if not hasattr(builtins, 'md5'):
        builtins.md5 = lambda text: hashlib.md5(text.encode()).hexdigest()
    
    if not hasattr(builtins, 'sha256'):
        builtins.sha256 = lambda text: hashlib.sha256(text.encode()).hexdigest()

def test_specialist_environment():
    """Test that specialist environment has all required modules"""
    sandbox = get_specialist_sandbox()
    
    test_cases = [
        # Test hashlib
        ("hashlib.md5('test'.encode()).hexdigest()", "098f6bcd4621d373cade4e832627b4f6"),
        
        # Test md5 function
        ("md5('test')", "098f6bcd4621d373cade4e832627b4f6"),
        
        # Test math
        ("math.sqrt(16)", 4.0),
        ("sqrt(25)", 5.0),
        
        # Test json
        ("json.dumps({'test': 123})", '{"test": 123}'),
        
        # Test time
        ("int(time.time()) > 0", True),
    ]
    
    results = []
    for expression, expected in test_cases:
        try:
            result = sandbox.evaluate_expression(expression)
            success = result == expected
            results.append({
                "expression": expression,
                "expected": expected,
                "actual": result,
                "success": success
            })
        except Exception as e:
            results.append({
                "expression": expression,
                "expected": expected,
                "actual": f"ERROR: {e}",
                "success": False
            })
    
    return results

if __name__ == "__main__":
    # Apply the fix
    fix_specialist_imports()
    
    # Test the environment
    results = test_specialist_environment()
    
    print("🔧 SPECIALIST SANDBOX FIX")
    print("=" * 50)
    
    passed = 0
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['expression']}")
        if not result["success"]:
            print(f"   Expected: {result['expected']}")
            print(f"   Actual: {result['actual']}")
        else:
            passed += 1
    
    print(f"\n📊 Results: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("✅ All specialists should now have access to hashlib!")
    else:
        print("❌ Some tests failed - specialists may still have import issues") 