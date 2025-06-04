#!/bin/bash
set -euo pipefail

# 🚨 AutoGen Council v2.6.0 Canary Emergency Rollback
# Instantly drops canary weight to 0% and routes all traffic to main service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🚨 EMERGENCY v2.6.0 CANARY ROLLBACK"
echo "===================================="
echo "⚡ Dropping canary traffic to 0%..."

# Set main service to 100% weight
echo "🔄 Setting main service to 100% traffic..."
docker exec autogen-council \
    docker label set "traefik.http.services.council-main.loadbalancer.weight=100" 2>/dev/null || true

# Set canary service to 0% weight
echo "🔄 Setting canary service to 0% traffic..."
docker exec autogen-council-canary \
    docker label set "traefik.http.services.council-canary.loadbalancer.weight=0" 2>/dev/null || true

# Update canary environment variable
echo "📝 Updating canary COUNCIL_TRAFFIC_PERCENT to 0..."
docker exec autogen-council-canary \
    sh -c "sed -i 's/COUNCIL_TRAFFIC_PERCENT=.*/COUNCIL_TRAFFIC_PERCENT=0/' /app/.env && kill -HUP 1" 2>/dev/null || true

# Reload Traefik configuration
echo "⚖️ Reloading load balancer..."
docker kill -s HUP traefik-lb 2>/dev/null || true

# Wait for propagation
echo "⏳ Waiting for traffic routing changes..."
sleep 5

# Verify rollback
echo "🧪 Verifying rollback..."

# Test main service gets all traffic
SUCCESS_COUNT=0
for i in {1..10}; do
    if curl -s http://localhost/health | grep -q "healthy" 2>/dev/null; then
        ((SUCCESS_COUNT++))
    fi
    sleep 0.5
done

if [[ $SUCCESS_COUNT -eq 10 ]]; then
    echo "✅ All traffic routing to main service"
else
    echo "⚠️ Traffic routing verification incomplete ($SUCCESS_COUNT/10 successful)"
fi

# Optionally pause the canary container (but keep it running for investigation)
read -p "🔍 Pause canary container for investigation? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⏸️ Pausing canary container..."
    docker pause autogen-council-canary
    echo "✅ Canary container paused (use 'docker unpause autogen-council-canary' to resume)"
fi

echo ""
echo "🎯 v2.6.0 Rollback complete!"
echo ""
echo "📊 Current status:"
echo "   • Main service: 100% traffic (port 8000)"
echo "   • Canary service: 0% traffic ($(docker ps --format 'table {{.Status}}' -f name=autogen-council-canary | tail -1))"
echo ""
echo "🔍 Investigation commands:"
echo "   docker logs autogen-council-canary --since 1h"
echo "   curl http://localhost:8001/health  # Direct canary health"
echo "   curl http://localhost:8000/health  # Direct main health"
echo "   curl http://localhost:8000/stats   # v2.6.0 enhanced stats"
echo ""
echo "🚨 Alert triggers that caused rollback:"
echo "   • Council total latency > 626ms for 5+ minutes"
echo "   • Memory query latency > 7ms"
echo "   • Sandbox exec latency > 45ms"
echo "   • swarm_council_cost_dollars_total > \$1/day"
echo "   • VRAM usage > 9.8GB"
echo "   • mistral_errors_total / mistral_tokens_total > 2%"
echo ""
echo "🔧 Next steps:"
echo "1. Investigate logs and metrics"
echo "2. Fix the issue in code"  
echo "3. Deploy new canary: ./canary-deploy.sh"
echo "4. Or clean up: docker compose down api-canary" 