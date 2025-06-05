#!/usr/bin/env python3
"""
🚀 BOOT LOCAL MODELS
===================

Force boot local models and disable cloud fallback
"""

import os
import sys

# Set environment for local-only operation
os.environ["SWARM_CLOUD_ENABLED"] = "false"
os.environ["PROVIDER_PRIORITY"] = "local,cloud"
os.environ["SWARM_FORCE_LOCAL"] = "true"

print("🔧 Environment set:")
print(f"   SWARM_CLOUD_ENABLED = {os.environ['SWARM_CLOUD_ENABLED']}")
print(f"   PROVIDER_PRIORITY = {os.environ['PROVIDER_PRIORITY']}")
print(f"   SWARM_FORCE_LOCAL = {os.environ['SWARM_FORCE_LOCAL']}")

try:
    from loader.deterministic_loader import boot_models, get_loaded_models
    
    print("\n🚀 Booting models with rtx_4070 profile...")
    result = boot_models(profile="rtx_4070")
    
    print(f"✅ Boot result: {result}")
    
    print("\n📊 Checking loaded models...")
    loaded = get_loaded_models()
    
    if loaded:
        print(f"✅ Found {len(loaded)} loaded models:")
        for name, info in loaded.items():
            backend = info.get('backend', 'unknown')
            device = info.get('device', 'unknown')
            print(f"   🤖 {name}: {backend} on {device}")
    else:
        print("❌ No models loaded!")
        
    # Test math specialist specifically
    if "math_specialist_0.8b" in loaded:
        print("\n🧮 Testing math specialist...")
        from loader.deterministic_loader import generate_response
        result = generate_response("math_specialist_0.8b", "What is 2+2?")
        print(f"✅ Math specialist result: {result}")
    else:
        print("❌ Math specialist not found in loaded models")
        
except Exception as e:
    print(f"❌ Error booting models: {e}")
    import traceback
    traceback.print_exc() 