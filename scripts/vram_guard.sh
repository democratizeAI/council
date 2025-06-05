#!/usr/bin/env bash
# VRAM Guard - Hybrid implementation (Ticket #206)
# Metrics from NVML container, control actions on host
set -euo pipefail

THRESH=10240       # 10 GB in MiB
TRAINER_CNAME="trainer"
METRIC_DIR="/var/lib/node_exporter/textfile_collector"
METRIC_FILE="$METRIC_DIR/trainer_vram_paused.prom"

# Ensure metric directory exists
mkdir -p "$METRIC_DIR"

# Get total VRAM usage from NVML exporter container (primary)
vram_used=$(curl -s http://localhost:9108/metrics \
  | awk -F'[{} ]' '/gpu_vram_used_mb{gpu="0"}/ {print $2}')

# Fallback to nvidia-smi if exporter is unavailable
if [[ -z "$vram_used" || "$vram_used" == "0" ]]; then
    echo "⚠️ NVML exporter unavailable, falling back to nvidia-smi"
    vram_used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk '{sum+=$1} END{print sum}')
fi

# Check if trainer container is currently paused
is_paused=$(docker inspect -f '{{ .State.Paused }}' "$TRAINER_CNAME" 2>/dev/null || echo "false")

# VRAM management logic
if [[ $vram_used -gt $THRESH && $is_paused == "false" ]]; then
    echo "⚠️ VRAM ${vram_used} MiB > ${THRESH}; pausing trainer"
    docker pause "$TRAINER_CNAME"
    trainer_paused=1
    echo "📊 Trainer paused due to high VRAM usage"
elif [[ $vram_used -le $THRESH && $is_paused == "true" ]]; then
    echo "✅ VRAM back to safe level (${vram_used} MiB); resuming trainer"
    docker unpause "$TRAINER_CNAME"
    trainer_paused=0
    echo "🚀 Trainer resumed - VRAM within limits"
else
    trainer_paused=$([[ $is_paused == "true" ]] && echo 1 || echo 0)
    echo "📈 VRAM: ${vram_used} MiB, Trainer paused: $trainer_paused"
fi

# Expose trainer pause state for node_exporter textfile collector
echo "# HELP trainer_vram_paused Trainer container paused due to high VRAM usage" > "$METRIC_FILE"
echo "# TYPE trainer_vram_paused gauge" >> "$METRIC_FILE"
echo "trainer_vram_paused{reason=\"vram_high\"} $trainer_paused" >> "$METRIC_FILE"

echo "💾 Trainer pause state exported to $METRIC_FILE" 