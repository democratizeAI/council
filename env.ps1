# 🚀 Swarm Development Environment (PowerShell)
# Usage: . .\env.ps1

Write-Host "🚀 Setting up Swarm development environment..." -ForegroundColor Cyan

# Core environment variables
$env:LUMINA_ENV = "dev"
$env:CUDA_VISIBLE_DEVICES = "0"
$env:PYTHONUNBUFFERED = "1"

# API Configuration
$env:SWARM_PROFILE = "development"
$env:ENABLE_SANDBOX = "true"
$env:CLOUD_ENABLED = "true"
$env:PROVIDER_PRIORITY = "mistral,openai"

# Memory and caching
$env:AZ_MEMORY_ENABLED = "yes"
$env:AZ_MEMORY_PATH = "./memory"
$env:MEM_EMB_MODEL = "all-MiniLM-L6-v2"

# Performance tuning
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:128"
$env:EXEC_TIMEOUT_SEC = "30"
$env:GPU_MEMORY_FRACTION = "0.8"

# Development budget controls
$env:SWARM_CLOUD_BUDGET_USD = "5.0"  # Higher for dev testing
$env:TRAINING_BUDGET_USD = "1.0"

# Redis and databases
$env:REDIS_URL = "redis://localhost:6379/0"

# Monitoring and metrics
$env:PROMETHEUS_URL = "http://localhost:9090"
$env:GRAFANA_URL = "http://localhost:3000"

# Development flags
$env:DEBUG = "true"
$env:LOG_LEVEL = "DEBUG"
$env:RELOAD = "true"

# Ensemble configuration
$env:MAX_ADAPTERS = "3"
$env:BASE_MODEL_PATH = "./models/tinyllama"
$env:REDIS_CLUSTER_PREFIX = "pattern:cluster:"

# Optional: Load secrets from .env file if it exists
if (Test-Path ".env") {
    Write-Host "📄 Loading additional config from .env file..." -ForegroundColor Yellow
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            Set-Item -Path "env:$($matches[1])" -Value $matches[2]
        }
    }
}

Write-Host "✅ Environment configured for development" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Quick commands:" -ForegroundColor Cyan
Write-Host "   • Start API: uvicorn main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Gray
Write-Host "   • Run tests: pytest tests/ -v" -ForegroundColor Gray
Write-Host "   • Health check: curl http://localhost:8000/health" -ForegroundColor Gray
Write-Host "   • View metrics: curl http://localhost:9090/api/v1/query?query=up" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Development URLs:" -ForegroundColor Cyan
Write-Host "   • API: http://localhost:8000" -ForegroundColor Gray
Write-Host "   • Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "   • Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor Gray
Write-Host "   • Prometheus: http://localhost:9090" -ForegroundColor Gray

# Helper functions
function Test-SwarmHealth {
    Write-Host "🏥 Testing Swarm health..." -ForegroundColor Cyan
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Swarm API is healthy" -ForegroundColor Green
        }
    } catch {
        Write-Host "❌ Swarm API is not responding" -ForegroundColor Red
    }
}

function Start-SwarmDev {
    Write-Host "🚀 Starting Swarm development server..." -ForegroundColor Cyan
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

function Test-SwarmSmoke {
    Write-Host "🧪 Running smoke test..." -ForegroundColor Cyan
    python tests/test_e2e_smoke.py smoke
}

Write-Host "💡 Available functions: Test-SwarmHealth, Start-SwarmDev, Test-SwarmSmoke" -ForegroundColor Yellow 