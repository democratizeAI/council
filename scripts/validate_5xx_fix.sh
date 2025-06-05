#!/bin/bash
# 🎯 Ticket #222 - Final Validation
# Confirms the 5xx noise-window fix is correctly applied

set -euo pipefail

echo "🎯 Validating Ticket #222 - 5xx Noise-Window Fix"
echo "=================================================="

# Check if API5xxSpike rule exists
echo "🔍 1. Checking API5xxSpike rule exists..."
RULE_EXISTS=$(curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[].rules[] | select(.name == "API5xxSpike")' | jq -r '.name' 2>/dev/null || echo "")

if [[ "$RULE_EXISTS" == "API5xxSpike" ]]; then
    echo "✅ API5xxSpike rule found"
else
    echo "❌ API5xxSpike rule not found"
    exit 1
fi

# Check the 'for' duration (noise window)
echo "🔍 2. Checking noise window duration..."
DURATION=$(curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[].rules[] | select(.name == "API5xxSpike").duration' 2>/dev/null || echo "0")

if [[ "$DURATION" == "180" ]]; then
    echo "✅ Noise window correctly set to 180 seconds (3 minutes)"
else
    echo "❌ Noise window incorrect: ${DURATION}s (expected 180s)"
    exit 1
fi

# Check expression
echo "🔍 3. Checking alert expression..."
EXPR=$(curl -s "http://localhost:9090/api/v1/rules" | jq -r '.data.groups[].rules[] | select(.name == "API5xxSpike").query' 2>/dev/null || echo "")

if [[ "$EXPR" == "increase(swarm_api_5xx_total[2m]) > 5" ]]; then
    echo "✅ Alert expression correct: $EXPR"
else
    echo "❌ Alert expression incorrect: $EXPR"
    exit 1
fi

# Check alert state
echo "🔍 4. Checking alert state..."
STATE=$(curl -s "http://localhost:9090/api/v1/rules" | jq -r '.data.groups[].rules[] | select(.name == "API5xxSpike").state' 2>/dev/null || echo "")

if [[ "$STATE" == "inactive" ]]; then
    echo "✅ Alert currently inactive (no 5xx spike)"
elif [[ "$STATE" == "pending" ]]; then
    echo "⚠️  Alert pending (5xx spike detected, waiting for noise window)"
elif [[ "$STATE" == "firing" ]]; then
    echo "🚨 Alert firing (5xx spike exceeded noise window)"
else
    echo "❓ Alert state unknown: $STATE"
fi

# Show full rule configuration
echo ""
echo "📋 Complete API5xxSpike rule configuration:"
curl -s "http://localhost:9090/api/v1/rules" | jq '.data.groups[].rules[] | select(.name == "API5xxSpike")' | jq '{
    name: .name,
    expression: .query,
    duration: .duration,
    state: .state,
    labels: .labels,
    annotations: .annotations
}'

echo ""
echo "🎯 Ticket #222 Validation Results:"
echo "=================================="
echo "✅ sed patch: Applied correctly"
echo "✅ for: 3m: Noise window properly set"
echo "✅ Prom reload: Configuration loaded successfully"
echo "✅ Done-check: API5xxSpike rule active in Prometheus"
echo ""
echo "🚀 5xx noise-window fix successfully implemented!"
echo ""
echo "📊 Monitor at: http://localhost:9090/alerts" 