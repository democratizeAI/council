#!/bin/bash
# API Smoke Test Script (Ticket #217)
# Tests API endpoints for basic functionality

API_SERVICE=${1:-api}

if [ "$API_SERVICE" = "api" ]; then
    BASE_URL="http://localhost:8000"
    SERVICE_NAME="Main API"
elif [ "$API_SERVICE" = "api_canary" ]; then
    BASE_URL="http://localhost:8001"
    SERVICE_NAME="Canary API"
else
    echo "❌ Usage: $0 {api|api_canary}"
    exit 1
fi

echo "💨 Smoke testing $SERVICE_NAME ($BASE_URL)..."

# Health check
echo "🔍 Testing /healthz..."
HEALTH_RESPONSE=$(curl -s -w "%{http_code}" $BASE_URL/healthz)
HTTP_CODE="${HEALTH_RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Health check passed"
else
    echo "  ❌ Health check failed: $HTTP_CODE"
    exit 1
fi

# Basic orchestration
echo "🎯 Testing /orchestrate..."
ORCH_RESPONSE=$(curl -s -w "%{http_code}" -X POST $BASE_URL/orchestrate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "smoke test", "flags": [], "temperature": 0.7}')
HTTP_CODE="${ORCH_RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Orchestration passed"
else
    echo "  ❌ Orchestration failed: $HTTP_CODE"
    exit 1
fi

# Metrics endpoint
echo "📊 Testing /metrics..."
METRICS_RESPONSE=$(curl -s -w "%{http_code}" $BASE_URL/metrics)
HTTP_CODE="${METRICS_RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Metrics endpoint passed"
else
    echo "  ❌ Metrics endpoint failed: $HTTP_CODE"
    exit 1
fi

# Admin reload
echo "🔄 Testing /admin/reload..."
RELOAD_RESPONSE=$(curl -s -w "%{http_code}" -X POST "$BASE_URL/admin/reload?lora=models/smoke_test.bin")
HTTP_CODE="${RELOAD_RESPONSE: -3}"
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✅ Admin reload passed"
else
    echo "  ❌ Admin reload failed: $HTTP_CODE"
    exit 1
fi

echo "✅ $SERVICE_NAME smoke test completed successfully" 