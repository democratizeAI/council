import random
import yaml
import pathlib
import logging
from typing import Dict, Any, Optional
from api.metrics import adapter_select_total

logger = logging.getLogger(__name__)

# Global weight table - loaded from config
_WEIGHT_TABLE: Optional[Dict[str, Dict[str, float]]] = None

def _load_weight_table() -> Dict[str, Dict[str, float]]:
    """Load adapter weights from YAML config"""
    global _WEIGHT_TABLE
    
    if _WEIGHT_TABLE is not None:
        return _WEIGHT_TABLE
    
    config_path = pathlib.Path(__file__).parent.parent / "config" / "adapter_weights.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            _WEIGHT_TABLE = config['clusters']
            
        logger.info(f"Loaded adapter weights for {len(_WEIGHT_TABLE)} clusters")
        
        # Validate weights sum properly
        for cluster_id, weights in _WEIGHT_TABLE.items():
            total_weight = sum(weights.values())
            if total_weight < 0.01:  # Effectively zero
                logger.warning(f"Cluster {cluster_id} has very low total weight: {total_weight}")
        
        return _WEIGHT_TABLE
        
    except FileNotFoundError:
        logger.error(f"Weight config not found: {config_path}")
        # Emergency fallback
        _WEIGHT_TABLE = {
            'default': {'base': 1.0}
        }
        return _WEIGHT_TABLE
        
    except Exception as e:
        logger.error(f"Failed to load weight config: {e}")
        _WEIGHT_TABLE = {
            'default': {'base': 1.0}
        }
        return _WEIGHT_TABLE

def reload_weight_table() -> bool:
    """Hot-reload the weight table from disk"""
    global _WEIGHT_TABLE
    _WEIGHT_TABLE = None
    
    try:
        _load_weight_table()
        logger.info("Weight table reloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to reload weight table: {e}")
        return False

def choose_adapter(cluster_id: str) -> str:
    """
    Choose adapter using weighted random selection
    
    Args:
        cluster_id: The cluster identifier from pattern-miner
        
    Returns:
        Selected adapter name (e.g., 'base', 'lora-2048', 'code-specialist-v2')
    """
    weight_table = _load_weight_table()
    
    # Default fallback guard
    if cluster_id not in weight_table:
        logger.debug(f"Cluster {cluster_id} not in weight table, using default")
        cluster_id = 'default'
    
    # Get weights for this cluster
    weights = weight_table[cluster_id]
    
    if not weights:
        logger.warning(f"Empty weights for cluster {cluster_id}, falling back to base")
        adapter_name = 'base'
    else:
        # Weighted random selection
        adapters = list(weights.keys())
        probabilities = list(weights.values())
        
        try:
            adapter_name = random.choices(adapters, weights=probabilities, k=1)[0]
        except (ValueError, IndexError) as e:
            logger.error(f"Failed weighted selection for {cluster_id}: {e}")
            adapter_name = 'base'
    
    # Track selection in metrics
    adapter_select_total.labels(adapter=adapter_name).inc()
    
    logger.debug(f"Selected adapter '{adapter_name}' for cluster '{cluster_id}'")
    return adapter_name

def get_weight_stats() -> Dict[str, Any]:
    """Get statistics about the current weight configuration"""
    weight_table = _load_weight_table()
    
    total_clusters = len(weight_table)
    adapters_used = set()
    cluster_weights = {}
    
    for cluster_id, weights in weight_table.items():
        adapters_used.update(weights.keys())
        cluster_weights[cluster_id] = {
            'total_weight': sum(weights.values()),
            'adapter_count': len(weights),
            'top_adapter': max(weights.items(), key=lambda x: x[1]) if weights else None
        }
    
    return {
        'total_clusters': total_clusters,
        'unique_adapters': len(adapters_used),
        'adapters_used': sorted(list(adapters_used)),
        'cluster_weights': cluster_weights,
        'has_default': 'default' in weight_table
    }

def validate_weights() -> Dict[str, Any]:
    """Validate weight configuration for deployment readiness"""
    weight_table = _load_weight_table()
    issues = []
    warnings = []
    
    for cluster_id, weights in weight_table.items():
        total_weight = sum(weights.values())
        
        # Check for zero/negative weights
        if total_weight <= 0:
            issues.append(f"Cluster {cluster_id} has zero/negative total weight: {total_weight}")
        
        # Check for very low weights (might indicate misconfiguration)
        if total_weight < 0.1:
            warnings.append(f"Cluster {cluster_id} has very low total weight: {total_weight}")
        
        # Check for empty weight dict
        if not weights:
            issues.append(f"Cluster {cluster_id} has no adapters defined")
    
    # Check for default cluster
    if 'default' not in weight_table:
        warnings.append("No 'default' cluster defined - unmapped clusters will error")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'clusters_checked': len(weight_table)
    } 