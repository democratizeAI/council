"""
🧪 Unit Tests for Early-Stop Guard (Ticket #223)
Tests the safety validation and automatic fixes for training configurations
"""

import pytest
import yaml
import tempfile
import os
from pathlib import Path
from training.early_stop_guard import EarlyStopGuard, EarlyStopGuardError, mutate_early_stopping_config

class TestEarlyStopGuard:
    """Test suite for the EarlyStopGuard class"""
    
    @pytest.fixture
    def safe_config(self):
        """A safe training configuration"""
        return {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 3,
                    'min_delta': 0.001,
                    'monitor': 'eval_loss',
                    'mode': 'min',
                    'restore_best_weights': True
                }
            }
        }
    
    @pytest.fixture
    def unsafe_config(self):
        """An unsafe training configuration"""
        return {
            'training': {
                'epochs': 2,  # Too few epochs
                'early_stopping': {
                    'enabled': True,
                    'patience': 1,  # Too low patience
                    'min_delta': 0,  # Invalid min_delta
                    'monitor': 'invalid_metric',  # Invalid monitor
                    'mode': 'max'  # Wrong mode for loss
                }
            }
        }
    
    @pytest.fixture
    def temp_config_file(self, safe_config):
        """Create a temporary config file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(safe_config, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        os.unlink(temp_path)
    
    def test_load_config_success(self, temp_config_file):
        """Test successful config loading"""
        guard = EarlyStopGuard(temp_config_file)
        assert guard.config is not None
        assert 'training' in guard.config
    
    def test_load_config_file_not_found(self):
        """Test handling of missing config file"""
        with pytest.raises(EarlyStopGuardError, match="Training config not found"):
            EarlyStopGuard("nonexistent_config.yml")
    
    def test_validate_safe_config(self, temp_config_file):
        """Test validation of a safe configuration"""
        guard = EarlyStopGuard(temp_config_file)
        is_safe, reason = guard.validate_early_stopping_config()
        
        assert is_safe is True
        assert "safe" in reason
    
    def test_validate_disabled_early_stopping(self):
        """Test validation when early stopping is disabled"""
        config = {
            'training': {
                'epochs': 5,
                'early_stopping': {
                    'enabled': False,
                    'patience': 1  # This would be unsafe if enabled
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is True
            assert "disabled" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_too_few_epochs(self):
        """Test validation with too few epochs"""
        config = {
            'training': {
                'epochs': 2,
                'early_stopping': {
                    'enabled': True,
                    'patience': 1,
                    'min_delta': 0.001,
                    'monitor': 'eval_loss',
                    'mode': 'min'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "Too few epochs" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_low_patience(self):
        """Test validation with too low patience"""
        config = {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 1,
                    'min_delta': 0.001,
                    'monitor': 'eval_loss',
                    'mode': 'min'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "Patience too low" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_high_patience_ratio(self):
        """Test validation with patience ratio too high"""
        config = {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 6,  # 60% of epochs
                    'min_delta': 0.001,
                    'monitor': 'eval_loss',
                    'mode': 'min'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "Patience too high" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_invalid_min_delta(self):
        """Test validation with invalid min_delta"""
        config = {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 3,
                    'min_delta': 0,  # Invalid
                    'monitor': 'eval_loss',
                    'mode': 'min'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "min_delta must be positive" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_invalid_monitor(self):
        """Test validation with invalid monitor metric"""
        config = {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 3,
                    'min_delta': 0.001,
                    'monitor': 'invalid_metric',
                    'mode': 'min'
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "Invalid monitor metric" in reason
        finally:
            os.unlink(temp_path)
    
    def test_validate_unsafe_config_wrong_mode(self):
        """Test validation with wrong mode for loss metric"""
        config = {
            'training': {
                'epochs': 10,
                'early_stopping': {
                    'enabled': True,
                    'patience': 3,
                    'min_delta': 0.001,
                    'monitor': 'eval_loss',
                    'mode': 'max'  # Wrong mode for loss
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.safe_dump(config, f)
            temp_path = f.name
        
        try:
            guard = EarlyStopGuard(temp_path)
            is_safe, reason = guard.validate_early_stopping_config()
            
            assert is_safe is False
            assert "Loss metrics should use mode='min'" in reason
        finally:
            os.unlink(temp_path)
    
    def test_apply_safety_guards_safe_config(self, temp_config_file):
        """Test applying guards to already safe config"""
        guard = EarlyStopGuard(temp_config_file)
        guarded_config = guard.apply_safety_guards()
        
        assert guarded_config is not None
        assert guarded_config == guard.config
    
    def test_get_safety_report(self, temp_config_file):
        """Test safety report generation"""
        guard = EarlyStopGuard(temp_config_file)
        report = guard.get_safety_report()
        
        assert 'is_safe' in report
        assert 'reason' in report
        assert 'config_path' in report
        assert 'early_stopping_enabled' in report
        assert 'current_settings' in report
        
        assert report['is_safe'] is True
        assert report['early_stopping_enabled'] is True
    
    def test_mutate_early_stopping_config(self, temp_config_file):
        """Test yq-style mutation function"""
        result = mutate_early_stopping_config(
            temp_config_file,
            patience=5,
            min_delta=0.005
        )
        
        assert result is not None
        early_stopping = result['training']['early_stopping']
        assert early_stopping['patience'] == 5
        assert early_stopping['min_delta'] == 0.005

class TestEarlyStopGuardErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_yaml_file(self):
        """Test handling of invalid YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed bracket")
            temp_path = f.name
        
        try:
            with pytest.raises(EarlyStopGuardError, match="Invalid YAML"):
                EarlyStopGuard(temp_path)
        finally:
            os.unlink(temp_path)

# Test coverage markers
pytestmark = pytest.mark.early_stop_guard

if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([__file__, "-v", "--cov=training.early_stop_guard", "--cov-report=term-missing"]) 