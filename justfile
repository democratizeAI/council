# 🚀 Swarm Development Commands
# Usage: just <command>
# Install: curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash

# Default recipe - show help
default:
    @just --list

# 🏃 Development server
run:
    @echo "🚀 Starting Swarm development server..."
    export LUMINA_ENV=dev && export CUDA_VISIBLE_DEVICES=0 && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 🧪 Run all tests
test:
    @echo "🧪 Running test suite..."
    pytest tests/ -v --tb=short

# 🏃‍♂️ Run smoke tests only
smoke:
    @echo "🧪 Running smoke tests..."
    python tests/test_e2e_smoke.py smoke

# 📊 Performance benchmark
bench:
    @echo "📊 Running performance benchmark..."
    python tests/test_e2e_smoke.py bench

# 🏗️ Build & start full stack
up:
    @echo "🏗️ Starting full production stack..."
    docker-compose up -d

# 🛑 Stop all services
down:
    @echo "🛑 Stopping all services..."
    docker-compose down

# 🔄 Restart with fresh state
restart:
    @echo "🔄 Restarting with fresh state..."
    docker-compose down -v
    sleep 2
    docker-compose up -d

# 📈 Open monitoring dashboards
monitor:
    @echo "📈 Opening monitoring dashboards..."
    @echo "Grafana: http://localhost:3000 (admin/admin)"
    @echo "Prometheus: http://localhost:9090"
    @echo "Ops Dashboard: ops/ops_dashboard_v2.html"

# 🧹 Clean up Docker resources
clean:
    @echo "🧹 Cleaning up Docker resources..."
    docker system prune -f
    docker volume prune -f

# 🔍 Show service status
status:
    @echo "🔍 Service status:"
    docker-compose ps

# 📊 Show metrics
metrics:
    @echo "📊 Current metrics:"
    curl -s http://localhost:9090/api/v1/query?query=up | jq '.data.result[] | {instance: .metric.instance, status: .value[1]}'

# 🚨 Test alert rules
alerts:
    @echo "🚨 Active alerts:"
    curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | {alertname: .labels.alertname, state: .state}'

# 🏥 Health check all services
health:
    @echo "🏥 Health check results:"
    @echo "Main API:" && curl -s http://localhost:8000/health | jq .status || echo "❌ DOWN"
    @echo "Grafana:" && curl -s http://localhost:3000/api/health | jq .database || echo "❌ DOWN"
    @echo "Prometheus:" && curl -s http://localhost:9090/-/healthy || echo "❌ DOWN"

# 🔬 Quick development smoke test
dev-test:
    @echo "🔬 Quick development validation..."
    curl -X POST http://localhost:8000/orchestrate -H "Content-Type: application/json" -d '{"prompt":"What is 2+2?","route":"math"}' | jq .response

# 🎯 Load test (requires wrk)
load-test:
    @echo "🎯 Running load test..."
    echo '{"prompt":"Load test","route":"default"}' > /tmp/payload.json
    wrk -t4 -c100 -d30s -s wrk_script.lua http://localhost:8000/orchestrate

# 📦 Install dependencies
deps:
    @echo "📦 Installing dependencies..."
    pip install -r requirements.txt
    npm install  # if you have frontend deps

# 🏷️ Tag new release
tag VERSION:
    @echo "🏷️ Tagging release {{VERSION}}..."
    git tag {{VERSION}}
    git push origin {{VERSION}}

# 🚀 Deploy to production (requires proper setup)
deploy:
    @echo "🚀 Deploying to production..."
    @echo "Running boot sequence validation..."
    bash scripts/boot_sequence_cursor.sh
    @echo "Deployment validated! ✅"

# 🧪 CI simulation (runs all validation)
ci:
    @echo "🧪 Simulating CI pipeline..."
    just test
    just smoke
    just health
    @echo "CI simulation complete! 🎉"

# 🚪 Soak test gates evaluation
gates:
    @echo "🚪 Evaluating soak test gates..."
    python scripts/soak_gates.py

# 🚪 Watch soak gates continuously
gates-watch:
    @echo "👀 Starting continuous gate monitoring..."
    python scripts/soak_gates.py --watch

# 🚪 Soak gates JSON output
gates-json:
    @echo "📄 Soak gates JSON report..."
    python scripts/soak_gates.py --json

# 🚪 Custom soak gate monitoring
gates-custom INTERVAL="60" DURATION="3600":
    @echo "⚙️  Custom gate monitoring ({{INTERVAL}}s interval, {{DURATION}}s duration)..."
    python scripts/soak_gates.py --watch --interval {{INTERVAL}} --duration {{DURATION}}

# 📅 Generate soak test calendar
calendar-soak:
    @echo "📅 Generating soak test calendar..."
    python scripts/ics_generator.py --type soak --name "Weekly Soak Test" --duration 24

# 📅 Generate deployment calendar
calendar-deploy VERSION="v1.0.0":
    @echo "📅 Generating deployment calendar..."
    python scripts/ics_generator.py --type deployment --name "{{VERSION}}" --duration 1

# 📅 Custom calendar event
calendar-custom TYPE="soak" START="" NAME="" DURATION="24":
    @echo "📅 Generating custom calendar event..."
    python scripts/ics_generator.py --type {{TYPE}} --start "{{START}}" --name "{{NAME}}" --duration {{DURATION}}

# 📅 Generate full test schedule
calendar-schedule:
    @echo "📅 Generating complete test schedule..."
    python scripts/ics_generator.py --type soak --name "Soak Test #1" --start "2025-06-07 10:00" --duration 24
    python scripts/ics_generator.py --type soak --name "Soak Test #2" --start "2025-06-14 10:00" --duration 24
    python scripts/ics_generator.py --type soak --name "Soak Test #3" --start "2025-06-21 10:00" --duration 24
    @echo "📅 Generated 3 weekly soak test events with 10-minute alarms" 