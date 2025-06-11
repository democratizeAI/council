# Builder Hardening Wave - Production Operations Runbook
## Enterprise AutoGen Council v0.1-pre Operational Guide

**Version:** 1.0  
**Last Updated:** December 28, 2024  
**Next Review:** January 28, 2025  
**On-Call Escalation:** @builder-sre, @autogen-ops  

---

## 🎯 **Overview**

The Builder Hardening Wave represents the AutoGen Council's enterprise-grade safety infrastructure. This runbook provides complete operational procedures for production deployment, monitoring, incident response, and maintenance.

### **System Architecture**
```
[Production Traffic] → [HA LoadBalancer] → [Council Swarm]
                               ↓
[Gemini Audit] ← [Meta Hash Audit] → [Streaming Auditor]
       ↓                 ↓                    ↓
[O3 Audit Proxy] ← [PatchCtl v2] → [Auto-Rollback]
       ↓                 ↓                    ↓
[Prometheus] ← [Cost Guards] → [Accuracy Guards]
```

### **Critical SLAs**
- **Uptime Target**: 99.97% (26.3 minutes downtime/month)
- **Response Time**: p95 < 200ms, p99 < 500ms
- **Cost Protection**: $0.50/day hard limit with emergency stops
- **Recovery Time**: <90s automatic rollback on violations
- **Accuracy Baseline**: ≥95% maintained with regression detection

---

## 🚀 **Production Deployment**

### **Pre-Deployment Checklist**

```bash
# 1. Verify prerequisites
kubectl cluster-info
helm version
prometheus --version
grafana-cli --version

# 2. Check resource availability
kubectl get nodes
kubectl get pv
kubectl describe node | grep "Allocatable:"

# 3. Validate configuration
kubectl get secrets builder-hardening-secrets
kubectl get configmaps builder-hardening-config
```

### **Step 1: Deploy Core Services**

```bash
# Deploy Gemini Audit service
helm upgrade --install gemini-audit ./deploy/gemini \
  --namespace autogen-council \
  --set image.tag=v0.1-pre \
  --set resources.requests.memory=4Gi \
  --set resources.requests.cpu=2 \
  --set replicaCount=2 \
  --set prometheus.enabled=true

# Deploy PatchCtl v2
helm upgrade --install patchctl ./deploy/patchctl \
  --namespace autogen-council \
  --set image.tag=v0.1-pre \
  --set audit.enabled=true \
  --set rollback.timeout=90s \
  --set quota.daily_limit=3

# Deploy shadow namespace for canary testing
kubectl apply -f k8s/shadow-namespace.yaml

# Verify deployments
kubectl get pods -n autogen-council
kubectl get services -n autogen-council
```

### **Step 2: Configure Monitoring**

```bash
# Apply Prometheus targets
kubectl apply -f deploy/prometheus/targets_builder_hardening.yml

# Reload Prometheus configuration
curl -s http://prometheus:9090/-/reload

# Import Grafana dashboards
grafana-cli admin import-dashboard ./monitoring/dashboards/builder_hardening.json

# Verify metrics collection
curl -s http://prometheus:9090/api/v1/query?query=up{job="builder-hardening"}
```

### **Step 3: Enable Safety Systems**

```bash
# Set environment variables
export GEMINI_AUDIT_ENABLED=true
export PATCHCTL_ROLLBACK_TIMEOUT=90s
export COST_DAILY_LIMIT=0.50
export ACCURACY_BASELINE_THRESHOLD=0.95
export O3_AUDIT_MODE=enabled

# Update configuration
kubectl create configmap builder-hardening-config \
  --from-env-file=.env.production \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart services to pick up configuration
kubectl rollout restart deployment/gemini-audit -n autogen-council
kubectl rollout restart deployment/patchctl -n autogen-council
```

### **Step 4: Production Smoke Test**

```bash
# Run comprehensive smoke test
python tools/qa/inject_bad_canary.py --pr QA-302-demo

# Expected: gemini_rollback_triggered_total += 1
# Expected: PR auto-reverted within 90s
# Expected: System returns to healthy state

# Verify all metrics are green
python tools/monitoring/verify_deployment.py --check-all
```

---

## 📊 **Monitoring & Alerting**

### **Critical Metrics Dashboard**

| Metric | Threshold | Action |
|--------|-----------|--------|
| `quorum_ast_diff_percent` | >3% | Escalate to Gemini audit |
| `builder_meta_explained_total{result="pass"}` | <95% | Check accuracy baseline |
| `gemini_rollback_triggered_total` | Rate >1/hour | Investigate root cause |
| `cost_daily_burn_rate` | >$0.50 | Emergency cost stop |
| `accuracy_baseline_score` | <0.95 | Freeze deployments |
| `api_response_time_p95` | >200ms | Scale up or rollback |

### **Grafana Dashboard Panels**

```json
{
  "dashboard": "Builder Hardening - Production",
  "panels": [
    {
      "title": "System Health Overview",
      "queries": [
        "up{job='builder-hardening'}",
        "api_requests_total",
        "api_response_time_histogram"
      ]
    },
    {
      "title": "Safety Net Status",
      "queries": [
        "gemini_audit_pass_rate",
        "cost_guard_violations_total",
        "accuracy_guard_violations_total"
      ]
    },
    {
      "title": "Resource Utilization",
      "queries": [
        "container_memory_usage_bytes",
        "container_cpu_usage_seconds_total",
        "nvidia_gpu_utilization_percent"
      ]
    }
  ]
}
```

### **Alert Configuration**

```yaml
# prometheus/rules/builder_hardening.yml
groups:
  - name: builder_hardening_critical
    rules:
      - alert: CostBudgetExceeded
        expr: cost_daily_burn_rate > 0.50
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Daily cost budget exceeded"
          description: "Cost burn rate: ${{ $value }}/day"
          action: "EMERGENCY_STOP"
          
      - alert: AccuracyRegressionDetected
        expr: accuracy_baseline_score < 0.95
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Accuracy baseline violated"
          description: "Current accuracy: {{ $value }}"
          action: "FREEZE_DEPLOYMENTS"
          
      - alert: AutoRollbackTriggered
        expr: increase(gemini_rollback_triggered_total[5m]) > 0
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "Automatic rollback executed"
          description: "Check logs for rollback reason"
          action: "INVESTIGATE"
```

---

## 🛠️ **Incident Response**

### **Severity Levels**

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| **P0** | Production down, data loss | 5 minutes | All hands |
| **P1** | Core functionality broken | 15 minutes | On-call team |
| **P2** | Degraded performance | 1 hour | Business hours |
| **P3** | Minor issues, monitoring alerts | 4 hours | Next sprint |

### **Common Incident Scenarios**

#### **P0: Total System Failure**

```bash
# 1. Immediate assessment
kubectl get pods -n autogen-council
kubectl get events --sort-by='.lastTimestamp'
kubectl logs -l app=builder-hardening --tail=100

# 2. Emergency rollback
kubectl rollout undo deployment/gemini-audit -n autogen-council
kubectl rollout undo deployment/patchctl -n autogen-council
helm rollback gemini-audit
helm rollback patchctl

# 3. Verify rollback success
python tools/monitoring/health_check.py --emergency
```

#### **P1: Cost Budget Exceeded**

```bash
# 1. Immediate cost stop
curl -X POST http://autoscaler:8080/emergency_stop
export O3_AUDIT_MODE=degraded

# 2. Identify cost spike source
kubectl logs -l app=o3-audit-proxy --since=1h | grep "cost"
python tools/cost/analyze_spend.py --last-hour

# 3. Implement cost controls
kubectl scale deployment o3-audit-proxy --replicas=0
export COST_DAILY_LIMIT=0.25  # Reduce limit temporarily
```

#### **P1: Accuracy Regression**

```bash
# 1. Freeze deployments
export ACCURACY_GUARD_STRICT=true
kubectl annotate deployment/gemini-audit freeze=accuracy-regression

# 2. Run diagnostic tests
python tools/accuracy/baseline_check.py --verbose
python tools/accuracy/regression_analysis.py --since=24h

# 3. Revert to last known good
kubectl rollout undo deployment/gemini-audit
python tools/accuracy/verify_baseline.py --threshold=0.95
```

#### **P2: High Latency**

```bash
# 1. Check resource utilization
kubectl top pods -n autogen-council
kubectl describe node | grep -A5 "Allocated resources"

# 2. Scale up if needed
kubectl scale deployment/gemini-audit --replicas=4
helm upgrade patchctl ./deploy/patchctl --set replicaCount=3

# 3. Monitor improvement
watch 'curl -s http://prometheus:9090/api/v1/query?query=api_response_time_p95'
```

### **Escalation Procedures**

```bash
# Slack notifications
slack-cli send "#builder-hardening-alerts" \
  "🚨 P$SEVERITY incident detected: $DESCRIPTION"

# PagerDuty integration
curl -X POST https://events.pagerduty.com/v2/enqueue \
  -H "Content-Type: application/json" \
  -d '{
    "routing_key": "$PAGERDUTY_KEY",
    "event_action": "trigger",
    "dedup_key": "builder-hardening-$INCIDENT_ID",
    "payload": {
      "summary": "$INCIDENT_SUMMARY",
      "severity": "$SEVERITY",
      "source": "AutoGen Council"
    }
  }'
```

---

## 🔧 **Maintenance Procedures**

### **Daily Operations**

```bash
# 1. Health check (automated via cron)
#!/bin/bash
# daily_health_check.sh
python tools/monitoring/daily_health.py > /tmp/health_report.txt
if [ $? -ne 0 ]; then
  slack-cli send "#builder-ops" "❌ Daily health check failed"
  exit 1
fi

# 2. Cost analysis
python tools/cost/daily_report.py --email ops@autogen-council.dev

# 3. Performance review
python tools/performance/daily_metrics.py --dashboard-update
```

### **Weekly Maintenance**

```bash
# 1. Update accuracy baseline if needed
python tools/accuracy/update_baseline.py --if-improved

# 2. Clean up old logs and metrics
kubectl delete pods -l app=builder-hardening --field-selector=status.phase=Succeeded
prometheus-cli clean --retention=30d

# 3. Backup configuration
kubectl get configmaps -o yaml > backup/configmaps-$(date +%Y%m%d).yaml
kubectl get secrets -o yaml > backup/secrets-$(date +%Y%m%d).yaml
```

### **Monthly Reviews**

```bash
# 1. Capacity planning
python tools/capacity/monthly_analysis.py --forecast=3months

# 2. Security updates
helm repo update
helm upgrade gemini-audit ./deploy/gemini --reuse-values
helm upgrade patchctl ./deploy/patchctl --reuse-values

# 3. Performance optimization review
python tools/performance/monthly_optimization.py --recommendations
```

---

## 🔒 **Security Operations**

### **Access Control**

```bash
# 1. Verify RBAC permissions
kubectl auth can-i get pods --as=system:serviceaccount:autogen-council:builder
kubectl auth can-i create deployments --as=system:serviceaccount:autogen-council:ops

# 2. Audit access logs
kubectl logs -l app=api-gateway | grep "authentication"
python tools/security/access_audit.py --last-24h

# 3. Rotate secrets if needed
kubectl create secret generic builder-secrets-new --from-env-file=.env.prod
kubectl patch deployment gemini-audit -p '{"spec":{"template":{"spec":{"containers":[{"name":"gemini-audit","envFrom":[{"secretRef":{"name":"builder-secrets-new"}}]}]}}}}'
```

### **Vulnerability Management**

```bash
# 1. Scan container images
trivy image autogen/gemini-audit:v0.1-pre
trivy image autogen/patchctl:v0.1-pre

# 2. Check dependencies
python tools/security/dependency_check.py --sbom reports/sbom_v0.1_delta.json

# 3. Update base images if needed
docker build --pull -t autogen/gemini-audit:v0.1-pre-patched .
```

---

## 📞 **Contacts & Escalation**

### **On-Call Rotation**

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| **Builder SRE** | @alice.builder | @bob.ops | @charlie.lead |
| **Security** | @diana.sec | @eve.audit | @frank.ciso |
| **Product** | @grace.pm | @henry.eng | @irene.vp |

### **Communication Channels**

- **#builder-hardening-alerts**: Automated alerts and notifications
- **#builder-ops**: Daily operations and maintenance
- **#builder-incidents**: Active incident coordination
- **#builder-escalation**: P0/P1 incident escalation

### **Emergency Contacts**

```bash
# Slack emergency notification
slack-cli send "#builder-escalation" "@channel 🚨 EMERGENCY: $DESCRIPTION"

# Email emergency list
echo "$INCIDENT_DETAILS" | mail -s "🚨 AutoGen Council Emergency" \
  emergency@autogen-council.dev

# SMS via Twilio
curl -X POST https://api.twilio.com/2010-04-01/Accounts/$TWILIO_SID/Messages.json \
  --data-urlencode "From=$TWILIO_FROM" \
  --data-urlencode "To=$EMERGENCY_PHONE" \
  --data-urlencode "Body=AutoGen Council Emergency: $DESCRIPTION"
```

---

## 🧪 **Testing & Validation**

### **Production Testing Schedule**

| Test Type | Frequency | Duration | Impact |
|-----------|-----------|----------|---------|
| **Rollback Drill** | Daily | 2 minutes | None (shadow) |
| **Cost Cap Test** | Weekly | 5 minutes | None (canary) |
| **Accuracy Validation** | Daily | 10 minutes | None (baseline) |
| **HA Failover** | Monthly | 30 minutes | Brief degradation |

### **Rollback Drill Procedure**

```bash
# 1. Execute rollback drill
python tools/qa/inject_bad_canary.py --pr QA-302-demo --shadow

# 2. Verify automatic rollback
timeout 120 bash -c 'until curl -f http://health-check/status; do sleep 5; done'

# 3. Confirm metrics
python tools/monitoring/verify_rollback.py --drill-id $(date +%s)

# 4. Generate report
python tools/reporting/rollback_drill.py --success
```

### **Chaos Engineering**

```bash
# 1. Network partition simulation
kubectl apply -f tools/chaos/network-partition.yaml

# 2. Resource exhaustion test
kubectl apply -f tools/chaos/memory-pressure.yaml

# 3. Pod failure simulation
kubectl delete pod -l app=gemini-audit --force

# 4. Recovery verification
python tools/chaos/verify_recovery.py --all-tests
```

---

## 📈 **Performance Optimization**

### **Scaling Guidelines**

```bash
# CPU-based scaling
kubectl autoscale deployment gemini-audit \
  --cpu-percent=70 \
  --min=2 \
  --max=10

# Custom metrics scaling (accuracy-based)
kubectl apply -f - <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: accuracy-scaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gemini-audit
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Pods
    pods:
      metric:
        name: accuracy_baseline_score
      target:
        type: AverageValue
        averageValue: "0.95"
EOF
```

### **Resource Optimization**

```bash
# 1. Review resource usage
kubectl top pods -n autogen-council --sort-by=memory
kubectl top nodes

# 2. Optimize resource requests/limits
helm upgrade gemini-audit ./deploy/gemini \
  --set resources.requests.cpu=1.5 \
  --set resources.limits.cpu=3 \
  --set resources.requests.memory=3Gi \
  --set resources.limits.memory=6Gi

# 3. Enable vertical pod autoscaling
kubectl apply -f tools/vpa/gemini-audit-vpa.yaml
```

---

## 📋 **Troubleshooting Guide**

### **Common Issues**

#### **"Hash comparison failed" errors**

```bash
# 1. Check meta hash generation
python tools/qa/debug_meta_hash.py --pr-id $PR_ID

# 2. Verify PatchCtl connectivity
curl -f http://patchctl:8080/health
curl -f http://patchctl:8080/api/audit/latest

# 3. Restart meta hash auditor
kubectl rollout restart deployment/meta-hash-audit
```

#### **"Cost limit exceeded" alerts**

```bash
# 1. Check current spend
python tools/cost/current_burn.py --detailed

# 2. Identify expensive operations
kubectl logs -l app=o3-audit-proxy | grep "cost" | tail -20

# 3. Enable degraded mode temporarily
export O3_AUDIT_MODE=degraded
kubectl set env deployment/o3-audit-proxy O3_AUDIT_MODE=degraded
```

#### **"Accuracy baseline violated" warnings**

```bash
# 1. Run accuracy diagnostic
python tools/accuracy/full_diagnostic.py --verbose

# 2. Check for model drift
python tools/accuracy/drift_analysis.py --baseline-date 7d

# 3. Retrain baseline if needed
python tools/accuracy/retrain_baseline.py --if-drift-confirmed
```

### **Log Analysis**

```bash
# 1. Centralized log aggregation
kubectl logs -l app=builder-hardening --all-containers=true | \
  grep -E "(ERROR|WARN|CRITICAL)" | \
  sort -k1,1 | \
  tail -50

# 2. Performance analysis
kubectl logs -l app=gemini-audit | \
  grep "response_time" | \
  awk '{print $3}' | \
  sort -n | \
  python tools/stats/percentiles.py

# 3. Error pattern detection
kubectl logs -l app=builder-hardening --since=1h | \
  python tools/logs/error_patterns.py --top=10
```

---

## 📚 **Documentation & References**

### **Related Documentation**
- **Architecture Guide**: `docs/architecture/builder_hardening.md`
- **API Reference**: `docs/api/builder_hardening_v1.md`
- **Security Guide**: `docs/security/builder_hardening_security.md`
- **Cost Analysis**: `docs/cost/optimization_guide.md`

### **External Resources**
- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Dashboards**: https://grafana.com/docs/
- **Kubernetes Operations**: https://kubernetes.io/docs/
- **Helm Charts**: https://helm.sh/docs/

### **Emergency Procedures Summary**

```bash
# EMERGENCY ROLLBACK (30 seconds)
kubectl rollout undo deployment/gemini-audit -n autogen-council
kubectl rollout undo deployment/patchctl -n autogen-council

# EMERGENCY COST STOP (10 seconds)
curl -X POST http://autoscaler:8080/emergency_stop
export O3_AUDIT_MODE=degraded

# EMERGENCY SCALE DOWN (15 seconds)
kubectl scale deployment --all --replicas=1 -n autogen-council

# HEALTH CHECK (5 seconds)
python tools/monitoring/emergency_health.py
```

---

## ✅ **Go-Live Validation Checklist**

Before marking production deployment as complete:

- [ ] All services deployed and healthy
- [ ] Prometheus metrics collecting successfully
- [ ] Grafana dashboards displaying data
- [ ] Cost guards operational ($0.50/day limit active)
- [ ] Accuracy guards operational (95% baseline enforced)
- [ ] Rollback drill successful (<90s recovery)
- [ ] All alerts configured and tested
- [ ] On-call rotation established
- [ ] Emergency procedures validated
- [ ] Documentation updated and accessible

**Production Deployment Certified By**: ________________  
**Date**: ________________  
**Next Review**: ________________  

---

**🎉 Builder Hardening Wave Production Deployment Complete! 🎉**

*The AutoGen Council is now running with enterprise-grade safety nets and bulletproof operational procedures.* 