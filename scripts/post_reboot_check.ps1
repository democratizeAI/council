$PROM = "http://localhost:9090"
try {
    $targetsResponse = Invoke-RestMethod "$PROM/api/v1/targets" -ErrorAction Stop
    $alertsResponse = Invoke-RestMethod "$PROM/api/v1/alerts" -ErrorAction Stop
    
    $up = ($targetsResponse.data.activeTargets | Where-Object { $_.health -eq "up" }).Count
    $total = $targetsResponse.data.activeTargets.Count
    $alerts = $alertsResponse.data.alerts.Count
    
    Write-Host "=== POST-REBOOT GREEN-BOARD CHECK ==="
    Write-Host "Targets UP: $up / $total"
    Write-Host "Active alerts: $alerts"
    Write-Host ""
    
    if ($up -ge 20 -and $alerts -eq 0) {
        New-Item "$env:TEMP\soak_phase4.done" -Force | Out-Null
        Write-Host "✅ Green board – soak timer started."
        Write-Host "Phase 5 gate OPEN - Ready to proceed!"
    } else {
        Write-Host "❌ Still red – investigate before Phase-5 tasks."
        Write-Host "Need: ≥20 UP targets AND 0 alerts"
        
        if ($up -lt 20) {
            Write-Host "  → Fix: Connect missing containers to monitoring network"
            Write-Host "  → Check: docker network connect --alias <svc> monitoring <container>"
        }
        if ($alerts -gt 0) {
            Write-Host "  → Fix: Restart guardian after targets turn UP"
        }
    }
} catch {
    Write-Host "❌ Prometheus not responding: $($_.Exception.Message)"
    Write-Host "Check: docker ps | grep prometheus"
} 