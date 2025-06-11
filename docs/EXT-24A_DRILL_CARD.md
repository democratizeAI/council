# 🔧 EXT-24A HA Load-Balancer Drill - Quick Reference

**Time Window**: T-28h (04:30 ET)  
**Objective**: Validate HA failover under load with minimal latency impact

## 📋 Execution Sequence

| Step | Action | Command | Success Signal |
|------|--------|---------|----------------|
| **1️⃣** | **Merge PR** | `gh pr merge devops/EXT-24A-ha-lb-overlay --merge -b "ops-green"` | Slack #builder-alerts: ✅ merged... |
| **2️⃣** | **Deploy** | PatchCtl auto-rolls tag | Prom target `lb_exporter:9100` appears |
| **3️⃣** | **Failover** | `./scripts/kill_primary_gpu.sh` | `lb_failover_success_total +1`<br/>p95 spike < 20ms |
| **4️⃣** | **Document** | `/ops snapshot note "HA LB drill pass (spike 18 ms)"` | Logged to state-of-titan |
| **5️⃣** | **[If Fail]** | `patchctl rollback deploy ha-lb-overlay` | p95 returns < 160ms |

## 🚨 Success Gates

✅ **PASS Criteria**:
- `lb_failover_success_total ≥ 1`
- p95 latency spike < 20ms during failover
- Recovery to < 160ms within 60s
- `frag_events_total = 0` (no container restarts)

❌ **FAIL Triggers**:
- p95 > 170ms for 2+ minutes → Guardian auto-page
- `frag_events_total > 0` → Breaks 24h soak
- p95 spike > 20ms → Manual rollback required

## 🛡️ Rollback Procedure

```bash
# Immediate rollback if gates fail
patchctl rollback deploy ha-lb-overlay

# Verify recovery
curl -s http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(http_request_duration_seconds_bucket[5m]))
```

## 📊 Key Metrics Watch

- **Primary**: `lb_failover_success_total`
- **Latency**: p95 spike during failover
- **Recovery**: Return to baseline < 60s
- **Stability**: `frag_events_total = 0`

## ⏰ Timeline Context

- **Pre-drill**: Soak test running (10.9h elapsed, 13.1h remaining)
- **Post-drill**: T-26h EXT-24B Anomaly Burst
- **LG-210**: Auto-enables when soak completes (~18:30 ET)

---
*Status: 🟢 Ready for execution at T-28h* 