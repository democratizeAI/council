# AutoGen Council v2.7.0 Startup Script
# =====================================

Write-Host "🚀 Starting AutoGen Council v2.7.0-preview..." -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Load environment variables
Write-Host "🔧 Loading environment variables..." -ForegroundColor Yellow

$env:LLM_ENDPOINT = "http://localhost:8001/v1"
$env:OPENAI_API_BASE = "http://localhost:8001/v1"
$env:OPENAI_API_KEY = "sk-fake-key-for-local-server"

$env:AZ_MEMORY_ENABLED = "yes"
$env:AZ_MEMORY_PATH = "./memory_store"
$env:AZ_SHELL_TRUSTED = "yes"
$env:ENABLE_SANDBOX = "true"

$env:SWARM_GPU_PROFILE = "rtx_4070"
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:128"
$env:SWARM_DEBUG = "true"
$env:SWARM_LOG_LEVEL = "INFO"
$env:SWARM_METRICS_ENABLED = "true"

Write-Host "✅ Environment configured:" -ForegroundColor Green
Write-Host "  LLM Endpoint: $env:LLM_ENDPOINT" -ForegroundColor Gray
Write-Host "  Memory System: $env:AZ_MEMORY_ENABLED" -ForegroundColor Gray
Write-Host "  Sandbox: $env:ENABLE_SANDBOX" -ForegroundColor Gray

# Create memory directory if it doesn't exist
if (!(Test-Path "memory_store")) {
    New-Item -ItemType Directory -Path "memory_store" -Force | Out-Null
    Write-Host "📁 Created memory_store directory" -ForegroundColor Green
}

# Start Local LLM Server (background)
Write-Host "🤖 Starting Local LLM Server on port 8001..." -ForegroundColor Yellow
$llmJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    python local_llm_server.py
}

# Wait for LLM server to start
Write-Host "⏳ Waiting for LLM server to initialize..." -ForegroundColor Yellow
Start-Sleep 5

# Test LLM server
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 5
    Write-Host "✅ LLM Server healthy: $($response.service)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  LLM Server not responding (will use fallback mode)" -ForegroundColor Red
}

# Start AutoGen Council
Write-Host "🏛️ Starting AutoGen Council on port 8000..." -ForegroundColor Yellow
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "🌐 Web Interfaces will be available at:" -ForegroundColor Cyan
Write-Host "  💬 Chat: http://localhost:8000/chat/" -ForegroundColor White
Write-Host "  ⚙️  Admin: http://localhost:8000/admin/" -ForegroundColor White  
Write-Host "  📊 Monitor: http://localhost:8000/monitor/" -ForegroundColor White
Write-Host "  📋 API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "=====================================================" -ForegroundColor Cyan

# Clear browser cache notice
Write-Host "🔄 NOTE: If web pages appear blank, clear browser cache (Ctrl+F5)" -ForegroundColor Yellow

try {
    python autogen_api_shim.py
} finally {
    # Cleanup: Stop LLM server when main process exits
    Write-Host "`n🛑 Shutting down..." -ForegroundColor Yellow
    Stop-Job $llmJob -ErrorAction SilentlyContinue
    Remove-Job $llmJob -ErrorAction SilentlyContinue
    Write-Host "✅ AutoGen Council shutdown complete" -ForegroundColor Green
} 