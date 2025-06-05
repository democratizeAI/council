# Install Agent-0 Windows Service
# Usage: Run as Administrator

Write-Host "🚀 Installing Agent-0 AutoGen Council Service" -ForegroundColor Green

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    pause
    exit 1
}

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found in PATH" -ForegroundColor Red
    Write-Host "Please install Python and ensure it's in your PATH" -ForegroundColor Yellow
    pause
    exit 1
}

# Install pywin32 if not already installed
Write-Host "📦 Installing pywin32..." -ForegroundColor Yellow
try {
    pip install pywin32
    Write-Host "✅ pywin32 installed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install pywin32" -ForegroundColor Red
    pause
    exit 1
}

# Set environment variable to indicate service management
Write-Host "🔧 Setting environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("AGENT0_SERVICE_MANAGED", "true", "Machine")

# Create logs directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$logsDir = Join-Path $projectDir "logs"

if (!(Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force
    Write-Host "✅ Created logs directory: $logsDir" -ForegroundColor Green
}

# Stop existing service if running
Write-Host "🛑 Stopping existing service..." -ForegroundColor Yellow
try {
    python (Join-Path $scriptDir "agent0_service.py") stop
    Write-Host "✅ Existing service stopped" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ No existing service found" -ForegroundColor Cyan
}

# Remove existing service if installed
Write-Host "🗑️ Removing existing service..." -ForegroundColor Yellow
try {
    python (Join-Path $scriptDir "agent0_service.py") remove
    Write-Host "✅ Existing service removed" -ForegroundColor Green
} catch {
    Write-Host "ℹ️ No existing service to remove" -ForegroundColor Cyan
}

# Install the service
Write-Host "📥 Installing Agent0Council service..." -ForegroundColor Yellow
try {
    python (Join-Path $scriptDir "agent0_service.py") install
    Write-Host "✅ Service installed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install service" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    pause
    exit 1
}

# Configure service recovery options
Write-Host "⚙️ Configuring service recovery..." -ForegroundColor Yellow
try {
    sc.exe failure Agent0Council reset= 3600 actions= restart/60000/restart/60000/restart/60000
    Write-Host "✅ Service recovery configured: restart after 1 minute if crashed" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Could not configure service recovery" -ForegroundColor Yellow
}

# Start the service
Write-Host "▶️ Starting Agent0Council service..." -ForegroundColor Yellow
try {
    python (Join-Path $scriptDir "agent0_service.py") start
    Write-Host "✅ Service started successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start service" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    
    # Show service status for debugging
    Write-Host "`n🔍 Service status:" -ForegroundColor Yellow
    sc.exe query Agent0Council
    
    Write-Host "`n📋 Check Event Viewer for detailed error logs:" -ForegroundColor Yellow
    Write-Host "   eventvwr.msc -> Windows Logs -> Application" -ForegroundColor Cyan
    pause
    exit 1
}

# Wait a moment and check if service is running
Start-Sleep -Seconds 5

Write-Host "`n🏥 Testing health endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 10
    if ($response.status -eq "healthy") {
        Write-Host "✅ Agent-0 service is healthy and responding" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Service responding but not healthy" -ForegroundColor Yellow
        Write-Host "Status: $($response.status)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Health check failed - service may still be starting" -ForegroundColor Red
    Write-Host "Wait a minute and check http://localhost:8000/health manually" -ForegroundColor Yellow
}

Write-Host "`n🎉 Installation complete!" -ForegroundColor Green
Write-Host "📊 Service Info:" -ForegroundColor Yellow
Write-Host "   Name: Agent0Council" -ForegroundColor Cyan
Write-Host "   Display: Agent-0 AutoGen Council" -ForegroundColor Cyan
Write-Host "   URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "   Health: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host "   Metrics: http://localhost:8000/metrics" -ForegroundColor Cyan

Write-Host "`n🔧 Management Commands:" -ForegroundColor Yellow
Write-Host "   Start:   python services\agent0_service.py start" -ForegroundColor Cyan
Write-Host "   Stop:    python services\agent0_service.py stop" -ForegroundColor Cyan
Write-Host "   Remove:  python services\agent0_service.py remove" -ForegroundColor Cyan

Write-Host "`n📋 Check logs at: $logsDir\agent0_service.log" -ForegroundColor Yellow
Write-Host "`n🔄 The service will now start automatically on boot!" -ForegroundColor Green

pause
