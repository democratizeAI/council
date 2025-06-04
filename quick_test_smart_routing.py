#!/usr/bin/env python3
"""
Quick test to verify smart routing is working correctly
Tests the routing logic without starting the full server
"""

import sys
sys.path.append('.')

from router.hybrid import hybrid_route
from router.voting import smart_select
from loader.deterministic_loader import load_models, get_loaded_models
import asyncio

async def test_smart_routing():
    """Test that smart routing correctly selects single models for simple prompts"""
    
    print("🧪 Testing Smart Routing Logic")
    print("=" * 50)
    
    # Load models with dummy loading to avoid VRAM issues
    print("📂 Loading models (dummy mode for testing)...")
    summary = load_models(profile="rtx_4070", use_real_loading=False)
    print(f"✅ Loaded: {summary['loaded_models']}")
    
    # Get the actual loaded models registry
    loaded_models = get_loaded_models()
    print(f"📋 Available in registry: {list(loaded_models.keys())}")
    
    # Test cases for smart routing
    test_cases = [
        {
            "prompt": "2+2?",
            "expected_behavior": "smart_select",
            "description": "Simple math - should use smart select"
        },
        {
            "prompt": "What is the capital of France?",
            "expected_behavior": "smart_select", 
            "description": "Simple knowledge - should use smart select"
        },
        {
            "prompt": "Please explain in detail why neural networks work and provide step by step analysis of backpropagation",
            "expected_behavior": "voting",
            "description": "Complex prompt - should use voting"
        }
    ]
    
    # Test smart_select function directly with loaded models
    print("\n🎯 Testing smart_select function:")
    available_models = list(loaded_models.keys())[:3]  # Use first 3 loaded models
    print(f"   Using models: {available_models}")
    
    for case in test_cases:
        try:
            selected = smart_select(case['prompt'], available_models)
            print(f"  📝 '{case['prompt'][:40]}...'")
            print(f"     Selected: {selected}")
            print(f"     Expected: {case['expected_behavior']}")
            print()
        except Exception as e:
            print(f"  ❌ smart_select error: {e}")
    
    # Test hybrid_route function 
    print("🔄 Testing hybrid_route function:")
    
    for case in test_cases:
        print(f"  📝 '{case['prompt'][:40]}...'")
        
        # Check prompt length and keywords
        is_simple = (len(case['prompt']) < 120 and 
                    not any(keyword in case['prompt'].lower() 
                           for keyword in ["explain", "why", "step by step", "analyze", "compare", "reasoning"]))
        
        expected_path = "smart" if is_simple else "voting"
        print(f"     Prompt length: {len(case['prompt'])}")
        print(f"     Contains complex keywords: {not is_simple}")
        print(f"     Expected path: {expected_path}")
        
        try:
            result = await hybrid_route(case['prompt'], available_models[:2])
            actual_provider = result.get('provider', 'unknown')
            print(f"     Actual provider: {actual_provider}")
            print(f"     Model used: {result.get('model_used', 'unknown')}")
            print(f"     Latency: {result.get('hybrid_latency_ms', 0):.1f}ms")
            
            # Verify the routing decision
            if expected_path == "smart" and "smart" in actual_provider:
                print("     ✅ PASSED: Used smart routing as expected")
            elif expected_path == "voting" and "voting" in actual_provider:
                print("     ✅ PASSED: Used voting as expected")
            else:
                print(f"     ⚠️ UNEXPECTED: Expected {expected_path}, got {actual_provider}")
            
        except Exception as e:
            print(f"     ❌ ERROR: {e}")
        
        print()
    
    # Test the prompt classification logic directly
    print("🔍 Testing prompt classification logic:")
    for case in test_cases:
        prompt = case['prompt']
        
        # This is the actual logic from hybrid.py
        is_simple = (len(prompt) < 120 and 
                    not any(keyword in prompt.lower() for keyword in ["explain", "why", "step by step", "analyze", "compare", "reasoning"]))
        
        print(f"  📝 '{prompt[:50]}...'")
        print(f"     Length: {len(prompt)} (threshold: 120)")
        
        complex_keywords = [k for k in ["explain", "why", "step by step", "analyze", "compare", "reasoning"] 
                           if k in prompt.lower()]
        print(f"     Complex keywords found: {complex_keywords}")
        print(f"     Classification: {'SIMPLE (smart routing)' if is_simple else 'COMPLEX (voting)'}")
        print()
    
    print("🎯 Smart Routing Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_smart_routing()) 