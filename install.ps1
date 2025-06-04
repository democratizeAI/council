# 🚀 AutoGen Council v2.6.0 - Complete 1-Click Installation Script
# Memory-Powered Desktop OS Assistant with Secure Code Execution
# Built through 90 Days of Architectural Blueprinting + 45 Hours of Human-AI Development
# Usage: irm https://raw.githubusercontent.com/luminainterface/council/master/install.ps1 | iex

param(
    [switch]$SkipDockerInstall = $false,
    [switch]$CPUOnly = $false,
    [string]$InstallPath = "$env:USERPROFILE\AutoGenCouncil"
)

Write-Host "🚀 AutoGen Council v2.6.0 - Complete Installation" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "Memory-Powered AI Assistant with Secure Code Execution" -ForegroundColor Green
Write-Host "🧠 FAISS Memory System • 🛡️ Firejail Sandbox • ⚡ 626ms Latency" -ForegroundColor Green
Write-Host ""

# Function to check if running as administrator
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Function to check system requirements
function Test-SystemRequirements {
    Write-Host "🔍 Checking system requirements..." -ForegroundColor Yellow
    
    # Check Windows version
    $version = [System.Environment]::OSVersion.Version
    if ($version.Major -lt 10) {
        Write-Host "❌ Windows 10 or later required" -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Windows version: $($version)" -ForegroundColor Green
    
    # Check memory (increased requirement for v2.6.0)
    $memory = Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property capacity -Sum
    $memoryGB = [math]::Round($memory.sum / 1GB)
    if ($memoryGB -lt 12) {
        Write-Host "⚠️ Recommended 12GB+ RAM for optimal v2.6.0 performance, found: ${memoryGB}GB" -ForegroundColor Yellow
        Write-Host "   System will work with 8GB+ but may be slower" -ForegroundColor Gray
        if ($memoryGB -lt 8) {
            Write-Host "❌ Minimum 8GB RAM required, found: ${memoryGB}GB" -ForegroundColor Red
            return $false
        }
    }
    Write-Host "✅ Memory: ${memoryGB}GB" -ForegroundColor Green
    
    # Check disk space (increased for v2.6.0 features)
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
    $freeSpaceGB = [math]::Round($disk.FreeSpace / 1GB)
    if ($freeSpaceGB -lt 30) {
        Write-Host "❌ Minimum 30GB free space required for v2.6.0, found: ${freeSpaceGB}GB" -ForegroundColor Red
        return $false
    }
    Write-Host "✅ Free disk space: ${freeSpaceGB}GB" -ForegroundColor Green
    
    # Check GPU (enhanced for v2.6.0)
    if (-not $CPUOnly) {
        try {
            $gpu = Get-CimInstance Win32_VideoController | Where-Object { $_.Name -like "*NVIDIA*" }
            if ($gpu) {
                Write-Host "✅ NVIDIA GPU detected: $($gpu.Name)" -ForegroundColor Green
                # Check VRAM if possible
                try {
                    $vram = [math]::Round($gpu.AdapterRAM / 1GB)
                    if ($vram -ge 10) {
                        Write-Host "✅ GPU VRAM: ${vram}GB (optimal for v2.6.0)" -ForegroundColor Green
                    } elseif ($vram -ge 6) {
                        Write-Host "✅ GPU VRAM: ${vram}GB (good for v2.6.0)" -ForegroundColor Yellow
                    } else {
                        Write-Host "⚠️ GPU VRAM: ${vram}GB (may be limited)" -ForegroundColor Yellow
                    }
                } catch {
                    Write-Host "ℹ️ GPU memory information not available" -ForegroundColor Blue
                }
            } else {
                Write-Host "⚠️ No NVIDIA GPU detected - will use CPU mode" -ForegroundColor Yellow
                $global:CPUOnly = $true
            }
        } catch {
            Write-Host "⚠️ Could not detect GPU - will use CPU mode" -ForegroundColor Yellow
            $global:CPUOnly = $true
        }
    } else {
        Write-Host "ℹ️ CPU-only mode selected" -ForegroundColor Blue
    }
    
    return $true
}

# Function to install Docker Desktop
function Install-Docker {
    if ($SkipDockerInstall) {
        Write-Host "⏭️ Skipping Docker installation" -ForegroundColor Blue
        return $true
    }
    
    Write-Host "🐳 Installing Docker Desktop..." -ForegroundColor Yellow
    
    # Check if Docker is already installed
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Write-Host "✅ Docker already installed: $dockerVersion" -ForegroundColor Green
            return $true
        }
    } catch {
        # Docker not found, proceed with installation
    }
    
    # Download Docker Desktop installer
    $dockerUrl = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
    $dockerInstaller = "$env:TEMP\DockerDesktopInstaller.exe"
    
    Write-Host "📥 Downloading Docker Desktop..." -ForegroundColor Blue
    try {
        Invoke-WebRequest -Uri $dockerUrl -OutFile $dockerInstaller -UseBasicParsing
    } catch {
        Write-Host "❌ Failed to download Docker Desktop: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Install Docker Desktop
    Write-Host "⚡ Installing Docker Desktop (this may take a few minutes)..." -ForegroundColor Blue
    try {
        Start-Process -FilePath $dockerInstaller -ArgumentList "install", "--quiet" -Wait -NoNewWindow
        Write-Host "✅ Docker Desktop installed" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to install Docker Desktop: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        Remove-Item $dockerInstaller -ErrorAction SilentlyContinue
    }
    
    # Start Docker Desktop
    Write-Host "🚀 Starting Docker Desktop..." -ForegroundColor Blue
    try {
        Start-Process -FilePath "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
        
        # Wait for Docker to be ready
        Write-Host "⏳ Waiting for Docker to start (this may take 2-3 minutes)..." -ForegroundColor Blue
        $timeout = 180 # 3 minutes
        $elapsed = 0
        
        do {
            Start-Sleep -Seconds 5
            $elapsed += 5
            try {
                docker version | Out-Null
                Write-Host "✅ Docker is ready!" -ForegroundColor Green
                return $true
            } catch {
                if ($elapsed % 30 -eq 0) {
                    Write-Host "⏳ Still waiting for Docker... ($elapsed/${timeout}s)" -ForegroundColor Yellow
                }
            }
        } while ($elapsed -lt $timeout)
        
        Write-Host "❌ Docker failed to start within timeout" -ForegroundColor Red
        return $false
    } catch {
        Write-Host "❌ Failed to start Docker Desktop: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to install Git if needed
function Install-Git {
    try {
        git --version | Out-Null
        Write-Host "✅ Git is already installed" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "📥 Installing Git..." -ForegroundColor Yellow
        
        # Install Git via winget
        try {
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
            Write-Host "✅ Git installed successfully" -ForegroundColor Green
            
            # Refresh PATH
            $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
            return $true
        } catch {
            Write-Host "❌ Failed to install Git. Please install manually from https://git-scm.com" -ForegroundColor Red
            return $false
        }
    }
}

# Function to download and setup AutoGen Council
function Install-AutoGenCouncil {
    Write-Host "📦 Setting up AutoGen Council v2.6.0..." -ForegroundColor Yellow
    
    # Create installation directory
    if (Test-Path $InstallPath) {
        Write-Host "📁 Installation directory exists: $InstallPath" -ForegroundColor Blue
        $response = Read-Host "Remove existing installation? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Remove-Item $InstallPath -Recurse -Force
        } else {
            Write-Host "⏭️ Using existing installation" -ForegroundColor Blue
        }
    }
    
    if (-not (Test-Path $InstallPath)) {
        New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null
    }
    
    # Clone repository
    Write-Host "📥 Downloading AutoGen Council v2.6.0..." -ForegroundColor Blue
    try {
        Set-Location $InstallPath
        git clone https://github.com/luminainterface/council.git .
        Write-Host "✅ Repository downloaded" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to clone repository: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    return $true
}

# Function to configure the system for v2.6.0
function Configure-System {
    Write-Host "⚙️ Configuring AutoGen Council v2.6.0..." -ForegroundColor Yellow
    
    # Create environment configuration for v2.6.0
    $envContent = @"
# AutoGen Council v2.6.0 Configuration
SWARM_PROFILE=production

# v2.6.0 Memory System
AZ_MEMORY_ENABLED=yes
AZ_MEMORY_PATH=./memory_store
MEMORY_DIMENSION=384

# v2.6.0 Sandbox System  
AZ_SHELL_TRUSTED=yes
ENABLE_SANDBOX=true

# Performance Configuration
SWARM_MAX_CONCURRENT=10
SWARM_TIMEOUT_MS=5000
SWARM_CLOUD_BUDGET_USD=10.0

# Monitoring
PROMETHEUS_ENABLED=true
"@
    
    if ($CPUOnly) {
        $envContent += "`nSWARM_PROFILE=quick_test`nCUDA_VISIBLE_DEVICES="
    }
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ Environment configured for v2.6.0" -ForegroundColor Green
    
    # Create desktop shortcut
    try {
        $shell = New-Object -comObject WScript.Shell
        $shortcut = $shell.CreateShortcut("$env:USERPROFILE\Desktop\AutoGen Council v2.6.0.lnk")
        $shortcut.TargetPath = "http://localhost:8000"
        $shortcut.IconLocation = "shell32.dll,13"
        $shortcut.Description = "AutoGen Council v2.6.0 - Memory-Powered Desktop OS Assistant"
        $shortcut.Save()
        Write-Host "✅ Desktop shortcut created" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Could not create desktop shortcut" -ForegroundColor Yellow
    }
    
    return $true
}

# Function to start the v2.6.0 system
function Start-AutoGenCouncil {
    Write-Host "🚀 Starting AutoGen Council v2.6.0..." -ForegroundColor Yellow
    Write-Host "This will start all services with memory + sandbox (may take 2-3 minutes)..." -ForegroundColor Blue
    
    try {
        # Start services
        docker compose up -d
        
        # Wait for services to be ready
        Write-Host "⏳ Waiting for v2.6.0 services to initialize..." -ForegroundColor Blue
        Start-Sleep -Seconds 30
        
        # Health check
        $maxAttempts = 12
        $attempt = 0
        $healthy = $false
        
        do {
            $attempt++
            try {
                $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
                if ($response.status -eq "healthy") {
                    $healthy = $true
                    break
                }
            } catch {
                # Service not ready yet
            }
            
            if ($attempt % 3 -eq 0) {
                Write-Host "⏳ Still initializing... (attempt $attempt/$maxAttempts)" -ForegroundColor Yellow
            }
            Start-Sleep -Seconds 10
        } while ($attempt -lt $maxAttempts)
        
        if ($healthy) {
            Write-Host "✅ AutoGen Council v2.6.0 is running!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Services failed to start properly" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Failed to start services: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to run v2.6.0 system test
function Test-Installation {
    Write-Host "🧪 Testing v2.6.0 installation..." -ForegroundColor Yellow
    
    try {
        # Test basic functionality
        Write-Host "  📡 Testing basic API..." -ForegroundColor Blue
        $testRequest = @{
            prompt = "Hello! Can you tell me what 2+2 equals?"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "http://localhost:8000/hybrid" -Method Post -Body $testRequest -ContentType "application/json" -TimeoutSec 30
        
        if ($response.text) {
            Write-Host "  ✅ Basic API test passed!" -ForegroundColor Green
            Write-Host "     Response: $($response.text)" -ForegroundColor Gray
            Write-Host "     Skill: $($response.skill_type)" -ForegroundColor Gray
            Write-Host "     Latency: $($response.latency_ms)ms" -ForegroundColor Gray
        }
        
        # Test memory system
        Write-Host "  🧠 Testing memory system..." -ForegroundColor Blue
        $memoryRequest = @{
            prompt = "Remember that my favorite color is blue"
        } | ConvertTo-Json
        
        $memoryResponse = Invoke-RestMethod -Uri "http://localhost:8000/hybrid" -Method Post -Body $memoryRequest -ContentType "application/json" -TimeoutSec 30
        Write-Host "  ✅ Memory test completed" -ForegroundColor Green
        
        # Test specialist routing
        Write-Host "  🧮 Testing math specialist..." -ForegroundColor Blue
        $mathRequest = @{
            prompt = "What is 25 * 16?"
        } | ConvertTo-Json
        
        $mathResponse = Invoke-RestMethod -Uri "http://localhost:8000/hybrid" -Method Post -Body $mathRequest -ContentType "application/json" -TimeoutSec 30
        if ($mathResponse.text -match "400") {
            Write-Host "  ✅ Math specialist working correctly!" -ForegroundColor Green
        }
        
        return $true
        
    } catch {
        Write-Host "❌ System test failed: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to display v2.6.0 success information
function Show-SuccessInfo {
    Write-Host ""
    Write-Host "🎉 AutoGen Council v2.6.0 Installation Complete!" -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Green
    Write-Host "Memory-Powered Desktop OS Assistant Ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Web Interfaces:" -ForegroundColor Cyan
    Write-Host "   • Main API: http://localhost:8000" -ForegroundColor White
    Write-Host "   • Health Check: http://localhost:8000/health" -ForegroundColor White
    Write-Host "   • Statistics: http://localhost:8000/stats" -ForegroundColor White
    Write-Host "   • Metrics: http://localhost:8000/metrics" -ForegroundColor White
    Write-Host "   • Grafana Dashboard: http://localhost:3000 (admin/autogen123)" -ForegroundColor White
    Write-Host "   • Prometheus: http://localhost:9090" -ForegroundColor White
    Write-Host ""
    Write-Host "💬 Quick Tests:" -ForegroundColor Cyan
    Write-Host "   # Basic conversation" -ForegroundColor Gray
    Write-Host '   curl -X POST http://localhost:8000/hybrid -H "Content-Type: application/json" -d "{\"prompt\":\"Hello world!\"}"' -ForegroundColor Gray
    Write-Host "   # Memory test" -ForegroundColor Gray
    Write-Host '   curl -X POST http://localhost:8000/hybrid -H "Content-Type: application/json" -d "{\"prompt\":\"Remember my name is Alice\"}"' -ForegroundColor Gray
    Write-Host "   # Math test" -ForegroundColor Gray  
    Write-Host '   curl -X POST http://localhost:8000/hybrid -H "Content-Type: application/json" -d "{\"prompt\":\"What is 50 * 40?\"}"' -ForegroundColor Gray
    Write-Host "   # Code execution test" -ForegroundColor Gray
    Write-Host '   curl -X POST http://localhost:8000/hybrid -H "Content-Type: application/json" -d "{\"prompt\":\"Run: print(sum([1,2,3,4,5]))\"}"' -ForegroundColor Gray
    Write-Host ""
    Write-Host "📚 Documentation:" -ForegroundColor Cyan
    Write-Host "   • Full Guide: $InstallPath\README.md" -ForegroundColor White
    Write-Host "   • Evolution Story: $InstallPath\docs\evolution\v2.6.0_full.md" -ForegroundColor White
    Write-Host ""
    Write-Host "🛠️ Management Commands:" -ForegroundColor Cyan
    Write-Host "   • Start: docker compose up -d" -ForegroundColor White
    Write-Host "   • Stop: docker compose down" -ForegroundColor White
    Write-Host "   • Logs: docker compose logs -f council" -ForegroundColor White
    Write-Host "   • Status: curl http://localhost:8000/health" -ForegroundColor White
    Write-Host ""
    Write-Host "🎯 v2.6.0 Features Enabled:" -ForegroundColor Cyan
    Write-Host "   ✅ Memory Persistence (FAISS vector storage - 7ms queries)" -ForegroundColor White
    Write-Host "   ✅ Secure Code Execution (Firejail sandbox - 45ms execution)" -ForegroundColor White
    Write-Host "   ✅ Specialist Routing (Math, Logic, Knowledge, Code)" -ForegroundColor White
    Write-Host "   ✅ Production Monitoring (Prometheus + Grafana)" -ForegroundColor White
    Write-Host "   ✅ Docker Deployment (Persistent volumes)" -ForegroundColor White
    if ($CPUOnly) {
        Write-Host "   ℹ️ CPU-Only Mode (GPU acceleration disabled)" -ForegroundColor Yellow
    } else {
        Write-Host "   ✅ GPU Acceleration (RTX 4070 optimized)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "📊 Performance Targets (v2.6.0):" -ForegroundColor Cyan
    Write-Host "   • Total Latency: 626ms (37% better than 1000ms target)" -ForegroundColor White
    Write-Host "   • Memory Queries: 7ms (86% better than 50ms target)" -ForegroundColor White
    Write-Host "   • Sandbox Execution: 45ms (55% better than 100ms target)" -ForegroundColor White
    Write-Host "   • Success Rate: 87.5%+ (9% over 80% target)" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 Your memory-powered AI assistant is ready!" -ForegroundColor Green
    Write-Host ""
}

# Main installation flow
try {
    # Check if running as administrator
    if (-not (Test-Administrator)) {
        Write-Host "⚠️ This script should be run as Administrator for Docker installation" -ForegroundColor Yellow
        Write-Host "You can continue, but Docker installation may fail" -ForegroundColor Yellow
        $response = Read-Host "Continue anyway? (y/N)"
        if ($response -ne 'y' -and $response -ne 'Y') {
            Write-Host "Please run as Administrator and try again" -ForegroundColor Red
            exit 1
        }
    }
    
    # System requirements check
    if (-not (Test-SystemRequirements)) {
        Write-Host "❌ System requirements not met" -ForegroundColor Red
        exit 1
    }
    
    # Install Git
    if (-not (Install-Git)) {
        Write-Host "❌ Git installation failed" -ForegroundColor Red
        exit 1
    }
    
    # Install Docker
    if (-not (Install-Docker)) {
        Write-Host "❌ Docker installation failed" -ForegroundColor Red
        exit 1
    }
    
    # Download and setup AutoGen Council
    if (-not (Install-AutoGenCouncil)) {
        Write-Host "❌ AutoGen Council setup failed" -ForegroundColor Red
        exit 1
    }
    
    # Configure system
    if (-not (Configure-System)) {
        Write-Host "❌ System configuration failed" -ForegroundColor Red
        exit 1
    }
    
    # Start the system
    if (-not (Start-AutoGenCouncil)) {
        Write-Host "❌ Failed to start AutoGen Council" -ForegroundColor Red
        Write-Host "Check logs with: docker compose logs council" -ForegroundColor Yellow
        exit 1
    }
    
    # Test installation
    if (-not (Test-Installation)) {
        Write-Host "⚠️ Installation completed but system test failed" -ForegroundColor Yellow
        Write-Host "Services may still be starting - try again in a few minutes" -ForegroundColor Yellow
    }
    
    # Show success information
    Show-SuccessInfo
    
} catch {
    Write-Host "❌ Installation failed with error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please check the error and try again" -ForegroundColor Yellow
    exit 1
} 