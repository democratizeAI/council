# 🌌 SwarmAI Council Deployment Script
# Enables and tests the five-voice council system

param(
    [switch]$EnableCouncil = $false,
    [switch]$RunTests = $false,
    [switch]$StartServer = $false,
    [string]$Environment = "staging"
)

Write-Host "🌌 SwarmAI Council Deployment" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

# Set environment variables for council
if ($EnableCouncil) {
    Write-Host "🌌 Enabling Council..." -ForegroundColor Yellow
    
    $env:SWARM_COUNCIL_ENABLED = "true"
    $env:COUNCIL_MIN_TOKENS = "20"
    $env:COUNCIL_MAX_COST = "0.30"
    $env:COUNCIL_DAILY_BUDGET = "1.00"
    $env:COUNCIL_TARGET_LATENCY_MS = "2000"
    
    Write-Host "✅ Council environment configured" -ForegroundColor Green
    Write-Host "   SWARM_COUNCIL_ENABLED: $env:SWARM_COUNCIL_ENABLED" -ForegroundColor Gray
    Write-Host "   COUNCIL_MAX_COST: $env:COUNCIL_MAX_COST" -ForegroundColor Gray
    Write-Host "   COUNCIL_DAILY_BUDGET: $env:COUNCIL_DAILY_BUDGET" -ForegroundColor Gray
}

# Start server if requested
if ($StartServer) {
    Write-Host "🚀 Starting SwarmAI server..." -ForegroundColor Yellow
    
    try {
        # Start server in background
        $serverJob = Start-Job -ScriptBlock {
            Set-Location $using:PWD
            python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
        }
        
        # Wait for server to start
        Start-Sleep -Seconds 5
        
        # Test server connectivity
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
            Write-Host "✅ Server started successfully" -ForegroundColor Green
            Write-Host "   URL: http://localhost:8000" -ForegroundColor Gray
        } catch {
            Write-Host "❌ Server failed to start: $($_.Exception.Message)" -ForegroundColor Red
            Stop-Job $serverJob -Force
            return
        }
    } catch {
        Write-Host "❌ Failed to start server: $($_.Exception.Message)" -ForegroundColor Red
        return
    }
}

# Run tests if requested
if ($RunTests) {
    Write-Host "🧪 Running Council Tests..." -ForegroundColor Yellow
    
    # Stage 1: Offline smoke tests
    Write-Host "🏠 Stage 1: Offline Council Tests" -ForegroundColor Blue
    try {
        $env:SWARM_CLOUD_ENABLED = "false"
        python -m pytest -q -m "not cloud and not council" tests/test_council_integration.py
        Write-Host "✅ Offline tests passed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Offline tests failed: $($_.Exception.Message)" -ForegroundColor Red
        return
    }
    
    # Stage 2: Council integration tests (if keys available)
    if ($env:MISTRAL_API_KEY -or $env:OPENAI_API_KEY) {
        Write-Host "🌌 Stage 2: Live Council Tests" -ForegroundColor Blue
        try {
            $env:SWARM_COUNCIL_ENABLED = "true"
            python -m pytest -q -m council tests/test_council_integration.py
            Write-Host "✅ Council tests passed" -ForegroundColor Green
        } catch {
            Write-Host "⚠️ Council tests had issues: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️ No API keys - skipping live council tests" -ForegroundColor Gray
        Write-Host "   Set MISTRAL_API_KEY or OPENAI_API_KEY for full testing" -ForegroundColor Gray
    }
}

# Test council endpoints if server is running
if ($StartServer -and $RunTests) {
    Write-Host "🌌 Testing Council Endpoints..." -ForegroundColor Yellow
    
    try {
        # Test council status
        $status = Invoke-RestMethod -Uri "http://localhost:8000/council/status" -Method Get
        Write-Host "✅ Council status endpoint working" -ForegroundColor Green
        Write-Host "   Enabled: $($status.council_enabled)" -ForegroundColor Gray
        Write-Host "   Voices: $($status.voice_models.Count)" -ForegroundColor Gray
        
        # Test hybrid with council
        $hybridRequest = @{
            prompt = "Explain the strategic implications of AI governance"
            enable_council = $true
        } | ConvertTo-Json
        
        $hybridResponse = Invoke-RestMethod -Uri "http://localhost:8000/hybrid" -Method Post -Body $hybridRequest -ContentType "application/json"
        
        Write-Host "✅ Hybrid+Council endpoint working" -ForegroundColor Green
        Write-Host "   Provider: $($hybridResponse.provider)" -ForegroundColor Gray
        Write-Host "   Council used: $($hybridResponse.council_used)" -ForegroundColor Gray
        Write-Host "   Response length: $($hybridResponse.text.Length) chars" -ForegroundColor Gray
        
    } catch {
        Write-Host "⚠️ Endpoint test issues: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "🎯 Council Deployment Summary:" -ForegroundColor Cyan
Write-Host "   Environment: $Environment" -ForegroundColor Gray
Write-Host "   Council Enabled: $env:SWARM_COUNCIL_ENABLED" -ForegroundColor Gray
Write-Host "   Budget Limit: `$$env:COUNCIL_DAILY_BUDGET/day" -ForegroundColor Gray

if ($StartServer) {
    Write-Host ""
    Write-Host "🌌 Council is now active!" -ForegroundColor Green
    Write-Host "Ready to deliberate on your deepest AI questions." -ForegroundColor Green
    Write-Host ""
    Write-Host "Test council deliberation:" -ForegroundColor Yellow
    Write-Host 'curl -X POST http://localhost:8000/council -H "Content-Type: application/json" -d "{\"prompt\":\"Explain quantum computing implications\",\"force_council\":true}"' -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press Ctrl+C to stop the server." -ForegroundColor Yellow
    
    # Keep server running
    try {
        Wait-Job $serverJob
    } finally {
        Stop-Job $serverJob -Force
        Remove-Job $serverJob -Force
    }
} else {
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. ./deploy-council.ps1 -EnableCouncil -StartServer" -ForegroundColor Gray
    Write-Host "2. Test council: POST /council" -ForegroundColor Gray
    Write-Host "3. Monitor via: GET /council/status" -ForegroundColor Gray
} 