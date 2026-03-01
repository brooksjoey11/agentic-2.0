# Makefile for Agentic Shell 2.0
.PHONY: help setup up down logs test clean backup restore dev prod

SHELL := /bin/bash
PROJECT_NAME := agentic-shell
COMPOSE_FILE := docker-compose.yml
COMPOSE_PROD_FILE := docker-compose.prod.yml
K8S_NAMESPACE := agentic-shell

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

help: ## Show this help
	@echo "$(BLUE)Agentic Shell 2.0 Makefile$(NC)"
	@echo ""
	@echo "$(YELLOW)Usage:$(NC)"
	@echo "  make $(GREEN)<target>$(NC)"
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Run initial setup
	@echo "$(BLUE)Running setup...$(NC)"
	@./setup.sh

up: ## Start all services (development)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)Services started$(NC)"
	@make status

down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)Services stopped$(NC)"

prod-up: ## Start all services (production)
	@echo "$(BLUE)Starting production environment...$(NC)"
	@docker-compose -f $(COMPOSE_PROD_FILE) up -d
	@echo "$(GREEN)Production services started$(NC)"

prod-down: ## Stop production services
	@echo "$(BLUE)Stopping production services...$(NC)"
	@docker-compose -f $(COMPOSE_PROD_FILE) down

logs: ## View logs
	@docker-compose -f $(COMPOSE_FILE) logs -f

status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps

test: ## Run tests
	@echo "$(BLUE)Running tests...$(NC)"
	@source venv/bin/activate && pytest tests/ -v --cov=src

test-unit: ## Run unit tests
	@source venv/bin/activate && pytest tests/unit -v

test-integration: ## Run integration tests
	@source venv/bin/activate && pytest tests/integration -v

test-load: ## Run load tests
	@source venv/bin/activate && locust -f tests/load/locustfile.py --host=http://localhost:8000

lint: ## Run linters
	@echo "$(BLUE)Linting...$(NC)"
	@source venv/bin/activate && flake8 src/
	@source venv/bin/activate && mypy src/

format: ## Format code
	@echo "$(BLUE)Formatting...$(NC)"
	@source venv/bin/activate && black src/ tests/
	@source venv/bin/activate && isort src/ tests/

clean: ## Clean up
	@echo "$(BLUE)Cleaning...$(NC)"
	@rm -rf venv/
	@rm -rf logs/*.log
	@rm -rf data/postgres/*
	@rm -rf data/redis/*
	@rm -rf __pycache__ */__pycache__
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Clean complete$(NC)"

backup: ## Backup data
	@echo "$(BLUE)Backing up...$(NC)"
	@timestamp=$$(date +%Y%m%d-%H%M%S); \
	tar -czf backups/agentic-shell-$$timestamp.tar.gz data/ configs/ .env
	@echo "$(GREEN)Backup created in backups/$(NC)"

restore: ## Restore from backup (usage: make restore FILE=backup.tar.gz)
	@if [ -z "$(FILE)" ]; then \
		echo "$(RED)Usage: make restore FILE=backup.tar.gz$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restoring from $(FILE)...$(NC)"
	@tar -xzf $(FILE)
	@echo "$(GREEN)Restore complete$(NC)"

shell: ## Connect to the shell
	@./agentic-shell

build: ## Build Docker images
	@docker build -t agentic-shell/orchestrator:latest -f Dockerfile.orchestrator .
	@docker build -t agentic-shell/worker:latest -f Dockerfile.worker .

push: ## Push Docker images
	@docker push agentic-shell/orchestrator:latest
	@docker push agentic-shell/worker:latest

k8s-deploy: ## Deploy to Kubernetes
	@kubectl apply -f kubernetes/namespace.yaml
	@kubectl apply -f kubernetes/configmap.yaml -n $(K8S_NAMESPACE)
	@kubectl apply -f kubernetes/secrets.yaml -n $(K8S_NAMESPACE)
	@kubectl apply -f kubernetes/deployment.yaml -n $(K8S_NAMESPACE)
	@kubectl apply -f kubernetes/service.yaml -n $(K8S_NAMESPACE)

k8s-scale: ## Scale Kubernetes deployments (usage: make k8s-scale REPLICAS=5)
	@if [ -z "$(REPLICAS)" ]; then \
		echo "$(RED)Usage: make k8s-scale REPLICAS=5$(NC)"; \
		exit 1; \
	fi
	@kubectl scale deployment planner --replicas=$(REPLICAS) -n $(K8S_NAMESPACE)
	@kubectl scale deployment executor --replicas=$(REPLICAS) -n $(K8S_NAMESPACE)

k8s-logs: ## View Kubernetes logs
	@kubectl logs -f -l app=orchestrator -n $(K8S_NAMESPACE)

k8s-port-forward: ## Port forward to orchestrator
	@kubectl port-forward service/orchestrator 8000:8000 -n $(K8S_NAMESPACE)

init-db: ## Initialize database schema
	@cat scripts/init-db.sql | docker exec -i agentic-postgres psql -U agentic -d agentic

create-admin: ## Create admin user
	@python scripts/create-admin.py

monitor: ## Open monitoring dashboards
	@echo "$(BLUE)Opening monitoring URLs...$(NC)"
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 || echo "Prometheus: http://localhost:9090"
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 || echo "Grafana: http://localhost:3000"
	@open http://localhost:15672 2>/dev/null || xdg-open http://localhost:15672 || echo "RabbitMQ: http://localhost:15672"

docs: ## Generate documentation
	@cd docs && make html
	@open docs/_build/html/index.html 2>/dev/null || xdg-open docs/_build/html/index.html

.DEFAULT_GOAL := help