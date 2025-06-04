# SwarmAI environment configuration for PowerShell
# Run with: .\env.ps1

# GPU Profile (determines VRAM limits and model loading strategy)
$env:SWARM_GPU_PROFILE = "rtx_4070"

# CUDA memory allocator settings (prevents fragmentation at high QPS)
$env:PYTORCH_CUDA_ALLOC_CONF = "max_split_size_mb:128"

# Model storage root (optional - customize for your setup)
# $env:SWARM_MODEL_ROOT = "C:\path\to\your\models"

# FastAPI development settings
$env:SWARM_DEBUG = "true"
$env:SWARM_LOG_LEVEL = "INFO"

# Locust load testing target (for CI vs local vs remote testing)
$env:SWARM_ROUTER_HOST = "http://127.0.0.1:8000"

# Prometheus metrics collection
$env:SWARM_METRICS_ENABLED = "true"

# CI-specific overrides
if ($env:CI -eq "true") {
    $env:SWARM_GPU_PROFILE = "gtx_1080"  # Smaller memory footprint for CI
    $env:SWARM_DEBUG = "false"
    $env:SWARM_LOG_LEVEL = "WARNING"
}

Write-Host "SwarmAI environment loaded:" -ForegroundColor Green
Write-Host "  GPU Profile: $($env:SWARM_GPU_PROFILE)" -ForegroundColor Cyan
Write-Host "  CUDA Allocator: $($env:PYTORCH_CUDA_ALLOC_CONF)" -ForegroundColor Cyan
Write-Host "  Router Host: $($env:SWARM_ROUTER_HOST)" -ForegroundColor Cyan 