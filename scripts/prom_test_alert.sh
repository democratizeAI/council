#!/bin/bash
# Prometheus Alert Test Script (Ticket #217)
# Sends intentional 5xx to check alert route

echo "🚨 Testing Prometheus Alert Route..."

# Send 5 intentional 5xx errors to trigger alert
echo "📡 Sending 5 intentional 5xx errors..."
for i in {1..5}; do
    echo "  Error $i/5..."
    curl -s -X POST http://localhost:8000/test/error > /dev/null || true
    sleep 1
done

echo "✅ 5xx errors sent"

# Check metrics endpoint for error count
echo "📊 Checking metrics for 5xx count..."
curl -s http://localhost:8000/metrics | grep "swarm_api_5xx_total" | grep -v "^#"

echo "🔍 Alert should fire within 2 minutes if Prometheus is monitoring..."
echo "   - Alert: SoakTest5xxErrors"
echo "   - Threshold: increase(swarm_api_5xx_total[2m]) > 0"
echo "   - Expected: Slack notification to #dev-alerts"

echo "✅ Prometheus alert test completed" 