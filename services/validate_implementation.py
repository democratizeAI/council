#!/usr/bin/env python3
"""
Service Wrapper Implementation Validator
=========================================

Validates the service wrapper implementation without requiring admin privileges
or actual service installation. Tests the core components and configuration.
"""

import os
import sys
import platform
import importlib.util
from pathlib import Path

def test_file_exists(filepath: str, description: str) -> bool:
    """Test if a required file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} missing: {filepath}")
        return False

def test_python_import(module_path: str, description: str) -> bool:
    """Test if a Python module can be imported"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ {description}: syntax valid")
            return True
        else:
            print(f"❌ {description}: cannot load module")
            return False
    except Exception as e:
        print(f"❌ {description}: {str(e)}")
        return False

def test_service_config(config_path: str) -> bool:
    """Test service configuration file"""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        # Check for required sections
        required_sections = ['[Unit]', '[Service]', '[Install]']
        if platform.system() == 'Windows':
            # Windows service - check for class definition
            required_patterns = ['class Agent0Service', '_svc_name_', '_svc_display_name_']
        else:
            # Linux systemd - check for service sections
            required_patterns = required_sections
            
        missing = []
        for pattern in required_patterns:
            if pattern not in content:
                missing.append(pattern)
                
        if not missing:
            print(f"✅ Service configuration valid: {config_path}")
            return True
        else:
            print(f"❌ Service configuration missing: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ Service configuration error: {e}")
        return False

def test_health_endpoint_integration() -> bool:
    """Test if health endpoint has service metrics integration"""
    try:
        # Read the main.py file and check for service metrics
        main_py_path = os.path.join('app', 'main.py')
        if not os.path.exists(main_py_path):
            print(f"❌ Main application not found: {main_py_path}")
            return False
            
        with open(main_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Check for service-specific metrics
        required_patterns = [
            'SERVICE_STARTUPS_TOTAL',
            'service_status',
            'startups_total',
            'service_managed'
        ]
        
        missing = []
        for pattern in required_patterns:
            if pattern not in content:
                missing.append(pattern)
                
        if not missing:
            print("✅ Health endpoint integration: service metrics present")
            return True
        else:
            print(f"❌ Health endpoint missing service metrics: {missing}")
            return False
            
    except Exception as e:
        print(f"❌ Health endpoint integration error: {e}")
        return False

def validate_service_wrapper() -> dict:
    """Run complete validation of service wrapper implementation"""
    print("🔍 Service Wrapper Implementation Validator")
    print("=" * 50)
    
    results = {}
    tests = []
    
    # Test 1: Required files exist
    tests.append(("Windows service script", lambda: test_file_exists(
        "services/agent0_service.py", "Windows service script")))
    
    tests.append(("Linux service config", lambda: test_file_exists(
        "services/agent0.service", "Linux systemd service")))
    
    tests.append(("Windows installer", lambda: test_file_exists(
        "services/install_windows.ps1", "Windows installation script")))
    
    tests.append(("Linux installer", lambda: test_file_exists(
        "services/install_linux.sh", "Linux installation script")))
    
    tests.append(("Smoke test script", lambda: test_file_exists(
        "services/test_service_wrapper.py", "Service smoke test")))
    
    tests.append(("Documentation", lambda: test_file_exists(
        "services/README.md", "Service documentation")))
    
    # Test 2: Python syntax validation
    tests.append(("Windows service syntax", lambda: test_python_import(
        "services/agent0_service.py", "Windows service Python script")))
    
    tests.append(("Smoke test syntax", lambda: test_python_import(
        "services/test_service_wrapper.py", "Smoke test Python script")))
    
    # Test 3: Service configuration validation
    if platform.system() == "Windows":
        tests.append(("Service configuration", lambda: test_service_config(
            "services/agent0_service.py")))
    else:
        tests.append(("Service configuration", lambda: test_service_config(
            "services/agent0.service")))
    
    # Test 4: Integration validation
    tests.append(("Health endpoint integration", test_health_endpoint_integration))
    
    # Run all tests
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
                results[test_name] = "PASS"
            else:
                results[test_name] = "FAIL"
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results[test_name] = "ERROR"
    
    # Summary
    print(f"\n🏁 Validation Results: {passed}/{total} tests passed")
    pass_rate = passed / total
    
    if pass_rate >= 1.0:
        print("✅ All validations passed - Service wrapper implementation is complete!")
        status = "COMPLETE"
    elif pass_rate >= 0.8:
        print("⚠️ Most validations passed - Minor issues detected")
        status = "MOSTLY_COMPLETE"
    else:
        print("❌ Multiple validation failures - Implementation needs work")
        status = "INCOMPLETE"
    
    results["summary"] = {
        "total_tests": total,
        "passed_tests": passed,
        "pass_rate": pass_rate,
        "status": status,
        "platform": platform.system()
    }
    
    print(f"\n📊 Implementation Status: {status}")
    print(f"📋 Platform: {platform.system()}")
    
    return results

def main():
    """Main validation entry point"""
    try:
        results = validate_service_wrapper()
        
        # Print next steps
        print("\n🚀 Next Steps:")
        if results["summary"]["status"] == "COMPLETE":
            if platform.system() == "Windows":
                print("1. Run as Administrator: Right-click PowerShell → 'Run as Administrator'")
                print("2. Install service: .\\services\\install_windows.ps1")
                print("3. Verify: sc query Agent0Council")
            else:
                print("1. Install service: sudo ./services/install_linux.sh")
                print("2. Verify: sudo systemctl status agent0")
            print("4. Test: python services/test_service_wrapper.py")
        else:
            print("1. Fix failing validations above")
            print("2. Re-run this validator")
            print("3. Proceed with installation once all tests pass")
        
        # Exit with appropriate code
        if results["summary"]["pass_rate"] >= 1.0:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()