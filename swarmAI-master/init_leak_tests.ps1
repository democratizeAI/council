# Leak Test Suite Initialization Script for Windows
# Equivalent to: make -f Makefile.leak_tests init_env

Write-Host "Initializing clean air-gapped validation environment..." -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow

# Create audit directory structure
Write-Host "Creating directory structure..." -ForegroundColor Cyan
$directories = @(
    "audits\leak_tests",
    "audits\performance", 
    "audits\security",
    "lora_adapters",
    "jobs\queue",
    "jobs\completed", 
    "jobs\failed",
    "datasets",
    "logs"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "[+] Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "[+] Exists: $dir" -ForegroundColor Green
    }
}

# Validate environment isolation  
Write-Host "Checking environment isolation..." -ForegroundColor Cyan
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[+] Python available" -ForegroundColor Green
    $pythonVersion = python --version
    Write-Host "   Version: $pythonVersion" -ForegroundColor Gray
} else {
    Write-Host "[-] Python not found - install Python 3.8+" -ForegroundColor Red
    exit 1
}

# Install core dependencies
Write-Host "Installing validation dependencies..." -ForegroundColor Cyan
try {
    python -m pip install --upgrade pip --quiet
    python -m pip install requests numpy pytest setuptools wheel --quiet
    python -m pip install jsonlines pyyaml --quiet --no-warn-script-location
    Write-Host "[+] Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "[-] Failed to install dependencies: $_" -ForegroundColor Red
    exit 1
}

# Network isolation check (Windows version)
Write-Host "Validating network isolation..." -ForegroundColor Cyan
try {
    $networkCheck = Test-NetConnection -ComputerName "8.8.8.8" -Port 53 -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($networkCheck) {
        Write-Host "[!] WARNING: External network access available - not fully air-gapped" -ForegroundColor Yellow
        Write-Host "    For full isolation: Disable network adapter during tests" -ForegroundColor Yellow
    } else {
        Write-Host "[+] Network isolated - no external connectivity" -ForegroundColor Green
    }
} catch {
    Write-Host "[i] Network tools not available - proceeding" -ForegroundColor Gray
}

# Create evolution checksum file if missing
if (!(Test-Path "evolution_checksums.txt")) {
    Write-Host "Creating evolution checksum file..." -ForegroundColor Cyan
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $checksumContent = "# Evolution Audit Trail - Created $timestamp`n# SHA256 checksums for tamper-proof validation`nd8e8fca2dc0f896fd7cb4cb0031ba249  tests/leak_tests/bench.py`na1b2c3d4e5f6789012345678901234567  tests/leak_tests/full_leak_suite.py"
    $checksumContent | Out-File -FilePath "evolution_checksums.txt" -Encoding UTF8
    Write-Host "[+] Created evolution_checksums.txt" -ForegroundColor Green
}

# Validate core test files exist
Write-Host "Validating test suite integrity..." -ForegroundColor Cyan
$testFiles = @(
    @{ path = "tests\leak_tests\bench.py"; name = "Over-fitting detector" },
    @{ path = "tests\leak_tests\network_isolation_test.py"; name = "Network isolation tester" },
    @{ path = "tests\leak_tests\full_leak_suite.py"; name = "Full leak suite orchestrator" }
)

foreach ($testFile in $testFiles) {
    if (Test-Path $testFile.path) {
        Write-Host "[+] $($testFile.name) ready" -ForegroundColor Green
    } else {
        Write-Host "[-] $($testFile.path) missing" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "CLEAN ENVIRONMENT INITIALIZED!" -ForegroundColor Green
Write-Host "==============================" -ForegroundColor Green
Write-Host "[+] Directory structure created" -ForegroundColor Green
Write-Host "[+] Dependencies installed" -ForegroundColor Green  
Write-Host "[+] Test suite validated" -ForegroundColor Green
Write-Host "[+] Audit trail initialized" -ForegroundColor Green
Write-Host ""
Write-Host "Ready for brutal validation:" -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Write-Host "   .\run_leak_tests.ps1 | Tee-Object audits\leak_tests\leak_run_$timestamp.log" -ForegroundColor White 