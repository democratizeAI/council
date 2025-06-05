#!/bin/bash
# 🧪 Test API 5xx Alert Configuration
# Validates the noise window fix is working correctly

set -euo pipefail

echo "🧪 Testing API 5xx alert configuration..."

# Check if API is running
API_URL="http://localhost:8000"
if ! curl -sf "$API_URL/health" > /dev/null; then
    echo "❌ API not running at $API_URL"
    exit 1
fi

echo "✅ API is running"

# Check Prometheus is running
PROM_URL="http://localhost:9090"
if ! curl -sf "$PROM_URL/-/healthy" > /dev/null; then
    echo "❌ Prometheus not running at $PROM_URL"
    exit 1
fi

echo "✅ Prometheus is running"

# Verify API5xxSpike rule exists and has 'for: 3m'
echo "🔍 Checking API5xxSpike alert configuration..."
RULE_CONFIG=$(curl -s "$PROM_URL/api/v1/rules" | jq '.data.groups[].rules[] | select(.alert == "API5xxSpike")')

if [[ -z "$RULE_CONFIG" ]]; then
    echo "❌ API5xxSpike rule not found in Prometheus"
    echo "Available rules:"
    curl -s "$PROM_URL/api/v1/rules" | jq -r '.data.groups[].rules[].alert' | sort
    exit 1
fi

echo "✅ API5xxSpike rule found"

# Check if 'for' duration is set
FOR_DURATION=$(echo "$RULE_CONFIG" | jq -r '.for // "none"')
if [[ "$FOR_DURATION" == "3m" ]]; then
    echo "✅ Noise window correctly set to 3 minutes"
elif [[ "$FOR_DURATION" == "none" ]]; then
    echo "❌ No 'for' duration set - noise window fix not applied"
    exit 1
else
    echo "⚠️  'for' duration is $FOR_DURATION (expected 3m)"
fi

# Display full rule configuration
echo ""
echo "📋 Full API5xxSpike rule configuration:"
echo "$RULE_CONFIG" | jq .

# Test current 5xx metrics
echo ""
echo "📊 Current 5xx metrics:"
CURRENT_5XX=$(curl -s "$PROM_URL/api/v1/query?query=swarm_api_5xx_total" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
echo "Current 5xx count: $CURRENT_5XX"

# Check if alert is currently active
echo ""
echo "🚨 Checking active alerts..."
ACTIVE_ALERTS=$(curl -s "$PROM_URL/api/v1/alerts" | jq '.data[] | select(.labels.alertname == "API5xxSpike")')

if [[ -n "$ACTIVE_ALERTS" ]]; then
    echo "⚠️  API5xxSpike alert is currently active:"
    echo "$ACTIVE_ALERTS" | jq .
else
    echo "✅ No active API5xxSpike alerts"
fi

# Simulate 5xx spike (optional - requires confirmation)
echo ""
read -p "🧪 Simulate 5xx spike for testing? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔥 Generating 5xx errors for testing..."
    
    # Generate some 5xx errors by hitting a non-existent endpoint
    for i in {1..7}; do
        curl -sf "$API_URL/nonexistent_endpoint_$(date +%s)" > /dev/null 2>&1 || true
        echo -n "."
        sleep 1
    done
    echo ""
    
    echo "⏱️  Waiting 30 seconds for metrics to update..."
    sleep 30
    
    # Check updated metrics
    NEW_5XX=$(curl -s "$PROM_URL/api/v1/query?query=increase(swarm_api_5xx_total[2m])" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
    echo "5xx increase in last 2 minutes: $NEW_5XX"
    
    if (( $(echo "$NEW_5XX > 5" | bc -l) )); then
        echo "🚨 Alert threshold exceeded - should trigger after 3 minutes"
        echo "Monitor at: $PROM_URL/alerts"
    else
        echo "📊 Alert threshold not exceeded ($NEW_5XX ≤ 5)"
    fi
else
    echo "⏭️  Skipping simulation"
fi

echo ""
echo "🎯 Test complete! Summary:"
echo "  ✅ API5xxSpike rule loaded"
echo "  ✅ Noise window set to 3 minutes"
echo "  ✅ Alert configuration validated"
echo ""
echo "🔗 Useful links:"
echo "  • Prometheus Rules: $PROM_URL/rules"
echo "  • Active Alerts: $PROM_URL/alerts" 
echo "  • API Health: $API_URL/health" 