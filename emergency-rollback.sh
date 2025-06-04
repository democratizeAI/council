#!/bin/bash
set -euo pipefail

# 🚨 AutoGen Council v2.6.0 - Emergency Rollback
# Fast rollback if any monitoring dial flares

echo "🚨 EMERGENCY ROLLBACK ACTIVATED"
echo "==============================="

# Method 1: Set traffic to 0% (immediate)
echo "⚡ Setting canary traffic to 0%..."
docker exec api-canary \
  sh -c 'sed -i "s/COUNCIL_TRAFFIC_PERCENT=.*/COUNCIL_TRAFFIC_PERCENT=0/" /app/.env && kill -HUP 1'

sleep 2

# Method 2: Stop canary service (if needed)
read -p "🛑 Also stop canary container? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 Stopping canary container..."
    docker compose stop api-canary
fi

# Verify rollback
echo "🧪 Verifying main service handles 100% traffic..."
SUCCESS_COUNT=0
for i in {1..10}; do
    if curl -s http://localhost:8000/health >/dev/null; then
        ((SUCCESS_COUNT++))
    fi
    sleep 0.5
done

echo "📊 Main service handling: $SUCCESS_COUNT/10 requests"

echo ""
echo "🎯 Emergency rollback complete!"
echo ""
echo "📋 Next steps:"
echo "1. Check Grafana dashboard for root cause"
echo "2. Review logs: docker logs autogen-council-canary --since 1h"
echo "3. Investigate the failing metric"
echo "4. Fix issue and redeploy canary"
echo ""
echo "🔍 Investigation commands:"
echo "   curl http://localhost:8000/health  # Main service"
echo "   curl http://localhost:8001/health  # Canary (if still running)"
echo "   docker logs autogen-council-canary --tail 50" 