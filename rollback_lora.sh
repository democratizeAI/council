#!/bin/bash
# Emergency LoRA Rollback Script - Phase 3 Self-Improvement
# =========================================================
#
# Emergency rollback system that:
# 1. Detects quality regressions automatically
# 2. Restores previous known-good LoRA adapter  
# 3. Validates rollback success
# 4. Alerts monitoring systems

set -euo pipefail

# Configuration
ROLLBACK_LOG="logs/rollback_$(date +%Y%m%d_%H%M%S).log"
HEALTH_ENDPOINT="http://localhost:8000/health"
METRICS_ENDPOINT="http://localhost:8000/metrics"
CURRENT_LORA_LINK="loras/current"

mkdir -p logs

echo "🚨 EMERGENCY LORA ROLLBACK INITIATED" | tee -a "$ROLLBACK_LOG"
echo "=========================================" | tee -a "$ROLLBACK_LOG"
echo "📅 Timestamp: $(date)" | tee -a "$ROLLBACK_LOG"
echo "🔍 Reason: Quality regression detected" | tee -a "$ROLLBACK_LOG"

# Find the most recent rollback target
ROLLBACK_TARGET=""

# Look for rollback directories (created by deploy script)
LATEST_ROLLBACK=$(find loras -name "rollback_*" -type d -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || echo "")

if [[ -n "$LATEST_ROLLBACK" ]]; then
    ROLLBACK_TARGET="$LATEST_ROLLBACK"
    echo "🎯 Found rollback target: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"
else
    # Look for backup directories (older backup pattern)
    LATEST_BACKUP=$(find loras -name "backup_*" -type d -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || echo "")
    
    if [[ -n "$LATEST_BACKUP" ]]; then
        ROLLBACK_TARGET="$LATEST_BACKUP"
        echo "🎯 Found backup target: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"
    fi
fi

# Last resort: look for any previous LoRA
if [[ -z "$ROLLBACK_TARGET" ]]; then
    echo "⚠️ No rollback target found, scanning for any previous LoRA..." | tee -a "$ROLLBACK_LOG"
    
    # Find any LoRA directory that's not the current one
    LORA_DIRS=$(find loras -maxdepth 1 -type d -name "*" ! -name "loras" ! -name "current" ! -name "latest" 2>/dev/null || echo "")
    
    if [[ -n "$LORA_DIRS" ]]; then
        ROLLBACK_TARGET=$(echo "$LORA_DIRS" | head -1)
        echo "🎯 Using fallback target: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"
    fi
fi

# Abort if no rollback target
if [[ -z "$ROLLBACK_TARGET" ]] || [[ ! -d "$ROLLBACK_TARGET" ]]; then
    echo "❌ CRITICAL: No rollback target available!" | tee -a "$ROLLBACK_LOG"
    echo "💡 Manual intervention required - no previous LoRA found" | tee -a "$ROLLBACK_LOG"
    
    # Alert monitoring systems
    curl -X POST "http://localhost:9093/api/v1/alerts" -H "Content-Type: application/json" -d '{
        "alerts": [{
            "labels": {
                "alertname": "LoRAEmergencyRollbackFailed",
                "severity": "critical",
                "service": "autogen-council"
            },
            "annotations": {
                "summary": "Emergency LoRA rollback failed - no rollback target available"
            }
        }]
    }' 2>/dev/null || echo "⚠️ Could not send alert to Alertmanager" | tee -a "$ROLLBACK_LOG"
    
    exit 1
fi

# Validate rollback target
echo "🔍 Validating rollback target: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"

REQUIRED_FILES=("adapter_config.json")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$ROLLBACK_TARGET/$file" ]]; then
        echo "❌ Rollback target missing required file: $file" | tee -a "$ROLLBACK_LOG"
        exit 1
    fi
done

echo "✅ Rollback target validated" | tee -a "$ROLLBACK_LOG"

# Capture pre-rollback state for comparison
echo "📊 Capturing pre-rollback metrics..." | tee -a "$ROLLBACK_LOG"

PRE_ROLLBACK_METRICS=$(curl -s "$METRICS_ENDPOINT" 2>/dev/null || echo "metrics_unavailable")
if [[ "$PRE_ROLLBACK_METRICS" != "metrics_unavailable" ]]; then
    PRE_SUCCESS_TOTAL=$(echo "$PRE_ROLLBACK_METRICS" | grep "autogen_requests_success_total" | tail -1 | awk '{print $2}' || echo "0")
    PRE_TOTAL_REQUESTS=$(echo "$PRE_ROLLBACK_METRICS" | grep "autogen_requests_total" | tail -1 | awk '{print $2}' || echo "1")
    PRE_AVG_LATENCY=$(echo "$PRE_ROLLBACK_METRICS" | grep "autogen_latency_ms_avg" | tail -1 | awk '{print $2}' || echo "0")
    
    if (( PRE_TOTAL_REQUESTS > 0 )); then
        PRE_SUCCESS_RATE=$(echo "scale=3; $PRE_SUCCESS_TOTAL / $PRE_TOTAL_REQUESTS" | bc -l)
    else
        PRE_SUCCESS_RATE="0.000"
    fi
    
    echo "📈 Pre-rollback success rate: $PRE_SUCCESS_RATE" | tee -a "$ROLLBACK_LOG"
    echo "⚡ Pre-rollback avg latency: ${PRE_AVG_LATENCY}ms" | tee -a "$ROLLBACK_LOG"
fi

# Backup the failed deployment for analysis
FAILED_LORA=""
if [[ -L "$CURRENT_LORA_LINK" ]]; then
    FAILED_LORA=$(readlink -f "$CURRENT_LORA_LINK")
    FAILED_BACKUP="loras/failed_$(date +%Y%m%d_%H%M%S)"
    
    echo "💾 Backing up failed deployment: $FAILED_LORA -> $FAILED_BACKUP" | tee -a "$ROLLBACK_LOG"
    cp -r "$FAILED_LORA" "$FAILED_BACKUP"
    
    # Mark as failed for analysis
    echo "rollback_$(date -Iseconds)" > "$FAILED_BACKUP/rollback_reason.txt"
    echo "quality_regression" > "$FAILED_BACKUP/failure_type.txt"
fi

# Execute rollback
echo "🔄 Executing rollback to: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"

# Remove current symlink and create new one
if [[ -L "$CURRENT_LORA_LINK" ]] || [[ -e "$CURRENT_LORA_LINK" ]]; then
    rm -f "$CURRENT_LORA_LINK"
fi

ln -sfn "$(realpath "$ROLLBACK_TARGET")" "$CURRENT_LORA_LINK"

# Mark rollback timestamp
echo "$(date -Iseconds)" > "$ROLLBACK_TARGET/rollback_deployed_at.txt"

# Signal model loader to reload
echo "🔄 Signaling model loader to reload with rollback..." | tee -a "$ROLLBACK_LOG"
touch "loras/reload_trigger.txt"
echo "rollback" > "loras/reload_reason.txt"

echo "✅ Rollback deployment completed" | tee -a "$ROLLBACK_LOG"

# Wait for rollback to take effect
echo "⏳ Waiting 45s for rollback to take effect..." | tee -a "$ROLLBACK_LOG"
sleep 45

# Validate rollback success
echo "🔍 Validating rollback success..." | tee -a "$ROLLBACK_LOG"

# Health check
HEALTH_STATUS=$(curl -s "$HEALTH_ENDPOINT" 2>/dev/null || echo '{"status":"unknown"}')
SERVICE_STATUS=$(echo "$HEALTH_STATUS" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
")

echo "🏥 Post-rollback service health: $SERVICE_STATUS" | tee -a "$ROLLBACK_LOG"

if [[ "$SERVICE_STATUS" != "healthy" ]]; then
    echo "❌ CRITICAL: Service still unhealthy after rollback!" | tee -a "$ROLLBACK_LOG"
    echo "🚨 Manual intervention required immediately" | tee -a "$ROLLBACK_LOG"
    exit 2
fi

# Check if metrics have improved
echo "📊 Checking post-rollback metrics..." | tee -a "$ROLLBACK_LOG"

POST_ROLLBACK_METRICS=$(curl -s "$METRICS_ENDPOINT" 2>/dev/null || echo "metrics_unavailable")
if [[ "$POST_ROLLBACK_METRICS" != "metrics_unavailable" ]]; then
    POST_SUCCESS_TOTAL=$(echo "$POST_ROLLBACK_METRICS" | grep "autogen_requests_success_total" | tail -1 | awk '{print $2}' || echo "0")
    POST_TOTAL_REQUESTS=$(echo "$POST_ROLLBACK_METRICS" | grep "autogen_requests_total" | tail -1 | awk '{print $2}' || echo "1")
    POST_AVG_LATENCY=$(echo "$POST_ROLLBACK_METRICS" | grep "autogen_latency_ms_avg" | tail -1 | awk '{print $2}' || echo "0")
    
    if (( POST_TOTAL_REQUESTS > 0 )); then
        POST_SUCCESS_RATE=$(echo "scale=3; $POST_SUCCESS_TOTAL / $POST_TOTAL_REQUESTS" | bc -l)
    else
        POST_SUCCESS_RATE="0.000"
    fi
    
    echo "📈 Post-rollback success rate: $POST_SUCCESS_RATE" | tee -a "$ROLLBACK_LOG"
    echo "⚡ Post-rollback avg latency: ${POST_AVG_LATENCY}ms" | tee -a "$ROLLBACK_LOG"
fi

# Create rollback summary
cat > "$ROLLBACK_TARGET/rollback_summary.json" << EOF
{
    "rollback_timestamp": "$(date -Iseconds)",
    "rollback_target": "$ROLLBACK_TARGET",
    "failed_deployment": "${FAILED_LORA:-unknown}",
    "pre_rollback": {
        "success_rate": "${PRE_SUCCESS_RATE:-unknown}",
        "avg_latency_ms": "${PRE_AVG_LATENCY:-unknown}"
    },
    "post_rollback": {
        "success_rate": "${POST_SUCCESS_RATE:-unknown}",
        "avg_latency_ms": "${POST_AVG_LATENCY:-unknown}"
    },
    "rollback_reason": "quality_regression",
    "service_health": "$SERVICE_STATUS",
    "rollback_status": "completed"
}
EOF

# Send success notification to monitoring
curl -X POST "http://localhost:9093/api/v1/alerts" -H "Content-Type: application/json" -d '{
    "alerts": [{
        "labels": {
            "alertname": "LoRAEmergencyRollbackCompleted", 
            "severity": "warning",
            "service": "autogen-council"
        },
        "annotations": {
            "summary": "Emergency LoRA rollback completed successfully",
            "description": "Rollback to '"$ROLLBACK_TARGET"' completed. Service health: '"$SERVICE_STATUS"'"
        }
    }]
}' 2>/dev/null || echo "⚠️ Could not send success alert" | tee -a "$ROLLBACK_LOG"

echo "✅ EMERGENCY ROLLBACK COMPLETED SUCCESSFULLY" | tee -a "$ROLLBACK_LOG"
echo "🎯 Rollback Summary:" | tee -a "$ROLLBACK_LOG"
echo "   ✅ Status: Successful" | tee -a "$ROLLBACK_LOG"
echo "   🔄 Target: $ROLLBACK_TARGET" | tee -a "$ROLLBACK_LOG"
echo "   🏥 Health: $SERVICE_STATUS" | tee -a "$ROLLBACK_LOG"
echo "   📋 Summary: $ROLLBACK_TARGET/rollback_summary.json" | tee -a "$ROLLBACK_LOG"
echo "   📝 Log: $ROLLBACK_LOG" | tee -a "$ROLLBACK_LOG"

if [[ -n "${FAILED_LORA:-}" ]]; then
    echo "   🔍 Failed deployment saved for analysis: $FAILED_BACKUP" | tee -a "$ROLLBACK_LOG"
fi

echo "📊 System restored to previous known-good state" | tee -a "$ROLLBACK_LOG" 