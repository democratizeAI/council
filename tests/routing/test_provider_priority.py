"""
Provider Priority Regression Tests
==================================

Tests to ensure provider priority system works correctly
and prevent accidental re-ordering of providers.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# Mock the router modules
@pytest.fixture
def mock_providers():
    """Mock the provider modules"""
    with patch('router.hybrid.PROVIDER_MAP') as mock_map:
        mock_mistral = AsyncMock()
        mock_openai = AsyncMock()
        
        mock_map.__getitem__.side_effect = lambda x: {
            'mistral': mock_mistral,
            'openai': mock_openai
        }[x]
        
        yield mock_mistral, mock_openai

def test_priority_mistral_first(monkeypatch, mock_providers):
    """Test that Mistral is tried first in priority list"""
    monkeypatch.setenv("PROVIDER_PRIORITY", "mistral,openai")
    
    # Import after setting env var
    from router.hybrid import call_llm
    
    mock_mistral, mock_openai = mock_providers
    
    # Setup: Mistral succeeds, OpenAI should never be called
    mock_mistral.return_value = {"text": "Success from Mistral", "provider": "mistral"}
    mock_openai.return_value = {"text": "This should not be called", "provider": "openai"}
    
    result = asyncio.run(call_llm("test prompt"))
    
    # Assertions
    mock_mistral.assert_called_once()
    mock_openai.assert_not_called()
    assert result["provider"] == "mistral"

def test_fallback_to_openai(monkeypatch, mock_providers):
    """Test fallback when Mistral fails"""
    monkeypatch.setenv("PROVIDER_PRIORITY", "mistral,openai")
    
    from router.hybrid import call_llm
    from providers import CloudRetry
    
    mock_mistral, mock_openai = mock_providers
    
    # Setup: Mistral fails, OpenAI succeeds
    mock_mistral.side_effect = CloudRetry("Mistral quota exceeded")
    mock_openai.return_value = {"text": "Success from OpenAI", "provider": "openai"}
    
    result = asyncio.run(call_llm("test prompt"))
    
    # Assertions
    mock_mistral.assert_called_once()
    mock_openai.assert_called_once()
    assert result["provider"] == "openai"
    assert "routing_tried" in result
    assert "mistral" in result["routing_tried"]

def test_all_providers_fail(monkeypatch, mock_providers):
    """Test error when all providers fail"""
    monkeypatch.setenv("PROVIDER_PRIORITY", "mistral,openai")
    
    from router.hybrid import call_llm
    from providers import CloudRetry
    
    mock_mistral, mock_openai = mock_providers
    
    # Setup: Both providers fail
    mock_mistral.side_effect = CloudRetry("Mistral failed")
    mock_openai.side_effect = CloudRetry("OpenAI failed")
    
    with pytest.raises(RuntimeError, match="All providers failed"):
        asyncio.run(call_llm("test prompt"))
    
    # Both should have been tried
    mock_mistral.assert_called_once()
    mock_openai.assert_called_once()

def test_config_priority_override():
    """Test that config file can override environment priority"""
    from router.hybrid import PROVIDER_PRIORITY
    
    # Should have loaded from config/providers.yaml
    assert "mistral" in PROVIDER_PRIORITY
    assert "openai" in PROVIDER_PRIORITY
    
    # Mistral should be first (preferred)
    assert PROVIDER_PRIORITY[0] == "mistral"

def test_models_endpoint_data():
    """Test that /models endpoint returns proper provider data"""
    from router.hybrid import get_loaded_models
    
    models_info = get_loaded_models()
    
    assert "count" in models_info
    assert "models" in models_info
    assert "providers" in models_info
    assert "priority" in models_info
    assert models_info["count"] > 0
    assert "mistral" in models_info["providers"] 