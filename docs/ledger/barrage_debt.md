# Barrage Technical Debt — Trinity Council Analysis
*Generated from methodical barrage testing — 09 Jun 2025*

## Priority P0 — Critical Bugs

| ID | Wave | Owner | Deliverable | KPI / Gate | Effort | Status | Evidence |
|----|------|-------|-------------|------------|---------|---------|----------|
| B-09 | Router-Stability | Backend | Fix RouterCascade set/list type bug | Security prompts succeed | 0.5d | 🔴 autonomous | `unsupported operand type(s) for \|=: 'set' and 'list'` in security domain |
| B-10 | Monitoring-Gap | DevOps | Restore Prometheus scrape targets | Guardian alerts clear | 0.25d | 🔴 autonomous | Guardian: "prometheus_down" triggered continuously |

## Priority P1 — Performance Issues  

| ID | Wave | Owner | Deliverable | KPI / Gate | Effort | Status | Evidence |
|----|------|-------|-------------|------------|---------|---------|----------|
| B-11 | Cold-Start | Infra | RouterCascade pre-warming | Cold start ≤ 5s | 0.75d | 🟡 autonomous | First request: 23.9s vs subsequent 1.8-3.3s |
| B-12 | Response-Limits | Backend | Fix response truncation | Strategic prompts complete | 0.5d | 🟡 autonomous | Monitoring/CI/UX responses cut mid-sentence |

## Priority P2 — User Experience

| ID | Wave | Owner | Deliverable | KPI / Gate | Effort | Status | Evidence |
|----|------|-------|-------------|------------|---------|---------|----------|
| B-13 | Error-Handling | Backend | Graceful complex prompt fallback | User-friendly errors | 0.5d | 🟡 autonomous | Security prompt failed with TypeError vs helpful message |
| B-14 | Documentation | PM/Docs | UX onboarding checklist from Council analysis | GA-ready docs exist | 0.25d | 🟡 autonomous | "What onboarding docs must exist before GA?" → extract action items |

## Implementation Notes

### B-09: RouterCascade Type Bug
- **Location**: Security prompt processing path
- **Error**: `unsupported operand type(s) for |=: 'set' and 'list'`
- **Test**: "List the top three auth or data-privacy vulnerabilities still present."
- **Regression Test**: Add to barrage suite with assertion for proper response

### B-10: Prometheus Monitoring Gap
- **Guardian Alert**: Rule 'prometheus_down' triggered: 1.00 > 0.5
- **Frequency**: Every 5-minute check cycle
- **Impact**: Guardian cannot monitor system health for auto-restart decisions

### B-11: Cold Start Performance
- **First Request**: 23.94s latency (likely RouterCascade initialization)
- **Subsequent**: 1.8s-3.3s normal range
- **Solution**: Pre-load TinyLlama weights or implement warm-up ping

### B-12: Response Truncation
- **Pattern**: Strategic domain responses cut off mid-processing
- **Example**: Monitoring prompt returned router metadata instead of complete analysis
- **Likely Cause**: Token limits or timeout in model processing chain

## Autonomous Processing Labels

All tickets labeled `autonomous` for Builder-bot scaffold generation:
- Priority P0 → Immediate PR creation  
- Priority P1 → Next sprint cycle
- Priority P2 → Background improvement queue

## Barrage Evidence Links

- **Raw Data**: `reports/council_barrage.ndjson` (4 prompts, 12s throttling)
- **Analysis**: `reports/barrage_summary.md` (75% success rate documented)
- **Verification**: `verify_barrage.py` (Sunday Verification Principle applied) 