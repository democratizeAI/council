#!/bin/bash
# SciWave Triple Agent Swarm Deployment Script
# 🌊 Deploy and manage the SciWave research system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.sciwave.yml"
PROJECT_NAME="sciwave"
HEALTH_TIMEOUT=120

echo -e "${BLUE}🌊 SciWave Triple Agent Swarm Deployment${NC}"
echo "================================================="

# Function to log messages
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log "Docker is running ✓"
}

# Function to check if Docker Compose is available
check_compose() {
    if ! command -v docker-compose > /dev/null 2>&1; then
        error "docker-compose is not installed. Please install it and try again."
        exit 1
    fi
    log "Docker Compose is available ✓"
}

# Function to create necessary directories
create_directories() {
    log "Creating data directories..."
    
    mkdir -p data/sciwave/{papers,summaries,reviews,metrics}
    mkdir -p config/sciwave/grafana
    mkdir -p logs
    
    # Set permissions
    chmod 755 data/sciwave
    chmod 755 logs
    
    log "Directories created ✓"
}

# Function to check if required files exist
check_requirements() {
    log "Checking requirements..."
    
    required_files=(
        "$COMPOSE_FILE"
        "Dockerfile.sciwave"
        "agents/sciwave/__init__.py"
        "agents/sciwave/fetch_agent.py"
        "agents/sciwave/review_agent.py"
        "agents/sciwave/peer_agent.py"
        "agents/sciwave/swarm_coordinator.py"
        "services/sciwave/sciwave_service.py"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            error "Required file not found: $file"
            exit 1
        fi
    done
    
    log "All required files present ✓"
}

# Function to build Docker images
build_images() {
    log "Building SciWave Docker images..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build --no-cache
    
    if [ $? -eq 0 ]; then
        log "Docker images built successfully ✓"
    else
        error "Failed to build Docker images"
        exit 1
    fi
}

# Function to start services
start_services() {
    log "Starting SciWave services..."
    
    # Start Redis first
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d sciwave-redis redis
    sleep 10
    
    # Start main services
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d
    
    if [ $? -eq 0 ]; then
        log "Services started successfully ✓"
    else
        error "Failed to start services"
        exit 1
    fi
}

# Function to wait for health checks
wait_for_health() {
    log "Waiting for services to become healthy..."
    
    local timeout=$HEALTH_TIMEOUT
    local elapsed=0
    
    while [ $elapsed -lt $timeout ]; do
        # Check main SciWave service
        if curl -f http://localhost:8080/health > /dev/null 2>&1; then
            log "SciWave service is healthy ✓"
            return 0
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    
    warn "Health check timeout reached"
    return 1
}

# Function to show status
show_status() {
    echo ""
    log "SciWave Service Status:"
    echo "======================="
    
    # Service URLs
    echo -e "${BLUE}SciWave API:${NC}        http://localhost:8080"
    echo -e "${BLUE}Health Check:${NC}       http://localhost:8080/health"
    echo -e "${BLUE}Metrics:${NC}            http://localhost:8080/metrics"
    echo -e "${BLUE}Prometheus:${NC}         http://localhost:9091"
    echo -e "${BLUE}Grafana:${NC}            http://localhost:3001 (admin/sciwave123)"
    echo ""
    
    # Container status
    echo -e "${BLUE}Container Status:${NC}"
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    echo ""
    
    # Quick health check
    if curl -f http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ SciWave is healthy and ready${NC}"
    else
        echo -e "${RED}✗ SciWave health check failed${NC}"
    fi
}

# Function to run tests
run_tests() {
    log "Running SciWave tests..."
    
    # Test individual agents
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" exec sciwave python -c "
import asyncio
from agents.sciwave.fetch_agent import test_fetch_agent
from agents.sciwave.review_agent import test_review_agent
from agents.sciwave.peer_agent import test_peer_agent

async def run_all_tests():
    print('🔬 Testing Fetch Agent...')
    await test_fetch_agent()
    
    print('🧠 Testing Review Agent...')
    await test_review_agent()
    
    print('👥 Testing Peer Agent...')
    await test_peer_agent()
    
    print('✅ All tests completed')

asyncio.run(run_all_tests())
"
}

# Function to stop services
stop_services() {
    log "Stopping SciWave services..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    
    if [ $? -eq 0 ]; then
        log "Services stopped successfully ✓"
    else
        warn "Some services may not have stopped cleanly"
    fi
}

# Function to cleanup
cleanup() {
    log "Cleaning up SciWave deployment..."
    
    docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans
    docker system prune -f
    
    log "Cleanup completed ✓"
}

# Function to show logs
show_logs() {
    local service=${1:-""}
    
    if [ -n "$service" ]; then
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "$service"
    else
        docker-compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
    fi
}

# Function to trigger manual cycle
trigger_cycle() {
    log "Triggering manual SciWave cycle..."
    
    if curl -f -X POST http://localhost:8080/cycle > /dev/null 2>&1; then
        log "Cycle triggered successfully ✓"
        log "Monitor progress at: http://localhost:8080/status"
    else
        error "Failed to trigger cycle"
        exit 1
    fi
}

# Main deployment function
deploy() {
    log "Starting SciWave deployment..."
    
    check_docker
    check_compose
    check_requirements
    create_directories
    build_images
    start_services
    
    if wait_for_health; then
        show_status
        log "🎉 SciWave deployment completed successfully!"
        echo ""
        echo -e "${GREEN}Next steps:${NC}"
        echo "1. Visit http://localhost:8080/health to verify status"
        echo "2. View metrics at http://localhost:9091 (Prometheus)"
        echo "3. Access dashboards at http://localhost:3001 (Grafana)"
        echo "4. Trigger a manual cycle: $0 cycle"
        echo "5. View logs: $0 logs"
    else
        error "Deployment completed but health checks failed"
        show_status
        exit 1
    fi
}

# Command line interface
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    start)
        start_services
        show_status
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 5
        start_services
        show_status
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    test)
        run_tests
        ;;
    cycle)
        trigger_cycle
        ;;
    cleanup)
        cleanup
        ;;
    health)
        if curl -f http://localhost:8080/health 2>/dev/null; then
            echo -e "${GREEN}✓ SciWave is healthy${NC}"
            curl -s http://localhost:8080/health | python -m json.tool
        else
            echo -e "${RED}✗ SciWave is not healthy${NC}"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|status|logs|test|cycle|cleanup|health}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  start    - Start services"
        echo "  stop     - Stop services"
        echo "  restart  - Restart services"
        echo "  status   - Show service status"
        echo "  logs     - Show logs (optionally specify service)"
        echo "  test     - Run integration tests"
        echo "  cycle    - Trigger manual research cycle"
        echo "  cleanup  - Clean up all resources"
        echo "  health   - Check service health"
        echo ""
        echo "Examples:"
        echo "  $0 deploy"
        echo "  $0 logs sciwave"
        echo "  $0 cycle"
        exit 1
        ;;
esac 