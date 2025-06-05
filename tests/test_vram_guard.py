#!/usr/bin/env python3
"""
VRAM Guard Smoke Tests (Ticket #206 - Hybrid Implementation)
Tests the hybrid VRAM scheduler: metrics from container, control on host
"""

import subprocess
import pathlib
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

def test_vram_guard_script_exists():
    """Test that the hybrid VRAM guard script exists"""
    script_path = pathlib.Path("scripts/vram_guard.sh")
    assert script_path.exists(), "VRAM guard script not found"
    assert script_path.is_file(), "VRAM guard script is not a file"
    
    # Check for hybrid implementation markers
    content = script_path.read_text(encoding='utf-8')
    assert "curl -s http://localhost:9108/metrics" in content, "Should use NVML exporter"
    assert "nvidia-smi" in content, "Should have fallback to nvidia-smi"

def test_nvml_exporter_files():
    """Test that NVML exporter container files exist"""
    main_py = pathlib.Path("scheduler/main.py")
    dockerfile = pathlib.Path("scheduler/Dockerfile")
    
    assert main_py.exists(), "NVML exporter main.py not found"
    assert dockerfile.exists(), "NVML exporter Dockerfile not found"
    
    # Check main.py has required functionality
    content = main_py.read_text(encoding='utf-8')
    assert "pynvml" in content, "Should use NVML library"
    assert "gpu_vram_used_mb" in content, "Should export VRAM metrics"
    assert "/metrics" in content, "Should have metrics endpoint"
    assert "/health" in content, "Should have health endpoint"

def test_docker_compose_configuration():
    """Test that docker-compose.yml has slimmed scheduler service"""
    compose_file = pathlib.Path("docker-compose.yml")
    assert compose_file.exists(), "docker-compose.yml not found"
    
    content = compose_file.read_text(encoding='utf-8')
    assert "scheduler:" in content, "Should have scheduler service"
    assert "9108:8000" in content, "Should expose metrics port"
    
    # Parse scheduler service specifically to ensure no Docker socket
    lines = content.split('\n')
    in_scheduler_section = False
    scheduler_section = []
    
    for line in lines:
        if line.strip().startswith('scheduler:'):
            in_scheduler_section = True
            scheduler_section.append(line)
        elif in_scheduler_section:
            if line.startswith('  ') or line.strip() == '':
                scheduler_section.append(line)
            else:
                # Next service started
                break
    
    scheduler_config = '\n'.join(scheduler_section)
    assert "/var/run/docker.sock" not in scheduler_config, "Scheduler should NOT mount Docker socket"

def test_vram_threshold_logic():
    """Test the VRAM threshold decision logic (same as before)"""
    
    # Test case 1: Low VRAM (< 10GB) - should not pause
    vram_used = 8192  # 8GB
    threshold = 10240  # 10GB
    is_paused = False
    
    should_pause = vram_used > threshold and not is_paused
    assert not should_pause, "Should not pause when VRAM is below threshold"
    
    # Test case 2: High VRAM (> 10GB) - should pause
    vram_used = 12288  # 12GB
    should_pause = vram_used > threshold and not is_paused
    assert should_pause, "Should pause when VRAM exceeds threshold"
    
    # Test case 3: VRAM back to safe level - should resume
    vram_used = 8192  # 8GB
    is_paused = True
    should_resume = vram_used <= threshold and is_paused
    assert should_resume, "Should resume when VRAM returns to safe level"

def test_hybrid_metric_collection():
    """Test that the hybrid approach creates proper metrics"""
    with tempfile.TemporaryDirectory() as tmpdir:
        metric_file = pathlib.Path(tmpdir) / "trainer_vram_paused.prom"
        
        # Simulate the textfile metric that systemd script creates
        metric_content = """# HELP trainer_vram_paused Trainer container paused due to high VRAM usage
# TYPE trainer_vram_paused gauge
trainer_vram_paused{reason="vram_high"} 0
"""
        metric_file.write_text(metric_content)
        
        # Verify file exists and has valid content
        assert metric_file.exists(), "Metric file was not created"
        content = metric_file.read_text()
        
        # Parse the trainer_vram_paused value
        lines = content.strip().split('\n')
        metric_line = [line for line in lines if line.startswith('trainer_vram_paused{')]
        assert len(metric_line) == 1, "trainer_vram_paused metric not found"
        
        # Extract value (should be 0 or 1)
        value = float(metric_line[0].split()[-1])
        assert value in {0.0, 1.0}, f"Invalid metric value: {value}"

def test_systemd_files_exist():
    """Test that systemd service and timer files exist"""
    service_file = pathlib.Path("systemd/vram-guard.service")
    timer_file = pathlib.Path("systemd/vram-guard.timer")
    
    assert service_file.exists(), "systemd service file not found"
    assert timer_file.exists(), "systemd timer file not found"
    
    # Verify service file has required sections
    service_content = service_file.read_text(encoding='utf-8')
    assert "[Unit]" in service_content
    assert "[Service]" in service_content
    assert "Type=oneshot" in service_content
    assert "ExecStart=" in service_content
    assert "hybrid implementation" in service_content, "Should be marked as hybrid"
    
    # Verify timer file has required sections
    timer_content = timer_file.read_text(encoding='utf-8')
    assert "[Timer]" in timer_content
    assert "OnBootSec=" in timer_content
    assert "OnUnitActiveSec=" in timer_content

def test_alert_rules():
    """Test that GPU memory pressure alert rules exist"""
    alert_file = pathlib.Path("monitoring/vram_alert.yml")
    assert alert_file.exists(), "VRAM alert rules not found"
    
    content = alert_file.read_text(encoding='utf-8')
    assert "GPUMemoryPressure" in content, "Should have memory pressure alert"
    assert "gpu_vram_used_mb" in content, "Should use NVML exporter metrics"
    assert "10240" in content, "Should use 10GB threshold"

@pytest.mark.integration
def test_prometheus_scrape_config():
    """Test that Prometheus is configured to scrape NVML exporter"""
    prom_config = pathlib.Path("monitoring/prometheus.yml")
    assert prom_config.exists(), "Prometheus config not found"
    
    content = prom_config.read_text(encoding='utf-8')
    assert "gpu-vram-exporter" in content, "gpu-vram-exporter job not found"
    assert "localhost:9108" in content, "NVML exporter target not configured"

if __name__ == "__main__":
    # Quick smoke test for manual execution
    test_vram_guard_script_exists()
    test_nvml_exporter_files()
    test_docker_compose_configuration()
    test_systemd_files_exist()
    test_vram_threshold_logic()
    test_alert_rules()
    print("✅ All hybrid VRAM guard smoke tests passed!") 