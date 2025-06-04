# 🧪 Live Alert Test Guide

## 🎯 Goal
Verify your alert pipeline works end-to-end by triggering real VRAM spikes and watching alerts fire in the correct escalation sequence.

---

## 🚀 Quick Start

### **Option A: Full Escalation Test (7 minutes)**
Tests all three levels: Warning → Critical → Emergency

```bash
make -f Makefile.day2 test-alerts-e2e
```

### **Option B: Single Threshold Test (3 minutes)**
Test one specific alert threshold

```bash
# Test warning alert (75% threshold)
make -f Makefile.day2 test-alerts-single VRAM=78

# Test critical alert (85% threshold) 
make -f Makefile.day2 test-alerts-single VRAM=88

# Test emergency alert (95% threshold)
make -f Makefile.day2 test-alerts-single VRAM=97
```

---

## 📋 Pre-Test Checklist

### **1. Verify Monitoring Stack is Running**
```bash
# Check services are up
make -f Makefile.day2 health

# Verify Prometheus is accessible
curl http://localhost:9090/api/v1/status/config

# Verify AlertManager is accessible  
curl http://localhost:9093/api/v1/status
```

### **2. Configure Notification Channels**
Edit `monitoring/alertmanager.yml` and replace:
- `REPLACE_WITH_SLACK_WEBHOOK_URL` → Your Slack webhook
- `REPLACE_WITH_PAGERDUTY_INTEGRATION_KEY` → Your PagerDuty key

### **3. Load Alert Rules**
```bash
# Reload configurations
curl -X POST http://localhost:9090/-/reload
curl -X POST http://localhost:9093/-/reload

# Verify rules are loaded
make -f Makefile.day2 validate-alert-config
```

---

## 🧪 Test Execution

### **Step 1: Start the Test**
```bash
make -f Makefile.day2 test-alerts-e2e
```

### **Step 2: Expected Timeline**
```
00:00 - Test starts, monitoring begins
00:05 - VRAM spike to 78% (Warning threshold)
03:00 - Alert "VRAMWarning" should fire
03:05 - VRAM spike to 88% (Critical threshold)  
05:00 - Alert "VRAMCritical" should fire
05:05 - VRAM spike to 97% (Emergency threshold)
05:30 - Alert "VRAMEmergency" should fire
07:30 - Test completes, cleanup begins
```

### **Step 3: Watch for Notifications**

**Slack #swarm-ops:**
```
⚠️ Warning: VRAMWarning
GPU memory usage is 78.0% (>75%). Monitor for potential allocation issues.

🚨 Critical: VRAMCritical  
GPU memory usage is 88.0% (>85%). Immediate attention required to prevent OOM failures.
```

**Slack #swarm-incidents:**
```
🚨 URGENT: VRAMEmergency
GPU memory usage is 97.0% (>95%). OOM failure imminent. Immediate intervention required.
```

**Email (swarm-ops@company.com):**
```
Subject: 🚨 SwarmAI Critical Alert: VRAMCritical
Critical alert fired in SwarmAI production environment...
```

**PagerDuty:**
```
New Incident: 🚨 VRAMEmergency - URGENT
Environment: production
Component: gpu-memory
```

---

## 📊 Verification Points

### **During Test - Check Grafana**
1. Open http://localhost:3000
2. Navigate to "SwarmAI Day-2 Operations Dashboard"
3. Watch the "VRAM Usage %" panel spike to target levels
4. Verify colors change: Green → Yellow → Red

### **During Test - Check Prometheus**
```bash
# Check current alerts
make -f Makefile.day2 show-alerts

# Expected output:
# VRAMWarning (warning) - VRAM usage elevated
# VRAMCritical (critical) - VRAM usage critically high  
# VRAMEmergency (page) - VRAM EMERGENCY - OOM imminent
```

### **During Test - Check AlertManager**
```bash
# Check active alerts
curl -s http://localhost:9093/api/v1/alerts | jq '.data[].labels.alertname'

# Check silences (should be empty)
make -f Makefile.day2 show-silences
```

---

## ✅ Success Criteria

### **Alert Firing**
- ✅ VRAMWarning fires when usage > 75%
- ✅ VRAMCritical fires when usage > 85%  
- ✅ VRAMEmergency fires when usage > 95%
- ✅ Correct escalation sequence (Warning → Critical → Emergency)

### **Notification Delivery**  
- ✅ Slack #swarm-ops receives warning + critical alerts
- ✅ Slack #swarm-incidents receives emergency alerts
- ✅ Email sent for critical alerts
- ✅ PagerDuty incident created for emergency

### **Alert Content**
- ✅ Alerts include runbook URLs
- ✅ Descriptions explain the issue clearly
- ✅ Severity levels match expectation
- ✅ Environment and component labels correct

---

## 🔧 Troubleshooting

### **No Alerts Firing**
```bash
# Check Prometheus is scraping metrics
curl "http://localhost:9090/api/v1/query?query=up"

# Check alert rules are loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].name'

# Verify GPU detection
python scripts/chaos_gpu.py --vram 50 --duration 10
```

### **Alerts Firing but No Notifications**
```bash
# Check AlertManager routing
curl http://localhost:9093/api/v1/routes

# Check receiver configuration
curl http://localhost:9093/api/v1/receivers

# Verify webhook URLs in alertmanager.yml
grep -n "REPLACE_WITH" monitoring/alertmanager.yml
```

### **Wrong Alert Thresholds**
```bash
# Check current thresholds
grep -A5 "VRAMWarning\|VRAMCritical\|VRAMEmergency" monitoring/alerts.yml

# Tune if needed
make -f Makefile.day2 tune-alert-thresholds
```

---

## 🧹 Cleanup

### **Stop Any Running Tests**
```bash
# Stop chaos tests
make -f Makefile.day2 clear-chaos

# Silence test alerts
make -f Makefile.day2 silence-test-alerts
```

### **Check System Recovery**
```bash
# Verify alerts have resolved
make -f Makefile.day2 show-alerts

# Check Grafana dashboard is green
# Check VRAM usage is back to normal levels
```

---

## 📋 Test Report Template

After running the test, document results:

```
🧪 Alert Pipeline Test Results - [DATE]
===============================================

✅ Test Execution:
- Full escalation test completed: [YES/NO]
- Duration: [X] minutes
- Chaos scenarios: VRAM 78% → 88% → 97%

✅ Alert Firing:
- VRAMWarning (75%): [FIRED/NOT FIRED] at [TIME]
- VRAMCritical (85%): [FIRED/NOT FIRED] at [TIME]  
- VRAMEmergency (95%): [FIRED/NOT FIRED] at [TIME]
- Escalation sequence: [CORRECT/INCORRECT]

✅ Notification Delivery:
- Slack #swarm-ops: [RECEIVED/NOT RECEIVED]
- Slack #swarm-incidents: [RECEIVED/NOT RECEIVED]
- Email notifications: [RECEIVED/NOT RECEIVED]
- PagerDuty incidents: [CREATED/NOT CREATED]

🔧 Issues Found:
- [List any issues or misconfigurations]

🎯 Next Actions:
- [Any threshold adjustments needed]
- [Notification channel fixes required]
- [Additional testing needed]
```

---

## 🎉 Success!

If all tests pass, you now have **battle-tested alerts** that:

✅ **Fire at the right thresholds** with proper burn-in times  
✅ **Escalate correctly** from warning → critical → emergency  
✅ **Deliver notifications** to the right channels  
✅ **Provide actionable context** with runbook links  
✅ **Reduce noise** with inhibit rules  

Your production monitoring is now **proven to work** when it matters most! 🚀

Remember: Test your alerts quarterly to ensure they stay reliable as your system evolves. 📅 