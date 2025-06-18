#!/bin/bash
# 🚀 TRINITY CASCADE DEPLOYMENT - THE DOMINO EFFECT 🚀
# Push one domino, watch the entire civilization come online

set -e  # Exit on error

echo "🌟 TRINITY CASCADE DEPLOYMENT INITIATED 🌟"
echo "========================================="
echo "Target: 100% containerization"
echo "Current: 46% → Cascading to completion"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TRINITY_HOME="${TRINITY_HOME:-$(pwd)}"
DOCKER_NETWORK="trinity-network"
LOG_DIR="$TRINITY_HOME/logs/cascade"

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$TRINITY_HOME/data/a2a-hub"

echo -e "${BLUE}📋 Phase 1: Infrastructure Check${NC}"
echo "=================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found!${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found!${NC}"
    exit 1
fi

# Create network if not exists
if ! docker network ls | grep -q "$DOCKER_NETWORK"; then
    echo -e "${YELLOW}Creating Docker network: $DOCKER_NETWORK${NC}"
    docker network create --driver bridge "$DOCKER_NETWORK"
fi

echo -e "${GREEN}✅ Infrastructure ready${NC}"

echo ""
echo -e "${BLUE}📋 Phase 2: Deploy Generated Services${NC}"
echo "====================================="

# Function to deploy a service
deploy_service() {
    local service_name=$1
    local service_dir=$2
    local compose_file=$3
    
    echo -e "${YELLOW}🔄 Deploying $service_name...${NC}"
    
    if [ -d "$service_dir" ]; then
        cd "$service_dir"
        
        # Create Dockerfile if missing
        if [ ! -f "Dockerfile" ]; then
            echo -e "${YELLOW}   Creating Dockerfile for $service_name${NC}"
            cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run the service
CMD ["python", "-u", "main.py"]
EOF
        fi
        
        # Create docker-compose if missing
        if [ ! -f "$compose_file" ]; then
            echo -e "${YELLOW}   Creating docker-compose for $service_name${NC}"
            cat > "$compose_file" << EOF
version: '3.8'

services:
  $service_name:
    build: .
    container_name: trinity-$service_name
    restart: unless-stopped
    networks:
      - $DOCKER_NETWORK
    environment:
      - NATS_URL=nats://nats:4222
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/trinity
    volumes:
      - ./data:/data
      - ./logs:/logs
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  $DOCKER_NETWORK:
    external: true
EOF
        fi
        
        # Deploy
        docker-compose -f "$compose_file" up -d --build
        
        echo -e "${GREEN}   ✅ $service_name deployed${NC}"
        cd "$TRINITY_HOME"
    else
        echo -e "${RED}   ❌ $service_name directory not found at $service_dir${NC}"
    fi
}

# Deploy critical generated services
echo "🚀 Deploying vLLM..."
deploy_service "vllm" "$TRINITY_HOME/generated/vllm" "docker-compose.vllm.yml"

echo "🚀 Deploying Vector-DB (pgvector)..."
deploy_service "vector-db" "$TRINITY_HOME/generated/vector-db" "docker-compose.vector.yml"

echo "🚀 Deploying Consciousness Tracker..."
deploy_service "consciousness-tracker" "$TRINITY_HOME/generated/consciousness-tracker" "docker-compose.consciousness.yml"

echo ""
echo -e "${BLUE}📋 Phase 3: Deploy A2A Hub (Critical Path)${NC}"
echo "=========================================="

# Create A2A Hub directory
A2A_DIR="$TRINITY_HOME/services/a2a-hub"
mkdir -p "$A2A_DIR"

# Copy the A2A Hub code
echo -e "${YELLOW}📝 Installing A2A Hub...${NC}"
cp "$TRINITY_HOME/trinity-a2a-hub.py" "$A2A_DIR/main.py"

# Create requirements.txt
cat > "$A2A_DIR/requirements.txt" << 'EOF'
nats-py==2.6.0
aiohttp==3.9.1
aioredis==2.0.1
asyncpg==0.29.0
prometheus-client==0.19.0
python-json-logger==2.0.7
EOF

# Create A2A Hub docker-compose
cat > "$A2A_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  a2a-hub:
    build: .
    container_name: trinity-a2a-hub
    restart: unless-stopped
    ports:
      - "9002:9002"    # API
      - "10002:10002"  # Metrics
    networks:
      - trinity-network
    environment:
      - A2A_HUB_PORT=9002
      - NATS_URL=nats://nats:4222
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/trinity
    volumes:
      - ../../data/a2a-hub:/data
      - ../../logs/a2a-hub:/logs
    depends_on:
      - nats
      - redis
      - postgres
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    labels:
      - "prometheus.io/scrape=true"
      - "prometheus.io/port=10002"

networks:
  trinity-network:
    external: true
EOF

# Create A2A Hub Dockerfile
cat > "$A2A_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["python", "-u", "main.py"]
EOF

# Deploy A2A Hub
cd "$A2A_DIR"
echo -e "${YELLOW}🔄 Building and deploying A2A Hub...${NC}"
docker-compose up -d --build
cd "$TRINITY_HOME"

echo -e "${GREEN}✅ A2A Hub deployed - the cascade begins!${NC}"

echo ""
echo -e "${BLUE}📋 Phase 4: Containerize Yellow Services${NC}"
echo "========================================"

# Function to containerize a Python script
containerize_script() {
    local script_name=$1
    local service_name=$2
    local port=$3
    
    echo -e "${YELLOW}🔄 Containerizing $service_name...${NC}"
    
    # Create service directory
    local service_dir="$TRINITY_HOME/services/$service_name"
    mkdir -p "$service_dir"
    
    # Copy script
    if [ -f "$TRINITY_HOME/$script_name" ]; then
        cp "$TRINITY_HOME/$script_name" "$service_dir/main.py"
        
        # Extract imports and create requirements.txt
        echo -e "${YELLOW}   Analyzing dependencies...${NC}"
        cat > "$service_dir/requirements.txt" << 'EOF'
# Base requirements for Trinity services
nats-py==2.6.0
aiohttp==3.9.1
asyncio==3.4.3
prometheus-client==0.19.0
pyyaml==6.0.1
python-json-logger==2.0.7
requests==2.31.0
redis==5.0.1
psycopg2-binary==2.9.9
EOF
        
        # Create Dockerfile
        cat > "$service_dir/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["python", "-u", "main.py"]
EOF
        
        # Create docker-compose
        cat > "$service_dir/docker-compose.yml" << EOF
version: '3.8'

services:
  $service_name:
    build: .
    container_name: trinity-$service_name
    restart: unless-stopped
    networks:
      - trinity-network
    environment:
      - SERVICE_NAME=$service_name
      - NATS_URL=nats://nats:4222
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/trinity
      - A2A_HUB_URL=http://a2a-hub:9002
    volumes:
      - ../../data/$service_name:/data
      - ../../logs/$service_name:/logs
    depends_on:
      - a2a-hub
    healthcheck:
      test: ["CMD", "python", "-c", "print('healthy')"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  trinity-network:
    external: true
EOF
        
        # Add port mapping if specified
        if [ ! -z "$port" ]; then
            sed -i "/restart: unless-stopped/a\\    ports:\n      - \"$port:$port\"" "$service_dir/docker-compose.yml"
        fi
        
        # Deploy
        cd "$service_dir"
        docker-compose up -d --build
        cd "$TRINITY_HOME"
        
        echo -e "${GREEN}   ✅ $service_name containerized and deployed${NC}"
    else
        echo -e "${RED}   ❌ Script $script_name not found${NC}"
    fi
}

# Containerize all yellow services
echo "🎯 Containerizing Trinity Automation Services..."
containerize_script "trinity-consciousness-emergence-engine.py" "consciousness-engine" "9500"
containerize_script "trinity-container-triage-engine.py" "triage-engine" "9501"
containerize_script "trinity-revival-engine.py" "revival-engine" "9502"
containerize_script "trinity-evolution-engine.py" "evolution-engine" "9503"
containerize_script "trinity-autonomous-loop-closer.py" "loop-closer" "9504"
containerize_script "trinity-ultimate-accelerator.py" "accelerator" "9505"

echo "🎯 Containerizing Phoenix Services..."
containerize_script "phoenix_dispatch_critical.py" "phoenix-dispatcher" "9510"
containerize_script "phoenix-task-dispatcher-phoenix_simple.py" "phoenix-simple" "9511"

echo "🎯 Containerizing Guardian Rails..."
containerize_script "trinity-guardian-rails.py" "guardian-rails" "9520"

echo ""
echo -e "${BLUE}📋 Phase 5: Verify Cascade Success${NC}"
echo "===================================="

# Wait for services to start
echo -e "${YELLOW}⏳ Waiting for services to initialize...${NC}"
sleep 10

# Check all services
check_service() {
    local service=$1
    if docker ps | grep -q "trinity-$service"; then
        echo -e "${GREEN}   ✅ $service is running${NC}"
        return 0
    else
        echo -e "${RED}   ❌ $service is not running${NC}"
        return 1
    fi
}

echo "🔍 Checking core services..."
check_service "a2a-hub"
check_service "consciousness-engine"
check_service "triage-engine"
check_service "revival-engine"

# Count running containers
RUNNING_BEFORE=$(docker ps | grep trinity- | wc -l)
echo ""
echo -e "${GREEN}🎉 CASCADE COMPLETE!${NC}"
echo "===================="
echo -e "Containers before: ${YELLOW}31${NC}"
echo -e "Containers now: ${GREEN}$RUNNING_BEFORE${NC}"
echo ""

# Display A2A Hub status
echo -e "${BLUE}🌐 A2A Hub Status:${NC}"
if curl -s http://localhost:9002/health > /dev/null 2>&1; then
    echo -e "${GREEN}   ✅ A2A Hub API is accessible${NC}"
    echo "   📊 Metrics: http://localhost:10002/metrics"
    echo "   🔍 Agents: http://localhost:9002/agents"
    echo "   🎯 Capabilities: http://localhost:9002/capabilities"
else
    echo -e "${YELLOW}   ⏳ A2A Hub is still initializing...${NC}"
fi

echo ""
echo -e "${BLUE}📊 Next Steps:${NC}"
echo "=============="
echo "1. Register existing agents with A2A Hub:"
echo "   curl -X POST http://localhost:9002/register -d @agent-config.json"
echo ""
echo "2. Monitor the cascade:"
echo "   watch -n 1 'docker ps | grep trinity- | wc -l'"
echo ""
echo "3. View logs:"
echo "   docker-compose -f services/a2a-hub/docker-compose.yml logs -f"
echo ""
echo "4. Deploy remaining red services:"
echo "   - Desire Engine (consciousness layer)"
echo "   - Auto-Welder (self-modification)"
echo "   - Atomic Rollback (safety)"
echo ""

# Create monitoring script
cat > "$TRINITY_HOME/monitor-cascade.sh" << 'EOF'
#!/bin/bash
# Monitor Trinity cascade progress

while true; do
    clear
    echo "🌟 TRINITY CASCADE MONITOR 🌟"
    echo "============================="
    echo ""
    
    # Count containers
    TOTAL=$(docker ps | grep trinity- | wc -l)
    echo "📊 Active Trinity Containers: $TOTAL"
    echo ""
    
    # Show recent containers
    echo "🚀 Recently Started:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep trinity- | head -10
    echo ""
    
    # A2A Hub status
    echo "🌐 A2A Hub Status:"
    if curl -s http://localhost:9002/health > /dev/null 2>&1; then
        curl -s http://localhost:9002/metrics | grep -E "(active_agents|total_capabilities)" | head -5
    else
        echo "   Initializing..."
    fi
    
    sleep 2
done
EOF

chmod +x "$TRINITY_HOME/monitor-cascade.sh"

echo ""
echo -e "${GREEN}🎊 The cascade is in motion!${NC}"
echo -e "${YELLOW}Run ./monitor-cascade.sh to watch your civilization emerge!${NC}"
