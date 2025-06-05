#!/bin/bash
set -e

echo "🧪 Ensemble Integration Test Suite"
echo "================================="

BASE_URL="${BASE_URL:-http://localhost:8000}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; exit 1; }

# Test utilities
check_status() {
    if [ $? -eq 0 ]; then
        success "$1"
    else
        error "$1 failed"
    fi
}

wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=1

    echo "Waiting for $name to be ready..."
    
    while ! curl -s "$url" > /dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            error "$name not ready after ${max_attempts} attempts"
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    success "$name is ready"
}

# 1. Service Health Checks
echo -e "\n📋 Service Health Checks"
echo "------------------------"

wait_for_service "$BASE_URL/health" "Swarm API"
wait_for_service "http://localhost:9090/-/ready" "Prometheus"

# Check Redis
redis-cli -u "$REDIS_URL" ping > /dev/null
check_status "Redis connectivity"

# 2. Ensemble API Tests
echo -e "\n🔗 Ensemble API Tests"
echo "--------------------"

# Clear any existing mappings
redis-cli -u "$REDIS_URL" DEL lora:router_map > /dev/null

# Test setting single mapping
response=$(curl -s -X POST "$BASE_URL/admin/ensemble" \
    -d "cluster_id=test_c42&adapter_tag=test-adapter-v1")
echo "$response" | jq -e '.status == "mapped"' > /dev/null
check_status "Set single mapping"

# Test bulk mappings
bulk_data='{
    "test_c10": "adapter-v1",
    "test_c20": "adapter-v2", 
    "test_c30": "adapter-v3"
}'

response=$(curl -s -X POST "$BASE_URL/admin/ensemble/bulk" \
    -H "Content-Type: application/json" \
    -d "$bulk_data")
echo "$response" | jq -e '.mappings_set == 3' > /dev/null
check_status "Set bulk mappings"

# Test retrieving mappings
response=$(curl -s "$BASE_URL/admin/ensemble")
total_clusters=$(echo "$response" | jq -r '.total_clusters')
[ "$total_clusters" = "4" ]  # 1 single + 3 bulk
check_status "Retrieve mappings (count: $total_clusters)"

# Test specific cluster lookup
response=$(curl -s "$BASE_URL/admin/ensemble/cluster/test_c42")
adapter_tag=$(echo "$response" | jq -r '.adapter_tag')
[ "$adapter_tag" = "test-adapter-v1" ]
check_status "Specific cluster lookup"

# Test mapping removal
curl -s -X DELETE "$BASE_URL/admin/ensemble/test_c42" > /dev/null
check_status "Remove mapping"

# Verify removal
response=$(curl -s "$BASE_URL/admin/ensemble/cluster/test_c42" || echo '{"error":"not found"}')
echo "$response" | jq -e '.error' > /dev/null
check_status "Verify mapping removed"

# 3. Cache Management Tests
echo -e "\n💾 Cache Management Tests"
echo "------------------------"

# Test cache stats
response=$(curl -s "$BASE_URL/admin/ensemble/stats")
cache_size=$(echo "$response" | jq -r '.cache_stats.cache_size')
[ "$cache_size" = "0" ]  # Should start empty
check_status "Initial cache empty (size: $cache_size)"

# Test cache warming (will fail gracefully if adapters don't exist)
warm_data='["adapter-v1", "adapter-v2"]'
curl -s -X POST "$BASE_URL/admin/ensemble/cache/warm" \
    -H "Content-Type: application/json" \
    -d "$warm_data" > /dev/null
check_status "Cache warm command accepted"

# Test cache clearing
curl -s -X POST "$BASE_URL/admin/ensemble/cache/clear" > /dev/null
check_status "Cache clear command"

# 4. Redis Integration Tests
echo -e "\n🗄️  Redis Integration Tests"
echo "--------------------------"

# Test cluster pattern storage
test_prompt="Write a Python function to calculate fibonacci"
prompt_hash=$(echo -n "$test_prompt" | sha1sum | cut -d' ' -f1)
cluster_key="pattern:cluster:$prompt_hash"

# Simulate pattern-miner setting cluster
redis-cli -u "$REDIS_URL" SET "$cluster_key" "test_c_programming" > /dev/null
check_status "Set cluster mapping in Redis"

# Set adapter mapping for this cluster
curl -s -X POST "$BASE_URL/admin/ensemble" \
    -d "cluster_id=test_c_programming&adapter_tag=code-specialist-v2" > /dev/null
check_status "Set adapter mapping for cluster"

# Verify end-to-end lookup
cluster_id=$(redis-cli -u "$REDIS_URL" GET "$cluster_key")
adapter_tag=$(redis-cli -u "$REDIS_URL" HGET lora:router_map "$cluster_id")
[ "$adapter_tag" = "code-specialist-v2" ]
check_status "End-to-end cluster→adapter resolution"

# 5. Metrics Validation
echo -e "\n📊 Metrics Validation"
echo "--------------------"

# Check if ensemble metrics are exposed
metrics_response=$(curl -s "$BASE_URL/metrics")

# Check for ensemble-specific metrics
echo "$metrics_response" | grep -q "ensemble_mappings_total"
check_status "ensemble_mappings_total metric exists"

echo "$metrics_response" | grep -q "ensemble_miss_total"
check_status "ensemble_miss_total metric exists"

echo "$metrics_response" | grep -q "ensemble_cache_size"
check_status "ensemble_cache_size metric exists"

# 6. Alert Rule Tests
echo -e "\n🚨 Alert Rule Tests"
echo "------------------"

# Check if Prometheus has loaded ensemble alerts
prom_rules=$(curl -s "http://localhost:9090/api/v1/rules")
echo "$prom_rules" | jq -e '.data.groups[] | select(.name == "ensemble-adapter")' > /dev/null
check_status "Ensemble alert rules loaded in Prometheus"

# Test specific alert expressions
alerts=("EnsembleMissRateHigh" "EnsembleCacheEvictionsHigh" "EnsembleAdapterLoadFailure")
for alert in "${alerts[@]}"; do
    echo "$prom_rules" | jq -e ".data.groups[] | select(.name == \"ensemble-adapter\") | .rules[] | select(.name == \"$alert\")" > /dev/null
    check_status "Alert rule: $alert"
done

# 7. Load Test Simulation
echo -e "\n🔄 Load Test Simulation"
echo "----------------------"

# Create multiple mappings for load testing
for i in {1..10}; do
    curl -s -X POST "$BASE_URL/admin/ensemble" \
        -d "cluster_id=load_test_c$i&adapter_tag=load-test-adapter-$((i % 3 + 1))" > /dev/null
done
check_status "Created 10 test mappings"

# Verify mapping distribution
response=$(curl -s "$BASE_URL/admin/ensemble/stats")
total_mappings=$(echo "$response" | jq -r '.total_mappings')
unique_adapters=$(echo "$response" | jq -r '.unique_adapters')
[ "$total_mappings" -ge "10" ]
check_status "Load test mappings created (total: $total_mappings, unique adapters: $unique_adapters)"

# 8. Error Handling Tests
echo -e "\n❌ Error Handling Tests"
echo "----------------------"

# Test invalid cluster lookup
response=$(curl -s "$BASE_URL/admin/ensemble/cluster/nonexistent_cluster" || echo '{"error":"not found"}')
echo "$response" | jq -e '.error' > /dev/null
check_status "Invalid cluster returns error"

# Test malformed bulk mapping
response=$(curl -s -X POST "$BASE_URL/admin/ensemble/bulk" \
    -H "Content-Type: application/json" \
    -d '{}' || echo '{"error":"no mappings"}')
[ $? -ne 0 ] || echo "$response" | jq -e '.error' > /dev/null
check_status "Empty bulk mapping returns error"

# 9. Cleanup
echo -e "\n🧹 Cleanup"
echo "---------"

# Remove test mappings
redis-cli -u "$REDIS_URL" DEL lora:router_map > /dev/null
redis-cli -u "$REDIS_URL" DEL "$cluster_key" > /dev/null
check_status "Cleaned up test data"

# Final stats
response=$(curl -s "$BASE_URL/admin/ensemble/stats")
total_mappings=$(echo "$response" | jq -r '.total_mappings')
[ "$total_mappings" = "0" ]
check_status "All mappings cleaned up"

echo -e "\n🎉 All ensemble integration tests passed!"
echo "========================================"
echo
echo "Next Steps:"
echo "1. Deploy LoRA adapters to /loras/ directory"
echo "2. Set production cluster→adapter mappings"
echo "3. Monitor ensemble_miss_rate < 10%"
echo "4. Measure holdout_success_ratio improvement"
echo
echo "Monitoring URLs:"
echo "  Dashboard: http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo "  Ensemble API: $BASE_URL/admin/ensemble" 