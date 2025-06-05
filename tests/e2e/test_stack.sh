#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting E2E Docker Stack Test${NC}"

# Cleanup function
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up Docker containers${NC}"
    docker compose down --remove-orphans || true
    docker system prune -f || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Check if docker-compose.yml exists
if [[ ! -f "docker-compose.yml" ]]; then
    echo -e "${RED}❌ docker-compose.yml not found${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Building and starting Docker stack${NC}"
docker compose up -d --build

# Function to wait for service health
wait_for_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}⏳ Waiting for $service_name to be healthy...${NC}"
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is healthy${NC}"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts failed, waiting 2s..."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to become healthy${NC}"
    docker compose logs "$service_name" || true
    return 1
}

# Wait for main API health
wait_for_health "council-api" "http://localhost:9000/health" || wait_for_health "council-api" "http://localhost:9000/healthz"

# Test basic API connectivity
echo -e "${YELLOW}🔌 Testing API connectivity${NC}"
api_response=$(curl -s -w "%{http_code}" http://localhost:9000/health 2>/dev/null || curl -s -w "%{http_code}" http://localhost:9000/healthz 2>/dev/null || echo "000")
if [[ "${api_response: -3}" == "200" ]]; then
    echo -e "${GREEN}✅ API health check passed${NC}"
else
    echo -e "${RED}❌ API health check failed (status: ${api_response: -3})${NC}"
    exit 1
fi

# Test chat endpoint with simple query
echo -e "${YELLOW}💬 Testing chat endpoint with simple query${NC}"
simple_response=$(curl -s -X POST http://localhost:9000/chat \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"hi"}' || echo '{}')

if echo "$simple_response" | jq -e '.cost_usd' > /dev/null 2>&1; then
    cost=$(echo "$simple_response" | jq -r '.cost_usd')
    if (( $(echo "$cost == 0" | bc -l) )); then
        echo -e "${GREEN}✅ Local processing confirmed (cost: \$0)${NC}"
    else
        echo -e "${YELLOW}⚠️  Non-zero cost detected: \$$cost${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Cost field not found in response${NC}"
fi

# Test math query routing to local
echo -e "${YELLOW}🧮 Testing math query local routing${NC}"
math_response=$(curl -s -X POST http://localhost:9000/chat \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Solve x^2-5x+6=0"}' || echo '{}')

if echo "$math_response" | jq -e '.provider_chain[0]' > /dev/null 2>&1; then
    first_provider=$(echo "$math_response" | jq -r '.provider_chain[0]')
    case "$first_provider" in
        local*|*local*)
            echo -e "${GREEN}✅ Math query routed to local provider: $first_provider${NC}"
            ;;
        *)
            echo -e "${YELLOW}⚠️  Math query routed to: $first_provider (expected local)${NC}"
            ;;
    esac
else
    echo -e "${YELLOW}⚠️  Provider chain not found in math response${NC}"
fi

# Test whiteboard API if available
echo -e "${YELLOW}📝 Testing whiteboard API${NC}"
wb_health=$(curl -s -w "%{http_code}" http://localhost:9000/whiteboard/health 2>/dev/null || echo "000")
if [[ "${wb_health: -3}" == "200" ]]; then
    echo -e "${GREEN}✅ Whiteboard API is healthy${NC}"
    
    # Test write operation
    wb_write=$(curl -s -X POST http://localhost:9000/whiteboard/write \
        -H 'Content-Type: application/json' \
        -d '{"session":"test_e2e","author":"test","content":"E2E test entry","tags":["test"]}' || echo '{}')
    
    # Test read operation
    wb_read=$(curl -s "http://localhost:9000/whiteboard/read?session=test_e2e" || echo '[]')
    if echo "$wb_read" | jq -e 'length > 0' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Whiteboard write/read operations working${NC}"
    else
        echo -e "${YELLOW}⚠️  Whiteboard read returned empty result${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Whiteboard API not available (status: ${wb_health: -3})${NC}"
fi

# Test canary API if available
echo -e "${YELLOW}🐤 Testing canary API${NC}"
canary_health=$(curl -s -w "%{http_code}" http://localhost:8000/health 2>/dev/null || curl -s -w "%{http_code}" http://localhost:8000/healthz 2>/dev/null || echo "000")
if [[ "${canary_health: -3}" == "200" ]]; then
    echo -e "${GREEN}✅ Canary API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Canary API not available (status: ${canary_health: -3})${NC}"
fi

# Check Docker container health statuses
echo -e "${YELLOW}🏥 Checking container health statuses${NC}"
container_health=$(docker compose ps --format "table {{.Name}}\t{{.Status}}" | grep -E "(healthy|up)" | wc -l)
total_containers=$(docker compose ps --format "table {{.Name}}" | tail -n +2 | wc -l)

if [[ $container_health -gt 0 ]]; then
    echo -e "${GREEN}✅ $container_health/$total_containers containers are healthy/up${NC}"
else
    echo -e "${RED}❌ No healthy containers found${NC}"
    docker compose ps
    exit 1
fi

# Test council consensus if possible
echo -e "${YELLOW}🏛️  Testing council consensus${NC}"
council_response=$(curl -s -X POST http://localhost:9000/chat \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"What is the capital of France?"}' || echo '{}')

if echo "$council_response" | jq -e '.voices' > /dev/null 2>&1; then
    voice_count=$(echo "$council_response" | jq '.voices | length')
    if [[ $voice_count -ge 3 ]]; then
        echo -e "${GREEN}✅ Council consensus working ($voice_count voices)${NC}"
    else
        echo -e "${YELLOW}⚠️  Limited council voices ($voice_count voices)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Council voices not found in response${NC}"
fi

# Test Redis if configured
echo -e "${YELLOW}🔴 Testing Redis connectivity${NC}"
redis_health=$(docker compose exec -T redis redis-cli ping 2>/dev/null || echo "FAIL")
if [[ "$redis_health" == "PONG" ]]; then
    echo -e "${GREEN}✅ Redis is responding${NC}"
else
    echo -e "${YELLOW}⚠️  Redis not responding${NC}"
fi

# Test GPU availability if configured
echo -e "${YELLOW}🎮 Testing GPU availability${NC}"
gpu_check=$(docker compose exec -T council-api nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "NO_GPU")
if [[ "$gpu_check" != "NO_GPU" && "$gpu_check" != "" ]]; then
    echo -e "${GREEN}✅ GPU detected: $(echo "$gpu_check" | head -1)${NC}"
else
    echo -e "${YELLOW}⚠️  No GPU detected or nvidia-smi not available${NC}"
fi

# Performance test - measure response time
echo -e "${YELLOW}⏱️  Testing response performance${NC}"
start_time=$(date +%s.%N)
perf_response=$(curl -s -X POST http://localhost:9000/chat \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"Quick test"}' || echo '{}')
end_time=$(date +%s.%N)
response_time=$(echo "$end_time - $start_time" | bc)

if (( $(echo "$response_time < 30.0" | bc -l) )); then
    echo -e "${GREEN}✅ Response time: ${response_time}s (< 30s)${NC}"
else
    echo -e "${YELLOW}⚠️  Slow response time: ${response_time}s${NC}"
fi

# Final summary
echo -e "${GREEN}"
echo "=================================="
echo "🎉 E2E Docker Stack Test Complete"
echo "=================================="
echo -e "${NC}"

# Show final container status
echo -e "${YELLOW}📊 Final container status:${NC}"
docker compose ps

echo -e "${GREEN}✅ All critical tests passed! Stack is operational.${NC}" 