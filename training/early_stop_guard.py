"""
🚦 Early-Stop Guard (Ticket #223)
Protects training runs from premature termination due to misconfigured early stopping
"""

import yaml
import logging
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class EarlyStopGuardError(Exception):
    """Exception raised when early stopping configuration is unsafe"""
    pass

class EarlyStopGuard:
    """
    Guards against unsafe early stopping configurations that could 
    terminate training prematurely or waste compute resources.
    """
    
    def __init__(self, config_path: str = "config/training.yml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load training configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise EarlyStopGuardError(f"Training config not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise EarlyStopGuardError(f"Invalid YAML in {self.config_path}: {e}")
    
    def validate_early_stopping_config(self) -> Tuple[bool, str]:
        """
        Validates early stopping configuration for safety
        
        Returns:
            Tuple[bool, str]: (is_safe, reason)
        """
        training = self.config.get('training', {})
        early_stopping = training.get('early_stopping', {})
        
        if not early_stopping.get('enabled', False):
            return True, "Early stopping disabled - safe"
        
        # Check minimum epochs requirement
        epochs = training.get('epochs', 0)
        patience = early_stopping.get('patience', 1)
        
        if epochs < 3:
            return False, f"Too few epochs ({epochs}) for early stopping - minimum 3 required"
        
        if patience < 2:
            return False, f"Patience too low ({patience}) - minimum 2 epochs required"
        
        # Check patience vs epochs ratio
        patience_ratio = patience / epochs
        if patience_ratio > 0.5:
            return False, f"Patience too high ({patience}/{epochs} = {patience_ratio:.2f}) - max 50% of epochs"
        
        # Check minimum delta
        min_delta = early_stopping.get('min_delta', 0)
        if min_delta <= 0:
            return False, "min_delta must be positive for meaningful early stopping"
        
        if min_delta > 0.1:
            return False, f"min_delta too high ({min_delta}) - maximum 0.1 recommended"
        
        # Validate monitor metric
        monitor = early_stopping.get('monitor', '')
        valid_metrics = ['eval_loss', 'eval_accuracy', 'val_loss', 'val_accuracy', 'train_loss']
        if monitor not in valid_metrics:
            return False, f"Invalid monitor metric '{monitor}' - use one of {valid_metrics}"
        
        # Check mode consistency
        mode = early_stopping.get('mode', 'min')
        if monitor.endswith('_loss') and mode != 'min':
            return False, f"Loss metrics should use mode='min', got '{mode}'"
        
        if monitor.endswith('_accuracy') and mode != 'max':
            return False, f"Accuracy metrics should use mode='max', got '{mode}'"
        
        return True, "Early stopping configuration is safe"
    
    def apply_safety_guards(self) -> Dict[str, Any]:
        """
        Apply safety guards to the configuration
        
        Returns:
            Dict with the guarded configuration
        """
        is_safe, reason = self.validate_early_stopping_config()
        
        if not is_safe:
            logger.warning(f"Unsafe early stopping config: {reason}")
            
            # Apply automatic fixes
            guarded_config = self._apply_automatic_fixes()
            
            # Validate again
            self.config = guarded_config
            is_safe_after_fix, fix_reason = self.validate_early_stopping_config()
            
            if is_safe_after_fix:
                logger.info(f"Applied safety guards: {fix_reason}")
                return guarded_config
            else:
                raise EarlyStopGuardError(f"Could not make config safe: {fix_reason}")
        
        logger.info(f"Early stopping config is safe: {reason}")
        return self.config
    
    def _apply_automatic_fixes(self) -> Dict[str, Any]:
        """Apply automatic safety fixes to the configuration"""
        config_copy = yaml.safe_load(yaml.safe_dump(self.config))  # Deep copy
        training = config_copy.get('training', {})
        early_stopping = training.get('early_stopping', {})
        
        epochs = training.get('epochs', 10)
        
        # Fix patience if too low or too high
        current_patience = early_stopping.get('patience', 1)
        min_patience = max(2, epochs // 10)  # At least 2, or 10% of epochs
        max_patience = epochs // 3  # Maximum 33% of epochs
        
        if current_patience < min_patience:
            early_stopping['patience'] = min_patience
            logger.info(f"Increased patience from {current_patience} to {min_patience}")
        
        if current_patience > max_patience:
            early_stopping['patience'] = max_patience
            logger.info(f"Decreased patience from {current_patience} to {max_patience}")
        
        # Fix min_delta if invalid
        current_min_delta = early_stopping.get('min_delta', 0)
        if current_min_delta <= 0:
            early_stopping['min_delta'] = 0.001
            logger.info("Set min_delta to 0.001 (was <= 0)")
        
        if current_min_delta > 0.1:
            early_stopping['min_delta'] = 0.01
            logger.info(f"Reduced min_delta from {current_min_delta} to 0.01")
        
        # Fix monitor metric if invalid
        monitor = early_stopping.get('monitor', '')
        if monitor not in ['eval_loss', 'eval_accuracy', 'val_loss', 'val_accuracy', 'train_loss']:
            early_stopping['monitor'] = 'eval_loss'
            logger.info(f"Changed monitor from '{monitor}' to 'eval_loss'")
        
        # Fix mode if inconsistent
        monitor = early_stopping.get('monitor', 'eval_loss')
        mode = early_stopping.get('mode', 'min')
        
        if monitor.endswith('_loss') and mode != 'min':
            early_stopping['mode'] = 'min'
            logger.info(f"Changed mode to 'min' for loss metric")
        
        if monitor.endswith('_accuracy') and mode != 'max':
            early_stopping['mode'] = 'max'
            logger.info(f"Changed mode to 'max' for accuracy metric")
        
        return config_copy
    
    def get_safety_report(self) -> Dict[str, Any]:
        """Generate a comprehensive safety report"""
        is_safe, reason = self.validate_early_stopping_config()
        
        training = self.config.get('training', {})
        early_stopping = training.get('early_stopping', {})
        
        return {
            'is_safe': is_safe,
            'reason': reason,
            'config_path': str(self.config_path),
            'early_stopping_enabled': early_stopping.get('enabled', False),
            'current_settings': {
                'epochs': training.get('epochs'),
                'patience': early_stopping.get('patience'),
                'min_delta': early_stopping.get('min_delta'),
                'monitor': early_stopping.get('monitor'),
                'mode': early_stopping.get('mode')
            }
        }

# yq-style mutation function
def mutate_early_stopping_config(config_path: str, **kwargs) -> Dict[str, Any]:
    """
    Mutate early stopping configuration safely using yq-style operations
    """
    guard = EarlyStopGuard(config_path)
    
    # Apply mutations
    config = guard.config
    early_stopping = config.setdefault('training', {}).setdefault('early_stopping', {})
    
    for key, value in kwargs.items():
        early_stopping[key] = value
        logger.info(f"Mutated early_stopping.{key} = {value}")
    
    # Re-validate with mutations
    guard.config = config
    guarded_config = guard.apply_safety_guards()
    
    return guarded_config
