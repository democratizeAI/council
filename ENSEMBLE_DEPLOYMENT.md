# Ensemble Adapter Deployment Guide

## Overview
The Adapter-Ensemble system routes prompts to specialized LoRA adapters based on pattern clustering, achieving accuracy lifts without VRAM inflation by maintaining an intelligent cache of ≤3 adapters.

## Architecture

```
┌──────── RouterCascade ────────┐
│ 1. sha1(prompt) → cluster_id  │
│ 2. redis HGET lora:router_map │──► "2025-06-07"  (adapter tag)
│ 3. lora_manager.get(tag)      │──► merged PEFT weights  
│ 4. generate()                 │
└───────────────────────────────┘
```

## Performance Targets
- **ensemble_miss_rate** < 0.10 (90%+ prompts routed to adapters)
- **holdout_success_ratio** ↑ +1.5 pp vs base model
- **VRAM overhead** ≤ 120 MB (3 × 40 MB adapters)

## Deployment Steps

### 1. Infrastructure Setup

```bash
# Deploy with ensemble support
docker-compose -f docker-compose.ensemble.yml up -d

# Verify GPU access and VRAM
docker exec swarm-api nvidia-smi
```

**Key Environment Variables:**
```env
MAX_ADAPTERS=3                    # Cache capacity
BASE_MODEL_PATH=/models/tinyllama # Base model location
REDIS_CLUSTER_PREFIX=pattern:cluster:
CUDA_VISIBLE_DEVICES=0           # GPU assignment
```

### 2. LoRA Directory Structure

```
/loras/
├── 2025-06-06/              # Adapter version tags
│   ├── adapter.bin          # PEFT weights
│   └── adapter_config.json  # LoRA configuration
├── 2025-06-07/
│   ├── adapter.bin
│   └── adapter_config.json
└── code-specialist-v2/
    ├── adapter.bin
    └── adapter_config.json
```

### 3. Initial Mapping Setup

Seed high-traffic clusters manually before nightly eval (#204):

```bash
# Set cluster→adapter mappings
curl -X POST "localhost:8000/admin/ensemble" \
  -d "cluster_id=c17&adapter_tag=2025-06-06"

curl -X POST "localhost:8000/admin/ensemble" \
  -d "cluster_id=c42&adapter_tag=code-specialist-v2"

# Bulk mapping for efficiency
curl -X POST "localhost:8000/admin/ensemble/bulk" \
  -H "Content-Type: application/json" \
  -d '{
    "c10": "2025-06-06",
    "c25": "2025-06-07", 
    "c88": "code-specialist-v2"
  }'
```

### 4. Cache Warming

Pre-load popular adapters to reduce cold-start latency:

```bash
curl -X POST "localhost:8000/admin/ensemble/cache/warm" \
  -H "Content-Type: application/json" \
  -d '["2025-06-07", "code-specialist-v2", "2025-06-06"]'
```

## Operations Manual

### Monitoring Dashboard

Access ensemble metrics at `http://localhost:3000` (Grafana):

**Key Panels:**
- Ensemble Miss Rate (target: <10%)
- Cache Hit Ratio (target: >80%)
- Adapter Load Times (target: <2s)
- VRAM Usage (target: <4GB total)

### Performance Tuning

**Cache Size Optimization:**
```bash
# Monitor eviction rate
curl "localhost:9090/api/v1/query?query=rate(ensemble_cache_evictions_total[5m])"

# Increase cache if evictions > 0.5/min
export MAX_ADAPTERS=4
docker-compose restart swarm-api
```

**Adapter Placement:**
- Place adapters on SSD for faster loading
- Use `adapter_config.json` to tune LoRA rank/alpha
- Monitor `ensemble_adapter_load_duration_seconds` for bottlenecks

### Troubleshooting

**High Miss Rate (>10%):**
```bash
# Check cluster mappings
curl "localhost:8000/admin/ensemble/stats"

# View unmapped clusters
redis-cli --scan --pattern "pattern:cluster:*" | \
  xargs -I {} redis-cli HGET lora:router_map {}
```

**VRAM Overflow:**
```bash
# Check GPU memory usage  
nvidia-smi

# Clear adapter cache if needed
curl -X POST "localhost:8000/admin/ensemble/cache/clear"

# Reduce cache size
export MAX_ADAPTERS=2
docker-compose restart swarm-api
```

**Adapter Load Failures:**
```bash
# Check adapter integrity
ls -la /loras/*/adapter.bin

# Verify permissions
docker exec swarm-api ls -la /loras/

# Check logs for specific errors
docker logs swarm-api | grep "adapter.*failed"
```

### Alert Responses

**EnsembleMissRateHigh** (>10% for 15m):
1. Check `/admin/ensemble/stats` for missing mappings
2. Verify pattern-miner is running and clustering prompts
3. Review adapter availability in `/loras/` directory

**EnsembleAdapterLoadFailure** (0.1/min for 5m):
1. Check disk space: `df -h /loras`
2. Verify adapter file integrity
3. Review GPU memory availability
4. Check for corrupted adapter files

**EnsembleCacheEvictionsHigh** (>0.5/min for 10m):
1. Consider increasing `MAX_ADAPTERS`
2. Review adapter usage patterns
3. Pre-warm cache with popular adapters
4. Optimize cluster→adapter mapping distribution

## VRAM Budget Analysis

**Base System:**
- TinyLLaMA base model: ~2.8 GB
- System overhead: ~0.5 GB
- **Available for adapters: ~0.7 GB**

**Per-Adapter Cost:**
- Rank-64 LoRA: ~40 MB
- 3 adapters max: 120 MB
- **Safety margin: ~580 MB**

**Scaling Considerations:**
- 4 adapters: 160 MB (recommended max)
- 5+ adapters: Monitor `nvidia-smi` closely
- Consider model sharding for >5 adapters

## Integration with Nightly Eval (#204)

Once reward-weighted PPO training is deployed:

```bash
# Nightly adapter update script
./scripts/update_ensemble_mappings.sh

# Evaluates each cluster on hold-out set
# Updates lora:router_map where new adapter > baseline
# Automatically triggered by cron at 2 AM
```

## Success Validation

**Week 1 Targets:**
- [ ] ensemble_miss_rate < 15% (allowing ramp-up)
- [ ] No adapter load failures
- [ ] Cache evictions < 1/min

**Week 2 Targets:**
- [ ] ensemble_miss_rate < 10% 
- [ ] holdout_success_ratio baseline established
- [ ] VRAM usage stable <4GB

**Production Ready:**
- [ ] ensemble_miss_rate < 5%
- [ ] holdout_success_ratio +1.5 pp vs base
- [ ] P95 adapter resolution <100ms
- [ ] Zero adapter load failures for 48h

## Rollback Procedure

If ensemble causes issues:

```bash
# 1. Disable ensemble middleware (fallback to base model)
export ENSEMBLE_ENABLED=false
docker-compose restart swarm-api

# 2. Clear all mappings (emergency fallback)
redis-cli DEL lora:router_map

# 3. Monitor miss rate should → 100% (expected in fallback)
# 4. Verify base model responses working normally
```

## Cost-Benefit Analysis

**Benefits:**
- **Accuracy**: +1.5 pp success rate improvement
- **Specialization**: Domain-specific adapters for code, creative, etc.
- **Efficiency**: 120MB vs 2.8GB for equivalent specialized models

**Costs:**
- **Complexity**: Additional Redis mappings and cache management
- **Latency**: +10-50ms for adapter resolution and loading
- **Ops overhead**: Monitoring ensemble miss rates and cache health

**ROI**: Positive if accuracy gains > 1.5% justify 10-50ms latency cost.

---

## Quick Reference

```bash
# View ensemble status
curl localhost:8000/admin/ensemble/stats

# Set mapping
curl -X POST "localhost:8000/admin/ensemble?cluster_id=c42&adapter_tag=2025-06-07"

# Warm cache
curl -X POST localhost:8000/admin/ensemble/cache/warm -d '["adapter-tag"]'

# Monitor miss rate
curl "localhost:9090/api/v1/query?query=rate(ensemble_miss_total[5m])/rate(swarm_router_requests_total[5m])"
``` 