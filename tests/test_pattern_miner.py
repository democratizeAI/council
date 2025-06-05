#!/usr/bin/env python3
"""
Pattern Miner Tests
Tests for HDBSCAN clustering and Redis integration
"""

import pytest
import json
import redis
from unittest.mock import patch, MagicMock

def test_cluster_write(redis_client=None):
    """Test that clustering writes to Redis correctly"""
    # Mock Redis if not provided
    if redis_client is None:
        redis_client = MagicMock()
        redis_client.lrange.return_value = ['{"text":"test pattern"}']
        redis_client.hset = MagicMock()
        redis_client.incr = MagicMock()
        redis_client.ltrim = MagicMock()
    
    # Import and test pattern miner
    import pattern_miner as pm
    
    # Test batch processing
    test_batch = [{"text": "test pattern"}]
    
    with patch('pattern_miner.R', redis_client):
        with patch('pattern_miner.EMB') as mock_emb:
            with patch('pattern_miner.hdbscan.HDBSCAN') as mock_hdbscan:
                # Mock embeddings and clustering
                mock_emb.encode.return_value = [[0.1, 0.2, 0.3]]
                mock_clusterer = MagicMock()
                mock_clusterer.fit_predict.return_value = [0]  # Cluster ID 0
                mock_hdbscan.return_value = mock_clusterer
                
                # Run batch mining
                pm.mine_batch(test_batch)
                
                # Verify Redis calls
                redis_client.hset.assert_called()
                redis_client.incr.assert_called_with("pattern_clusters_total")

def test_pattern_miner_import():
    """Test that pattern_miner imports without errors"""
    try:
        import pattern_miner
        assert hasattr(pattern_miner, 'mine_batch')
        assert hasattr(pattern_miner, 'run')
    except ImportError as e:
        pytest.fail(f"Pattern miner import failed: {e}")

def test_hdbscan_available():
    """Test that HDBSCAN is available"""
    try:
        import hdbscan
        from sentence_transformers import SentenceTransformer
        assert True
    except ImportError:
        pytest.fail("HDBSCAN or SentenceTransformers not available")

@pytest.mark.asyncio
async def test_redis_integration():
    """Test Redis integration with mocked client"""
    mock_redis = MagicMock()
    mock_redis.lrange.return_value = []
    
    import pattern_miner as pm
    
    with patch('pattern_miner.R', mock_redis):
        with patch('time.sleep'):  # Mock sleep to avoid waiting
            with patch('pattern_miner.json.loads', side_effect=StopIteration):
                # This should exit the loop due to StopIteration
                try:
                    pm.run()
                except StopIteration:
                    pass
    
    # Verify Redis was called
    mock_redis.lrange.assert_called()

if __name__ == "__main__":
    test_pattern_miner_import()
    test_hdbscan_available()
    test_cluster_write()
    print("✅ All pattern miner tests passed!") 