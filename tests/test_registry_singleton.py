#!/usr/bin/env python3
"""
Registry Singleton Tests (Ticket #121)
Tests for preventing duplicate registry pushes via singleton pattern
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Mock registry singleton implementation
class RegistrySingleton:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.active_pushes = set()
        return cls._instance
    
    async def push_image(self, image_tag):
        async with self._lock:
            if image_tag in self.active_pushes:
                raise ValueError(f"Push already in progress for {image_tag}")
            self.active_pushes.add(image_tag)
            
        try:
            # Simulate push operation
            await asyncio.sleep(0.1)
            return f"pushed: {image_tag}"
        finally:
            async with self._lock:
                self.active_pushes.discard(image_tag)

@pytest.mark.asyncio
async def test_singleton_prevents_duplicate_pushes():
    """Test that singleton prevents duplicate pushes of same image"""
    registry = RegistrySingleton()
    
    # Try to push same image simultaneously
    tasks = [
        registry.push_image("test:v1.0"),
        registry.push_image("test:v1.0"),
        registry.push_image("test:v1.0")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Should have 1 success and 2 ValueError exceptions
    successes = [r for r in results if isinstance(r, str)]
    errors = [r for r in results if isinstance(r, ValueError)]
    
    assert len(successes) == 1
    assert len(errors) == 2
    assert "Push already in progress" in str(errors[0])

def test_parallel_different_images():
    """Test that different images can be pushed in parallel"""
    async def run_test():
        registry = RegistrySingleton()
        
        tasks = [
            registry.push_image("test:v1.0"),
            registry.push_image("test:v1.1"), 
            registry.push_image("test:v1.2")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed since they're different images
        successes = [r for r in results if isinstance(r, str)]
        assert len(successes) == 3
    
    asyncio.run(run_test())

@pytest.mark.slow
def test_singleton_stress():
    """Stress test with 5 parallel pushes as mentioned in runbook"""
    async def run_stress():
        registry = RegistrySingleton()
        
        # 5 parallel pushes of same image
        tasks = [registry.push_image("stress:test") for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = [r for r in results if isinstance(r, str)]
        errors = [r for r in results if isinstance(r, ValueError)]
        
        assert len(successes) == 1
        assert len(errors) == 4
    
    asyncio.run(run_stress())

if __name__ == "__main__":
    # Quick smoke test
    asyncio.run(test_singleton_prevents_duplicate_pushes())
    test_parallel_different_images()
    print("All tests passed!") 