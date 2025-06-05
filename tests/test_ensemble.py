import pytest
import asyncio
import redis.asyncio as redis
from unittest.mock import Mock, AsyncMock, patch
from api.routes.ensemble import router
from api.middleware.ensemble import EnsembleMiddleware
from lora.manager import get, clear_cache, get_cache_stats
import json
import hashlib

@pytest.fixture
async def redis_client():
    """Redis client for testing"""
    client = redis.Redis.from_url("redis://localhost:6379/1", decode_responses=True)  # Use test DB
    yield client
    await client.flushdb()  # Clean up after tests
    await client.close()

@pytest.fixture  
def mock_app():
    """Mock FastAPI app for middleware testing"""
    app = Mock()
    return app

@pytest.fixture
def mock_request():
    """Mock request object"""
    request = Mock()
    request.url.path = "/orchestrate"
    request.state = Mock()
    return request

class TestEnsembleRoutes:
    """Test ensemble admin endpoints"""
    
    async def test_set_mapping(self, redis_client):
        """Test setting cluster-to-adapter mapping"""
        await redis_client.hset("lora:router_map", "c42", "2025-06-07")
        
        # Verify mapping was set
        adapter_tag = await redis_client.hget("lora:router_map", "c42")
        assert adapter_tag == "2025-06-07"
    
    async def test_get_mappings(self, redis_client):
        """Test retrieving all mappings"""
        # Set up test data
        test_mappings = {
            "c17": "2025-06-06",
            "c42": "2025-06-07",
            "c88": "2025-06-08"
        }
        
        for cluster_id, adapter_tag in test_mappings.items():
            await redis_client.hset("lora:router_map", cluster_id, adapter_tag)
        
        # Retrieve mappings
        mappings = await redis_client.hgetall("lora:router_map")
        assert mappings == test_mappings
        assert len(mappings) == 3
    
    async def test_remove_mapping(self, redis_client):
        """Test removing cluster mapping"""
        # Set up mapping
        await redis_client.hset("lora:router_map", "c99", "test-adapter")
        
        # Verify it exists
        assert await redis_client.hget("lora:router_map", "c99") == "test-adapter"
        
        # Remove mapping
        result = await redis_client.hdel("lora:router_map", "c99")
        assert result == 1  # 1 key deleted
        
        # Verify removal
        assert await redis_client.hget("lora:router_map", "c99") is None
    
    async def test_bulk_mappings(self, redis_client):
        """Test bulk mapping operations"""
        bulk_mappings = {
            "c10": "adapter-v1",
            "c20": "adapter-v2", 
            "c30": "adapter-v3"
        }
        
        # Set bulk mappings using pipeline
        async with redis_client.pipeline() as pipe:
            for cluster_id, adapter_tag in bulk_mappings.items():
                await pipe.hset("lora:router_map", cluster_id, adapter_tag)
            await pipe.execute()
        
        # Verify all mappings were set
        for cluster_id, expected_adapter in bulk_mappings.items():
            actual_adapter = await redis_client.hget("lora:router_map", cluster_id)
            assert actual_adapter == expected_adapter

class TestEnsembleMiddleware:
    """Test ensemble middleware routing logic"""
    
    @patch('lora.manager.get')
    async def test_adapter_resolution_success(self, mock_get_adapter, redis_client):
        """Test successful adapter resolution"""
        # Setup
        prompt = "test prompt for clustering"
        prompt_hash = hashlib.sha1(prompt.encode()).hexdigest()
        cluster_id = "c42"
        adapter_tag = "2025-06-07"
        
        # Set up Redis data
        await redis_client.set(f"pattern:cluster:{prompt_hash}", cluster_id)
        await redis_client.hset("lora:router_map", cluster_id, adapter_tag)
        
        # Mock adapter loading
        mock_adapter = Mock()
        mock_get_adapter.return_value = mock_adapter
        
        # Create middleware
        middleware = EnsembleMiddleware(None)
        middleware.redis = redis_client
        
        # Test adapter resolution
        result = await middleware._resolve_adapter(prompt)
        
        assert result["cluster_id"] == cluster_id
        assert result["adapter_tag"] == adapter_tag
        assert result["adapter"] == mock_adapter
        assert result["is_miss"] == False
        mock_get_adapter.assert_called_once_with(adapter_tag)
    
    async def test_no_cluster_mapping(self, redis_client):
        """Test handling when prompt has no cluster mapping"""
        middleware = EnsembleMiddleware(None)
        middleware.redis = redis_client
        
        result = await middleware._resolve_adapter("unmapped prompt")
        
        assert result["is_miss"] == True
        assert result["reason"] == "no_cluster_mapping"
    
    async def test_no_adapter_mapping(self, redis_client):
        """Test handling when cluster has no adapter mapping"""
        prompt = "test prompt"
        prompt_hash = hashlib.sha1(prompt.encode()).hexdigest()
        cluster_id = "c999"
        
        # Set cluster but no adapter mapping
        await redis_client.set(f"pattern:cluster:{prompt_hash}", cluster_id)
        
        middleware = EnsembleMiddleware(None)
        middleware.redis = redis_client
        
        result = await middleware._resolve_adapter(prompt)
        
        assert result["cluster_id"] == cluster_id
        assert result["is_miss"] == True
        assert result["reason"] == "no_adapter_mapping"
    
    @patch('lora.manager.get')
    async def test_adapter_load_failure(self, mock_get_adapter, redis_client):
        """Test handling when adapter fails to load"""
        prompt = "test prompt"
        prompt_hash = hashlib.sha1(prompt.encode()).hexdigest()
        cluster_id = "c42"
        adapter_tag = "broken-adapter"
        
        # Set up Redis data
        await redis_client.set(f"pattern:cluster:{prompt_hash}", cluster_id)
        await redis_client.hset("lora:router_map", cluster_id, adapter_tag)
        
        # Mock adapter loading failure
        mock_get_adapter.side_effect = FileNotFoundError("Adapter not found")
        
        middleware = EnsembleMiddleware(None)
        middleware.redis = redis_client
        
        result = await middleware._resolve_adapter(prompt)
        
        assert result["cluster_id"] == cluster_id
        assert result["adapter_tag"] == adapter_tag
        assert result["is_miss"] == True
        assert result["reason"] == "adapter_load_failed"
        assert "Adapter not found" in result["error"]

class TestLoRAManager:
    """Test LoRA adapter manager"""
    
    def test_cache_initialization(self):
        """Test cache starts empty"""
        clear_cache()
        stats = get_cache_stats()
        assert stats["cache_size"] == 0
        assert stats["loaded_adapters"] == []
    
    @patch('lora.manager._load_adapter')
    def test_adapter_loading_and_caching(self, mock_load_adapter):
        """Test adapter loading and LRU caching"""
        clear_cache()
        
        # Mock adapter loading
        mock_adapter = Mock()
        mock_load_adapter.return_value = mock_adapter
        
        # Load adapter
        result = get("test-adapter")
        
        assert result == mock_adapter
        mock_load_adapter.assert_called_once_with("test-adapter")
        
        # Check cache
        stats = get_cache_stats()
        assert stats["cache_size"] == 1
        assert "test-adapter" in stats["loaded_adapters"]
    
    @patch('lora.manager._load_adapter')
    def test_cache_hit(self, mock_load_adapter):
        """Test cache hit behavior"""
        clear_cache()
        
        mock_adapter = Mock()
        mock_load_adapter.return_value = mock_adapter
        
        # First call loads
        result1 = get("cached-adapter")
        assert mock_load_adapter.call_count == 1
        
        # Second call hits cache
        result2 = get("cached-adapter")
        assert result1 == result2
        assert mock_load_adapter.call_count == 1  # No additional loading
    
    @patch('lora.manager._load_adapter')
    @patch('lora.manager.MAX_ADAPTERS', 2)  # Force small cache for testing
    def test_lru_eviction(self, mock_load_adapter):
        """Test LRU eviction when cache is full"""
        clear_cache()
        
        # Mock multiple adapters
        mock_adapters = [Mock() for _ in range(3)]
        mock_load_adapter.side_effect = mock_adapters
        
        # Load adapters up to capacity
        get("adapter-1")
        get("adapter-2")
        
        stats = get_cache_stats()
        assert stats["cache_size"] == 2
        assert set(stats["loaded_adapters"]) == {"adapter-1", "adapter-2"}
        
        # Load third adapter, should evict first
        get("adapter-3")
        
        stats = get_cache_stats()
        assert stats["cache_size"] == 2
        assert "adapter-1" not in stats["loaded_adapters"]  # Evicted
        assert set(stats["loaded_adapters"]) == {"adapter-2", "adapter-3"}

class TestIntegration:
    """Integration tests for full ensemble workflow"""
    
    @patch('lora.manager._load_adapter')
    async def test_full_ensemble_workflow(self, mock_load_adapter, redis_client):
        """Test complete ensemble workflow from prompt to adapter"""
        clear_cache()
        
        # Setup test data
        prompt = "Write a Python function to calculate fibonacci"
        prompt_hash = hashlib.sha1(prompt.encode()).hexdigest()
        cluster_id = "c_programming"
        adapter_tag = "code-specialist-v2"
        
        # Mock adapter
        mock_adapter = Mock()
        mock_load_adapter.return_value = mock_adapter
        
        # Setup Redis mappings
        await redis_client.set(f"pattern:cluster:{prompt_hash}", cluster_id)
        await redis_client.hset("lora:router_map", cluster_id, adapter_tag)
        
        # Create middleware and process request
        middleware = EnsembleMiddleware(None)
        middleware.redis = redis_client
        
        # Test resolution
        result = await middleware._resolve_adapter(prompt)
        
        # Verify complete workflow
        assert result["cluster_id"] == cluster_id
        assert result["adapter_tag"] == adapter_tag
        assert result["adapter"] == mock_adapter
        assert result["is_miss"] == False
        assert result["resolution_time"] > 0
        
        # Verify adapter is cached
        stats = get_cache_stats()
        assert adapter_tag in stats["loaded_adapters"]
        assert stats["cache_size"] == 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 