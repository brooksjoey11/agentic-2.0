.PHONY: help install dev build test lint fmt clean docker-build docker-up docker-down k8s-deploy

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	poetry install

dev: ## Run development server
	poetry run uvicorn src.orchestrator.main:app --reload --host 0.0.0.0 --port 8000

build: ## Build Docker images
	docker compose build

test: ## Run all tests
	poetry run pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests
	poetry run pytest tests/unit/ -v

test-integration: ## Run integration tests
	poetry run pytest tests/integration/ -v

test-load: ## Run load tests
	poetry run locust -f tests/load/locustfile.py

lint: ## Lint code
	poetry run ruff check src/ tests/
	poetry run mypy src/

fmt: ## Format code
	poetry run black src/ tests/
	poetry run isort src/ tests/

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf dist/ build/ .coverage .pytest_cache

docker-build: ## Build Docker images
	docker compose build

docker-up: ## Start all services
	docker compose up -d

docker-down: ## Stop all services
	docker compose down

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -k kubernetes/

k8s-delete: ## Delete Kubernetes resources
	kubectl delete -k kubernetes/

init-db: ## Initialise database
	poetry run python scripts/create-admin.py
