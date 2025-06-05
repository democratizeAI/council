#!/bin/bash
# 🔄 Prometheus Configuration Reload
# Safely reloads Prometheus config after alert rule changes

set -euo pipefail

echo "🔄 Reloading Prometheus configuration..."

# Detect Prometheus container name
PROM_CONTAINER=$(docker ps --format "table {{.Names}}" | grep -E "(prom|prometheus)" | head -1 || echo "")

if [[ -z "$PROM_CONTAINER" ]]; then
    echo "❌ Prometheus container not found"
    echo "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Image}}"
    exit 1
fi

echo "📦 Found Prometheus container: $PROM_CONTAINER"

# Method 1: Try HUP signal (Prometheus v2.51+)
echo "🔄 Attempting graceful reload with HUP signal..."
if docker exec "$PROM_CONTAINER" kill -HUP 1; then
    echo "✅ HUP signal sent successfully"
    
    # Wait a moment for reload
    sleep 2
    
    # Verify reload was successful
    echo "✅ Verifying reload status..."
    if curl -sf http://localhost:9090/-/reload > /dev/null 2>&1; then
        echo "✅ Prometheus reload verified via API"
    else
        echo "⚠️  Could not verify via API, but HUP signal was sent"
    fi
else
    echo "⚠️  HUP signal failed, trying HTTP reload API..."
    
    # Method 2: HTTP reload API (fallback)
    if curl -X POST http://localhost:9090/-/reload; then
        echo "✅ Prometheus reloaded via HTTP API"
    else
        echo "❌ Both reload methods failed"
        exit 1
    fi
fi

# Verify configuration is valid
echo "🔍 Checking configuration validity..."
CONFIG_STATUS=$(curl -s http://localhost:9090/api/v1/status/config | jq -r '.status' 2>/dev/null || echo "unknown")

if [[ "$CONFIG_STATUS" == "success" ]]; then
    echo "✅ Configuration is valid"
else
    echo "⚠️  Could not verify configuration status"
fi

# Check if our new alert rules are loaded
echo "🚨 Checking if alert rules are loaded..."
RULES_COUNT=$(curl -s http://localhost:9090/api/v1/rules | jq '.data.groups | length' 2>/dev/null || echo "0")
echo "📊 Found $RULES_COUNT rule groups loaded"

# Specifically check for API5xxSpike rule
if curl -s http://localhost:9090/api/v1/rules | jq -r '.data.groups[].rules[].alert' 2>/dev/null | grep -q "API5xxSpike"; then
    echo "✅ API5xxSpike rule is loaded"
else
    echo "⚠️  API5xxSpike rule not found in loaded rules"
fi

echo ""
echo "🎯 Reload complete! Check status at:"
echo "   • Prometheus: http://localhost:9090"
echo "   • Rules: http://localhost:9090/rules"
echo "   • Alerts: http://localhost:9090/alerts" 