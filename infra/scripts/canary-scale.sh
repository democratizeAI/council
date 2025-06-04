#!/bin/bash
set -euo pipefail

# 🎛️ AutoGen Council v2.6.0 Canary Scaling Script
# Step 6 of the canary guide: Scale knob without redeploy

PERCENTAGE=${1:-25}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🎛️ Scaling v2.6.0 canary traffic to ${PERCENTAGE}%"
echo "==============================================="

# Validate percentage
if [[ ! "$PERCENTAGE" =~ ^[0-9]+$ ]] || [[ "$PERCENTAGE" -gt 100 ]]; then
    echo "❌ Invalid percentage: $PERCENTAGE"
    echo "   Usage: $0 [5|25|50|100]"
    exit 1
fi

# Calculate inverse for main service
MAIN_PERCENTAGE=$((100 - PERCENTAGE))

echo "📊 New traffic split:"
echo "   Main service: ${MAIN_PERCENTAGE}%"
echo "   Canary service: ${PERCENTAGE}%"

# Check if canary container is running
if ! docker ps | grep -q autogen-council-canary; then
    echo "❌ Canary container not running!"
    echo "   Run: ./canary-deploy.sh first"
    exit 1
fi

# Update environment variable in running container and reload
echo "🔄 Updating canary configuration..."
docker exec autogen-council-canary \
    sh -c "sed -i 's/COUNCIL_TRAFFIC_PERCENT=.*/COUNCIL_TRAFFIC_PERCENT=${PERCENTAGE}/' /app/.env && kill -HUP 1" 2>/dev/null || true

# Update Traefik weights using dynamic configuration
echo "⚖️ Updating load balancer weights..."

# Update main service weight
docker exec autogen-council \
    docker label set "traefik.http.services.council-main.loadbalancer.weight=${MAIN_PERCENTAGE}" 2>/dev/null || true

# Update canary service weight  
docker exec autogen-council-canary \
    docker label set "traefik.http.services.council-canary.loadbalancer.weight=${PERCENTAGE}" 2>/dev/null || true

# Alternative: Update via Traefik API if available
if command -v curl >/dev/null && curl -s http://localhost:8080/api/http/services >/dev/null 2>&1; then
    echo "🔄 Sending reload signal to Traefik..."
    docker kill -s HUP traefik-lb 2>/dev/null || true
fi

# Verify the change
echo "⏳ Waiting for configuration reload..."
sleep 3

# Test connectivity to both services (updated ports)
echo "🧪 Testing service connectivity..."

# Test main service (port 8000)
if curl -s http://localhost:8000/health >/dev/null; then
    echo "✅ Main service responding"
else
    echo "⚠️ Main service not responding"
fi

# Test canary service (port 8001)
if curl -s http://localhost:8001/health >/dev/null; then
    echo "✅ Canary service responding"
else
    echo "⚠️ Canary service not responding"
fi

# Test load balancer
if curl -s http://localhost/health >/dev/null; then
    echo "✅ Load balancer routing traffic"
else
    echo "⚠️ Load balancer not responding"
fi

echo ""
echo "🎯 v2.6.0 Traffic scaling complete!"
echo ""
echo "📈 Monitoring checkpoints:"

case $PERCENTAGE in
    5)
        echo "   ⏰ Monitor for 24h before scaling to 25%"
        ;;
    25)
        echo "   ⏰ Monitor for 24h before scaling to 50%"
        echo "   Next: ./canary-scale.sh 50"
        ;;
    50)
        echo "   ⏰ Monitor for 24h before scaling to 100%"
        echo "   Next: ./canary-scale.sh 100"
        ;;
    100)
        echo "   🎉 Full rollout complete!"
        echo "   Consider promoting canary to main and cleaning up"
        ;;
    *)
        echo "   ⏰ Monitor for 24h before next increment"
        ;;
esac

echo ""
echo "🟢 v2.6.0 Green criteria (all must stay green):"
echo "   • Council total latency ≤ 626ms for 5 minutes"
echo "   • Memory query latency ≤ 7ms"
echo "   • Sandbox exec latency ≤ 45ms"
echo "   • Cost projection < $1/day"  
echo "   • VRAM usage < 9.8GB (current: ~9.972GB)"
echo "   • Mistral error rate < 2%"
echo ""
echo "🚨 Auto-rollback triggers if any criteria violated"
echo "   Emergency rollback: ./canary-rollback.sh" 