# 🧪 Alert Tuning & Testing Guide

## 🎯 Overview

Your alert pipeline is now production-tuned with:
- **Multi-level escalation** (warning → critical → page)
- **Realistic thresholds** based on SLA requirements
- **Burn-in periods** to prevent flapping
- **Inhibit rules** to reduce noise
- **Test framework** to validate escalation paths

---

## 🚀 Quick Setup

### 1. **Install Dependencies**
```bash
pip install aiohttp prometheus-client
```

### 2. **Update Configuration Files**
Replace placeholders in `monitoring/alertmanager.yml`:
- `REPLACE_WITH_SLACK_WEBHOOK_URL` → Your Slack webhook
- `REPLACE_WITH_PAGERDUTY_INTEGRATION_KEY` → Your PagerDuty key
- `REPLACE_WITH_SECURITY_SLACK_WEBHOOK_URL` → Security team Slack

### 3. **Load Alert Rules**
```bash
# If using Docker Compose
docker-compose restart prometheus alertmanager

# Or manually reload
curl -X POST http://localhost:9090/-/reload
curl -X POST http://localhost:9093/-/reload
```

---

## 🧪 Testing Your Alert Pipeline

### **Step 1: Basic Connectivity Test**
```bash
make -f Makefile.day2 test-alerts-connectivity
```
**Expected Output:**
```
✅ Prometheus API accessible
✅ AlertManager API accessible
✅ Found rule group: test_alerts
✅ Found rule group: day2_operations
```

### **Step 2: Validate Alert Configuration**
```bash
make -f Makefile.day2 validate-alert-config
```
**This checks:**
- Alert rule syntax
- Threshold recommendations
- Burn-in timing analysis

### **Step 3: Test Escalation Paths**
```bash
make -f Makefile.day2 test-alerts
```
**This will:**
- Trigger test warning alert
- Trigger test critical alert
- Verify alerts reach AlertManager
- Test routing to correct receivers

### **Step 4: Manual Alert Testing**
```bash
# Test warning escalation
make -f Makefile.day2 trigger-test-warning

# Test critical escalation  
make -f Makefile.day2 trigger-test-critical

# Check if alerts are firing
make -f Makefile.day2 show-alerts
```

### **Step 5: Cleanup Test Alerts**
```bash
make -f Makefile.day2 silence-test-alerts
```

---

## 🎛️ Production-Tuned Thresholds

### **VRAM Monitoring** (Multi-level)
| Alert | Threshold | Burn-in | Purpose |
|-------|-----------|---------|---------|
| VRAMWarning | 75% | 3m | Early warning, plan capacity |
| VRAMCritical | 85% | 2m | Immediate attention needed |
| VRAMEmergency | 95% | 30s | OOM imminent, page ops |

### **Latency Monitoring** (SLA-based)
| Alert | Threshold | Burn-in | Purpose |
|-------|-----------|---------|---------|
| LatencyWarning | 200ms P95 | 5m | Performance degrading |
| LatencyCritical | 500ms P95 | 3m | SLA breach |
| LatencyEmergency | 2s P95 | 1m | System unresponsive |

### **Budget Monitoring** (Cost control)
| Alert | Threshold | Burn-in | Purpose |
|-------|-----------|---------|---------|
| BudgetWarning | $7.50/day | 10m | 75% budget consumed |
| BudgetCritical | $10/day | 5m | Budget limit hit |
| BudgetRunaway | $15/day | 2m | Cost bomb detection |

---

## 📞 Escalation Paths

### **Severity Levels**
```
test → silent logging only
warning → #swarm-ops Slack
critical → #swarm-ops Slack + Email
page → PagerDuty + #swarm-incidents
security → Security team immediate
```

### **Routing Logic**
1. **Test alerts** → Silent webhook (no noise)
2. **Warning alerts** → Slack every 8h
3. **Critical alerts** → Slack + Email every 1h
4. **Page alerts** → PagerDuty + Slack every 30m
5. **Security alerts** → Security team immediately

### **Inhibit Rules** (Reduces noise)
- Emergency alerts suppress lower-level alerts
- Service down suppresses component alerts
- Higher budget alerts suppress lower ones

---

## 🔧 Tuning Recommendations

### **If Getting Too Many Alerts:**
```bash
# Increase thresholds
# Edit monitoring/alerts.yml:
# VRAMWarning: 75% → 80%
# LatencyWarning: 200ms → 250ms

# Increase burn-in times
# VRAMWarning: for: 3m → for: 5m
```

### **If Missing Important Alerts:**
```bash
# Decrease thresholds
# VRAMCritical: 85% → 80%
# LatencyCritical: 500ms → 400ms

# Decrease burn-in times
# VRAMCritical: for: 2m → for: 1m
```

### **If Getting Noise During Load Spikes:**
```bash
# Increase burn-in for affected alerts
# LatencyWarning: for: 5m → for: 10m
# VRAMWarning: for: 3m → for: 5m
```

---

## 🚨 Emergency Procedures

### **Silence All Alerts** (Emergency maintenance)
```bash
make -f Makefile.day2 silence-maintenance
```

### **Show Current Alert Status**
```bash
make -f Makefile.day2 show-alerts
make -f Makefile.day2 show-silences
```

### **Emergency Circuit Breaker**
```bash
make -f Makefile.day2 circuit-breaker
```

---

## 📊 Monitoring Your Monitoring

### **Daily Health Check**
```bash
# Add to your daily ops routine
make -f Makefile.day2 test-alerts-connectivity
make -f Makefile.day2 show-alerts
```

### **Weekly Alert Review**
```bash
# Review alert frequency and tune thresholds
make -f Makefile.day2 tune-alert-thresholds
```

### **Monthly Escalation Test**
```bash
# Test full escalation paths end-to-end
make -f Makefile.day2 test-alerts
```

---

## 🎯 Success Metrics

### **Alert Quality KPIs**
- **Alert-to-incident ratio**: <3:1 (< 3 alerts per real incident)
- **Time-to-acknowledge**: <5 minutes for critical
- **False positive rate**: <10%
- **Alert fatigue**: No more than 5 alerts/day in steady state

### **Response Time SLAs**
- **Warning alerts**: Acknowledge within 30m
- **Critical alerts**: Acknowledge within 10m  
- **Page alerts**: Acknowledge within 5m
- **Security alerts**: Acknowledge within 2m

---

## 🔍 Troubleshooting

### **Alerts Not Firing**
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check alert rules loaded
curl http://localhost:9090/api/v1/rules

# Check metric availability
curl "http://localhost:9090/api/v1/query?query=up"
```

### **Alerts Not Routing**
```bash
# Check AlertManager config
curl http://localhost:9093/api/v1/status

# Check routing tree
curl http://localhost:9093/api/v1/routes

# Check receivers
curl http://localhost:9093/api/v1/receivers
```

### **Slack/PagerDuty Not Working**
1. Verify webhook URLs in `alertmanager.yml`
2. Test webhooks manually with curl
3. Check AlertManager logs: `docker logs alertmanager`

---

## 🎉 You're Ready!

Your alert pipeline is now production-ready with:

✅ **Tuned thresholds** that balance sensitivity vs. noise  
✅ **Multi-level escalation** that routes alerts appropriately  
✅ **Test framework** to validate end-to-end paths  
✅ **Inhibit rules** that prevent alert storms  
✅ **Emergency procedures** for incident management  

**Next Steps:**
1. Run initial tests: `make -f Makefile.day2 test-alerts`
2. Configure your Slack/PagerDuty credentials
3. Schedule weekly alert reviews
4. Celebrate having production-grade monitoring! 🎉

Remember: **Good alerts save sleep, bad alerts steal it.** Your tuned alerts should page you only when action is needed and give you the context to act quickly. 🌙💤 