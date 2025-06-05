#!/usr/bin/env python3
"""Test CUDA availability and GPU setup"""

try:
    import torch
    print("✅ PyTorch imported successfully")
    print(f"🎯 CUDA available: {torch.cuda.is_available()}")
    print(f"🖥️ Device count: {torch.cuda.device_count()}")
    
    if torch.cuda.is_available():
        print(f"🚀 Current device: {torch.cuda.current_device()}")
        print(f"📋 Device name: {torch.cuda.get_device_name(0)}")
        print(f"💾 CUDA version: {torch.version.cuda}")
    else:
        print("❌ CUDA not available - will use CPU mode")
        
    # Test a simple tensor operation
    if torch.cuda.is_available():
        x = torch.randn(3, 3).cuda()
        print(f"✅ GPU tensor test passed: {x.device}")
    else:
        x = torch.randn(3, 3)
        print(f"✅ CPU tensor test passed: {x.device}")
        
except Exception as e:
    print(f"❌ Error: {e}") 