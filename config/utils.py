#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UTF-8 Safe Config Loader

Fixes "charmap can't decode" errors when reading YAML config files.
"""

import io
import yaml
from pathlib import Path
from typing import Dict, Any

def load_yaml(path: str) -> Dict[str, Any]:
    """Load YAML file with explicit UTF-8 encoding"""
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except UnicodeDecodeError as e:
        print(f"⚠️ UTF-8 decode error in {path}: {e}")
        # Fallback: try with Windows-1252 encoding
        try:
            with io.open(path, "r", encoding="cp1252") as f:
                content = yaml.safe_load(f) or {}
                print(f"✅ Loaded {path} with cp1252 fallback")
                return content
        except Exception as fallback_error:
            print(f"❌ Both UTF-8 and cp1252 failed for {path}: {fallback_error}")
            return {}
    except Exception as e:
        print(f"❌ Failed to load {path}: {e}")
        return {}

def save_yaml(path: str, data: Dict[str, Any]) -> bool:
    """Save YAML file with explicit UTF-8 encoding"""
    try:
        with io.open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"❌ Failed to save {path}: {e}")
        return False

def convert_to_utf8(path: str) -> bool:
    """Convert a config file to UTF-8 encoding"""
    try:
        # Load with fallback detection
        data = load_yaml(path)
        if data:
            # Save back as UTF-8
            return save_yaml(path, data)
        return False
    except Exception as e:
        print(f"❌ Failed to convert {path} to UTF-8: {e}")
        return False

def check_yaml_encoding(path: str) -> str:
    """Check encoding of a YAML file"""
    try:
        with io.open(path, "r", encoding="utf-8") as f:
            f.read()
        return "utf-8"
    except UnicodeDecodeError:
        try:
            with io.open(path, "r", encoding="cp1252") as f:
                f.read()
            return "cp1252"
        except UnicodeDecodeError:
            return "unknown"
    except Exception:
        return "error" 