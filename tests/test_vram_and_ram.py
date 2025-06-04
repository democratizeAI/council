#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, psutil, subprocess, time, json, pytest

def test_vram_smokeload():
    env = os.environ.copy()
    env['SWARM_GPU_PROFILE'] = 'rtx_4070'
    p = subprocess.run(['python', '-m', 'loader.deterministic_loader'],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "[OK]" in p.stdout

def test_ram_guard():
    """Test if htop is available for RAM monitoring"""
    
    # Skip test on Windows CI where htop isn't available
    if os.name == 'nt' or os.environ.get('CI') == 'true':
        pytest.skip("htop not available on Windows CI")
    
    result = subprocess.run(['which', 'htop'], capture_output=True)
    assert result.returncode == 0, "htop should be available for RAM monitoring"
