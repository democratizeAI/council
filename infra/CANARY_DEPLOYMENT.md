# 🎛️ SwarmAI Canary Deployment Guide

## Overview

This guide implements a complete **"flip-the-switch" canary deployment system** for SwarmAI council services, enabling safe gradual rollouts with instant rollback capabilities.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │    Monitoring   │
│    (Traefik)    │    │    (Grafana)    │
│   95% │ 5%      │    │   4 Key Panels  │
└──────┬──────────┘    └─────────────────┘
       │                        │
   ┌───▼───┐              ┌─────▼─────┐
   │ Main  │              │  Canary   │
   │Council│              │ Council   │
   │ :9000 │              │  :9001    │
   └───────┘              └───────────┘
```

## 📁 File Structure

```
infra/
├── deploy/
│   ├── docker-compose.canary.yml    # Canary service overlay
│   └── canary.env                   # Canary configuration
├── scripts/
│   ├── canary-deploy.sh            # Main deployment script
│   ├── canary-scale.sh             # Traffic scaling script
│   ├── canary-rollback.sh          # Emergency rollback
│   ├── test_smoke.sh               # Offline tests (2s)
│   └── test_live_cloud.sh          # Live tests (15s)
└── monitoring/
    └── grafana-canary-dashboard.json # 4-panel monitoring dashboard
```

## 🚀 Quick Start

### 1. Setup

```bash
# Create infra directory structure
mkdir -p infra/{deploy,scripts,monitoring}

# Copy your API keys to canary.env
cd infra/deploy
cp canary.env canary.env.local
# Edit canary.env.local with real API keys
```

### 2. Deploy Canary (5% traffic)

```bash
# One command to deploy 5% canary
./infra/scripts/canary-deploy.sh
```

This will:
- ✅ Build and tag the exact Docker image
- ✅ Verify canary configuration
- ✅ Start parallel replica on port 9001
- ✅ Configure Traefik for 95%/5% traffic split
- ✅ Run smoke tests (offline + live)
- ✅ Display monitoring dashboard info

### 3. Monitor for 24h

Watch these 4 panels in Grafana (`http://localhost:3000`):

| Panel | Green Band | Alert Threshold |
|-------|------------|-----------------|
| Council p95 latency | ≤ 0.7s | CouncilLatencyHigh @ 1s |
| Council cost/day | < $1 | CloudBudgetExceeded |
| Edge high-risk ratio | < 10% | HighRiskSpike |
| VRAM usage | < 9.8GB | Loader guard @ 10.5GB |

### 4. Scale Up (if green)

```bash
# Scale to 25% after 24h
./infra/scripts/canary-scale.sh 25

# Scale to 50% after another 24h
./infra/scripts/canary-scale.sh 50

# Full rollout to 100%
./infra/scripts/canary-scale.sh 100
```

### 5. Emergency Rollback (if red)

```bash
# Instant rollback to 0% canary traffic
./infra/scripts/canary-rollback.sh
```

## 🎛️ Detailed Process

### Step 1: Bake & Tag Image
```bash
cd infra/deploy
docker compose build council
# Locks dependencies and CUDA kernels
```

### Step 2: Stage Canary Environment
```bash
cat > canary.env <<'EOF'
SWARM_COUNCIL_ENABLED=true
COUNCIL_TRAFFIC_PERCENT=5
SWARM_CLOUD_ENABLED=true
SWARM_GPU_PROFILE=rtx_4070
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
MISTRAL_API_KEY=your_real_key_here
OPENAI_API_KEY=your_real_key_here
EOF
```

### Step 3: Spin Up Parallel Replica
```bash
docker compose --env-file canary.env \
               -f ../docker-compose.yml \
               -f docker-compose.canary.yml up -d api-canary
```

### Step 4: Configure Load Balancer
Traefik automatically picks up weights from Docker labels:
- Main service: `weight=95`
- Canary service: `weight=5`

### Step 5: Monitor 4 Key Panels
Import `grafana-canary-dashboard.json` into Grafana for real-time monitoring.

### Step 6: Scale Without Redeploy
```bash
# Zero-downtime weight change via SIGHUP
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=5/COUNCIL_TRAFFIC_PERCENT=25/" /app/.env && kill -HUP 1'
```

### Step 7: Post-Flip Smoke Tests
```bash
# Offline functional (2s)
./infra/scripts/test_smoke.sh

# Live sanity with real APIs (15s)  
SWARM_COUNCIL_ENABLED=true \
SWARM_CLOUD_ENABLED=true \
./infra/scripts/test_live_cloud.sh
```

## 🟢 When NOT to Flip

Auto-rollback triggers if **any** of these conditions occur:

- **p95 latency > 0.7s** for 5+ minutes
- **swarm_council_cost_dollars_total** projects > $1/day  
- **VRAM crosses 9.8GB** (out-of-family model slipped in)
- **mistral_errors_total / mistral_tokens_total > 2%**

The load balancer script auto-drops canary weight to 0% until investigation.

## 🔧 Troubleshooting

### Canary Won't Start
```bash
# Check logs
docker logs autogen-council-canary

# Verify config
docker exec autogen-council-canary env | grep COUNCIL

# Check health
curl http://localhost:9001/health
```

### Load Balancer Issues
```bash
# Check Traefik dashboard
open http://localhost:8080

# Verify service discovery
docker exec traefik-lb cat /etc/traefik/dynamic.yml

# Test traffic distribution
for i in {1..20}; do curl -s http://localhost/health; done
```

### Monitoring Problems
```bash
# Check Prometheus metrics
curl http://localhost:9090/metrics | grep swarm_

# Verify Grafana datasource
curl http://admin:autogen123@localhost:3000/api/datasources

# Import dashboard manually
# Grafana → Dashboards → Import → Upload grafana-canary-dashboard.json
```

## 🎯 Production Checklist

Before production deployment:

- [ ] Replace placeholder API keys in `canary.env`
- [ ] Configure real Prometheus/Grafana endpoints
- [ ] Set up alert notifications (Slack, PagerDuty, etc.)
- [ ] Test rollback procedures in staging
- [ ] Configure log aggregation for canary containers
- [ ] Document incident response procedures
- [ ] Train team on monitoring dashboard

## 🔗 Integration Points

### CI/CD Pipeline
```yaml
# .github/workflows/canary-deploy.yml
- name: Deploy Canary
  run: |
    ./infra/scripts/canary-deploy.sh
    # Wait for health checks
    sleep 60
    # Run extended test suite
    ./infra/scripts/test_live_cloud.sh
```

### Slack Notifications
```bash
# Add to canary-rollback.sh
curl -X POST $SLACK_WEBHOOK_URL \
  -d '{"text":"🚨 Canary rollback triggered for SwarmAI"}'
```

### Custom Metrics
Extend `prometheus_metrics_exporter.py` to include:
- `swarm_canary_traffic_percentage`
- `swarm_deployment_version` 
- `swarm_rollback_events_total`

## 📊 Success Metrics

Track these KPIs during canary deployments:

- **MTTR (Mean Time To Rollback)**: < 2 minutes
- **False Positive Rate**: < 5% (rollbacks due to false alarms)
- **Deployment Success Rate**: > 95%
- **Zero-Downtime Achievement**: 100%

## 🎉 That's It!

Run three commands (`build → env → up`), add the weight in your load balancer, and you have a live 5% canary with pre-wired alarms and instant rollback.

Once the dashboard stays green overnight, just nudge `COUNCIL_TRAFFIC_PERCENT` upward and let the swarm spread its wings! 🚀 