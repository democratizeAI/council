# Zero-Regression Test Harness

A comprehensive 4-layer test suite that exercises every moving part of the AutoGen Council system to ensure no regressions during development.

## Test Architecture

```
Layer         What we check                     Files created
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unit          5 voice prompts → no stub         tests/unit/
              Ledger flow, scratchpad CRUD
              Router ladder gates
              Vote/fuse math penalty

Service       FastAPI endpoints                 tests/service/
              Provider chain + meta fields

End-to-end    Docker stack up                   tests/e2e/
              GPU model loads
              Cloud fall-back ladder
              Cost guardrail

Front-end     Chat panel renders fused answer   tests/ui/
              Collapsible Council panel
              Color badges 🟢🟠🔴
```

## Quick Start

### 1. Install Dependencies

```bash
# Install Python test dependencies
pip install -r tests/requirements.txt

# Install UI test dependencies (requires Node.js)
cd tests && npm install
```

Or use the Makefile:
```bash
make install-test-deps
```

### 2. Run All Tests

```bash
# Run complete test suite (all 4 layers)
make test-all

# Or run individual layers
make test-unit      # Fast unit tests
make test-service   # FastAPI endpoint tests  
make test-e2e       # Docker stack tests
make test-ui        # Frontend tests
```

### 3. Quick Development Testing

```bash
# Just unit + service (fastest feedback)
make test-quick

# CI-friendly run
make test-ci
```

## Test Layers in Detail

### Layer 1: Unit Tests (`tests/unit/`)

**Purpose**: Fast, isolated testing of core logic
**Runtime**: ~10 seconds

```bash
pytest tests/unit/
```

**What's tested**:
- `test_router_ladder.py`: Router cascade logic (3-tier fallback)
- `test_scratchpad.py`: Whiteboard CRUD operations  
- `test_prompts.py`: No stub text, voice definitions

**Key assertions**:
```python
# Router ladder stops at right tier
assert meta["provider_chain"] == ["local", "synth"]

# Scratchpad round-trip works
sp.write("S1", "tester", "foo", tags=["demo"])
assert sp.read("S1")[-1]["content"] == "foo"

# No stub text remains
assert not BAD_PATTERN.search(prompt_content)
```

### Layer 2: Service Tests (`tests/service/`)

**Purpose**: FastAPI endpoint validation
**Runtime**: ~30 seconds

```bash
pytest tests/service/
```

**What's tested**:
- Chat endpoint returns council voices
- Provider chain starts with `local`
- Cost tracking ≤ budget cap
- Whiteboard API integration
- Error handling

**Key assertions**:
```python
response = client.post("/chat/", json={"prompt": "test"})
body = response.json()

assert body["provider_chain"][0] == "local"
assert "voices" in body
assert any(v["voice"] == "Reason" for v in body["voices"])
assert body["cost_usd"] <= 0.10  # Local processing
```

### Layer 3: End-to-End Tests (`tests/e2e/`)

**Purpose**: Full Docker stack validation
**Runtime**: ~2-5 minutes

```bash
bash tests/e2e/test_stack.sh
```

**What's tested**:
- Docker health checks pass
- GPU model loading
- Local answer has cost $0
- Math prompt routes local
- Redis connectivity
- Performance < 30s response

**Success criteria**:
```bash
✅ API health check passed
✅ Local processing confirmed (cost: $0)  
✅ Math query routed to local provider: local_voting
✅ Council consensus working (5 voices)
✅ All critical tests passed! Stack is operational.
```

### Layer 4: UI Tests (`tests/ui/`)

**Purpose**: Frontend functionality verification
**Runtime**: ~1-3 minutes

```bash
npx playwright test tests/ui/
```

**What's tested**:
- Council panel renders and is collapsible
- 5 voices display correctly
- Color badges work (🟢🟠🔴)
- Responsive design
- Accessibility features

**Key assertions**:
```typescript
// Council panel appears
await expect(councilPanel).toBeVisible({ timeout: 30000 });

// Has collapsible functionality  
await summary.click();
await expect(panelContent).toBeVisible();

// Shows multiple voices
expect(voiceCount).toBeGreaterThanOrEqual(3);
```

## Configuration Files

### `pytest.ini`
```ini
[tool:pytest]
testpaths = tests
addopts = --cov=app --cov=router --cov-fail-under=50
markers = 
    unit: Unit tests (fast, isolated)
    service: Service-level tests
    docker: Tests requiring Docker
```

### `tests/package.json`
```json
{
  "scripts": {
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug"
  }
}
```

## Running Specific Test Types

### By Layer
```bash
pytest tests/unit/           # Unit only
pytest tests/service/        # Service only  
bash tests/e2e/test_stack.sh # E2E only
npx playwright test tests/ui/# UI only
```

### By Marker
```bash
pytest -m "unit"            # All unit tests
pytest -m "not slow"        # Skip slow tests
pytest -m "docker"          # Docker-dependent tests
pytest -m "gpu"             # GPU-dependent tests
```

### By Pattern
```bash
pytest -k "router"          # Tests with 'router' in name
pytest -k "not integration" # Skip integration tests
pytest tests/unit/test_prompts.py::test_no_stub_left  # Specific test
```

## Continuous Integration

### GitHub Actions

Add to `.github/workflows/test.yml`:

```yaml
name: Zero-Regression Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install test dependencies
      run: |
        pip install -r tests/requirements.txt
        
    - name: Run unit tests
      run: pytest tests/unit/ -v
      
    - name: Run service tests  
      run: pytest tests/service/ -v
      
    - name: Run E2E tests
      run: bash tests/e2e/test_stack.sh
      
    - name: Setup Node.js for UI tests
      uses: actions/setup-node@v4
      with:
        node-version: '18'
        
    - name: Run UI tests
      run: |
        cd tests && npm install
        npx playwright install --with-deps
        npx playwright test
```

### Local CI Simulation

```bash
# Simulate CI environment
CI=true make test-all

# Quick feedback loop
make test-quick && echo "✅ Ready to commit"
```

## Debugging Test Failures

### Unit Test Failures
```bash
# Verbose output
pytest tests/unit/ -v -s

# Stop on first failure
pytest tests/unit/ -x

# Run specific failing test
pytest tests/unit/test_router_ladder.py::test_ladder_three_tiers -v
```

### Service Test Failures
```bash
# Check FastAPI logs
pytest tests/service/ -v -s --tb=long

# Debug with pdb
pytest tests/service/ --pdb
```

### E2E Test Failures
```bash
# Check Docker logs
docker compose logs council-api

# Manual endpoint testing
curl -X POST http://localhost:9000/chat \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"debug test"}'
```

### UI Test Failures  
```bash
# Run with browser visible
npx playwright test --headed

# Debug mode (pauses execution)
npx playwright test --debug

# Generate trace for failed tests
npx playwright test --trace=on
npx playwright show-report  # View traces
```

## Coverage Reports

```bash
# Generate coverage report
pytest tests/unit/ tests/service/ --cov-report=html

# View in browser
open tests/htmlcov/index.html  # macOS
start tests/htmlcov/index.html # Windows
```

## Performance Monitoring

Track test performance over time:

```bash
# Benchmark mode
pytest tests/unit/ --benchmark-only

# Time individual tests
pytest tests/service/ --durations=10
```

## Writing New Tests

### Unit Test Template
```python
# tests/unit/test_new_feature.py
import pytest

def test_new_functionality():
    """Test that new feature works correctly"""
    # Arrange
    input_data = {"test": "data"}
    
    # Act  
    result = your_function(input_data)
    
    # Assert
    assert result["expected"] == "output"
```

### Service Test Template  
```python
# tests/service/test_new_endpoint.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_new_endpoint():
    """Test new API endpoint"""
    response = client.post("/new-endpoint/", json={"data": "test"})
    
    assert response.status_code == 200
    body = response.json()
    assert "result" in body
```

## Troubleshooting

### Common Issues

**"Module not found" errors**:
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/unit/
```

**Docker permission errors**:
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then logout/login
```

**Playwright browser install**:
```bash
# Install browsers manually
npx playwright install chromium firefox webkit
```

**Port conflicts**:
```bash
# Check what's using ports 8000/9000
netstat -tulpn | grep :9000
# Kill conflicting processes
sudo pkill -f "port 9000"
```

## Success Criteria Summary

When all four layers go green, you know:

✅ **Five-voice Council** delivers raw and fused answers  
✅ **Ladder stays local** first, escalates only as intended  
✅ **Scratchpad persists** between turns  
✅ **Frontend shows everything** correctly  

This test harness ensures every refactor, feature addition, or configuration change maintains system integrity across all layers of the stack. 