# Trinity Council – Runtime Stack `v10.3-δ-stable`

| Latest tag | CI | Docs | Slack |
|------------|----|------|-------|
| `v10.3-δ-stable` | ![CI](https://github.com/democratizeAI/council/actions/workflows/swarm-ci.yml/badge.svg) | [Runbook](docs/runbook.md) | #trinity-ops |

**Production-ready AI swarm runtime with GPU spike protection, distributed inference, and autonomous deployment.**

## 🚀 Quick Start (Dev Box)

```bash
git clone https://github.com/democratizeAI/council.git
cd council
cp .env.sample .env      # add your API keys
docker compose up -d
open http://localhost:9000/health
```

**Requirements:** Docker 24+, 8GB RAM, Optional: NVIDIA GPU + CUDA 12.3

## 📋 What's Included

- **🧠 Council API**: Multi-agent swarm orchestration  
- **⚡ GPU Circuit Breaker**: Automatic spike protection (>85% utilization)
- **🔄 Load Balancer**: Traefik with health checks + metrics
- **📊 Monitoring**: Prometheus + Grafana + AlertManager → Slack
- **🎯 Inference Heads**: Local GGUF models + cloud fallback
- **🏗️ Production Stack**: Docker Swarm ready with `docker-stack-prod.yml`

## 🛠️ Development

### Runtime Profiles
```bash
# Core services only (9 containers)
docker compose -f docker-compose.yml -f docker-compose.runtime.yml up -d

# Add development tools  
docker compose --profile dev up -d streamlit-ui

# Performance testing
docker compose --profile perf up -d loadtest_soak
```

### Contributing
- All PRs target `master`
- Must pass CI & markdownlint  
- Squash-merge only
- Auto-delete merged branches

## 📚 Documentation

- [**Production Deployment Guide**](ops/DOCKER_RUNTIME_GUIDE.md)
- [**GPU Spike Protection**](docs/gpu-guardrails.md) 
- [**Monitoring Setup**](grafana/README.md)
- [**API Reference**](docs/api.md)

## 🔧 Maintenance

```bash
# Weekly cleanup (removes merged branches)
./scripts/gh_branch_sweep.sh

# Docker housekeeping  
./ops/docker-housekeeping.sh

# Health check
curl http://localhost:9000/health
```

## 📊 System Status

**Current Runtime Footprint:**
- 9 core containers (was ~20)
- 3-5GB Docker data (was 8-12GB)  
- 72% reclaimable space on-demand
- Predictable resource usage

## 📄 License

Apache-2.0 - See [LICENSE](LICENSE) for details.

---
**Need help?** Join [#trinity-ops](https://democratizeai.slack.com/channels/trinity-ops) or check the [troubleshooting guide](docs/troubleshooting.md). 