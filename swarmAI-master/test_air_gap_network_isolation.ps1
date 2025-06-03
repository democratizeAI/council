# Test Network Isolation with Air-Gap Mode
# Sets SWARM_OFFLINE=1 and runs network isolation test

Write-Host "Testing Network Isolation with Air-Gap Mode..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Set air-gap environment variable
$env:SWARM_OFFLINE = "1"

Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "  SWARM_OFFLINE = $env:SWARM_OFFLINE" -ForegroundColor Gray

Write-Host ""
Write-Host "Running network isolation test..." -ForegroundColor Cyan

try {
    # Run the network isolation test
    $result = python "tests\leak_tests\network_isolation_test.py" --test all --api-url "http://localhost:8000" 2>&1
    $exitCode = $LASTEXITCODE
    
    Write-Host $result
    
    if ($exitCode -eq 0) {
        Write-Host ""
        Write-Host "[PASS] Network isolation test PASSED" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[FAIL] Network isolation test FAILED" -ForegroundColor Red
    }
    
    exit $exitCode
} catch {
    Write-Host "Error running network isolation test: $_" -ForegroundColor Red
    exit 1
} finally {
    # Clean up environment variable
    Remove-Item Env:SWARM_OFFLINE -ErrorAction SilentlyContinue
} 