#!/bin/bash
# scripts/health-check.sh - SWS-Core Health Check
# ===============================================
# 
# Docker health check script for SWS-Core platform
# Tests all critical endpoints and services

set -e

# Configuration
API_HOST="localhost"
API_PORT="8080"
TIMEOUT="10"

# Health check endpoints
HEALTH_ENDPOINTS=(
    "/health"
    "/a2a/map"
    "/platform/status" 
    "/metrics"
)

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to test HTTP endpoint
test_endpoint() {
    local endpoint=$1
    local url="http://${API_HOST}:${API_PORT}${endpoint}"
    
    if curl -f -s --max-time $TIMEOUT "$url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to test Redis connectivity
test_redis() {
    python3 -c "
import redis
import os
import sys

redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
try:
    r = redis.from_url(redis_url, socket_timeout=5)
    r.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null
}

# Main health check
main() {
    local failed=0
    local total=0
    
    echo "🏥 SWS-Core Health Check"
    echo "========================"
    
    # Test main health endpoint first
    echo -n "Testing main health endpoint... "
    if test_endpoint "/health"; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        failed=$((failed + 1))
    fi
    total=$((total + 1))
    
    # Test Redis connectivity
    echo -n "Testing Redis connectivity... "
    if test_redis; then
        echo -e "${GREEN}✅ PASS${NC}"
    else
        echo -e "${RED}❌ FAIL${NC}"
        failed=$((failed + 1))
    fi
    total=$((total + 1))
    
    # Test SWS endpoints
    for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
        if [ "$endpoint" != "/health" ]; then  # Skip main health (already tested)
            echo -n "Testing $endpoint... "
            if test_endpoint "$endpoint"; then
                echo -e "${GREEN}✅ PASS${NC}"
            else
                echo -e "${YELLOW}⚠️  WARN${NC}"
                # Don't fail for non-critical endpoints
            fi
            total=$((total + 1))
        fi
    done
    
    # Summary
    echo "========================"
    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}✅ Health check PASSED${NC} (${total} tests)"
        exit 0
    else
        echo -e "${RED}❌ Health check FAILED${NC} (${failed}/${total} failed)"
        exit 1
    fi
}

# Run health check
main "$@" 