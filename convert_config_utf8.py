#!/usr/bin/env python3
"""Convert config files to UTF-8 encoding"""

import os
import sys
sys.path.append('.')

from config.utils import convert_to_utf8, check_yaml_encoding

config_files = [
    'config/models.yaml',
    'config/council.yml', 
    'config/providers.yaml',
    'config/settings.yaml'
]

print("🔧 Converting config files to UTF-8...")

for config_file in config_files:
    if os.path.exists(config_file):
        print(f"\n📁 Processing {config_file}")
        
        # Check current encoding
        encoding = check_yaml_encoding(config_file)
        print(f"   Current encoding: {encoding}")
        
        if encoding != "utf-8":
            # Convert to UTF-8
            success = convert_to_utf8(config_file)
            if success:
                print(f"   ✅ Converted to UTF-8")
            else:
                print(f"   ❌ Conversion failed")
        else:
            print(f"   ✅ Already UTF-8")
    else:
        print(f"⚠️ {config_file} not found")

print("\n🎯 Testing YAML loading...")
try:
    import yaml
    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                print(f"✅ {config_file}: Loaded successfully")
except Exception as e:
    print(f"❌ YAML test failed: {e}")

print("\n✅ UTF-8 conversion complete!") 