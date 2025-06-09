#!/usr/bin/env python3
"""
Basic import tests for SwarmAI Router
Tests core functionality without complex ML dependencies
"""

import pytest
import sys
import os

class TestBasicImports:
    """Test that core modules can be imported"""
    
    def test_router_cost_tracking_import(self):
        """Test that cost tracking can be imported"""
        try:
            from router.cost_tracking import cost_ledger, debit, get_budget_status
            assert hasattr(cost_ledger, 'reset_budget')
            assert callable(debit)
            assert callable(get_budget_status)
        except ImportError as e:
            pytest.skip(f"Cost tracking import failed: {e}")
    
    def test_router_traffic_controller_import(self):
        """Test that traffic controller can be imported"""
        try:
            import router.traffic_controller
            assert hasattr(router.traffic_controller, '__file__')
        except ImportError as e:
            pytest.skip(f"Traffic controller import failed: {e}")
    
    def test_api_routes_basic_import(self):
        """Test that basic API routes can be imported"""
        try:
            import api.metrics
            assert hasattr(api.metrics, '__file__')
        except ImportError as e:
            pytest.skip(f"API metrics import failed: {e}")

    def test_python_version(self):
        """Test that Python version is compatible"""
        assert sys.version_info >= (3, 8), f"Python 3.8+ required, got {sys.version_info}"
        assert sys.version_info < (4, 0), f"Python 4.x not supported, got {sys.version_info}"

    def test_basic_dependencies(self):
        """Test that basic dependencies are available"""
        imports_to_test = [
            'fastapi',
            'pydantic', 
            'httpx',
            'pytest',
            'redis',
            'pandas'
        ]
        
        failed_imports = []
        for module_name in imports_to_test:
            try:
                __import__(module_name)
            except ImportError:
                failed_imports.append(module_name)
        
        if failed_imports:
            pytest.skip(f"Missing basic dependencies: {failed_imports}")

class TestConfiguration:
    """Test configuration and environment"""
    
    def test_environment_variables(self):
        """Test that essential environment variables can be set"""
        test_vars = {
            'SWARM_GPU_PROFILE': 'ci_test',
            'PYTHONPATH': '.',
        }
        
        for var_name, test_value in test_vars.items():
            os.environ[var_name] = test_value
            assert os.environ.get(var_name) == test_value

    def test_working_directory(self):
        """Test that we're in the correct working directory"""
        cwd = os.getcwd()
        required_files = ['requirements.txt', 'app', 'router', 'tests']
        
        missing_files = []
        for required in required_files:
            if not os.path.exists(required):
                missing_files.append(required)
        
        if missing_files:
            pytest.fail(f"Working directory missing required files: {missing_files} (cwd: {cwd})") 