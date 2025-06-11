# Green-Flip Sequence Monitor
# Tracks critical metrics and gates for v0.1 pre-release
param(
    [int]$RefreshSeconds = 30,
    [switch]$Quiet
)

Write-Host "GREEN-FLIP SEQUENCE MONITOR" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Write-Host ""

function Get-PhaseStatus {
    $status = @{
        "phase5_soak_p95" = "≤ 160ms"
        "fragment_events" = "0"
        "cloud_est_usd_total" = "≤ $0.50/day"
        "ledger_row_seen_lag_seconds" = "< 15s"
    }
    return $status
}

function Get-GreenFlipTargets {
    return @{
        "BC-130" = @{
            "owner" = "Council-Infra"
            "action" = "AI-Council smoke-cycle"
            "gate" = "council_smoke_pass_total >= 1"
            "deadline" = "06/11 13:00 ET"
            "status" = "IN PROGRESS"
        }
        "IDR-01" = @{
            "owner" = "Builder"
            "action" = "Merge PR -> deploy Intent-Distillation Agent"
            "gate" = "idr_json_total >= 1"
            "deadline" = "ASAP after OPS board green"
            "status" = "WAITING"
        }
        "LG-210" = @{
            "owner" = "Builder + QA"
            "action" = "Set GAUNTLET_ENABLED=true after 24h soak"
            "gate" = "Canary passes or auto-revert <= 120s"
            "deadline" = "After soak pass"
            "status" = "WAITING"
        }
        "BC-200" = @{
            "owner" = "QA"
            "action" = "Launch 6-h fast-Gauntlet"
            "gate" = "PASS verdict row posted"
            "deadline" = "T-22h"
            "status" = "WAITING"
        }
    }
}

function Get-InfrastructureDrills {
    return @{
        "EXT-24A" = @{
            "timeline" = "T-28h"
            "owner" = "DevOps"
            "drill" = "Deploy HA LB overlay; kill primary GPU node"
            "gate" = "lb_failover_success_total >= 1; p95 spike < 20ms"
        }
        "EXT-24B" = @{
            "timeline" = "T-26h"
            "owner" = "SRE"
            "drill" = "Wire anomaly panel; inject 10% latency burst"
            "gate" = "CouncilLatencyAnomaly fires <= 30s"
        }
        "EXT-24C" = @{
            "timeline" = "T-24h"
            "owner" = "FinOPs"
            "drill" = "Enable autoscaler; ramp to 600 QPS"
            "gate" = "GPU util 65-80%; VRAM < 10.5GB"
        }
    }
}

function Show-Dashboard {
    Clear-Host
    Write-Host "GREEN-FLIP SEQUENCE MONITOR" -ForegroundColor Green
    Write-Host "=============================" -ForegroundColor Green
    Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss ET')" -ForegroundColor Gray
    Write-Host ""
    
    # Board Health Metrics
    Write-Host "BOARD HEALTH TARGETS" -ForegroundColor Cyan
    Write-Host "---------------------" -ForegroundColor Cyan
    $health = Get-PhaseStatus
    foreach ($metric in $health.Keys) {
        $target = $health[$metric]
        Write-Host "  $metric : $target" -ForegroundColor White
    }
    Write-Host ""
    
    # Green-Flip Targets
    Write-Host "GREEN-FLIP TARGETS (24h)" -ForegroundColor Yellow
    Write-Host "------------------------" -ForegroundColor Yellow
    $targets = Get-GreenFlipTargets
    foreach ($id in $targets.Keys) {
        $target = $targets[$id]
        Write-Host "  $id [$($target.status)] - $($target.owner)" -ForegroundColor White
        Write-Host "    Action: $($target.action)" -ForegroundColor Gray
        Write-Host "    Gate: $($target.gate)" -ForegroundColor Gray
        Write-Host ""
    }
    
    # Infrastructure Drills
    Write-Host "INFRASTRUCTURE DRILLS" -ForegroundColor Magenta
    Write-Host "---------------------" -ForegroundColor Magenta
    $drills = Get-InfrastructureDrills
    foreach ($id in $drills.Keys) {
        $drill = $drills[$id]
        Write-Host "  $($drill.timeline) - $id ($($drill.owner))" -ForegroundColor White
        Write-Host "    Drill: $($drill.drill)" -ForegroundColor Gray
        Write-Host "    Gate: $($drill.gate)" -ForegroundColor Gray
        Write-Host ""
    }
    
    # Freeze Protocol Status
    Write-Host "FREEZE PROTOCOL STATUS" -ForegroundColor Red
    Write-Host "----------------------" -ForegroundColor Red
    Write-Host "  Ledger freeze-locked until: 06/11 18:30 ET" -ForegroundColor White
    Write-Host "  Allowed branches: hotfix/* or ops-green only" -ForegroundColor White
    Write-Host "  New rows: PROHIBITED" -ForegroundColor White
    Write-Host "  Status flips: ALLOWED" -ForegroundColor White
    Write-Host ""
    
    # Risk Monitor
    Write-Host "RISK MONITOR" -ForegroundColor Red
    Write-Host "------------" -ForegroundColor Red
    Write-Host "  LoRA Gauntlet fails -> ENABLE_LORA=false" -ForegroundColor Gray
    Write-Host "  Autoscaler overshoot -> Reduce to 2 QPS" -ForegroundColor Gray
    Write-Host "  New CVE in Gauntlet -> Auto-revert + 3h re-run" -ForegroundColor Gray
    Write-Host ""
    
    if (-not $Quiet) {
        Write-Host "Next refresh in $RefreshSeconds seconds... (Ctrl+C to exit)" -ForegroundColor Gray
    }
}

# Main monitoring loop
if ($Quiet) {
    Show-Dashboard
} else {
    while ($true) {
        Show-Dashboard
        Start-Sleep -Seconds $RefreshSeconds
    }
} 