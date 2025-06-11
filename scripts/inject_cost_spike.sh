#!/bin/bash

# Cost spike injection script for FMC-05 testing
# Usage: ./inject_cost_spike.sh --usd 12.5 --vendor openai

USD_AMOUNT=""
VENDOR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --usd)
            USD_AMOUNT="$2"
            shift 2
            ;;
        --vendor)
            VENDOR="$2"
            shift 2
            ;;
        *)
            echo "Usage: $0 --usd <amount> --vendor <provider>"
            exit 1
            ;;
    esac
done

if [[ -z "$USD_AMOUNT" || -z "$VENDOR" ]]; then
    echo "❌ Missing required parameters"
    echo "Usage: $0 --usd <amount> --vendor <provider>"
    exit 1
fi

echo "🚨 INJECTING COST SPIKE: $VENDOR = \$$USD_AMOUNT"

# Push metric to Prometheus pushgateway or directly set metric
# For simulation, we'll create a metric file that can be scraped
cat > /tmp/cost_spike_metric.prom << EOF
# HELP cloud_est_usd_total Estimated cloud costs in USD
# TYPE cloud_est_usd_total gauge
cloud_est_usd_total{provider="$VENDOR",day="today"} $USD_AMOUNT
EOF

echo "📊 Cost spike metric created:"
cat /tmp/cost_spike_metric.prom

# In production, this would push to a metrics endpoint:
# curl -X POST http://pushgateway:9091/metrics/job/cost-spike/instance/$VENDOR \
#      --data-binary @/tmp/cost_spike_metric.prom

echo "✅ Cost spike injected for $VENDOR: \$$USD_AMOUNT"
echo "🔍 Monitor CloudCostHigh alert at: http://localhost:9090/alerts"
echo "⏱️  Alert should fire within 1-2 minutes if threshold > \$10" 