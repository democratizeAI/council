#!/bin/bash
# 🔧 TRINITY A2A HUB DEBUG & FIX 🔧

set -e

echo "🔍 DEBUGGING A2A HUB ISSUES"
echo "=========================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Step 1: Check A2A Hub container status
echo -e "${BLUE}1. Checking A2A Hub container status...${NC}"
docker ps -a | grep a2a-hub || echo "No A2A Hub container found"

# Step 2: Check logs
echo -e "\n${BLUE}2. A2A Hub logs:${NC}"
docker logs trinity-a2a-hub 2>&1 | tail -20 || echo "Could not get logs"

# Step 3: Check if NATS is running
echo -e "\n${BLUE}3. Checking NATS status:${NC}"
if docker ps | grep -q nats; then
    echo -e "${GREEN}✅ NATS is running${NC}"
    docker ps | grep nats
else
    echo -e "${RED}❌ NATS is not running!${NC}"
    echo "Starting NATS..."
    
    # Create minimal NATS docker-compose if needed
    cat > /tmp/nats-compose.yml << 'EOF'
version: '3.8'

services:
  nats:
    image: nats:2.10-alpine
    container_name: trinity-nats
    restart: unless-stopped
    ports:
      - "4222:4222"
      - "8222:8222"
    command: ["-js", "-m", "8222"]
    networks:
      - trinity-network

networks:
  trinity-network:
    external: true
EOF
    
    docker-compose -f /tmp/nats-compose.yml up -d
    sleep 5
fi

# Step 4: Check Redis
echo -e "\n${BLUE}4. Checking Redis status:${NC}"
if docker ps | grep -q redis; then
    echo -e "${GREEN}✅ Redis is running${NC}"
else
    echo -e "${RED}❌ Redis is not running!${NC}"
    echo "Starting Redis..."
    docker run -d --name trinity-redis --network trinity-network -p 6379:6379 redis:7-alpine
    sleep 3
fi

# Step 5: Check PostgreSQL
echo -e "\n${BLUE}5. Checking PostgreSQL status:${NC}"
if docker ps | grep -q postgres; then
    echo -e "${GREEN}✅ PostgreSQL is running${NC}"
else
    echo -e "${RED}❌ PostgreSQL is not running!${NC}"
    echo "Starting PostgreSQL..."
    docker run -d --name trinity-postgres \
        --network trinity-network \
        -e POSTGRES_PASSWORD=postgres \
        -e POSTGRES_DB=trinity \
        -p 5432:5432 \
        postgres:15-alpine
    sleep 5
fi

# Step 6: Fix A2A Hub
echo -e "\n${BLUE}6. Fixing A2A Hub...${NC}"

# First, remove the broken container
docker stop trinity-a2a-hub 2>/dev/null || true
docker rm trinity-a2a-hub 2>/dev/null || true

# Create fixed A2A Hub directory
A2A_DIR="${TRINITY_HOME:-$(pwd)}/services/a2a-hub"
mkdir -p "$A2A_DIR"

# Copy the A2A Hub script with fixes
echo -e "${YELLOW}Creating fixed A2A Hub...${NC}"

# Create a wrapper script that ensures proper startup
cat > "$A2A_DIR/start.sh" << 'EOF'
#!/bin/bash
echo "🌐 A2A Hub starting..."
echo "Waiting for dependencies..."

# Wait for NATS
while ! nc -z nats 4222; do
    echo "Waiting for NATS..."
    sleep 2
done
echo "✅ NATS is ready"

# Wait for Redis
while ! nc -z redis 6379; do
    echo "Waiting for Redis..."
    sleep 2
done
echo "✅ Redis is ready"

# Wait for PostgreSQL
while ! nc -z postgres 5432; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo "✅ PostgreSQL is ready"

# Start the A2A Hub
echo "🚀 Starting A2A Hub service..."
python -u main.py
EOF

chmod +x "$A2A_DIR/start.sh"

# Update Dockerfile to install netcat and use start script
cat > "$A2A_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y curl netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY start.sh .

# Use the start script
CMD ["./start.sh"]
EOF

# Ensure main.py exists
if [ ! -f "$A2A_DIR/main.py" ]; then
    echo -e "${YELLOW}Copying A2A Hub main.py...${NC}"
    cp "${TRINITY_HOME:-$(pwd)}/trinity-a2a-hub.py" "$A2A_DIR/main.py" 2>/dev/null || \
    cp "${TRINITY_HOME:-$(pwd)}/roadmap/trinity-a2a-hub.py" "$A2A_DIR/main.py" 2>/dev/null || \
    echo -e "${RED}ERROR: Could not find trinity-a2a-hub.py${NC}"
fi

# Update docker-compose with proper dependencies
cat > "$A2A_DIR/docker-compose.yml" << 'EOF'
version: '3.8'

services:
  a2a-hub:
    build: .
    container_name: trinity-a2a-hub
    restart: unless-stopped
    ports:
      - "9002:9002"
      - "10002:10002"
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

  # Include dependencies if they don't exist
  nats:
    image: nats:2.10-alpine
    container_name: trinity-nats
    restart: unless-stopped
    ports:
      - "4222:4222"
      - "8222:8222"
    command: ["-js", "-m", "8222"]
    networks:
      - trinity-network

  redis:
    image: redis:7-alpine
    container_name: trinity-redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    networks:
      - trinity-network

  postgres:
    image: postgres:15-alpine
    container_name: trinity-postgres
    restart: unless-stopped
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=trinity
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - trinity-network

networks:
  trinity-network:
    external: true

volumes:
  postgres-data:
EOF

# Deploy the fixed A2A Hub
echo -e "\n${BLUE}7. Deploying fixed A2A Hub...${NC}"
cd "$A2A_DIR"
docker-compose down 2>/dev/null || true
docker-compose up -d --build

# Wait for it to start
echo -e "\n${YELLOW}⏳ Waiting for A2A Hub to initialize...${NC}"
sleep 10

# Check if it's running
echo -e "\n${BLUE}8. Verifying A2A Hub:${NC}"
if curl -s http://localhost:9002/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ A2A Hub API is responding!${NC}"
    curl -s http://localhost:9002/health | python3 -m json.tool
else
    echo -e "${RED}❌ A2A Hub API not responding yet${NC}"
    echo "Checking logs again..."
    docker logs trinity-a2a-hub --tail 50
fi

# Test NATS connectivity
echo -e "\n${BLUE}9. Testing NATS connectivity:${NC}"
cat > /tmp/test_nats.py << 'EOF'
import asyncio
from nats.aio.client import Client as NATS

async def test():
    nc = NATS()
    try:
        await nc.connect("nats://localhost:4222")
        print("✅ Successfully connected to NATS")
        
        # Try to publish a test message
        await nc.publish("test.subject", b"Hello NATS")
        print("✅ Successfully published to NATS")
        
        await nc.close()
    except Exception as e:
        print(f"❌ NATS connection failed: {e}")

asyncio.run(test())
EOF

python3 /tmp/test_nats.py

echo -e "\n${GREEN}🎯 TROUBLESHOOTING COMPLETE${NC}"
echo "================================"
echo ""
echo "📋 Next steps:"
echo "1. If A2A Hub is running, try registration again:"
echo "   python3 roadmap/trinity-agent-registration.py"
echo ""
echo "2. Monitor A2A Hub logs:"
echo "   docker logs -f trinity-a2a-hub"
echo ""
echo "3. Check all Trinity containers:"
echo "   docker ps | grep trinity"
echo ""
echo "4. If still having issues, check network:"
echo "   docker network inspect trinity-network"
