# -*- coding: utf-8 -*-
"""
Global test configuration and fixtures
Makes tests more resilient to environment differences
"""

import httpx
import pytest
import os
import subprocess
import time
import socket
import signal
from typing import Generator
import sys
from pathlib import Path

# Add project root to Python path to help with imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set common environment variables for testing
os.environ.setdefault("SWARM_TEST_MODE", "true")
os.environ.setdefault("DISABLE_REDIS", "true")  # Disable Redis for CI
os.environ.setdefault("DISABLE_GPU", "true")    # Disable GPU for CI
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")  # Offline mode for transformers

# Register custom pytest marks to avoid warnings
pytest_plugins = []

def pytest_configure(config):
    """Configure pytest with custom marks"""
    config.addinivalue_line("markers", "council: council integration tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "early_stop_guard: early stop guard tests")
    config.addinivalue_line("markers", "ensemble: ensemble routing tests")
    config.addinivalue_line("markers", "budget: budget tracking tests")
    config.addinivalue_line("markers", "smoke: smoke tests")

@pytest.fixture(autouse=True)
def setup_test_environment():
    """Auto-applied fixture to set up clean test environment"""
    # Ensure clean state for each test
    import logging
    logging.getLogger().setLevel(logging.WARNING)  # Reduce noise in CI
    
    yield
    
    # Cleanup after test if needed
    pass

@pytest.fixture
def mock_redis():
    """Mock Redis client for tests that need it"""
    from unittest.mock import Mock, AsyncMock
    
    redis_mock = Mock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.hget = AsyncMock(return_value=None)
    redis_mock.hset = AsyncMock(return_value=True)
    redis_mock.hgetall = AsyncMock(return_value={})
    redis_mock.hdel = AsyncMock(return_value=1)
    redis_mock.flushdb = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock(return_value=None)
    redis_mock.pipeline.return_value.__aenter__ = AsyncMock(return_value=redis_mock)
    redis_mock.pipeline.return_value.__aexit__ = AsyncMock(return_value=None)
    redis_mock.execute = AsyncMock(return_value=[])
    
    return redis_mock

def is_port_open(host: str, port: int) -> bool:
    """Check if a port is open"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex((host, port))
        return result == 0

@pytest.fixture(scope="session")
def api_server() -> Generator[None, None, None]:
    """Start FastAPI server for testing"""
    # Set environment for testing
    env = os.environ.copy()
    env["SWARM_GPU_PROFILE"] = "rtx_4070"
    
    # Check if server is already running
    if is_port_open("127.0.0.1", 8000):
        print("📡 Server already running on port 8000")
        yield
        return
    
    # Start server
    print("🚀 Starting FastAPI server for E2E tests...")
    proc = subprocess.Popen(
        ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start (max 15 seconds)
    for i in range(30):  # 30 * 0.5 = 15 seconds
        if is_port_open("127.0.0.1", 8000):
            print(f"✅ Server started after {i * 0.5:.1f}s")
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        stdout, stderr = proc.communicate()
        pytest.fail(f"Server failed to start: {stderr.decode()}")
    
    yield
    
    # Cleanup
    print("🛑 Shutting down test server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill() 