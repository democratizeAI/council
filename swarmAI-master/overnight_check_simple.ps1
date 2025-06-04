# SwarmAI Overnight Pre-Flight Checklist (Windows)
# Run this script to verify everything is ready for overnight training
param(
    [switch]$Verbose,
    [string]$ComposeFile = "docker-compose-simple.yaml"
)

$ErrorActionPreference = "Continue"

Write-Host "SwarmAI Overnight Pre-Flight Checklist" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

$checks = @()
$failed = 0

function Test-Check {
    param($Name, $Status, $Message)
    if ($Status) {
        Write-Host "   [OK] $Message" -ForegroundColor Green
        $script:checks += "$($Name): OK"
    } else {
        Write-Host "   [FAIL] $Message" -ForegroundColor Red
        $script:checks += "$($Name): FAILED"
        $script:failed++
    }
}

function Test-Warning {
    param($Name, $Message)
    Write-Host "   [WARN] $Message" -ForegroundColor Yellow
    $script:checks += "$($Name): WARNING"
}

# Test 1: Docker
Write-Host "1. Docker Status..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    Test-Check "Docker" ($LASTEXITCODE -eq 0) "Docker: $dockerVersion"
} catch {
    Test-Check "Docker" $false "Docker not available"
}

# Test 2: Start Stack
Write-Host "`n2. Starting SwarmAI Stack..." -ForegroundColor Yellow
try {
    $null = docker-compose -f $ComposeFile up -d 2>&1
    Test-Check "Stack" ($LASTEXITCODE -eq 0) "Stack deployment successful"
} catch {
    Test-Check "Stack" $false "Failed to start stack"
}

# Test 3: Container Health
Write-Host "`n3. Container Health..." -ForegroundColor Yellow
try {
    $runningContainers = docker-compose -f $ComposeFile ps -q | ForEach-Object { docker inspect $_ --format='{{.State.Status}}' } | Where-Object { $_ -eq "running" }
    $count = ($runningContainers | Measure-Object).Count
    Test-Check "Containers" ($count -gt 0) "$count containers running"
} catch {
    Test-Check "Containers" $false "Cannot check container status"
}

# Test 4: API Health
Write-Host "`n4. API Health..." -ForegroundColor Yellow
try {
    Start-Sleep 2
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10 -UseBasicParsing
    Test-Check "API" ($response.StatusCode -eq 200) "SwarmAI API responding (Status: $($response.StatusCode))"
} catch {
    Test-Check "API" $false "SwarmAI API not responding"
}

# Test 5: Metrics
Write-Host "`n5. Metrics Endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/metrics" -TimeoutSec 10 -UseBasicParsing
    Test-Check "Metrics" ($response.StatusCode -eq 200) "Metrics endpoint available"
} catch {
    Test-Check "Metrics" $false "Metrics endpoint not responding"
}

# Test 6: Prometheus
Write-Host "`n6. Prometheus..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:9091/-/healthy" -TimeoutSec 10 -UseBasicParsing
    Test-Check "Prometheus" ($response.StatusCode -eq 200) "Prometheus healthy"
} catch {
    Test-Check "Prometheus" $false "Prometheus not responding"
}

# Test 7: GPU
Write-Host "`n7. GPU Status..." -ForegroundColor Yellow
try {
    $gpuInfo = nvidia-smi --query-gpu=memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits 2>$null
    if ($LASTEXITCODE -eq 0) {
        $data = $gpuInfo -split ','
        $memUsed = [math]::Round([int]$data[0].Trim() / 1024, 1)
        $memTotal = [math]::Round([int]$data[1].Trim() / 1024, 1)
        $temp = [int]$data[2].Trim()
        
        Write-Host "   GPU Memory: $memUsed GB / $memTotal GB" -ForegroundColor Cyan
        Write-Host "   GPU Temperature: $temp C" -ForegroundColor Cyan
        
        if ($memUsed -le 10.5 -and $temp -le 50) {
            Test-Check "GPU" $true "GPU healthy (Memory: $memUsed GB, Temp: $temp C)"
        } else {
            Test-Warning "GPU" "GPU high usage (Memory: $memUsed GB, Temp: $temp C)"
        }
    } else {
        Test-Warning "GPU" "GPU monitoring not available"
    }
} catch {
    Test-Warning "GPU" "Cannot check GPU status"
}

# Test 8: Jobs Queue
Write-Host "`n8. Jobs Queue..." -ForegroundColor Yellow
try {
    if (Test-Path "jobs\queue") {
        $jobFiles = Get-ChildItem "jobs\queue" -File
        $jobCount = $jobFiles.Count
        if ($jobCount -eq 1) {
            Test-Check "Jobs" $true "1 job queued: $($jobFiles[0].Name)"
        } elseif ($jobCount -gt 1) {
            Test-Warning "Jobs" "$jobCount jobs queued (expected 1)"
        } else {
            Test-Warning "Jobs" "No jobs queued for tonight"
        }
    } else {
        Test-Check "Jobs" $false "Jobs queue directory missing"
    }
} catch {
    Test-Check "Jobs" $false "Cannot check jobs queue"
}

# Test 9: Logs
Write-Host "`n9. Logs Directory..." -ForegroundColor Yellow
if (Test-Path "logs") {
    Test-Check "Logs" $true "Logs directory exists"
} else {
    Test-Warning "Logs" "Logs directory missing (creating...)"
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
}

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "="*50 -ForegroundColor Cyan

foreach ($check in $checks) {
    if ($check -match "FAILED") {
        Write-Host "[FAIL] $check" -ForegroundColor Red
    } elseif ($check -match "WARNING") {
        Write-Host "[WARN] $check" -ForegroundColor Yellow
    } else {
        Write-Host "[OK]   $check" -ForegroundColor Green
    }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Host "RESULT: All critical systems operational!" -ForegroundColor Green
    Write-Host "Ready for overnight autonomous training." -ForegroundColor Green
} else {
    Write-Host "RESULT: $failed critical failures detected!" -ForegroundColor Red
    Write-Host "Fix critical issues before proceeding." -ForegroundColor Red
}

Write-Host ""
Write-Host "Dashboard Access:" -ForegroundColor Cyan
Write-Host "  SwarmAI API: http://localhost:8000/health" -ForegroundColor White
Write-Host "  Prometheus:  http://localhost:9091" -ForegroundColor White

if ($Verbose) {
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Cyan
    Write-Host "  View logs:    docker-compose -f $ComposeFile logs --tail=50" -ForegroundColor White
    Write-Host "  Restart API:  docker-compose -f $ComposeFile restart swarm-api" -ForegroundColor White
    Write-Host "  Stop all:     docker-compose -f $ComposeFile down" -ForegroundColor White
}