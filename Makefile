# DPO Microservice Development Makefile
# Provides common development tasks for the reorganized DPO training service

.PHONY: help setup install test lint clean api toy-data toy-train toy-trigger docker-build docker-run docker-clean test-api validate-structure

# Default target
help:
	@echo "DPO Microservice Development Commands"
	@echo "====================================="
	@echo ""
	@echo "Setup and Installation:"
	@echo "  setup          - Complete development environment setup"
	@echo "  install        - Install Python dependencies"
	@echo ""
	@echo "Development:"
	@echo "  test           - Run all tests"
	@echo "  test-api       - Run API integration tests"
	@echo "  lint           - Run code linting (if tools available)"
	@echo "  validate-structure - Validate package imports and structure"
	@echo ""
	@echo "Training Pipeline:"
	@echo "  toy-data       - Generate toy dataset for testing"
	@echo "  toy-train      - Run training with toy data"
	@echo "  toy-trigger    - Test full API → training pipeline"
	@echo ""
	@echo "API Server:"
	@echo "  api            - Start the FastAPI webhook server"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   - Build Docker image"
	@echo "  docker-run     - Run Docker container"
	@echo "  docker-clean   - Clean Docker artifacts"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          - Clean temporary files and caches"

# Setup and Installation
setup: install toy-data validate-structure
	@echo "✅ Development environment setup complete"

install:
	@echo "📦 Installing Python dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Testing
test:
	@echo "🧪 Running all tests..."
	python3 -m pytest tests/ -v
	@echo "✅ All tests completed"

test-api:
	@echo "🔗 Running API integration tests..."
	python3 -m pytest tests/test_api.py -v
	@echo "✅ API tests completed"

lint:
	@echo "🔍 Running code linting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics; \
		echo "✅ Linting completed"; \
	else \
		echo "⚠️  flake8 not installed, skipping linting"; \
	fi

validate-structure:
	@echo "🏗️  Validating package structure..."
	python3 -c "from training import run_training; print('✅ Training package import OK')"
	python3 -c "from datasets import PreferenceDatasetInterface; print('✅ Datasets package import OK')"
	python3 -c "from storage import StorageInterface; print('✅ Storage package import OK')"
	python3 -c "from core.validators import validate_all_configs; print('✅ Core validators import OK')"
	@echo "✅ Package structure validation complete"

# Training Pipeline
toy-data:
	@echo "🎲 Generating toy dataset..."
	mkdir -p data
	python3 tools/make_toy_novalto.py --out data/dataset.json --size 10
	@echo "✅ Toy dataset created at data/dataset.json"

toy-train:
	@echo "🚂 Running training with toy data..."
	python3 -c "from training import run_training; result = run_training(model_name='zephyr', datasets=['novalto'], loss_config={'name': 'dpo', 'beta': 0.1}, exp_name='toy_test', n_examples=5, debug=True); print(f'✅ Training completed: {result[\"artifact_path\"]}')"

toy-trigger: toy-data
	@echo "🎯 Testing full API pipeline..."
	@echo "Starting API server in background..."
	@(uvicorn webhook_handler:app --host 127.0.0.1 --port 8000 &) && \
	sleep 3 && \
	echo "Sending test request..." && \
	curl -X POST "http://127.0.0.1:8000/trigger-finetune" \
		-H "Content-Type: application/json" \
		-d '{"communityId": "toy_api_test", "dataset": [{"chosen": "Good response", "rejected": "Bad response", "prompt": "Test prompt"}]}' && \
	echo "" && \
	echo "✅ API pipeline test completed" && \
	pkill -f "uvicorn webhook_handler:app" || true

# API Server
api:
	@echo "🚀 Starting FastAPI webhook server..."
	uvicorn webhook_handler:app --host 0.0.0.0 --port 8000 --reload

# Docker
docker-build:
	@echo "🐳 Building Docker image..."
	docker build -t dpo-microservice .
	@echo "✅ Docker image built: dpo-microservice"

docker-run: docker-build
	@echo "🐳 Running Docker container..."
	docker run -p 8000:8000 -v $(PWD)/data:/app/data dpo-microservice
	@echo "✅ Docker container started on port 8000"

docker-clean:
	@echo "🐳 Cleaning Docker artifacts..."
	docker rmi dpo-microservice 2>/dev/null || true
	docker system prune -f
	@echo "✅ Docker cleanup completed"

# Cleanup
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .cache/ 2>/dev/null || true
	rm -rf data/dataset.json 2>/dev/null || true
	@echo "✅ Cleanup completed"

# Development workflow validation
validate-workflow: setup test docker-build
	@echo "🔬 Running complete workflow validation..."
	@echo "✅ Complete development workflow validated"