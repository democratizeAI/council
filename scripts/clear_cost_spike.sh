#!/bin/bash

# Cost spike cleanup script for FMC-05 testing
# Usage: ./clear_cost_spike.sh

echo "🧹 CLEARING COST SPIKE METRICS"

# Remove the temporary metric file
rm -f /tmp/cost_spike_metric.prom

# Reset metric to safe value
cat > /tmp/cost_reset_metric.prom << EOF
# HELP cloud_est_usd_total Estimated cloud costs in USD
# TYPE cloud_est_usd_total gauge
cloud_est_usd_total{provider="openai",day="today"} 5.0
EOF

echo "📊 Cost reset metric created:"
cat /tmp/cost_reset_metric.prom

# In production, this would push to a metrics endpoint:
# curl -X POST http://pushgateway:9091/metrics/job/cost-spike/instance/openai \
#      --data-binary @/tmp/cost_reset_metric.prom

echo "✅ Cost metrics reset to safe levels"
echo "🔍 Monitor alert resolution at: http://localhost:9090/alerts" 