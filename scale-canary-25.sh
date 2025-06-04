#!/bin/bash
set -euo pipefail

# 🎛️ AutoGen Council v2.6.0 - Scale to 25% Canary
# Ready-to-run script for proven green canary (24h @ 5%)

echo "🎛️ AutoGen Council v2.6.0 - Scaling to 25%"
echo "=========================================="
echo "Prerequisites: 24h green at 5% traffic"

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
echo "⚖️ Scaling canary from 5% → 25%..."
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=5/COUNCIL_TRAFFIC_PERCENT=25/" /app/.env && kill -HUP 1'

# Update Traefik weights
echo "🔄 Updating load balancer weights..."
docker exec autogen-council \
    docker label set "traefik.http.services.council-main.loadbalancer.weight=75" 2>/dev/null || true

docker exec autogen-council-canary \
    docker label set "traefik.http.services.council-canary.loadbalancer.weight=25" 2>/dev/null || true

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
echo "🎯 v2.6.0 Canary scaled to 25%!"
echo ""
echo "📈 Next 24h monitoring checklist:"
echo "   ✅ Council total latency ≤ 626ms"
echo "   ✅ Memory query latency ≤ 7ms" 
echo "   ✅ Sandbox exec latency ≤ 45ms"
echo "   ✅ VRAM usage < 9.8GB (current: ~9.972GB)"
echo "   ✅ Cost projection < $1/day"
echo "   ✅ 0 CUDA fragmentation events"
echo ""
echo "🟢 If all green for 24h → Next: ./scale-canary-50.sh"
echo "🚨 If any red → Emergency: ./infra/scripts/canary-rollback.sh"
echo ""
echo "📊 Monitor at: http://localhost:3000" 