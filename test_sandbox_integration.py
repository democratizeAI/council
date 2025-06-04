#!/usr/bin/env python3
"""
Test sandbox integration with router cascade
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for sandbox
os.environ["AZ_SHELL_TRUSTED"] = "yes"
os.environ["ENABLE_SANDBOX"] = "true"

async def test_sandbox_integration():
    """Test sandbox integration with the router"""
    print("🧪 Testing sandbox integration with AutoGen Council...")
    
    # Test 1: Direct sandbox execution
    print("\n1️⃣ Testing direct sandbox execution...")
    try:
        from sandbox_exec import exec_safe, get_sandbox_status
        
        status = get_sandbox_status()
        print(f"   Sandbox status: {status}")
        
        result = exec_safe("print(f'Direct sandbox test: {2**10}')")
        print(f"   ✅ Direct execution successful: {result}")
        
    except Exception as e:
        print(f"   ❌ Direct execution failed: {e}")
        return False
    
    # Test 2: Router cascade integration
    print("\n2️⃣ Testing router cascade integration...")
    try:
        from router_cascade import RouterCascade
        
        router = RouterCascade()
        
        # Test code execution query
        query = "Write and run Python code that calculates the factorial of 5"
        result = await router.route_query(query)
        
        print(f"   ✅ Router execution successful:")
        print(f"   Response: {result.get('text', 'No response')[:100]}...")
        print(f"   Latency: {result.get('latency_ms', 'Unknown')}ms")
        
        if "sandbox_execution" in result:
            print(f"   🛡️ Sandbox used: {result['sandbox_execution']}")
        
    except Exception as e:
        print(f"   ❌ Router execution failed: {e}")
        return False
    
    print("\n✅ All sandbox integration tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_sandbox_integration())
    sys.exit(0 if success else 1) 