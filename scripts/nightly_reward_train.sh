#!/usr/bin/env bash
# scripts/nightly_reward_train.sh
set -e

echo "$(date): Starting nightly reward model training"

# Build preference pairs from feedback buffer
echo "$(date): Building preference pairs from Redis feedback"
python preference_model/dataset.py

# Check if we have enough data
pair_count=$(wc -l < /opt/lumina/reward/pairs.jsonl || echo "0")
if [ "$pair_count" -lt 50 ]; then
    echo "$(date): Insufficient data ($pair_count pairs), skipping training"
    exit 0
fi

echo "$(date): Training on $pair_count preference pairs"

# Train the reward model
python preference_model/train_reward.py

# Extract validation accuracy and push to Prometheus
if [ -f /opt/lumina/reward/ckpt/trainer_state.json ]; then
    acc=$(jq '.log_history[-1].eval_accuracy // 0' /opt/lumina/reward/ckpt/trainer_state.json)
    echo "$(date): Validation accuracy: $acc"
    
    # Push metric to Prometheus Pushgateway
    echo "reward_val_accuracy $acc" | curl --data-binary @- \
        http://pushgateway:9091/metrics/job/reward/instance/nightly
    
    echo "$(date): Pushed reward_val_accuracy=$acc to Prometheus"
else
    echo "$(date): Warning: trainer_state.json not found"
fi

echo "$(date): Nightly reward training completed" 