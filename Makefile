# AutoGen Council Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help setup start stop test micro soak titanic health logs clean

# Default target
help:
	@echo "🚀 AutoGen Council - Development Commands"
	@echo "=================================================="
	@echo "Setup & Environment:"
	@echo "  setup       - Install dependencies and prepare environment"
	@echo "  download    - Download model files for ExLlamaV2"
	@echo ""
	@echo "Service Management:"
	@echo "  start       - Start all services (LLM + Council)"
	@echo "  start-llm   - Start only LLM backend"
	@echo "  start-api   - Start only Council API"
	@echo "  stop        - Stop all services"
	@echo "  restart     - Restart all services"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  health      - Check service health"
	@echo "  test        - Run basic API tests"
	@echo "  micro       - Micro test suite (50 prompts)"
	@echo "  soak        - Soak test (5 min @ 120 QPS)"
	@echo "  titanic     - Full Titanic test suite (380 prompts)"
	@echo ""
	@echo "Development:"
	@echo "  logs        - View service logs"
	@echo "  monitor     - Open monitoring dashboard"
	@echo "  clean       - Clean up containers and data"
	@echo ""
	@echo "Release Gate:"
	@echo "  gate        - Run complete release gate tests"
	@echo "  tag         - Tag new version"

# Setup and preparation
setup:
	@echo "🔧 Setting up AutoGen Council environment..."
	pip install -r requirements.txt
	python scripts/download_model.py
	@echo "✅ Setup complete!"

download:
	@echo "📥 Downloading model files..."
	python scripts/download_model.py

# Service management
start:
	@echo "🚀 Starting AutoGen Council services..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	sleep 30
	$(MAKE) health

start-llm:
	@echo "🤖 Starting LLM backend only..."
	docker-compose up -d llm
	@echo "⏳ Waiting for LLM to be ready..."
	sleep 20

start-api:
	@echo "📡 Starting Council API only..."
	docker-compose up -d council

stop:
	@echo "🛑 Stopping AutoGen Council services..."
	docker-compose down

restart:
	@echo "🔄 Restarting AutoGen Council services..."
	$(MAKE) stop
	$(MAKE) start

# Health and monitoring
health:
	@echo "🏥 Checking service health..."
	@echo "LLM Backend:"
	@curl -s http://localhost:8000/v1/models | jq '.data[0].id' || echo "❌ LLM not responding"
	@echo ""
	@echo "Council API:"
	@curl -s http://localhost:9000/health | jq '.' || echo "❌ Council API not responding"
	@echo ""
	@echo "Metrics:"
	@curl -s http://localhost:9000/metrics | head -5 || echo "❌ Metrics not available"

# Testing
test:
	@echo "🧪 Running basic API tests..."
	curl -X POST http://localhost:9000/hybrid \
		-H 'Content-Type: application/json' \
		-d '{"prompt":"2+2?"}' | jq '.'
	@echo ""
	curl -X POST http://localhost:9000/vote \
		-H 'Content-Type: application/json' \
		-d '{"prompt":"Write hello world in Python"}' | jq '.meta'

micro:
	@echo "🔬 Running micro test suite (50 prompts)..."
	@if [ "$(CLOUD)" = "off" ]; then \
		echo "Running with cloud disabled..."; \
		SWARM_CLOUD_ENABLED=false python -m pytest tests/ -v --tb=short; \
	else \
		python -m pytest tests/ -v --tb=short; \
	fi

soak:
	@echo "🏋️ Running soak test (5 min @ 120 QPS)..."
	@echo "⚠️  Monitor GPU temperature - should stay ≤75°C"
	python tests/soak_test.py --duration=300 --qps=120

titanic:
	@echo "🚢 Running Titanic test suite (380 prompts)..."
	@if [ "$(BUDGET)" != "" ]; then \
		echo "Budget limit: $$(BUDGET)"; \
		SWARM_CLOUD_BUDGET_USD=$(BUDGET) python tests/titanic_test.py; \
	else \
		python tests/titanic_test.py; \
	fi
	@echo "📊 Generating test report..."
	@if [ -f "reports/titanic_final.json" ]; then \
		echo "✅ Test report saved to reports/titanic_final.json"; \
	fi

# Development tools
logs:
	@echo "📋 Service logs:"
	docker-compose logs -f --tail=50

logs-llm:
	@echo "🤖 LLM Backend logs:"
	docker-compose logs -f llm --tail=50

logs-api:
	@echo "📡 Council API logs:"
	docker-compose logs -f council --tail=50

monitor:
	@echo "📊 Opening monitoring dashboard..."
	@echo "Grafana: http://localhost:3000 (admin/autogen123)"
	@echo "Prometheus: http://localhost:9090"
	@echo "API Metrics: http://localhost:9000/metrics"

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	docker system prune -f
	rm -rf logs/*

clean-models:
	@echo "🗑️ Cleaning model cache..."
	rm -rf models/

# Release gate
gate: micro soak titanic
	@echo "🚪 Release gate tests completed!"
	@echo "📊 Check reports/ directory for detailed results"

tag:
	@echo "🏷️ Tagging new version..."
	@if [ "$(VERSION)" = "" ]; then \
		echo "❌ Please specify VERSION: make tag VERSION=v2.5.0"; \
		exit 1; \
	fi
	git add reports/
	git commit -m "feat: release gate results for $(VERSION)"
	git tag -a $(VERSION) -m "AutoGen Council $(VERSION)"
	@echo "✅ Tagged $(VERSION)"
	@echo "📤 Push with: git push && git push --tags"

# Quick smoke test
smoke:
	@echo "💨 Quick smoke test..."
	@curl -s -o /dev/null -w "LLM Health: %{http_code}\n" http://localhost:8000/v1/models
	@curl -s -o /dev/null -w "API Health: %{http_code}\n" http://localhost:9000/health
	@curl -X POST http://localhost:9000/hybrid \
		-H 'Content-Type: application/json' \
		-d '{"prompt":"hello"}' -s | jq -r '.text' | head -1 