#!/usr/bin/env python3
"""
Test direct model generation to verify the fix
"""

import sys
import os
sys.path.insert(0, '.')

from loader.deterministic_loader import get_loaded_models, generate_response, boot_models

def test_direct():
    print("🧪 TESTING DIRECT MODEL GENERATION")
    print("=" * 50)
    
    # Set environment
    os.environ["SWARM_GPU_PROFILE"] = "rtx_4070"
    
    # Load models
    print("Loading models...")
    summary = boot_models(profile="rtx_4070")
    print(f"Loaded: {summary['loaded_models']}")
    
    # Test questions
    test_questions = [
        "What is 2 + 2?",
        "Calculate 15 * 16",
        "Write a Python function for factorial",
        "What is the capital of France?"
    ]
    
    loaded = get_loaded_models()
    if not loaded:
        print("❌ No models loaded!")
        return
    
    model_name = list(loaded.keys())[0]
    print(f"\n🎯 Testing with {model_name}")
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n--- Question {i} ---")
        print(f"Q: {question}")
        
        try:
            response = generate_response(model_name, question, max_tokens=50)
            print(f"A: {response}")
            
            # Check if it's mock
            if "Response from" in response:
                print("🎭 MOCK RESPONSE")
            else:
                print("🤖 REAL AI RESPONSE")
                
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_direct() 