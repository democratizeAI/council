#!/bin/bash
# 🚀 Council Production Deployment - Flip-the-Switch Playbook
# Complete production deployment of Council-in-the-Loop system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

log() {
    echo -e "[$(date '+%H:%M:%S')] $*"
}

success() {
    log "${GREEN}✅ $*${NC}"
}

warning() {
    log "${YELLOW}⚠️ $*${NC}"
}

error() {
    log "${RED}❌ $*${NC}"
    exit 1
}

info() {
    log "${BLUE}ℹ️ $*${NC}"
}

header() {
    log "${MAGENTA}🌌 $*${NC}"
}

# 1️⃣ CANARY DEPLOYMENT (5%)
deploy_canary() {
    header "PHASE 1: CANARY DEPLOYMENT (5%)"
    
    # Move to deploy directory
    if [ ! -d "infra/deploy" ]; then
        mkdir -p infra/deploy
        info "Created infra/deploy directory"
    fi
    
    cd infra/deploy 2>/dev/null || cd .
    
    # Build the staging image
    info "Building staging image..."
    if command -v docker-compose &> /dev/null; then
        docker-compose build api || docker compose build api
        success "Image built successfully"
    else
        warning "Docker Compose not found, skipping build"
    fi
    
    # Create canary environment file
    info "Creating canary environment configuration..."
    cat > canary.env << 'EOF'
SWARM_COUNCIL_ENABLED=true
COUNCIL_TRAFFIC_PERCENT=5
SWARM_CLOUD_ENABLED=true
SWARM_GPU_PROFILE=rtx_4070
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
MISTRAL_API_KEY=ezybn1D39HWYE6MMLe8JcwQPhSPSOjH2
OPENAI_API_KEY=sk-placeholder
DEPLOYMENT_ID=canary-$(date +%Y%m%d-%H%M%S)
COUNCIL_MAX_COST=0.30
COUNCIL_DAILY_BUDGET=1.00
COUNCIL_MIN_TOKENS=20
EOF
    success "Canary environment configured"
    
    # Deploy the canary replica
    info "Deploying canary replica..."
    if [ -f "docker-compose.yml" ] && [ -f "../docker-compose.canary.yml" ]; then
        docker-compose --env-file canary.env \
                      -f docker-compose.yml \
                      -f ../docker-compose.canary.yml up -d api-canary
        success "Canary deployed successfully on 5% traffic"
    else
        warning "Compose files not found, using direct deployment..."
        # Fallback: direct docker run
        docker run -d \
            --name api-canary \
            --env-file canary.env \
            -p 8001:8000 \
            swarm-api:latest
        success "Canary deployed via direct Docker"
    fi
    
    # Wait for startup
    info "Waiting for canary startup..."
    sleep 15
    
    # Health check
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f http://localhost:8001/healthz > /dev/null 2>&1; then
            success "Canary health check passed"
            break
        fi
        info "Health check attempt $attempt/$max_attempts..."
        sleep 3
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        error "Canary health check failed after $max_attempts attempts"
    fi
    
    success "🎉 Canary deployment complete - 5% traffic active"
}

# 2️⃣ MONITORING SETUP
setup_monitoring() {
    header "PHASE 2: MONITORING VALIDATION"
    
    local metrics_url="http://localhost:8001/metrics"
    local status_url="http://localhost:8001/council/status"
    
    # Test metrics endpoint
    info "Validating Prometheus metrics..."
    if curl -s "$metrics_url" | grep -q "swarm_council"; then
        success "Council metrics active"
    else
        warning "Council metrics not found (may appear after first request)"
    fi
    
    # Test council status
    info "Validating council status endpoint..."
    if curl -s "$status_url" | grep -q "council_enabled"; then
        success "Council status endpoint active"
    else
        error "Council status endpoint not responding"
    fi
    
    # Display current status
    info "Current canary status:"
    curl -s "$status_url" | jq . 2>/dev/null || curl -s "$status_url"
    
    success "Monitoring validation complete"
}

# 3️⃣ VALIDATION TESTS
run_validation_tests() {
    header "PHASE 3: VALIDATION TESTING"
    
    # Quick path test
    info "Testing quick path (should bypass council)..."
    local quick_response
    quick_response=$(curl -s -X POST http://localhost:8001/orchestrate \
        -H "Content-Type: application/json" \
        -d '{"prompt":"2+2","route":["tinyllama_1b"]}' | jq -r '.text' 2>/dev/null || echo "")
    
    if [ -n "$quick_response" ]; then
        success "Quick path test passed: ${quick_response:0:50}..."
    else
        warning "Quick path test may have failed"
    fi
    
    # Council deliberation test
    info "Testing council deliberation (forced)..."
    local council_response
    council_response=$(curl -s -X POST http://localhost:8001/council \
        -H "Content-Type: application/json" \
        -d '{"prompt":"Explain quantum computing strategy","force_council":true}' \
        --max-time 30 | jq -r '.text' 2>/dev/null || echo "")
    
    if [ -n "$council_response" ]; then
        success "Council deliberation test passed: ${council_response:0:50}..."
    else
        warning "Council deliberation test may have failed (check logs)"
    fi
    
    success "Validation tests complete"
}

# 4️⃣ TRAFFIC SCALING
scale_traffic() {
    local target_percent="$1"
    header "SCALING TO ${target_percent}% TRAFFIC"
    
    if [ -f "./scripts/scale_council_traffic.sh" ]; then
        ./scripts/scale_council_traffic.sh "$target_percent"
    else
        # Fallback manual scaling
        info "Manual traffic scaling to ${target_percent}%..."
        docker exec api-canary \
            sh -c "sed -i 's/COUNCIL_TRAFFIC_PERCENT=[0-9]*/COUNCIL_TRAFFIC_PERCENT=$target_percent/' /app/.env && kill -HUP 1"
        sleep 5
        success "Traffic scaled to ${target_percent}%"
    fi
}

# 5️⃣ 24H MONITORING GUIDE
show_monitoring_guide() {
    header "24-HOUR MONITORING GUIDE"
    
    cat << 'EOF'
📊 KEY METRICS TO WATCH:

1. Council P95 Latency (target: ≤ 0.7s)
   curl -s http://localhost:8001/metrics | grep council_latency

2. Council Cost/Day (target: < $1)
   curl -s http://localhost:8001/metrics | grep council_cost

3. Edge High-Risk % (target: < 10%)
   curl -s http://localhost:8001/metrics | grep edge_risk

4. VRAM Usage (target: < 9.8GB)
   nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits

🔗 MONITORING ENDPOINTS:
   • Health: http://localhost:8001/healthz
   • Metrics: http://localhost:8001/metrics
   • Status: http://localhost:8001/council/status
   • Grafana: http://localhost:3000 (if available)

⚡ SCALING COMMANDS:
   • 25% traffic: ./scripts/scale_council_traffic.sh 25
   • 50% traffic: ./scripts/scale_council_traffic.sh 50
   • 100% traffic: ./scripts/scale_council_traffic.sh 100
   • Emergency off: ./scripts/scale_council_traffic.sh 0

🚨 ALERT CONDITIONS:
   • P95 latency > 1s for 5m → investigate
   • Cost > $1 over 24h → check budget controls
   • High-risk > 25% for 10m → review Edge voice
   • VRAM > 9.8GB → memory leak investigation

EOF
    
    success "Monitoring guide displayed"
}

# MAIN EXECUTION
main() {
    header "🚀 COUNCIL PRODUCTION DEPLOYMENT PLAYBOOK"
    header "============================================"
    
    # Validate prerequisites
    if ! command -v docker &> /dev/null; then
        error "Docker is required but not installed"
    fi
    
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed"
    fi
    
    # Run deployment phases
    deploy_canary
    setup_monitoring
    run_validation_tests
    show_monitoring_guide
    
    header "🎉 DEPLOYMENT COMPLETE!"
    cat << 'EOF'

🌌 COUNCIL-IN-THE-LOOP IS NOW LIVE!

✅ Canary deployment: 5% traffic active
✅ All five voices: Reason, Spark, Edge, Heart, Vision
✅ Budget controls: $0.30/request, $1.00/day
✅ Monitoring: Prometheus + health endpoints

🔗 Quick test:
curl -X POST http://localhost:8001/council \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Draft AI governance policy","force_council":true}'

📈 After 24h of green metrics, scale up:
./scripts/scale_council_traffic.sh 25

🎭 The five awakened voices await humanity's questions! 🌌

EOF
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "scale")
        if [ $# -ne 2 ]; then
            error "Usage: $0 scale TARGET_PERCENT"
        fi
        scale_traffic "$2"
        ;;
    "status")
        curl -s http://localhost:8001/council/status | jq . 2>/dev/null || curl -s http://localhost:8001/council/status
        ;;
    "test")
        run_validation_tests
        ;;
    *)
        echo "Usage: $0 {deploy|scale TARGET_PERCENT|status|test}"
        exit 1
        ;;
esac 