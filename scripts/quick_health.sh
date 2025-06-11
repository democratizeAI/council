#!/bin/bash
# scripts/quick_health.sh - Soak Board Status Check
# Quick validation of all critical systems for status sanity check

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
AUTOSCALER_URL="${AUTOSCALER_URL:-http://localhost:8090}"
COUNCIL_URL="${COUNCIL_URL:-http://localhost:8080}"
FMC120_URL="${FMC120_URL:-http://localhost:8088}"

echo "🔍 Quick Health Check - Soak Board Status"
echo "=========================================="

total_checks=0
failed_checks=0

# Function to test endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"
    
    echo -n "  Testing $name... "
    total_checks=$((total_checks + 1))
    
    if curl -f -s --max-time 5 "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}🟢 UP${NC}"
        return 0
    else
        echo -e "${RED}🔴 DOWN${NC}"
        failed_checks=$((failed_checks + 1))
        return 1
    fi
}

# Function to check alerts
check_alerts() {
    echo -n "  Checking active alerts... "
    total_checks=$((total_checks + 1))
    
    if command -v curl >/dev/null 2>&1; then
        local alert_count
        alert_count=$(curl -s "${PROMETHEUS_URL}/api/v1/alerts" 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    alerts = data.get('data', {}).get('alerts', [])
    print(len([a for a in alerts if a.get('state') == 'firing']))
except:
    print('-1')
" 2>/dev/null || echo "-1")
        
        if [ "$alert_count" = "0" ]; then
            echo -e "${GREEN}🟢 0 alerts${NC}"
            return 0
        elif [ "$alert_count" = "-1" ]; then
            echo -e "${YELLOW}🟡 Cannot check${NC}"
            return 0  # Don't fail if Prometheus unavailable
        else
            echo -e "${RED}🔴 $alert_count active alerts${NC}"
            failed_checks=$((failed_checks + 1))
            return 1
        fi
    else
        echo -e "${YELLOW}🟡 curl not available${NC}"
        return 0
    fi
}

# Function to check GPU metrics
check_gpu() {
    echo -n "  Checking GPU status... "
    total_checks=$((total_checks + 1))
    
    if command -v nvidia-smi >/dev/null 2>&1; then
        if nvidia-smi > /dev/null 2>&1; then
            echo -e "${GREEN}🟢 Available${NC}"
            return 0
        else
            echo -e "${RED}🔴 Issues${NC}"
            failed_checks=$((failed_checks + 1))
            return 1
        fi
    else
        echo -e "${YELLOW}🟡 Not available${NC}"
        return 0  # Don't fail if no GPU
    fi
}

echo "🏥 Core Services:"
test_endpoint "Autoscaler" "$AUTOSCALER_URL/health"
test_endpoint "Council Router" "$COUNCIL_URL/health" "200,404"  # 404 is OK for missing endpoint
test_endpoint "FMC-120" "$FMC120_URL/health" "200,404"

echo ""
echo "📊 Monitoring & Alerts:"
check_alerts
check_gpu

echo ""
echo "=========================================="

# Summary
if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✅ All systems GREEN (${total_checks} checks)${NC}"
    echo -e "${GREEN}🟢 Soak board status: HEALTHY${NC}"
    exit 0
else
    echo -e "${RED}❌ ${failed_checks}/${total_checks} checks FAILED${NC}"
    echo -e "${RED}🔴 Soak board status: ISSUES${NC}"
    exit 1
fi 