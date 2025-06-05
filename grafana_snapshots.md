# Grafana Snapshots - 48h Soak Test

## Soak Start Snapshot
**Timestamp:** June 5, 2025 6:47 PM  
**Status:** 🟢 ALL SYSTEMS GREEN

### Dashboard URLs
- **Main Dashboard:** http://localhost:3001/d/fastapi-soak
- **API Metrics:** http://localhost:3001/d/api-core  
- **Error Tracking:** http://localhost:3001/d/api-errors

### Key Metrics at Start
```
swarm_api_latency_p95: < 50ms
swarm_api_error_rate: 0.0%
reward_head_val_acc: 0.6805 ✅
rl_lora_last_reward: 0.8346 (up trend) ✅
snapshot_pruned_total: 2 ✅
lineage_last_push_timestamp: updated ✅
```

### Container Health
- ✅ swarm-api-main: healthy (port 8000)
- ✅ swarm-api-canary: healthy (port 8001) 
- ✅ swarm-grafana: running (port 3001)
- ✅ swarm-redis: healthy (port 6380)

---

## Monitoring Schedule
- **Every 4h:** Check p95 latency & 5xx rate
- **09:00/21:00 ET:** Kill-switch drill (30s)
- **T+24h:** Cold-boot spare node test
- **T+48h:** Final snapshot & log collection 