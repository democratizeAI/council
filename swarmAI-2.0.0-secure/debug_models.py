#!/usr/bin/env python3
"""Debug loaded models and test real inference"""

def debug_models():
    from loader.deterministic_loader import get_loaded_models, generate_response
    
    models = get_loaded_models()
    
    print("🔍 Debugging Loaded Models")
    print("="*50)
    
    for name, info in models.items():
        print(f"📍 {name}:")
        print(f"   Backend: {info['backend']}")
        print(f"   Type: {info['type']}")
        print(f"   Handle: {type(info['handle'])}")
        print(f"   VRAM: {info['vram_mb']} MB")
        print()
    
    # Test direct generation
    print("🧪 Testing Direct Generation")
    print("="*50)
    
    test_model = "math_specialist_0.8b"
    test_prompt = "What is 2 + 2?"
    
    if test_model in models:
        model_info = models[test_model]
        print(f"Testing {test_model} ({model_info['backend']} backend)")
        print(f"Prompt: {test_prompt}")
        
        try:
            response = generate_response(test_model, test_prompt, max_tokens=50)
            print(f"✅ Response: {response}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Model {test_model} not found")

if __name__ == "__main__":
    debug_models() 