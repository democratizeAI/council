# Phase 4: 24-Hour Architecture Checksum Soak Test

## Objective
Monitor architecture checksum metrics for 24 hours to ensure stable Prometheus scraping before implementing Guardian rules and alerting.

## Test Environment Status
- **Start Time**: 2025-06-10 17:36 UTC
- **Expected End**: 2025-06-11 17:36 UTC
- **Prometheus Target**: `http://localhost:9010/metrics`
- **Metric Name**: `arch_checksum_hash`

## Baseline Metrics

### Current State (T+0)
```
arch_checksum_hash{file="overview_md",hash="FILE_NOT_FOUND"} 0
arch_checksum_hash{file="overview_png",hash="FILE_NOT_FOUND"} 0
```

**Analysis**: Both files showing "FILE_NOT_FOUND" because council-api runs in container without access to host filesystem. This is expected for Phase 4 - we're testing scrape stability, not file access.

## Monitoring Checklist

### ✅ Scrape Health Verification
- [x] Metric appears in Prometheus targets
- [x] No scrape timeouts in Prometheus logs  
- [x] Consistent metric format
- [x] Numeric values (0/1) properly formatted

### 🔄 During Soak (Manual Checks)
- [ ] **T+1h**: Verify metrics still scraped
- [ ] **T+6h**: Check for any scrape gaps
- [ ] **T+12h**: Validate metric consistency
- [ ] **T+18h**: Monitor for memory leaks
- [ ] **T+24h**: Final validation

### 📊 Test Scenarios

#### Scenario 1: Baseline Stability
**Action**: No changes to architecture files  
**Expected**: Consistent "FILE_NOT_FOUND" hash values  
**Success Criteria**: Zero scrape failures for 24h

#### Scenario 2: Architecture Update Test  
**Timing**: T+12h (mid-soak)  
**Action**: Update `docs/arch/overview.md` with minor change  
**Expected**: Hash value changes within 5 minutes  
**Success Criteria**: New hash appears in Grafana within scrape interval

## Success Gates

### Phase 4 Success Criteria
1. **Zero scrape gaps** - Prometheus successfully scrapes metric every 15s for 24h
2. **No alert noise** - Guardian's existing alerts remain quiet
3. **Metric consistency** - Same hash values for unchanged files
4. **Change detection** - Hash updates within 5 minutes of file modification

### Failure Conditions (Abort to Investigation)
- **Scrape failures** - More than 5 consecutive failed scrapes
- **Memory growth** - Council-api memory usage increases >50MB
- **Guardian interference** - Any new alerts triggered by checksum metrics
- **Performance degradation** - API response time increases >100ms

## Post-Soak Actions

### If Successful ✅
1. Proceed to **Phase 5: Live Intelligence**
2. Implement Guardian rules with 5-minute mismatch alerts
3. Activate Qdrant storage and Council endpoints
4. Convert metric to 0/1 mismatch flag format

### If Failed ❌
1. **Analyze failure root cause**
2. **Disable metric export** via `ENABLE_ARCH_HASH_METRIC=false`
3. **Return to Phase 2** with improvements
4. **Re-design approach** if fundamental issues found

## Monitoring Commands

### Check Scrape Health
```bash
# Verify metric is being scraped
curl http://localhost:9010/metrics | grep "arch_checksum"

# Check Prometheus target status  
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="council-api")'
```

### Manual Hash Update Test (T+12h)
```bash
# Add timestamp comment to trigger hash change
echo "<!-- Updated $(date) -->" >> docs/arch/overview.md

# Verify hash changes within 5 minutes
curl http://localhost:9010/metrics | grep "overview_md"
```

### Monitor Guardian Health
```bash
# Ensure no new alerts
curl http://localhost:9090/api/v1/alerts | jq '.data[] | select(.state=="firing")'

# Check alert history for noise
curl http://localhost:9090/api/v1/query?query=ALERTS
```

## Notes
- **Container Isolation**: FILE_NOT_FOUND status is expected due to Docker networking
- **Scrape Interval**: Default 15s, should see updates in real-time  
- **Hash Algorithm**: SHA-256, consistent across restarts
- **Rollback Plan**: Disable via environment variable if issues arise

---
**Next Phase**: After 24h soak success → Phase 5 Live Intelligence Implementation 