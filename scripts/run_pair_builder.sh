#!/usr/bin/env bash
# scripts/run_pair_builder.sh
# Hourly cron job to extract preference pairs from Redis feedback

set -e

echo "$(date): Running preference pair builder"

# Execute Lua script via redis-cli
pair_count=$(redis-cli -h redis -p 6379 --eval scripts/build_pairs.lua)

echo "$(date): Built $pair_count preference pairs"

# Push metric to Prometheus
echo "preference_pairs_built_total $pair_count" | \
    curl --data-binary @- http://pushgateway:9091/metrics/job/pair_builder/instance/hourly

echo "$(date): Preference pair building completed" 