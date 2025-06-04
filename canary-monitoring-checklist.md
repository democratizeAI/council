# 🚦 Canary-25% Go-Live Monitoring Checklist

## 📊 Four Green Dials to Watch (30 minutes)

Monitor these **4 critical panels** on the Grafana v2.6.0 dashboard:

| Panel | Metric | Green Band | Trip Threshold | Duration |
|-------|--------|------------|---------------|----------|
| **p95 Latency** | `swarm_council_latency_seconds_p95` | ≤ 120ms | 200ms | 5 min |
| **5xx Rate** | `rate(http_requests_total{code=~"5.."}[5m])` | ≤ 0.2 req/min | >0.5 spike | instant |
| **VRAM Used** | `swarm_vram_used_bytes` | < 10.5GB | ≥ 10.8GB | instant |
| **Fragment Events** | `swarm_cuda_fragmentation_events_total` | flat at 0 | first bump | instant |

### 🟢 Green Criteria (ALL must stay green for 30 min)
- **p95 Latency**: ≤ 120ms consistently
- **5xx Error Rate**: ≤ 0.2 req/min (no spikes >0.5)
- **VRAM Usage**: < 10.5GB (RTX 4070 limit)
- **CUDA Fragmentation**: Stays flat at 0 events

### 🚨 Auto-Rollback Triggers
**ANY** of these conditions → **IMMEDIATE ROLLBACK**:
- p95 latency > 200ms for 5+ minutes
- 5xx rate spike > 0.5 req/min
- VRAM usage ≥ 10.8GB
- First CUDA fragmentation event

## 🔍 Verification Commands

### Step 1: Verify 25% Traffic Split
```bash
curl -s localhost:8001/health | jq .route_mode   # → "canary25"
```

### Step 2: Health Checks
```bash
# Main service (75% traffic)
curl -s http://localhost:8000/health

# Canary service (25% traffic)  
curl -s http://localhost:8001/health

# Load balancer
curl -s http://localhost/health
```

### Step 3: Smoke Tests After Scaling
```bash
# Offline functional tests (2 seconds)
./test_smoke.sh

# Live cloud tests (15 seconds)
SWARM_COUNCIL_ENABLED=true \
SWARM_CLOUD_ENABLED=true \
./test_live_cloud.sh
```

## ⚡ Emergency Rollback (Copy-Paste Ready)

### Method 1: Zero Traffic (Instant)
```bash
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=.*/COUNCIL_TRAFFIC_PERCENT=0/" /app/.env && kill -HUP 1'
```

### Method 2: Stop Canary (Nuclear)
```bash
docker compose stop api-canary
```

## 🎯 Next Steps Decision Tree

### ✅ ALL GREEN for 30 minutes → Scale to 50%
```bash
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=25/COUNCIL_TRAFFIC_PERCENT=50/" /app/.env && kill -HUP 1'
```

### 🟡 MIXED/AMBER → Hold at 25%
- Continue monitoring for another 30 minutes
- Investigate amber metrics
- Consider rollback if trending toward red

### 🔴 ANY RED → Emergency Rollback
```bash
./emergency-rollback.sh  # or manual commands above
```

## 📊 Dashboard URLs
- **Grafana v2.6.0**: http://localhost:3000
- **Traefik LB**: http://localhost:8080
- **Main API**: http://localhost:8000/health  
- **Canary API**: http://localhost:8001/health

## 📝 Timeline Checklist

- [ ] **T+0**: Execute `./scale-canary-25.sh`
- [ ] **T+0**: Verify route_mode shows "canary25"
- [ ] **T+5**: Run smoke tests (`./test_smoke.sh`)
- [ ] **T+10**: First dashboard check (all 4 dials green?)
- [ ] **T+15**: One full Prometheus scrape complete
- [ ] **T+30**: Final go/no-go decision
  - [ ] **GO**: Scale to 50% (`./scale-canary-50.sh`)
  - [ ] **NO-GO**: Emergency rollback

## 🎯 Success Criteria for v0.4.1 Tag
After **24h at 50-100%** traffic:
- [ ] Zero fragmentation events
- [ ] p95 latency stable ≤ 120ms
- [ ] 5xx rate < 0.1 req/min
- [ ] VRAM usage stable < 10.5GB
- [ ] Tag v0.4.1 "stable canary scale-out"
- [ ] Merge Router 2.0 behind fresh 5% canary 