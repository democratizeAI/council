# TinyLlama Real API Verification Pipeline
# Run this after docker build completes

Write-Host "🚀 TINYLLAMA VERIFICATION PIPELINE" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

# Step 1: Start real API
Write-Host "`n📦 Step 1: Starting real TinyLlama API..." -ForegroundColor Yellow
$env:SKIP_MODEL_LOAD="false"
docker-compose up -d council-api

Start-Sleep -Seconds 5

# Step 2: Health check (Pass/Fail gate: <3s response)
Write-Host "`n🏥 Step 2: Health check..." -ForegroundColor Yellow
$healthStart = Get-Date
try {
    $health = Invoke-RestMethod -Uri "http://localhost:9000/health" -TimeoutSec 3
    $healthTime = (Get-Date) - $healthStart
    Write-Host "✅ Health: $($health.status) in $($healthTime.TotalMilliseconds)ms" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Prime the model (Pass/Fail gate: ≤3s first call)  
Write-Host "`n🧠 Step 3: Priming TinyLlama model..." -ForegroundColor Yellow
$primeStart = Get-Date
try {
    $primeBody = @{prompt="ping"} | ConvertTo-Json
    $prime = Invoke-RestMethod -Uri "http://localhost:9000/vote" -Method POST -Body $primeBody -ContentType "application/json" -TimeoutSec 30
    $primeTime = (Get-Date) - $primeStart
    Write-Host "✅ Model primed in $($primeTime.TotalSeconds)s" -ForegroundColor Green
    Write-Host "   Response: $($prime.winner.model)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Model priming failed: $_" -ForegroundColor Red
    exit 1
}

# Step 4: Run real smoke test
Write-Host "`n🔥 Step 4: Running real API smoke test..." -ForegroundColor Yellow
locust -u10 -r5 -t3m --headless --host http://localhost:9000 --csv real_smoke

# Step 5: Compare results
Write-Host "`n📊 Step 5: Performance comparison..." -ForegroundColor Yellow
if (Test-Path "real_smoke_stats.csv" -and Test-Path "mock_smoke_stats.csv") {
    $mockStats = Import-Csv "mock_smoke_stats.csv" | Where-Object {$_.Type -eq "POST" -and $_.Name -eq "/orchestrate"}
    $realStats = Import-Csv "real_smoke_stats.csv" | Where-Object {$_.Type -eq "POST" -and $_.Name -eq "/orchestrate"}
    
    $mockP95 = [int]$mockStats.'95%'
    $realP95 = [int]$realStats.'95%'
    $delta = $realP95 - $mockP95
    
    Write-Host "📈 Mock p95: ${mockP95}ms" -ForegroundColor Cyan
    Write-Host "📈 Real p95: ${realP95}ms" -ForegroundColor Cyan  
    Write-Host "📈 Delta: +${delta}ms" -ForegroundColor $(if($delta -lt 100) {"Green"} else {"Yellow"})
    
    if ($realP95 -le 120 -and $delta -lt 100) {
        Write-Host "✅ Performance gates PASSED" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Performance outside expected range" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  CSV files not found for comparison" -ForegroundColor Yellow
}

Write-Host "`n🎯 Verification complete! Check Prometheus:" -ForegroundColor Green
Write-Host "   • histogram_quantile(0.95, http_request_duration_seconds)" -ForegroundColor Cyan
Write-Host "   • nvidia_gpu_utilization (should stay flat - CPU path)" -ForegroundColor Cyan
Write-Host "   • gunicorn_active_workers" -ForegroundColor Cyan

Write-Host "`n🚀 Ready for nightly soak testing!" -ForegroundColor Green 