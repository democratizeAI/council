#!/usr/bin/env python3
"""Test the simplified VLLM direct RouterCascade"""

import asyncio
import os
from router_cascade import RouterCascade

async def test_simple_routing():
    """Test that the RouterCascade now uses direct VLLM routing"""
    
    # Set environment for test
    os.environ["VLLM_BASE_URL"] = "http://localhost:9300"
    os.environ["VLLM_MODEL_NAME"] = "phi-3-mini-int4"
    
    print("🧪 Testing simplified VLLM direct RouterCascade...")
    
    # Create router
    router = RouterCascade()
    
    # Test orchestrate method
    result = await router.orchestrate("Tell me a joke")
    
    print(f"✅ Orchestrate result: {result}")
    print(f"📊 Response length: {len(result.get('response', ''))}")
    print(f"🏷️ Fields: {list(result.keys())}")
    
    # Verify it has the expected Socket Mode fields
    assert "response" in result, "Missing 'response' field for Socket Mode"
    assert "text" in result, "Missing 'text' field" 
    assert "model_used" in result, "Missing 'model_used' field"
    
    print("✅ All required fields present!")
    
    # Test direct route_query method
    query_result = await router.route_query("What is 2+2?", agent="phi3")
    print(f"🧮 Direct query result: {query_result.get('text', '')}")
    
    print("🎯 VLLM Direct Routing Test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_simple_routing()) 