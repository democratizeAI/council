# 🎯 Trinity Cursor Agents Charter
## Coordinated Multi-Agent Development Framework

**Version**: v1.0  
**Status**: Active  
**Purpose**: Define roles, boundaries, and synchronization for Trinity's three Cursor agents

---

## 🌐 **Top-Level Contract**

### **Root Coordination**
- **Root folder**: `/cursorsync/` (mounted read-write for all agents)
- **Heartbeat cadence**: Every 90s each agent rewrites its own `status-<agent>.json`
- **Brief cadence**: On any meaningful state change, append markdown block to `brief-<agent>.md`
- **Alignment test**: If all three `status-*.json` share same `ledger_hash` and no `"blocked": true`, Guardian flips `cursor_sync_aligned = 1`

---

## 🛡️ **Agent A – Infra Sentinel**

| Field | Value |
|-------|-------|
| **Handle** | `cursor-infra-sentinel` |
| **Scope** | Cluster health, service mesh, GPU scaler, Vault templating |
| **NATS subjects** | `infra.*`, `alert.infra.*` |
| **Owns** | `docs/infrastructure/`, Nomad/K8s manifests, Prometheus rules |
| **Forbidden** | Writing to `ledger.*` subjects, changing model weights |

### **Agent A Artifacts**
```yaml
/cursorsync/status-A.json:
  { ts, latency_ms, gpu_util[], ledger_hash, blocked }

/cursorsync/brief-A.md:
  Human-readable summary of last infra change
```

**Success Flag**: `gpu_util.avg < 70%` and last 10 Prometheus alerts green

---

## 🤖 **Agent B – ML Fabricator**

| Field | Value |
|-------|-------|
| **Handle** | `cursor-ml-fabricator` |
| **Scope** | Φ-3 grid, LoRA trainer, drift analyser, model registry |
| **NATS subjects** | `ml.*`, `drift.*`, `plan.lora.*` |
| **Owns** | `/models/`, training configs, evaluation dashboards |
| **Forbidden** | Pushing to Git, editing ledger rows directly |

### **Agent B Artifacts**
```yaml
/cursorsync/status-B.json:
  { ts, active_models, drift_score, ledger_hash, blocked }

/cursorsync/brief-B.md:
  What was (re)trained, metrics delta, cost
```

**Success Flag**: `drift_score ≤ 0.05` and latest canary weight shadow passes SLO

---

## 📋 **Agent C – Ledger Scribe**

| Field | Value |
|-------|-------|
| **Handle** | `cursor-ledger-scribe` |
| **Scope** | Tamper-evident ledger, cost charts, SOC-2 artifacts |
| **NATS subjects** | `ledger.delta.*`, `cost.*`, `planner.o3.*` |
| **Owns** | `docs/ledger/latest.md`, cost exporter, Guardian hash-watch |
| **Forbidden** | Restarting containers, modifying model files |

### **Agent C Artifacts**
```yaml
/cursorsync/status-C.json:
  { ts, ledger_hash, cost_today_usd, blocked }

/cursorsync/brief-C.md:
  Ledger rows added/closed, budget posture
```

**Success Flag**: Ledger chain intact and daily spend ≤ budget cap

---

## 🤝 **Convergence Mechanism**

### **Ledger Hash as Single Source of Truth**
- Every heartbeat includes `ledger_hash` (SHA-256 of `docs/ledger/latest.md`)
- If hashes diverge for > 3min, Agent C emits `ledger.delta.out_of_sync`
- Agents A/B pause non-critical work until sync restored

### **Guardian Watcher**
```yaml
guardian-sync-probe:
  monitors: /cursorsync/status-*.json
  condition: all three "blocked": false AND hashes equal
  action: writes alignment-ok.flag
  result: Conductor resumes queued workflows
```

### **Human Override**
- Maintainer can drop `/cursorsync/override-unblock.flag`
- Guardian clears `"blocked"` on next check
- Emergency escape hatch for manual intervention

---

## 📁 **Directory Layout**

```bash
/cursorsync/
├── status-A.json          # Infra Sentinel status
├── status-B.json          # ML Fabricator status  
├── status-C.json          # Ledger Scribe status
├── brief-A.md             # Infra change summary
├── brief-B.md             # ML training summary
├── brief-C.md             # Ledger/cost summary
├── alignment-ok.flag      # Auto-created by Guardian
└── override-unblock.flag  # Manual override (optional)
```

---

## 🚀 **Bootstrapping Steps**

### **Container Initialization** (once per agent)
```bash
# On container start
mkdir -p /cursorsync
touch /cursorsync/brief-<agent>.md
echo '{"blocked":true,"ledger_hash":""}' > /cursorsync/status-<agent>.json

# Begin normal heartbeat loop
# Guardian will clear initial "blocked" after first good cycle
```

### **Agent Startup Commands**
```bash
# Agent A (Infra Sentinel)
export CURSOR_AGENT_HANDLE="cursor-infra-sentinel"
export CURSOR_AGENT_SCOPE="infra,gpu,vault"

# Agent B (ML Fabricator)  
export CURSOR_AGENT_HANDLE="cursor-ml-fabricator"
export CURSOR_AGENT_SCOPE="ml,lora,drift"

# Agent C (Ledger Scribe)
export CURSOR_AGENT_HANDLE="cursor-ledger-scribe"
export CURSOR_AGENT_SCOPE="ledger,cost,compliance"
```

---

## 📊 **Success Metrics & KPIs**

### **Individual Agent Health**
```yaml
Agent A Success:
  - gpu_util.avg < 70%
  - prometheus_alerts_green >= 10
  - infra_latency_p95 < 150ms

Agent B Success:  
  - drift_score <= 0.05
  - model_shadow_passes_slo = true
  - ml_cost_within_budget = true

Agent C Success:
  - ledger_chain_intact = true
  - daily_spend <= budget_cap
  - hmac_verification_passes = true
```

### **Convergence Health**
```yaml
System Aligned:
  - cursor_sync_aligned = 1
  - ledger_hash_consensus = true
  - all_agents_unblocked = true
  - alignment_ok_flag_exists = true
```

---

## 🛡️ **Security & Isolation**

### **Agent Boundaries**
- **No cross-contamination**: Agent A cannot edit ledger, Agent B cannot restart services
- **NATS subject isolation**: Each agent has distinct pub/sub patterns
- **File system isolation**: Clear ownership of directories and artifacts

### **Emergency Protocols**
- **Automatic blocking**: Any agent can set `"blocked": true` to halt system
- **Guardian oversight**: Independent watcher prevents infinite loops
- **Human override**: Manual unblock capability for emergency situations

---

## 📋 **Implementation Checklist**

### **Setup Phase**
- [ ] Create `/cursorsync/` directory with proper permissions
- [ ] Configure Guardian sync-probe monitoring
- [ ] Set up NATS subject routing for each agent
- [ ] Deploy agent containers with correct handles

### **Testing Phase**
- [ ] Verify heartbeat synchronization (90s intervals)
- [ ] Test convergence mechanism with hash mismatches
- [ ] Validate agent isolation (forbidden actions blocked)
- [ ] Confirm Guardian alignment detection

### **Production Phase**  
- [ ] Monitor cursor_sync_aligned metric
- [ ] Track individual agent success flags
- [ ] Implement alerting on synchronization failures
- [ ] Document operational procedures

---

**🎯 Result**: Three coordinated Cursor agents that self-synchronize while maintaining strict role boundaries, enabling Trinity's path to v∞ enterprise certification.** 