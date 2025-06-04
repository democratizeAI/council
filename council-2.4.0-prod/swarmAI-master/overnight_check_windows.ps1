# 🌙 Windows SwarmAI Overnight Pre-Flight Checklist
# Run this script to verify everything is ready for overnight training
param(
    [switch]$Verbose,
    [string]$ComposeFile = "docker-compose-simple.yaml"
)

$ErrorActionPreference = "Stop"

Write-Host "🌙 SwarmAI Overnight Pre-Flight Checklist" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$checks = @()

# Step 1: Docker Status
Write-Host "1. Docker Status..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "   ✅ Docker: $dockerVersion" -ForegroundColor Green
    $checks += "Docker: Running"
} catch {
    Write-Host "   ❌ Docker not running or not installed" -ForegroundColor Red
    $checks += "Docker: FAILED"
    exit 1
}

# Step 2: Start Stack
Write-Host "`n2. Starting SwarmAI Stack..." -ForegroundColor Yellow
try {
    $output = docker-compose -f $ComposeFile up -d 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Stack started successfully" -ForegroundColor Green
        $checks += "Stack: Running"
    } else {
        Write-Host "   ❌ Failed to start stack" -ForegroundColor Red
        Write-Host "   Error: $output" -ForegroundColor Red
        $checks += "Stack: FAILED"
    }
} catch {
    Write-Host "   ❌ Error starting stack: $_" -ForegroundColor Red
    $checks += "Stack: FAILED"
}

# Step 3: Container Health
Write-Host "`n3. Container Health Check..." -ForegroundColor Yellow
try {
    $containers = docker-compose -f $ComposeFile ps --format "table {{.Name}}\t{{.State}}\t{{.Health}}" 2>&1
    Write-Host "   Container Status:" -ForegroundColor Cyan
    Write-Host "   $containers" -ForegroundColor White
    
    $runningCount = (docker-compose -f $ComposeFile ps -q | docker inspect --format='{{.State.Status}}' | Where-Object { $_ -eq "running" }).Count
    if ($runningCount -gt 0) {
        Write-Host "   ✅ $runningCount containers running" -ForegroundColor Green
        $checks += "Containers: $runningCount running"
    } else {
        Write-Host "   ❌ No containers running" -ForegroundColor Red
        $checks += "Containers: FAILED"
    }
} catch {
    Write-Host "   ❌ Error checking containers: $_" -ForegroundColor Red
    $checks += "Containers: FAILED"
}

# Step 4: API Health
Write-Host "`n4. API Health Check..." -ForegroundColor Yellow
try {
    Start-Sleep 2  # Give containers time to start
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ SwarmAI API: Healthy (Status 200)" -ForegroundColor Green
        $checks += "API: Healthy"
    } else {
        Write-Host "   ⚠️  SwarmAI API: Unexpected status ($($response.StatusCode))" -ForegroundColor Yellow
        $checks += "API: Warning"
    }
} catch {
    Write-Host "   ❌ SwarmAI API: Not responding" -ForegroundColor Red
    $checks += "API: FAILED"
}

# Step 5: Metrics Endpoint
Write-Host "`n5. Metrics Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ Metrics: Available (Status 200)" -ForegroundColor Green
        $checks += "Metrics: Available"
    } else {
        Write-Host "   ⚠️  Metrics: Unexpected status ($($response.StatusCode))" -ForegroundColor Yellow
        $checks += "Metrics: Warning"
    }
} catch {
    Write-Host "   ❌ Metrics: Not responding" -ForegroundColor Red
    $checks += "Metrics: FAILED"
}

# Step 6: Prometheus Health
Write-Host "`n6. Prometheus Health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9091/-/healthy" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✅ Prometheus: Healthy (Status 200)" -ForegroundColor Green
        $checks += "Prometheus: Healthy"
    } else {
        Write-Host "   ⚠️  Prometheus: Unexpected status ($($response.StatusCode))" -ForegroundColor Yellow
        $checks += "Prometheus: Warning"
    }
} catch {
    Write-Host "   ❌ Prometheus: Not responding" -ForegroundColor Red
    $checks += "Prometheus: FAILED"
}

# Step 7: GPU Check
Write-Host "`n7. GPU Status..." -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>&1
    if ($LASTEXITCODE -eq 0) {
        $gpuData = $gpuInfo -split ','
        $memUsed = [int]$gpuData[0].Trim()
        $memTotal = [int]$gpuData[1].Trim()
        $temp = [int]$gpuData[2].Trim()
        
        $memUsedGB = [math]::Round($memUsed / 1024, 1)
        $memTotalGB = [math]::Round($memTotal / 1024, 1)
        
        Write-Host "   GPU Memory: $memUsedGB GB / $memTotalGB GB used" -ForegroundColor Cyan
        Write-Host "   GPU Temperature: $temp C" -ForegroundColor Cyan
        
        if ($memUsedGB -le 10.5 -and $temp -le 50) {
            Write-Host "   ✅ GPU: Healthy (Memory and temp within limits)" -ForegroundColor Green
            $checks += "GPU: Healthy ($memUsedGB GB, $temp C)"
        } else {
            Write-Host "   ⚠️  GPU: High usage/temperature ($memUsedGB GB, $temp C)" -ForegroundColor Yellow
            $checks += "GPU: Warning ($memUsedGB GB, $temp C)"
        }
    } else {
        Write-Host "   ⚠️  GPU: nvidia-smi not available or no GPU" -ForegroundColor Yellow
        $checks += "GPU: Not available"
    }
} catch {
    Write-Host "   ⚠️  GPU: Cannot check GPU status" -ForegroundColor Yellow
    $checks += "GPU: Unknown"
}

# Step 8: Jobs Queue
Write-Host "`n8. Jobs Queue..." -ForegroundColor Yellow
try {
    if (Test-Path "jobs\queue") {
        $jobFiles = Get-ChildItem "jobs\queue" -File
        $jobCount = $jobFiles.Count
        if ($jobCount -eq 1) {
            Write-Host "   ✅ Jobs Queue: $jobCount job ready ($($jobFiles[0].Name))" -ForegroundColor Green
            $checks += "Jobs: $jobCount queued"
        } elseif ($jobCount -gt 1) {
            Write-Host "   ⚠️  Jobs Queue: $jobCount jobs (expected 1)" -ForegroundColor Yellow
            $checks += "Jobs: $jobCount queued"
        } else {
            Write-Host "   ⚠️  Jobs Queue: Empty (no jobs for tonight)" -ForegroundColor Yellow
            $checks += "Jobs: Empty"
        }
    } else {
        Write-Host "   ❌ Jobs Queue: Directory not found" -ForegroundColor Red
        $checks += "Jobs: Directory missing"
    }
} catch {
    Write-Host "   ❌ Jobs Queue: Error checking directory" -ForegroundColor Red
    $checks += "Jobs: Error"
}

# Step 9: Logs Directory
Write-Host "`n9. Logs Directory..." -ForegroundColor Yellow
if (Test-Path "logs") {
    Write-Host "   ✅ Logs: Directory exists" -ForegroundColor Green
    $checks += "Logs: Ready"
} else {
    Write-Host "   ⚠️  Logs: Directory missing (will be created)" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    $checks += "Logs: Created"
}

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan
Write-Host "PRE-FLIGHT SUMMARY" -ForegroundColor Cyan
Write-Host "="*50 -ForegroundColor Cyan

$failedChecks = 0
$warningChecks = 0

foreach ($check in $checks) {
    if ($check -match "FAILED") {
        Write-Host "❌ $check" -ForegroundColor Red
        $failedChecks++
    } elseif ($check -match "Warning|Unknown|Empty") {
        Write-Host "⚠️  $check" -ForegroundColor Yellow
        $warningChecks++
    } else {
        Write-Host "✅ $check" -ForegroundColor Green
    }
}

Write-Host ""
if ($failedChecks -eq 0 -and $warningChecks -eq 0) {
    Write-Host "🎉 ALL SYSTEMS GREEN - Ready for overnight training!" -ForegroundColor Green
    Write-Host "💤 You can sleep soundly - the swarm will train autonomously." -ForegroundColor Green
} elseif ($failedChecks -eq 0) {
    Write-Host "⚠️  MOSTLY GREEN - $warningChecks warnings (likely okay for overnight run)" -ForegroundColor Yellow
    Write-Host "💤 Probably safe to proceed, but monitor first hour." -ForegroundColor Yellow
} else {
    Write-Host "❌ RED FLAGS DETECTED - $failedChecks critical issues need attention!" -ForegroundColor Red
    Write-Host "🚨 Do not proceed until critical issues are resolved." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Dashboard URLs:" -ForegroundColor Cyan
Write-Host "  SwarmAI API: http://localhost:8000/health" -ForegroundColor White
Write-Host "  Prometheus:  http://localhost:9091" -ForegroundColor White
Write-Host ""

if ($Verbose) {
    Write-Host "Troubleshooting commands:" -ForegroundColor Cyan
    Write-Host "  View logs:    docker-compose -f $ComposeFile logs --tail=50" -ForegroundColor White
    Write-Host "  Restart API:  docker-compose -f $ComposeFile restart swarm-api" -ForegroundColor White
    Write-Host "  Stop stack:   docker-compose -f $ComposeFile down" -ForegroundColor White
    Write-Host "  Start stack:  docker-compose -f $ComposeFile up -d" -ForegroundColor White
} 