#!/bin/bash
# Nightly Self-Improvement Cron Job - Phase 3
# ===========================================
#
# Complete autonomous improvement pipeline:
# 1. Harvest failures from yesterday
# 2. Train QLoRA adapter on failures  
# 3. Deploy new adapter with monitoring
# 4. Send notifications and update metrics

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/nightly_$(date +%Y%m%d_%H%M%S).log"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"
MIN_FAILURES_TO_TRAIN=5

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Notification function
notify() {
    local status="$1"
    local message="$2"
    
    log "📢 Notification: $status - $message"
    
    # Slack/Discord webhook notification (if configured)
    if [[ -n "$NOTIFICATION_WEBHOOK" ]]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{
                 \"text\": \"🤖 AutoGen Council Nightly Improvement\",
                 \"attachments\": [{
                     \"color\": \"$([ "$status" = "success" ] && echo "good" || echo "warning")\",
                     \"fields\": [{
                         \"title\": \"Status\",
                         \"value\": \"$status\",
                         \"short\": true
                     }, {
                         \"title\": \"Message\", 
                         \"value\": \"$message\",
                         \"short\": false
                     }, {
                         \"title\": \"Timestamp\",
                         \"value\": \"$(date -Iseconds)\",
                         \"short\": true
                     }]
                 }]
             }" 2>/dev/null || log "⚠️ Failed to send webhook notification"
    fi
    
    # System journal logging
    logger -t "autogen-improvement" "$status: $message"
}

# Cleanup function
cleanup() {
    local exit_code=$?
    if [[ $exit_code -ne 0 ]]; then
        log "💥 Nightly improvement failed with exit code $exit_code"
        notify "error" "Nightly improvement pipeline failed. Check logs: $LOG_FILE"
    fi
    exit $exit_code
}

trap cleanup EXIT

log "🌙 Nightly Self-Improvement Pipeline Starting"
log "=============================================="
log "📅 Date: $(date)"
log "📂 Project: $PROJECT_DIR"
log "📝 Log: $LOG_FILE"

# Change to project directory
cd "$PROJECT_DIR"

# Pre-flight checks
log "🔍 Pre-flight checks..."

# Check if server is running
if ! curl -s "http://localhost:8000/health" > /dev/null; then
    log "❌ AutoGen server not running - aborting improvement"
    notify "error" "AutoGen server not responding on localhost:8000"
    exit 1
fi

# Check disk space (need at least 2GB for training)
AVAILABLE_GB=$(df . | tail -1 | awk '{print int($4/1024/1024)}')
if [[ $AVAILABLE_GB -lt 2 ]]; then
    log "❌ Insufficient disk space: ${AVAILABLE_GB}GB available, need 2GB+"
    notify "warning" "Low disk space: ${AVAILABLE_GB}GB available, improvement skipped"
    exit 1
fi

log "✅ Pre-flight checks passed (${AVAILABLE_GB}GB available)"

# Step 1: Failure Harvesting
log "📊 Step 1: Harvesting yesterday's failures..."

HARVEST_START=$(date +%s)
python3 harvest_failures.py 2>&1 | tee -a "$LOG_FILE"
HARVEST_EXIT_CODE=$?
HARVEST_DURATION=$(($(date +%s) - HARVEST_START))

if [[ $HARVEST_EXIT_CODE -eq 0 ]]; then
    log "✅ Failure harvesting completed in ${HARVEST_DURATION}s"
    
    # Check if we have enough training data
    LATEST_HARVEST=$(find training_data -name "harvest_*.jsonl" -type f -printf "%T@ %p\n" 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2- || echo "")
    
    if [[ -n "$LATEST_HARVEST" ]]; then
        TRAINING_COUNT=$(wc -l < "$LATEST_HARVEST")
        log "📈 Training examples available: $TRAINING_COUNT"
        
        if [[ $TRAINING_COUNT -lt $MIN_FAILURES_TO_TRAIN ]]; then
            log "ℹ️ Too few failures ($TRAINING_COUNT < $MIN_FAILURES_TO_TRAIN) - no training needed"
            notify "info" "No training needed: only $TRAINING_COUNT failures (threshold: $MIN_FAILURES_TO_TRAIN)"
            
            # Clean up old training data to save space
            find training_data -name "harvest_*.jsonl" -type f -mtime +7 -delete 2>/dev/null || true
            
            log "🎯 Nightly improvement completed (no training needed)"
            exit 0
        fi
    else
        log "⚠️ No harvest data found despite successful exit"
        TRAINING_COUNT=0
    fi
    
elif [[ $HARVEST_EXIT_CODE -eq 1 ]]; then
    log "ℹ️ No failures to harvest (good news!)"
    notify "info" "No failures found to harvest - system performing well"
    exit 0
else
    log "❌ Failure harvesting failed with exit code $HARVEST_EXIT_CODE"
    notify "error" "Failure harvesting failed - check logs for details"
    exit 1
fi

# Step 2: QLoRA Training
log "🧠 Step 2: QLoRA training on $TRAINING_COUNT examples..."

TRAINING_START=$(date +%s)
bash train_lora.sh 2>&1 | tee -a "$LOG_FILE"
TRAINING_EXIT_CODE=$?
TRAINING_DURATION=$(($(date +%s) - TRAINING_START))

if [[ $TRAINING_EXIT_CODE -eq 0 ]]; then
    log "✅ QLoRA training completed in ${TRAINING_DURATION}s"
    
    # Validate training output
    if [[ -f "loras/latest/adapter_model.bin" && -f "loras/latest/training_metrics.json" ]]; then
        FINAL_LOSS=$(python3 -c "
import json
try:
    with open('loras/latest/training_metrics.json', 'r') as f:
        metrics = json.load(f)
    print(f\"{metrics.get('final_loss', 0):.3f}\")
except:
    print('unknown')
")
        log "📊 Training completed with final loss: $FINAL_LOSS"
    else
        log "⚠️ Training files not found despite successful exit"
    fi
else
    log "❌ QLoRA training failed with exit code $TRAINING_EXIT_CODE"
    notify "error" "QLoRA training failed after ${TRAINING_DURATION}s - check logs"
    exit 1
fi

# Step 3: Deployment
log "🚀 Step 3: Deploying new LoRA adapter..."

DEPLOY_START=$(date +%s)
bash deploy_lora.sh loras/latest 2>&1 | tee -a "$LOG_FILE"
DEPLOY_EXIT_CODE=$?
DEPLOY_DURATION=$(($(date +%s) - DEPLOY_START))

if [[ $DEPLOY_EXIT_CODE -eq 0 ]]; then
    log "✅ LoRA deployment completed in ${DEPLOY_DURATION}s"
    
    # Extract deployment metrics
    if [[ -f "loras/latest/deployment_summary.json" ]]; then
        DEPLOYMENT_SUMMARY=$(cat "loras/latest/deployment_summary.json")
        POST_SUCCESS_RATE=$(echo "$DEPLOYMENT_SUMMARY" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    rate = data['post_deployment']['success_rate']
    if rate == 'unknown': print('unknown')
    else: print(f'{float(rate):.1%}')
except:
    print('unknown')
")
        log "📈 Post-deployment success rate: $POST_SUCCESS_RATE"
    fi
    
elif [[ $DEPLOY_EXIT_CODE -eq 2 ]]; then
    log "🚨 Deployment failed due to quality regression - rollback completed"
    notify "warning" "LoRA deployment rolled back due to quality regression"
    exit 0  # Not a fatal error, rollback worked
else
    log "❌ LoRA deployment failed with exit code $DEPLOY_EXIT_CODE" 
    notify "error" "LoRA deployment failed after ${DEPLOY_DURATION}s"
    exit 1
fi

# Step 4: Post-deployment validation
log "🔍 Step 4: Post-deployment validation..."

# Wait for system to stabilize
sleep 60

# Quick health check
HEALTH_STATUS=$(curl -s "http://localhost:8000/health" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('status', 'unknown'))
except:
    print('unknown')
" 2>/dev/null || echo "unknown")

log "🏥 System health: $HEALTH_STATUS"

if [[ "$HEALTH_STATUS" != "healthy" ]]; then
    log "⚠️ System health check failed after deployment"
    notify "warning" "System health degraded after LoRA deployment"
fi

# Test basic functionality
TEST_RESPONSE=$(curl -s -X POST "http://localhost:8000/vote" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Test: What is 2+2?"}' 2>/dev/null || echo "")

if [[ -n "$TEST_RESPONSE" ]]; then
    TEST_TEXT=$(echo "$TEST_RESPONSE" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('text', 'no_response')[:50])
except:
    print('parse_error')
" 2>/dev/null || echo "unknown")
    log "🧪 Test query response: $TEST_TEXT..."
else
    log "⚠️ Test query failed to get response"
fi

# Calculate total improvement time
TOTAL_DURATION=$(($(date +%s) - HARVEST_START))
TOTAL_MINUTES=$((TOTAL_DURATION / 60))

# Success summary
log "🎯 Nightly Self-Improvement Summary"
log "===================================="
log "✅ Total duration: ${TOTAL_MINUTES}m ${TOTAL_DURATION}s"
log "📊 Harvest: ${HARVEST_DURATION}s ($TRAINING_COUNT examples)"
log "🧠 Training: ${TRAINING_DURATION}s (loss: ${FINAL_LOSS:-unknown})"
log "🚀 Deployment: ${DEPLOY_DURATION}s (success: ${POST_SUCCESS_RATE:-unknown})"
log "🏥 Final health: $HEALTH_STATUS"

# Clean up old files to save space
log "🧹 Cleaning up old files..."

# Remove training data older than 7 days
find training_data -name "harvest_*.jsonl" -type f -mtime +7 -delete 2>/dev/null || true

# Remove old LoRA backups (keep last 3)
find loras -name "backup_*" -type d -printf "%T@ %p\n" 2>/dev/null | sort -n | head -n -3 | cut -d' ' -f2- | xargs rm -rf 2>/dev/null || true
find loras -name "rollback_*" -type d -printf "%T@ %p\n" 2>/dev/null | sort -n | head -n -3 | cut -d' ' -f2- | xargs rm -rf 2>/dev/null || true

# Remove old logs (keep last 14 days)
find logs -name "*.log" -type f -mtime +14 -delete 2>/dev/null || true

log "✅ Cleanup completed"

# Final success notification
notify "success" "Nightly improvement completed in ${TOTAL_MINUTES}m: $TRAINING_COUNT examples → ${POST_SUCCESS_RATE:-unknown} success rate"

log "🌟 Nightly Self-Improvement Pipeline Completed Successfully!" 