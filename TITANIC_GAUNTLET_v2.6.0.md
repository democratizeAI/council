# 🏆 Titanic Gauntlet v2.6.0 - Docker Edition

## 🎯 Complete Evaluation Suite for Hardened Council Stack

Your v2.6.0 Council setup with **10GB memory limits**, **security hardening**, and **port 9000** is perfectly configured for comprehensive testing.

## 🚀 Quick Start

### 0. Environment Prep
```bash
# Your Docker setup already includes these optimizations:
# ✅ 10GB memory limit (prevents NVIDIA driver OOM)
# ✅ Security hardening (no-new-privileges)
# ✅ Health checks with 60s startup period
# ✅ Council API on port 9000

# Set your API keys
export MISTRAL_API_KEY=sk-••• 
export OPENAI_API_KEY=sk-•••
export COUNCIL_DAILY_BUDGET=10
```

### 1. Fast Smoke Test (≈3 min)
```bash
# Start Council and run micro suite
make -f Makefile.titanic start-council
make -f Makefile.titanic health
make -f Makefile.titanic micro

# Expected Pass Gates:
# ✅ Success Rate: ≥95%
# ✅ P95 Latency: ≤200ms  
# ✅ Total Cost: ≤$0.15
```

### 2. Full Titanic Gauntlet (≈25 min)
```bash
# Complete 380-prompt evaluation
make -f Makefile.titanic titanic BUDGET=10

# Expected Pass Gates:
# ✅ Success Rate: ≥92%
# ✅ P95 Latency: ≤200ms
# ✅ Total Cost: ≤$7.00
```

### 3. View Results
```bash
# Latest report summary
make -f Makefile.titanic latest-report

# Prometheus metrics check
curl http://localhost:9090/api/v1/query?query=swarm_titanic_requests_total
```

## 📊 Test Suites Available

| Suite | Prompts | Duration | Budget | Purpose |
|-------|---------|----------|--------|---------|
| **micro** | 50 | ~3 min | $0.15 | Smoke test, quick validation |
| **full** | 380 | ~25 min | $7.00 | Complete evaluation, release gate |

## 🛡️ Your Hardening Benefits

### **Memory Protection (10GB Limit)**
- **Prevents:** NVIDIA driver crashes from OOM
- **Result:** Container OOM → Graceful restart vs system freeze

### **Security Hardening**
- **no-new-privileges**: Prevents privilege escalation
- **tmpfs /tmp**: Secure temporary storage
- **read_only: false**: Allows necessary writes to logs

### **Enhanced Health Checks**
- **60s startup period**: Allows proper GPU initialization
- **5s timeout**: Quick failure detection
- **3 retries**: Reliable health assessment

## 📈 Monitoring Integration

Your setup automatically exposes metrics to Prometheus on port 9090:

### **Key Metrics to Watch:**
```bash
# Request volume
swarm_titanic_requests_total

# Cost tracking  
swarm_council_cost_dollars_total

# Performance
swarm_p95_latency_ms
swarm_gpu_memory_used_percent

# Success rates
swarm_council_success_rate
```

### **Grafana Dashboard (port 3000)**
- Real-time latency graphs
- Cost burn rate
- Success rate trends
- GPU utilization

## 🚦 Pass Gate Criteria

### **Micro Suite (Smoke Test)**
```bash
Metric              Threshold    Purpose
success-rate        ≥ 95%        Basic functionality
p95-latency         ≤ 200ms      Performance target
total-cost          ≤ $0.15      Budget efficiency
```

### **Full Titanic (Release Gate)**
```bash
Metric              Threshold    Purpose  
local-success       ≥ 92%        Core capability
effective-success   ≥ 97%        With cloud fallback
composite-accuracy  ≥ 85%        Quality benchmark
p95-latency         ≤ 200ms      Performance SLA
total-cost          ≤ $7.00      Budget compliance
```

## 🔧 Advanced Usage

### **Custom Budget Runs**
```bash
# Test with different budgets
make -f Makefile.titanic titanic BUDGET=5   # Conservative
make -f Makefile.titanic titanic BUDGET=15  # Aggressive
```

### **Direct Python Execution**
```bash
# Micro suite with custom settings
python scripts/run_titanic_gauntlet_docker.py \
    --suite micro \
    --budget 2 \
    --council-url http://localhost:9000

# Full gauntlet with detailed output
python scripts/run_titanic_gauntlet_docker.py \
    --suite full \
    --budget 10 \
    --report reports/custom_run.json
```

### **Prometheus Metrics Validation**
```bash
# Check if Titanic metrics are being scraped
curl -s http://localhost:9090/api/v1/query?query=swarm_titanic_requests_total

# Monitor real-time latency during test
watch "curl -s 'http://localhost:9090/api/v1/query?query=swarm_p95_latency_ms' | jq '.data.result[0].value[1]'"
```

## 🚨 Troubleshooting

### **Common Issues & Fixes**

| Problem | Symptom | Fix |
|---------|---------|-----|
| **Council Unresponsive** | Health check fails | `docker-compose restart council-api` |
| **High Latency** | P95 > 300ms | Check GPU power mode, restart container |
| **Budget Exceeded** | Early termination | Reset budget tracking or increase limit |
| **Memory Issues** | Container OOM (137) | Good! Hardening working. Container will restart |

### **Debug Commands**
```bash
# Check container health
docker ps
docker logs council-api --tail 20

# Monitor resource usage
docker stats council-api

# Test manual request
curl -X POST http://localhost:9000/hybrid \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is 2+2?"}'
```

## 📋 Complete Workflow Example

```bash
# 1. Start everything
make -f Makefile.titanic start-council

# 2. Verify health  
make -f Makefile.titanic health

# 3. Quick smoke test
make -f Makefile.titanic micro

# 4. If micro passes, run full gauntlet
make -f Makefile.titanic titanic

# 5. Review results
make -f Makefile.titanic latest-report

# 6. Check Prometheus metrics
curl http://localhost:9090/api/v1/query?query=swarm_titanic_requests_total

# 7. Archive results
git add reports/titanic_*.json
git commit -m "bench: titanic v2.6.0 with 10GB hardening"
```

## 🎯 Expected Performance

### **Your RTX 4070 Setup Should Achieve:**
- **Micro Suite**: 95%+ success, ~150ms P95 latency
- **Full Titanic**: 92%+ success, ~180ms P95 latency  
- **GPU Memory**: <8GB usage (well under 10GB limit)
- **Total Cost**: $4-6 for full run

### **If Performance Degrades:**
1. Check `docker stats` for memory/CPU usage
2. Verify GPU not in power-save mode
3. Restart containers to clear any memory fragmentation
4. Monitor Prometheus for resource trends

## ✅ Success Confirmation

When everything works perfectly, you'll see:

```bash
🏆 TITANIC GAUNTLET RESULTS
==================================================
Suite: full_titanic
Total Requests: 380
Success Rate: 94.2%
P95 Latency: 178ms  
Total Cost: $5.43
Total Time: 1456s

🚦 PASS GATES
==============================
success_rate: 94.20 (≥ 92%) - ✅ PASS
p95_latency_ms: 178.00 (≤ 200ms) - ✅ PASS  
total_cost: 5.43 (≤ $7.00) - ✅ PASS

🎯 Overall: ✅ ALL GATES PASSED
```

**Your hardened Council v2.6.0 setup is ready for production evaluation!** 🚀 