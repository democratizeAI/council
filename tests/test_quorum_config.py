#!/usr/bin/env python3
"""
Unit tests for quorum configuration synchronization
Ensures SONNET_QUORUM_SIZE environment variable stays in sync with PatchCtl config
"""

import os
import yaml
import pathlib
import pytest
from unittest.mock import patch

def test_quorum_match():
    """Test that SONNET_QUORUM_SIZE matches PatchCtl config"""
    # Load PatchCtl configuration
    patchctl_config_path = pathlib.Path('patchctl/config.yml')
    
    if not patchctl_config_path.exists():
        pytest.skip("PatchCtl config file not found")
    
    cfg = yaml.safe_load(patchctl_config_path.read_text())
    
    # Get expected quorum size from environment (default 2)
    wanted = int(os.getenv('SONNET_QUORUM_SIZE', 2))
    
    # Extract min_green from sonnet_builders quorum group
    sonnet_builders = cfg.get('quorum_groups', {}).get('sonnet_builders', {})
    min_green_config = sonnet_builders.get('min_green')
    
    # Handle environment variable substitution in config
    if isinstance(min_green_config, str) and '${' in min_green_config:
        # Extract default value from ${SONNET_QUORUM_SIZE:-2} pattern
        if ':-' in min_green_config:
            default_value = int(min_green_config.split(':-')[1].rstrip('}'))
            actual_min_green = wanted if 'SONNET_QUORUM_SIZE' in os.environ else default_value
        else:
            actual_min_green = wanted
    else:
        actual_min_green = int(min_green_config) if min_green_config is not None else 2
    
    assert actual_min_green == wanted, f"PatchCtl min_green ({actual_min_green}) doesn't match SONNET_QUORUM_SIZE ({wanted})"

def test_sonnet_builders_config_structure():
    """Test that sonnet_builders quorum group has correct structure"""
    patchctl_config_path = pathlib.Path('patchctl/config.yml')
    
    if not patchctl_config_path.exists():
        pytest.skip("PatchCtl config file not found")
    
    cfg = yaml.safe_load(patchctl_config_path.read_text())
    
    # Verify quorum_groups exists
    assert 'quorum_groups' in cfg, "quorum_groups section missing from PatchCtl config"
    
    # Verify sonnet_builders group exists
    quorum_groups = cfg['quorum_groups']
    assert 'sonnet_builders' in quorum_groups, "sonnet_builders quorum group missing"
    
    sonnet_builders = quorum_groups['sonnet_builders']
    
    # Verify required fields
    assert 'min_green' in sonnet_builders, "min_green field missing from sonnet_builders"
    assert 'heads' in sonnet_builders, "heads field missing from sonnet_builders"
    
    # Verify heads structure
    heads = sonnet_builders['heads']
    assert isinstance(heads, list), "heads should be a list"
    assert len(heads) >= 3, "Should have at least 3 Sonnet builder heads"
    
    # Verify each head has required fields
    expected_heads = {"Sonnet-A", "Sonnet-B", "Sonnet-C"}
    actual_heads = {head['name'] for head in heads}
    
    assert expected_heads.issubset(actual_heads), f"Missing expected heads. Expected: {expected_heads}, Got: {actual_heads}"
    
    for head in heads:
        assert 'name' in head, f"Head {head} missing name field"
        assert 'stream' in head, f"Head {head} missing stream field"
        assert 'weight' in head, f"Head {head} missing weight field"
        assert head['weight'] == 1, f"Head {head} weight should be 1"

@patch.dict(os.environ, {'SONNET_QUORUM_SIZE': '3'})
def test_quorum_match_with_env_var():
    """Test quorum match when SONNET_QUORUM_SIZE is explicitly set"""
    test_quorum_match()

@patch.dict(os.environ, {}, clear=True)
def test_quorum_match_default():
    """Test quorum match with default value when env var is not set"""
    # Remove SONNET_QUORUM_SIZE if it exists
    if 'SONNET_QUORUM_SIZE' in os.environ:
        del os.environ['SONNET_QUORUM_SIZE']
    
    test_quorum_match()

def test_env_example_consistency():
    """Test that .env.example contains SONNET_QUORUM_SIZE"""
    env_example_path = pathlib.Path('.env.example')
    
    if not env_example_path.exists():
        pytest.skip(".env.example file not found")
    
    env_example_content = env_example_path.read_text()
    
    assert 'SONNET_QUORUM_SIZE' in env_example_content, "SONNET_QUORUM_SIZE missing from .env.example"
    
    # Extract the value
    for line in env_example_content.split('\n'):
        if line.startswith('SONNET_QUORUM_SIZE='):
            value = line.split('=')[1].strip()
            assert value.isdigit(), "SONNET_QUORUM_SIZE should be a number in .env.example"
            assert int(value) >= 2, "SONNET_QUORUM_SIZE should be at least 2"
            break
    else:
        pytest.fail("SONNET_QUORUM_SIZE assignment not found in .env.example")

if __name__ == "__main__":
    pytest.main([__file__]) 