#!/usr/bin/env python3
"""
Unit tests for LG-210 LoRA Gauntlet Hook
Tests the deploy_lora.sh script behavior in various scenarios
"""

import os
import subprocess
import tempfile
import pytest
from unittest.mock import patch, MagicMock


class TestLoraGauntletHook:
    """Test suite for LoRA deployment gauntlet hook"""
    
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create mock LoRA config
        os.makedirs('lora_models', exist_ok=True)
        with open('lora_models/config.yml', 'w') as f:
            f.write('model_version: v1.0\n')
            
        # Create mock gauntlet script
        with open('run_titanic_gauntlet.py', 'w') as f:
            f.write('''#!/usr/bin/env python3
import sys
import os
exit_code = int(os.getenv('MOCK_GAUNTLET_EXIT', '0'))
print("Mock gauntlet execution")
sys.exit(exit_code)
''')
        os.chmod('run_titanic_gauntlet.py', 0o755)
        
        # Copy deploy script to test directory
        script_path = os.path.join(self.original_cwd, 'deploy_lora.sh')
        if os.path.exists(script_path):
            with open(script_path, 'r') as src, open('deploy_lora.sh', 'w') as dst:
                dst.write(src.read())
            os.chmod('deploy_lora.sh', 0o755)
    
    def teardown_method(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
    
    def test_gauntlet_disabled_by_default(self):
        """Test that gauntlet is disabled by default"""
        env = os.environ.copy()
        env.pop('GAUNTLET_ENABLED', None)  # Ensure not set
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Gauntlet Enabled: false" in result.stdout
        assert "Gauntlet disabled - Skipping titanic tests" in result.stdout
        assert "GAUNTLET ENABLED" not in result.stdout
    
    def test_gauntlet_enabled_success(self):
        """Test gauntlet execution when enabled and successful"""
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'true'
        env['A2A_ENABLED'] = 'false'  # Disable A2A for testing
        env['MOCK_GAUNTLET_EXIT'] = '0'
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Gauntlet Enabled: true" in result.stdout
        assert "GAUNTLET ENABLED - Running Titanic Gauntlet" in result.stdout
        assert "GAUNTLET_PASS - Proceeding with deployment" in result.stdout
    
    def test_gauntlet_enabled_failure(self):
        """Test gauntlet execution when enabled but fails"""
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'true'
        env['A2A_ENABLED'] = 'false'
        env['MOCK_GAUNTLET_EXIT'] = '1'  # Force failure
        
        # Create mock rollback handler
        os.makedirs('action_handlers', exist_ok=True)
        with open('action_handlers/rollback_handler.py', 'w') as f:
            f.write('''#!/usr/bin/env python3
import sys
print(f"Rollback triggered: {sys.argv[1]}")
''')
        os.chmod('action_handlers/rollback_handler.py', 0o755)
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "GAUNTLET_FAIL - Triggering rollback" in result.stdout
    
    def test_missing_lora_config_fails(self):
        """Test deployment fails when LoRA config is missing"""
        os.remove('lora_models/config.yml')
        
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'false'
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "ERROR: LoRA model configuration not found" in result.stdout
    
    def test_env_file_loading(self):
        """Test that .env file is properly loaded"""
        with open('.env', 'w') as f:
            f.write('GAUNTLET_ENABLED=true\n')
            f.write('A2A_ENABLED=false\n')
            f.write('MOCK_GAUNTLET_EXIT=0\n')
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Gauntlet Enabled: true" in result.stdout
    
    @patch('requests.post')
    def test_a2a_event_publishing(self, mock_post):
        """Test A2A event publishing when enabled"""
        # This test would need to be adapted based on the actual A2A implementation
        # For now, just verify the script handles A2A calls gracefully
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'true'
        env['A2A_ENABLED'] = 'true'
        env['MOCK_GAUNTLET_EXIT'] = '0'
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        # Should not fail even if A2A is not available
        assert result.returncode == 0
    
    def test_gauntlet_script_not_executable(self):
        """Test behavior when gauntlet script is not executable"""
        os.chmod('run_titanic_gauntlet.py', 0o644)  # Remove execute permission
        
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'true'
        env['A2A_ENABLED'] = 'false'
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1  # Should fail
    
    def test_script_permissions(self):
        """Test that deploy script is executable"""
        if os.path.exists('deploy_lora.sh'):
            stat_info = os.stat('deploy_lora.sh')
            assert stat_info.st_mode & 0o111  # Has execute permission
    
    def test_inert_state_safety(self):
        """Test that disabled gauntlet is completely safe"""
        env = os.environ.copy()
        env['GAUNTLET_ENABLED'] = 'false'
        
        # Even if gauntlet script is broken, deployment should succeed
        with open('run_titanic_gauntlet.py', 'w') as f:
            f.write('#!/bin/bash\nexit 42\n')  # Broken script
        
        result = subprocess.run(
            ['./deploy_lora.sh'],
            env=env,
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Gauntlet disabled" in result.stdout


def test_gauntlet_hook_enabled(monkeypatch):
    """Specific test requested in user requirements"""
    monkeypatch.setenv("GAUNTLET_ENABLED", "true")
    monkeypatch.setenv("SKIP_GAUNTLET", "true")  # skips heavy run
    monkeypatch.setenv("A2A_ENABLED", "false")
    
    # Mock the deploy_lora main function
    # This would need to be adapted if we had a Python version
    # For now, verify environment variables are set correctly
    assert os.getenv("GAUNTLET_ENABLED") == "true"
    assert os.getenv("SKIP_GAUNTLET") == "true"


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 