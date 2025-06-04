# 🎛️ SwarmAI Canary Deployment (PowerShell)
# Windows wrapper for the canary deployment system

param(
    [ValidateSet("deploy", "scale", "rollback", "test")]
    [string]$Action = "deploy",
    [int]$Percentage = 5,
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🎛️ SwarmAI Canary Deployment (Windows)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Check if Docker is available
try {
    docker --version | Out-Null
    Write-Host "✅ Docker available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Check if WSL/Bash is available for script execution
$bashAvailable = $false
try {
    bash --version | Out-Null
    $bashAvailable = $true
    Write-Host "✅ Bash available (will use Linux scripts)" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Bash not available (will use PowerShell implementations)" -ForegroundColor Yellow
}

switch ($Action) {
    "deploy" {
        Write-Host "🚀 Starting canary deployment..." -ForegroundColor Yellow
        
        if ($bashAvailable) {
            bash -c "./infra/scripts/canary-deploy.sh"
        } else {
            # PowerShell implementation of canary deployment
            Write-Host "📦 Building Docker image..." -ForegroundColor Blue
            Set-Location "infra/deploy"
            docker compose build council
            
            Write-Host "⚙️ Checking configuration..." -ForegroundColor Blue
            if (-not (Test-Path "canary.env")) {
                Write-Host "❌ canary.env not found!" -ForegroundColor Red
                Write-Host "   Copy from canary.env and update API keys" -ForegroundColor Gray
                exit 1
            }
            
            Write-Host "🚀 Starting canary service..." -ForegroundColor Blue
            docker compose --env-file canary.env -f ../docker-compose.yml -f docker-compose.canary.yml up -d api-canary
            
            Write-Host "⏳ Waiting for health check..." -ForegroundColor Blue
            Start-Sleep 10
            
            $healthCheck = $false
            for ($i = 1; $i -le 30; $i++) {
                try {
                    $response = Invoke-RestMethod -Uri "http://localhost:9001/health" -TimeoutSec 2
                    $healthCheck = $true
                    break
                } catch {
                    Start-Sleep 2
                }
            }
            
            if ($healthCheck) {
                Write-Host "✅ Canary service healthy" -ForegroundColor Green
            } else {
                Write-Host "❌ Canary service failed health check" -ForegroundColor Red
                exit 1
            }
            
            Write-Host "🎯 Canary deployment complete!" -ForegroundColor Green
            Set-Location "../.."
        }
    }
    
    "scale" {
        Write-Host "📊 Scaling canary to $Percentage%..." -ForegroundColor Yellow
        
        if ($bashAvailable) {
            bash -c "./infra/scripts/canary-scale.sh $Percentage"
        } else {
            # PowerShell implementation
            $mainPercent = 100 - $Percentage
            Write-Host "   Main service: $mainPercent%" -ForegroundColor Gray
            Write-Host "   Canary service: $Percentage%" -ForegroundColor Gray
            
            # Update environment in running container
            try {
                docker exec autogen-council-canary powershell -c "(Get-Content /app/.env) -replace 'COUNCIL_TRAFFIC_PERCENT=.*', 'COUNCIL_TRAFFIC_PERCENT=$Percentage' | Set-Content /app/.env"
                Write-Host "✅ Traffic scaling complete" -ForegroundColor Green
            } catch {
                Write-Host "❌ Failed to update canary configuration" -ForegroundColor Red
                exit 1
            }
        }
    }
    
    "rollback" {
        Write-Host "🚨 Emergency canary rollback..." -ForegroundColor Red
        
        if ($bashAvailable) {
            bash -c "./infra/scripts/canary-rollback.sh"
        } else {
            # PowerShell implementation
            Write-Host "⚡ Setting canary traffic to 0%..." -ForegroundColor Yellow
            
            try {
                docker exec autogen-council-canary powershell -c "(Get-Content /app/.env) -replace 'COUNCIL_TRAFFIC_PERCENT=.*', 'COUNCIL_TRAFFIC_PERCENT=0' | Set-Content /app/.env"
                Write-Host "✅ Canary traffic set to 0%" -ForegroundColor Green
                
                Write-Host "⏸️ Pausing canary container..." -ForegroundColor Yellow
                docker pause autogen-council-canary
                Write-Host "✅ Rollback complete" -ForegroundColor Green
            } catch {
                Write-Host "❌ Rollback failed" -ForegroundColor Red
                exit 1
            }
        }
    }
    
    "test" {
        Write-Host "🧪 Running canary tests..." -ForegroundColor Yellow
        
        if ($bashAvailable) {
            bash -c "./infra/scripts/test_smoke.sh"
            if ($env:MISTRAL_API_KEY -and $env:MISTRAL_API_KEY -ne "★REDACTED★") {
                bash -c "./infra/scripts/test_live_cloud.sh"
            }
        } else {
            # PowerShell implementation of basic tests
            Write-Host "🏥 Testing health endpoints..." -ForegroundColor Blue
            
            try {
                $mainHealth = Invoke-RestMethod -Uri "http://localhost:9000/health" -TimeoutSec 5
                Write-Host "✅ Main service healthy" -ForegroundColor Green
            } catch {
                Write-Host "❌ Main service unhealthy" -ForegroundColor Red
            }
            
            try {
                $canaryHealth = Invoke-RestMethod -Uri "http://localhost:9001/health" -TimeoutSec 5  
                Write-Host "✅ Canary service healthy" -ForegroundColor Green
            } catch {
                Write-Host "❌ Canary service unhealthy" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "📊 Dashboard URLs:" -ForegroundColor Cyan
Write-Host "   Grafana: http://localhost:3000" -ForegroundColor Gray
Write-Host "   Traefik: http://localhost:8080" -ForegroundColor Gray
Write-Host "   Main API: http://localhost:9000/health" -ForegroundColor Gray
Write-Host "   Canary API: http://localhost:9001/health" -ForegroundColor Gray 