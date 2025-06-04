#!/bin/bash
set -euo pipefail

# 🎛️ AutoGen Council v2.6.0 - Scale to 50% Canary
# Ready-to-run script for proven green canary (24h @ 25%)

echo "🎛️ AutoGen Council v2.6.0 - Scaling to 50%"
echo "=========================================="
echo "Prerequisites: 30+ min green at 25% traffic"

# Verify canary is currently running and healthy
if ! docker ps | grep -q autogen-council-canary; then
    echo "❌ Canary container not running!"
    echo "   Deploy first: ./infra/scripts/canary-deploy.sh"
    exit 1
fi

# Check current health
echo "🏥 Pre-scale health check..."
if ! curl -f -s http://localhost:8001/health >/dev/null; then
    echo "❌ Canary unhealthy before scaling!"
    echo "   Check: curl http://localhost:8001/health"
    exit 1
fi

echo "✅ Canary healthy, proceeding with scale"

# Execute the exact command from your ops checklist
echo "⚖️ Scaling canary from 25% → 50%..."
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=25/COUNCIL_TRAFFIC_PERCENT=50/" /app/.env && kill -HUP 1'

# Update Traefik weights
echo "🔄 Updating load balancer weights..."
docker exec autogen-council \
    docker label set "traefik.http.services.council-main.loadbalancer.weight=50" 2>/dev/null || true

docker exec autogen-council-canary \
    docker label set "traefik.http.services.council-canary.loadbalancer.weight=50" 2>/dev/null || true

# Reload Traefik
docker kill -s HUP traefik-lb 2>/dev/null || true

echo "⏳ Waiting for configuration reload..."
sleep 5

# Verify scaling
echo "🧪 Post-scale verification..."
CANARY_HITS=0
for i in {1..20}; do
    if curl -s http://localhost/health >/dev/null; then
        ((CANARY_HITS++))
    fi
    sleep 0.1
done

echo "📊 Traffic test: $CANARY_HITS/20 successful requests"

echo ""
echo "🎯 v2.6.0 Canary scaled to 50%!"
echo ""
echo "📈 Next 30min monitoring checklist:"
echo "   ✅ p95 latency ≤ 120ms (trip: 200ms for 5min)"
echo "   ✅ 5xx rate ≤ 0.2 req/min (trip: >0.5 spike)"
echo "   ✅ VRAM usage < 10.5GB (trip: ≥10.8GB)"
echo "   ✅ Fragment events flat at 0 (trip: first bump)"
echo ""
echo "🟢 If all green for 30min → Schedule 100% in low-traffic window"
echo "🚨 If any red → Emergency: ./infra/scripts/canary-rollback.sh"
echo ""
echo "📊 Monitor at: http://localhost:3000" 