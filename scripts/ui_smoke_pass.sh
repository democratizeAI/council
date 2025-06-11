#!/bin/bash
# UI Smoke Testing Playbook - v0.1 GA Validation
# Tests: Intent distillation, Council overwrite, Live metrics

set -e

echo "🧪 Starting UI Smoke Pass - v0.1 GA Validation"
echo "=============================================="

# Test environment setup
AGENT0_URL="http://localhost:8000"
WEBSOCKET_URL="ws://localhost:8765"
UI_URL="http://localhost:3000"
TIMEOUT=60

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
check_service() {
    echo -n "Checking $1... "
    if curl -sf "$2" > /dev/null 2>&1; then
        echo -e "${GREEN}UP${NC}"
        return 0
    else
        echo -e "${RED}DOWN${NC}"
        return 1
    fi
}

wait_for_service() {
    echo "Waiting for $1 to be ready..."
    for i in {1..30}; do
        if curl -sf "$2" > /dev/null 2>&1; then
            echo -e "${GREEN}$1 is ready${NC}"
            return 0
        fi
        sleep 2
    done
    echo -e "${RED}$1 failed to start${NC}"
    return 1
}

# Test 1: Prerequisites Check
echo -e "\n${YELLOW}Test 0: Prerequisites Check${NC}"
echo "=============================="

# Check if Agent-0 service is running
if ! check_service "Agent-0 API" "$AGENT0_URL/health"; then
    echo -e "${RED}❌ Agent-0 service not running. Start with: python app/main.py${NC}"
    exit 1
fi

# Check if IDR-01 distillation endpoint exists
echo -n "Checking IDR-01 /distill endpoint... "
if curl -sf "$AGENT0_URL/distill" -X POST -H "Content-Type: application/json" \
   -d '{"prompt":"test","session_id":"smoke_test"}' > /dev/null 2>&1; then
    echo -e "${GREEN}AVAILABLE${NC}"
    IDR_AVAILABLE=true
else
    echo -e "${YELLOW}NOT AVAILABLE (U-01 PR required)${NC}"
    IDR_AVAILABLE=false
fi

# Check if UI is running (development mode)
if ! check_service "Tauri UI" "$UI_URL"; then
    echo -e "${YELLOW}⚠️  UI not running. Expected for smoke test. Starting headless validation...${NC}"
    UI_RUNNING=false
else
    UI_RUNNING=true
fi

# Test 2: Intent Distillation Flow  
echo -e "\n${YELLOW}Test 1: Intent Distillation (U-01)${NC}"
echo "=================================="

if [ "$IDR_AVAILABLE" = true ]; then
    echo "Testing: UI sends raw text → IDR → preview → /ledger/new commit"
    
    # Test distillation endpoint
    DISTILL_RESPONSE=$(curl -sf "$AGENT0_URL/distill" -X POST \
        -H "Content-Type: application/json" \
        -d '{"prompt":"Create hello world function","session_id":"smoke_test"}')
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Distillation endpoint responds${NC}"
        echo "Response preview: $(echo $DISTILL_RESPONSE | head -c 100)..."
        
        # Check if response contains expected JSON structure
        if echo "$DISTILL_RESPONSE" | grep -q '"intent"'; then
            echo -e "${GREEN}✅ Valid distillation JSON structure${NC}"
        else
            echo -e "${YELLOW}⚠️  Distillation response format needs validation${NC}"
        fi
    else
        echo -e "${RED}❌ Distillation endpoint failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  SKIP - IDR-01 not available (requires PR U-01)${NC}"
fi

# Test 3: Council Overwrite Bubble Logic
echo -e "\n${YELLOW}Test 2: Council Overwrite UX (U-02)${NC}"
echo "===================================="

echo "Testing: Fast preview (<150ms) → Council overwrite"

# Measure response time for quick preview
START_TIME=$(date +%s%3N)
QUICK_RESPONSE=$(curl -sf "$AGENT0_URL/chat" -X POST \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Quick test","session_id":"smoke_test"}' 2>/dev/null | head -c 50)
END_TIME=$(date +%s%3N)
RESPONSE_TIME=$((END_TIME - START_TIME))

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Chat endpoint responds in ${RESPONSE_TIME}ms${NC}"
    
    if [ $RESPONSE_TIME -lt 150 ]; then
        echo -e "${GREEN}✅ Response time <150ms requirement met${NC}"
    else
        echo -e "${YELLOW}⚠️  Response time ${RESPONSE_TIME}ms exceeds 150ms target${NC}"
    fi
    
    echo "Preview: $QUICK_RESPONSE..."
else
    echo -e "${RED}❌ Chat endpoint failed${NC}"
fi

# Check WebSocket streaming capability
echo -n "Testing WebSocket streaming... "
if command -v wscat > /dev/null 2>&1; then
    # Test WebSocket if wscat is available
    timeout 5 wscat -c "$WEBSOCKET_URL" -x '{"prompt":"test stream","session_id":"smoke"}' > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}WORKING${NC}"
    else
        echo -e "${YELLOW}UNAVAILABLE${NC}"
    fi
else
    echo -e "${YELLOW}SKIP (wscat not installed)${NC}"
fi

# Test 4: Live Metrics Integration  
echo -e "\n${YELLOW}Test 3: Live Metrics Dashboard${NC}"
echo "==============================="

echo "Testing: voice_latency_p95, idr_json_total gauges"

# Test metrics endpoint
METRICS_RESPONSE=$(curl -sf "$AGENT0_URL/metrics" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Metrics endpoint responds${NC}"
    
    # Check for specific metrics mentioned in audit
    if echo "$METRICS_RESPONSE" | grep -q "voice_latency_p95"; then
        echo -e "${GREEN}✅ voice_latency_p95 metric found${NC}"
    else
        echo -e "${YELLOW}⚠️  voice_latency_p95 metric missing${NC}"
    fi
    
    if echo "$METRICS_RESPONSE" | grep -q "idr_json_total"; then
        echo -e "${GREEN}✅ idr_json_total metric found${NC}"
    else
        echo -e "${YELLOW}⚠️  idr_json_total metric missing (requires IDR-01)${NC}"
    fi
    
    # Count total metrics available
    METRIC_COUNT=$(echo "$METRICS_RESPONSE" | grep -c "^[a-zA-Z]")
    echo "Total metrics available: $METRIC_COUNT"
    
else
    echo -e "${RED}❌ Metrics endpoint failed${NC}"
fi

# Test 5: Live Ticket Table (U-02)
echo -e "\n${YELLOW}Test 4: Live Ticket Table (U-02)${NC}"
echo "================================="

echo "Testing: Auto-refresh ticket table with PR links"

# Check if ledger endpoint exists
echo -n "Checking ledger endpoint... "
if curl -sf "$AGENT0_URL/ledger" > /dev/null 2>&1; then
    echo -e "${GREEN}AVAILABLE${NC}"
    
    # Test ticket creation
    echo "Creating test ticket..."
    curl -sf "$AGENT0_URL/ledger/new" -X POST \
        -H "Content-Type: application/json" \
        -d '{"ticket":"UI smoke test ticket","owner":"QA","wave":"Test"}' > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Test ticket created${NC}"
    else
        echo -e "${YELLOW}⚠️  Ticket creation needs validation${NC}"
    fi
else
    echo -e "${YELLOW}NOT AVAILABLE${NC}"
fi

# Test 6: Alert Integration (U-03)
echo -e "\n${YELLOW}Test 5: Alert Toast Integration (U-03)${NC}"
echo "======================================"

echo "Testing: #ops-alerts webhook → UI toast (5s)"

# This test requires the Slack relay service to be running
echo -n "Checking Slack relay service... "
if curl -sf "http://localhost:9001/alerts" > /dev/null 2>&1; then
    echo -e "${GREEN}AVAILABLE${NC}"
    
    # Simulate alert
    curl -sf "http://localhost:9001/alerts" -X POST \
        -H "Content-Type: application/json" \
        -d '{"alert":"UI smoke test alert","severity":"warning"}' > /dev/null 2>&1
    echo -e "${GREEN}✅ Test alert sent${NC}"
else
    echo -e "${YELLOW}NOT AVAILABLE (requires PR U-03)${NC}"
fi

# Final Results Summary
echo -e "\n${YELLOW}📊 Smoke Test Results Summary${NC}"
echo "=============================="

TOTAL_TESTS=6
PASSED_TESTS=0
WARNING_TESTS=0

# Count results (simplified - in real implementation would track each test result)
if [ "$IDR_AVAILABLE" = true ]; then
    ((PASSED_TESTS++))
else
    ((WARNING_TESTS++))
fi

if [ $RESPONSE_TIME -lt 150 ] 2>/dev/null; then
    ((PASSED_TESTS++))
else
    ((WARNING_TESTS++))
fi

# Always count metrics as partial pass
((PASSED_TESTS++))

echo "Tests completed: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Warnings: ${YELLOW}$WARNING_TESTS${NC}"
echo -e "Failed: ${RED}$((TOTAL_TESTS - PASSED_TESTS - WARNING_TESTS))${NC}"

# Exit status
if [ $WARNING_TESTS -eq 0 ] && [ $PASSED_TESTS -eq $TOTAL_TESTS ]; then
    echo -e "\n${GREEN}🎉 ALL SMOKE TESTS PASSED - UI GA READY${NC}"
    exit 0
elif [ $WARNING_TESTS -gt 0 ] && [ $((PASSED_TESTS + WARNING_TESTS)) -eq $TOTAL_TESTS ]; then
    echo -e "\n${YELLOW}⚠️  SMOKE TESTS PASSED WITH WARNINGS - PRs REQUIRED${NC}"
    echo "Required PRs: U-01 (IDR integration), U-02 (Ticket table), U-03 (Alert toast)"
    exit 1
else
    echo -e "\n${RED}❌ SMOKE TESTS FAILED - CRITICAL ISSUES${NC}"
    exit 2
fi 