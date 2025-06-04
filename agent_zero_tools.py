#!/usr/bin/env python3
"""
Agent-Zero Tools Integration for AutoGen Council
===============================================
Safe code execution tools using Firejail sandbox
"""

from sandbox_exec import exec_safe
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def tool_exec_safe(snippet: str, language: str = "python") -> Dict[str, Any]:
    """
    Safely run code in a jailed sandbox (5s CPU, no network)
    
    Args:
        snippet: Code to execute
        language: Programming language (default: python)
    
    Returns:
        Dict with execution results
    """
    try:
        result = exec_safe(snippet, language)
        
        logger.info(f"🛡️ Safe execution completed: {result['elapsed_ms']}ms")
        
        return {
            "success": True,
            "output": result["stdout"] or result["stderr"] or "No output",
            "elapsed_ms": result["elapsed_ms"],
            "language": language
        }
        
    except RuntimeError as e:
        logger.warning(f"🚨 Sandbox execution failed: {e}")
        
        return {
            "success": False,
            "error": str(e),
            "output": f"Execution failed: {e}",
            "language": language
        }

# Agent-Zero compatible tool decorator
def create_exec_tool():
    """Create Agent-Zero compatible execution tool"""
    
    def exec_safe_tool(snippet: str) -> str:
        """Safely run Python in a jailed sandbox (5s CPU, no net)."""
        result = tool_exec_safe(snippet)
        
        if result["success"]:
            return result["output"]
        else:
            return f"Error: {result['error']}"
    
    return exec_safe_tool

# Integration test
if __name__ == "__main__":
    # Test basic execution
    print("🧪 Testing safe execution tool...")
    
    test_cases = [
        "print(2 + 2)",
        "import math; print(math.sqrt(16))",
        "print('Hello from sandbox!')"
    ]
    
    for code in test_cases:
        print(f"\n🔍 Testing: {code}")
        result = tool_exec_safe(code)
        print(f"   Result: {result}")
    
    print("\n✅ Agent-Zero tools integration ready!") 