# 🔥💀 Nexus v1.0 Production Dockerfile 💀🔥
# Oracle Threshold Crossed: 70.6% Accuracy
FROM python:3.11-slim

# Production metadata
LABEL version="v1.0-oracle-plus-2pp"
LABEL maintainer="nexus-production"
LABEL description="Nexus Production System - Oracle Threshold Crossed"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy production source
COPY mistral_judge_harness.py .
COPY temporal_logic_enhancer.py .
COPY nexus_evaluation_integration.py .
COPY production_ready_demo.py .
COPY production_guardrails.py .
COPY evaluation_questions.json .
COPY enhanced_math_v2.py .
COPY enhanced_code_runner_v2.py .
COPY rapidfuzz_retriever.py .
COPY reflector_v2_rules.yml .

# Copy additional breakthrough components
COPY judge_cost_tracker.py .

# Create production directories
RUN mkdir -p /app/logs /app/results /app/canary

# Production environment variables
ENV PYTHONPATH=/app
ENV NEXUS_USE_REASONING_V1=true
ENV NEXUS_USE_RATE_LIMITING=true
ENV NEXUS_CANARY_ENABLED=true
ENV NEXUS_MIN_ACCURACY=0.6
ENV NEXUS_MAX_LATENCY_MS=5000
ENV NEXUS_CANARY_INTERVAL_HOURS=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python production_guardrails.py || exit 1

# Production server setup (following SwarmAI pattern)
EXPOSE 8000

# Production startup script
COPY production_startup.sh .
RUN chmod +x production_startup.sh

CMD ["./production_startup.sh"]

# 🎯 Build & Run Instructions:
# 
# Build:
#   docker build -t swarm-ai:latest .
#   docker build -t swarm-ai:v1.0 .
# 
# Run Production:
#   docker run -d -p 8000:8000 --name swarm-production swarm-ai:latest
# 
# Run with Benchmark:
#   docker run -it -p 8000:8000 -p 8001:8001 swarm-ai:latest \
#     bash -c "python production_server.py --port 8000 & python baseline_server.py --port 8001 & sleep 10 && python live_wire_bench.py --swarm http://localhost:8000/infer --baseline http://localhost:8001/infer --dataset live_wire_100.yaml"
# 
# Development Mode:
#   docker run -it -v $(pwd):/app -p 8000:8000 swarm-ai:latest bash 