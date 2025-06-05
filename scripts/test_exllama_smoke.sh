#!/usr/bin/env bash
# Week 2-1: ExLlama V2 Smoke Test
set -e

echo "🧪 Week 2-1: Testing ExLlama V2 Implementation..."

# 1. Cold restart API container  
echo "🔄 Restarting API container..."
docker compose restart council-api
sleep 30  # Give ExLlama V2 time to load model

# 2. Check model loading in logs
echo "📋 Checking model loading..."
if docker compose logs council-api | tail -20 | grep -i "loaded.*tinyllama" | grep -i "exllama"; then
    echo "✅ ExLlama V2 model loaded successfully"
else
    echo "⚠️ ExLlama V2 loading not confirmed in logs"
    echo "Recent logs:"
    docker compose logs council-api | tail -10
fi

# 3. Test latency with math query
echo "⚡ Testing latency with math query..."
RESPONSE=$(curl -s -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"What is 13*17?"}' | jq -r '.latency_ms // "unknown"')

if [ "$RESPONSE" != "unknown" ] && [ "$RESPONSE" != "null" ]; then
    echo "📊 Latency: ${RESPONSE}ms"
    
    # Check against targets
    if (( $(echo "$RESPONSE < 280" | bc -l) )); then
        echo "✅ Latency target met (< 280ms for GTX 1080)"
    elif (( $(echo "$RESPONSE < 120" | bc -l) )); then
        echo "🚀 Excellent latency (< 120ms for RTX 4070)"
    else
        echo "⚠️ Latency higher than expected (target: <280ms)"
    fi
else
    echo "❌ Could not measure latency"
fi

# 4. Test confidence with Week 1 stub filtering
echo "🛡️ Testing Week 1 stub filtering still works..."
STUB_RESPONSE=$(curl -s -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message":"TODO: implement this function"}' | jq -r '.confidence // 0')

if (( $(echo "$STUB_RESPONSE == 0" | bc -l) )); then
    echo "✅ Stub filtering active (confidence = 0.0)"
else
    echo "⚠️ Stub filtering may not be working (confidence = $STUB_RESPONSE)"
fi

# 5. Health check
echo "❤️ Final health check..."
HEALTH=$(curl -s http://localhost:8000/health | jq -r '.status // "unknown"')

if [ "$HEALTH" = "healthy" ]; then
    echo "✅ API health: $HEALTH"
else
    echo "❌ API health check failed: $HEALTH"
fi

echo ""
echo "🎯 Week 2-1 ExLlama V2 Smoke Test Complete!"
echo "📊 Expected improvements:"
echo "   • VRAM usage: ~785MB (down from 1010MB)"
echo "   • Latency: ~280ms GTX1080 / ~120ms RTX4070"
echo "   • Provider: exllama2 (upgraded from transformers)" 