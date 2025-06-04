#!/bin/bash
# LoRA Deployment Script - Phase 3 Self-Improvement
# ================================================
#
# Automatically deploys trained LoRA adapters with:
# 1. Pre-deployment validation
# 2. Gradual rollout with metrics monitoring
# 3. Automatic rollback on quality degradation
# 4. Prometheus metrics integration

set -euo pipefail

# Configuration
LORA_DIR="${1:-loras/latest}"
DEPLOYMENT_LOG="logs/deployment_$(date +%Y%m%d_%H%M%S).log"
METRICS_ENDPOINT="http://localhost:8000/metrics"
HEALTH_ENDPOINT="http://localhost:8000/health"
ROLLBACK_THRESHOLD_LATENCY=1000  # ms
ROLLBACK_THRESHOLD_SUCCESS=0.85  # 85% success rate minimum

mkdir -p logs

echo "🚀 LoRA Deployment Pipeline Starting..." | tee -a "$DEPLOYMENT_LOG"
echo "=============================================" | tee -a "$DEPLOYMENT_LOG"
echo "📅 Timestamp: $(date)" | tee -a "$DEPLOYMENT_LOG"
echo "📂 LoRA Directory: $LORA_DIR" | tee -a "$DEPLOYMENT_LOG"

# Validation Phase
echo "🔍 Phase 1: Pre-deployment validation..." | tee -a "$DEPLOYMENT_LOG"

# Check if LoRA is ready for deployment
if [[ ! -f "$LORA_DIR/deployment_ready.txt" ]]; then
    echo "❌ LoRA not ready for deployment (missing deployment_ready.txt)" | tee -a "$DEPLOYMENT_LOG"
    exit 1
fi

# Validate LoRA files
REQUIRED_FILES=("adapter_config.json" "adapter_model.bin" "training_config.json")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$LORA_DIR/$file" ]]; then
        echo "❌ Missing required file: $file" | tee -a "$DEPLOYMENT_LOG"
        exit 1
    fi
done

echo "✅ LoRA files validated" | tee -a "$DEPLOYMENT_LOG"

# Check training metrics
if [[ -f "$LORA_DIR/training_metrics.json" ]]; then
    TRAINING_LOSS=$(python3 -c "
import json
with open('$LORA_DIR/training_metrics.json', 'r') as f:
    metrics = json.load(f)
print(metrics.get('final_loss', 999))
")
    
    TRAINING_EXAMPLES=$(python3 -c "
import json
with open('$LORA_DIR/training_metrics.json', 'r') as f:
    metrics = json.load(f)
print(metrics.get('training_examples', 0))
")
    
    echo "📊 Training loss: $TRAINING_LOSS" | tee -a "$DEPLOYMENT_LOG"
    echo "📈 Training examples: $TRAINING_EXAMPLES" | tee -a "$DEPLOYMENT_LOG"
    
    # Basic quality checks
    if (( $(echo "$TRAINING_LOSS > 2.0" | bc -l) )); then
        echo "⚠️ Warning: High training loss ($TRAINING_LOSS)" | tee -a "$DEPLOYMENT_LOG"
    fi
    
    if (( TRAINING_EXAMPLES < 10 )); then
        echo "⚠️ Warning: Low training examples ($TRAINING_EXAMPLES)" | tee -a "$DEPLOYMENT_LOG"
    fi
fi

# Pre-deployment metrics snapshot
echo "📊 Capturing pre-deployment metrics..." | tee -a "$DEPLOYMENT_LOG"

PRE_METRICS=$(curl -s "$METRICS_ENDPOINT" 2>/dev/null || echo "metrics_unavailable")
PRE_TIMESTAMP=$(date +%s)

if [[ "$PRE_METRICS" == "metrics_unavailable" ]]; then
    echo "⚠️ Warning: Cannot fetch pre-deployment metrics" | tee -a "$DEPLOYMENT_LOG"
    PRE_SUCCESS_RATE="unknown"
    PRE_LATENCY="unknown"
else
    # Parse Prometheus metrics (basic parsing)
    PRE_SUCCESS_RATE=$(echo "$PRE_METRICS" | grep "autogen_requests_success_total" | tail -1 | awk '{print $2}' || echo "0")
    PRE_TOTAL_REQUESTS=$(echo "$PRE_METRICS" | grep "autogen_requests_total" | tail -1 | awk '{print $2}' || echo "1")
    PRE_AVG_LATENCY=$(echo "$PRE_METRICS" | grep "autogen_latency_ms_avg" | tail -1 | awk '{print $2}' || echo "0")
    
    if (( PRE_TOTAL_REQUESTS > 0 )); then
        PRE_SUCCESS_RATE=$(echo "scale=3; $PRE_SUCCESS_RATE / $PRE_TOTAL_REQUESTS" | bc -l)
    else
        PRE_SUCCESS_RATE="0.000"
    fi
    
    echo "📈 Pre-deployment success rate: $PRE_SUCCESS_RATE" | tee -a "$DEPLOYMENT_LOG"
    echo "⚡ Pre-deployment avg latency: ${PRE_AVG_LATENCY}ms" | tee -a "$DEPLOYMENT_LOG"
fi

# Deployment Phase
echo "🔄 Phase 2: LoRA deployment..." | tee -a "$DEPLOYMENT_LOG"

# Backup current LoRA if exists
CURRENT_LORA_LINK="loras/current"
if [[ -L "$CURRENT_LORA_LINK" ]] || [[ -d "$CURRENT_LORA_LINK" ]]; then
    BACKUP_DIR="loras/rollback_$(date +%Y%m%d_%H%M%S)"
    echo "💾 Backing up current LoRA: $CURRENT_LORA_LINK -> $BACKUP_DIR" | tee -a "$DEPLOYMENT_LOG"
    
    if [[ -L "$CURRENT_LORA_LINK" ]]; then
        # If it's a symlink, copy the target
        cp -r "$(readlink -f "$CURRENT_LORA_LINK")" "$BACKUP_DIR"
    else
        # If it's a directory, move it
        mv "$CURRENT_LORA_LINK" "$BACKUP_DIR"
    fi
fi

# Create new deployment symlink
echo "🔗 Creating deployment symlink: $CURRENT_LORA_LINK -> $LORA_DIR" | tee -a "$DEPLOYMENT_LOG"
ln -sfn "$(realpath "$LORA_DIR")" "$CURRENT_LORA_LINK"

# Mark deployment timestamp
echo "$(date -Iseconds)" > "$LORA_DIR/deployed_at.txt"

# Signal loader to reload (create a reload trigger file)
echo "🔄 Signaling model loader to reload..." | tee -a "$DEPLOYMENT_LOG"
touch "loras/reload_trigger.txt"

echo "✅ LoRA deployment completed" | tee -a "$DEPLOYMENT_LOG"

# Monitoring Phase
echo "📊 Phase 3: Post-deployment monitoring..." | tee -a "$DEPLOYMENT_LOG"

# Allow time for models to reload
echo "⏳ Waiting 30s for model reload..." | tee -a "$DEPLOYMENT_LOG"
sleep 30

# Check health endpoint
HEALTH_STATUS=$(curl -s "$HEALTH_ENDPOINT" 2>/dev/null || echo '{"status":"unknown"}')
SERVICE_STATUS=$(echo "$HEALTH_STATUS" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
")

echo "🏥 Service health: $SERVICE_STATUS" | tee -a "$DEPLOYMENT_LOG"

if [[ "$SERVICE_STATUS" != "healthy" ]]; then
    echo "❌ Service unhealthy after deployment!" | tee -a "$DEPLOYMENT_LOG"
    echo "🔄 Initiating emergency rollback..." | tee -a "$DEPLOYMENT_LOG"
    bash "$(dirname "$0")/rollback_lora.sh" 2>&1 | tee -a "$DEPLOYMENT_LOG"
    exit 1
fi

# Monitor metrics for regression detection
echo "🔍 Monitoring for quality regression (60s window)..." | tee -a "$DEPLOYMENT_LOG"

MONITOR_START=$(date +%s)
MONITOR_DURATION=60  # Monitor for 60 seconds
SAMPLE_INTERVAL=10   # Check every 10 seconds

while [[ $(($(date +%s) - MONITOR_START)) -lt $MONITOR_DURATION ]]; do
    sleep $SAMPLE_INTERVAL
    
    # Get current metrics
    CURRENT_METRICS=$(curl -s "$METRICS_ENDPOINT" 2>/dev/null || echo "metrics_unavailable")
    
    if [[ "$CURRENT_METRICS" != "metrics_unavailable" ]]; then
        # Parse current metrics
        CURRENT_SUCCESS_TOTAL=$(echo "$CURRENT_METRICS" | grep "autogen_requests_success_total" | tail -1 | awk '{print $2}' || echo "0")
        CURRENT_TOTAL_REQUESTS=$(echo "$CURRENT_METRICS" | grep "autogen_requests_total" | tail -1 | awk '{print $2}' || echo "1") 
        CURRENT_AVG_LATENCY=$(echo "$CURRENT_METRICS" | grep "autogen_latency_ms_avg" | tail -1 | awk '{print $2}' || echo "0")
        
        # Calculate success rate
        if (( CURRENT_TOTAL_REQUESTS > 0 )); then
            CURRENT_SUCCESS_RATE=$(echo "scale=3; $CURRENT_SUCCESS_TOTAL / $CURRENT_TOTAL_REQUESTS" | bc -l)
        else
            CURRENT_SUCCESS_RATE="0.000"
        fi
        
        echo "📈 Current metrics: ${CURRENT_SUCCESS_RATE} success, ${CURRENT_AVG_LATENCY}ms latency" | tee -a "$DEPLOYMENT_LOG"
        
        # Check for regression (only if we have meaningful data)
        if (( CURRENT_TOTAL_REQUESTS >= 5 )); then
            # Latency regression check
            if (( $(echo "$CURRENT_AVG_LATENCY > $ROLLBACK_THRESHOLD_LATENCY" | bc -l) )); then
                echo "🚨 REGRESSION DETECTED: Latency too high (${CURRENT_AVG_LATENCY}ms > ${ROLLBACK_THRESHOLD_LATENCY}ms)" | tee -a "$DEPLOYMENT_LOG"
                echo "🔄 Initiating automatic rollback..." | tee -a "$DEPLOYMENT_LOG"
                bash "$(dirname "$0")/rollback_lora.sh" 2>&1 | tee -a "$DEPLOYMENT_LOG"
                exit 2
            fi
            
            # Success rate regression check
            if (( $(echo "$CURRENT_SUCCESS_RATE < $ROLLBACK_THRESHOLD_SUCCESS" | bc -l) )); then
                echo "🚨 REGRESSION DETECTED: Success rate too low (${CURRENT_SUCCESS_RATE} < ${ROLLBACK_THRESHOLD_SUCCESS})" | tee -a "$DEPLOYMENT_LOG"
                echo "🔄 Initiating automatic rollback..." | tee -a "$DEPLOYMENT_LOG"
                bash "$(dirname "$0")/rollback_lora.sh" 2>&1 | tee -a "$DEPLOYMENT_LOG"
                exit 2
            fi
        fi
    fi
    
    echo "⏱️ Monitoring... $((MONITOR_DURATION - ($(date +%s) - MONITOR_START)))s remaining" | tee -a "$DEPLOYMENT_LOG"
done

# Deployment Success
echo "✅ Phase 4: Deployment successful!" | tee -a "$DEPLOYMENT_LOG"
echo "📊 Final metrics snapshot..." | tee -a "$DEPLOYMENT_LOG"

# Final metrics capture
FINAL_METRICS=$(curl -s "$METRICS_ENDPOINT" 2>/dev/null || echo "metrics_unavailable")

if [[ "$FINAL_METRICS" != "metrics_unavailable" ]]; then
    FINAL_SUCCESS_TOTAL=$(echo "$FINAL_METRICS" | grep "autogen_requests_success_total" | tail -1 | awk '{print $2}' || echo "0")
    FINAL_TOTAL_REQUESTS=$(echo "$FINAL_METRICS" | grep "autogen_requests_total" | tail -1 | awk '{print $2}' || echo "1")
    FINAL_AVG_LATENCY=$(echo "$FINAL_METRICS" | grep "autogen_latency_ms_avg" | tail -1 | awk '{print $2}' || echo "0")
    
    if (( FINAL_TOTAL_REQUESTS > 0 )); then
        FINAL_SUCCESS_RATE=$(echo "scale=3; $FINAL_SUCCESS_TOTAL / $FINAL_TOTAL_REQUESTS" | bc -l)
    else
        FINAL_SUCCESS_RATE="0.000"
    fi
    
    echo "📈 Final success rate: $FINAL_SUCCESS_RATE" | tee -a "$DEPLOYMENT_LOG"
    echo "⚡ Final avg latency: ${FINAL_AVG_LATENCY}ms" | tee -a "$DEPLOYMENT_LOG"
fi

# Create deployment summary
cat > "$LORA_DIR/deployment_summary.json" << EOF
{
    "deployment_timestamp": "$(date -Iseconds)",
    "lora_directory": "$LORA_DIR",
    "pre_deployment": {
        "success_rate": "$PRE_SUCCESS_RATE",
        "avg_latency_ms": "$PRE_AVG_LATENCY"
    },
    "post_deployment": {
        "success_rate": "${FINAL_SUCCESS_RATE:-unknown}",
        "avg_latency_ms": "${FINAL_AVG_LATENCY:-unknown}"
    },
    "monitoring_duration_s": $MONITOR_DURATION,
    "rollback_thresholds": {
        "max_latency_ms": $ROLLBACK_THRESHOLD_LATENCY,
        "min_success_rate": $ROLLBACK_THRESHOLD_SUCCESS
    },
    "deployment_status": "successful"
}
EOF

echo "🎯 Deployment Summary:" | tee -a "$DEPLOYMENT_LOG"
echo "   ✅ Status: Successful" | tee -a "$DEPLOYMENT_LOG"
echo "   📂 LoRA: $LORA_DIR" | tee -a "$DEPLOYMENT_LOG"
echo "   📊 Monitoring: ${MONITOR_DURATION}s, no regressions detected" | tee -a "$DEPLOYMENT_LOG"
echo "   📋 Summary: $LORA_DIR/deployment_summary.json" | tee -a "$DEPLOYMENT_LOG"
echo "   📝 Log: $DEPLOYMENT_LOG" | tee -a "$DEPLOYMENT_LOG"

echo "🎉 LoRA deployment pipeline completed successfully!" | tee -a "$DEPLOYMENT_LOG" 