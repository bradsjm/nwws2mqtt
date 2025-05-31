# Makefile for NWWS2MQTT Docker operations
# Provides convenient shortcuts for common Docker tasks

.PHONY: help init build run up down logs shell health clean test lint format check

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON_VERSION ?= 3.13
IMAGE_NAME ?= nwws2mqtt
TAG ?= latest
PROFILE ?= default

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)NWWS2MQTT Docker Management$(NC)"
	@echo ""
	@echo "$(GREEN)Usage:$(NC) make [target] [options]"
	@echo ""
	@echo "$(GREEN)Targets:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Variables:$(NC)"
	@echo "  $(YELLOW)PYTHON_VERSION$(NC)  Python version for build (default: $(PYTHON_VERSION))"
	@echo "  $(YELLOW)IMAGE_NAME$(NC)      Docker image name (default: $(IMAGE_NAME))"
	@echo "  $(YELLOW)TAG$(NC)             Image tag (default: $(TAG))"
	@echo "  $(YELLOW)PROFILE$(NC)         Docker compose profile (default: $(PROFILE))"
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make build TAG=dev"
	@echo "  make up PROFILE=monitoring"
	@echo "  make logs SERVICE=mosquitto"

init: ## Initialize environment file from template
	@echo "$(BLUE)[INFO]$(NC) Initializing environment file"
	@if [ -f .env ]; then \
		echo "$(YELLOW)[WARNING]$(NC) .env file already exists"; \
		read -p "Overwrite? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1; \
	fi
	@cp .env.example .env
	@echo "$(GREEN)[SUCCESS]$(NC) Created .env file from template"
	@echo "$(BLUE)[INFO]$(NC) Please edit .env with your NWWS credentials"

build: ## Build Docker image
	@echo "$(BLUE)[INFO]$(NC) Building Docker image: $(IMAGE_NAME):$(TAG)"
	@echo "$(BLUE)[INFO]$(NC) Python version: $(PYTHON_VERSION)"
	@docker build \
		-f docker/Dockerfile \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		-t $(IMAGE_NAME):$(TAG) \
		.
	@echo "$(GREEN)[SUCCESS]$(NC) Image built successfully: $(IMAGE_NAME):$(TAG)"

build-dev: ## Build development image with dev tag
	@$(MAKE) build TAG=dev

build-multi: ## Build multi-platform image
	@echo "$(BLUE)[INFO]$(NC) Building multi-platform image"
	@docker buildx build \
		-f docker/Dockerfile \
		--platform linux/amd64,linux/arm64 \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		-t $(IMAGE_NAME):$(TAG) \
		.

run: ## Run container with basic setup
	@echo "$(BLUE)[INFO]$(NC) Running container with basic setup"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)[WARNING]$(NC) .env file not found, creating from template"; \
		$(MAKE) init; \
	fi
	@docker run -d \
		--name nwws2mqtt \
		-p 8080:8080 \
		--env-file .env \
		-v $(PWD)/logs:/app/logs \
		--restart unless-stopped \
		$(IMAGE_NAME):$(TAG)
	@echo "$(GREEN)[SUCCESS]$(NC) Container started successfully"
	@echo "$(BLUE)[INFO]$(NC) Access metrics at: http://localhost:8080/metrics"
	@echo "$(BLUE)[INFO]$(NC) Check health at: http://localhost:8080/health"

up: ## Start services with docker compose
	@echo "$(BLUE)[INFO]$(NC) Starting services with profile: $(PROFILE)"
	@cd docker && docker compose $(if $(filter-out default,$(PROFILE)),--profile $(PROFILE),) up -d
	@echo "$(GREEN)[SUCCESS]$(NC) Services started successfully"
	@$(MAKE) urls

up-monitoring: ## Start with monitoring stack
	@$(MAKE) up PROFILE=monitoring

up-full: ## Start all services
	@$(MAKE) up PROFILE=full

down: ## Stop and remove containers
	@echo "$(BLUE)[INFO]$(NC) Stopping and removing containers"
	@cd docker && docker compose down
	@echo "$(GREEN)[SUCCESS]$(NC) Containers stopped and removed"

restart: ## Restart services
	@$(MAKE) down
	@$(MAKE) up PROFILE=$(PROFILE)

logs: ## Show logs (SERVICE=service_name to specify service)
	@echo "$(BLUE)[INFO]$(NC) Showing logs for: $(or $(SERVICE),nwws2mqtt)"
	@cd docker && docker compose logs -f $(or $(SERVICE),nwws2mqtt)

shell: ## Open shell in running container
	@echo "$(BLUE)[INFO]$(NC) Opening shell in nwws2mqtt container"
	@docker exec -it nwws2mqtt /bin/sh

health: ## Check container health
	@echo "$(BLUE)[INFO]$(NC) Checking container health"
	@if ! docker ps --format "{{.Names}}" | grep -q "^nwws2mqtt$$"; then \
		echo "$(RED)[ERROR]$(NC) Container 'nwws2mqtt' is not running"; \
		exit 1; \
	fi
	@echo "Container status: $$(docker inspect --format='{{.State.Status}}' nwws2mqtt)"
	@if curl -f -s http://localhost:8080/health > /dev/null; then \
		echo "$(GREEN)[SUCCESS]$(NC) Health check passed"; \
	else \
		echo "$(RED)[ERROR]$(NC) Health check failed"; \
		exit 1; \
	fi
	@docker stats --no-stream nwws2mqtt

ps: ## Show running containers
	@cd docker && docker compose ps

clean: ## Remove containers, images, and optionally volumes
	@echo "$(YELLOW)[WARNING]$(NC) This will remove all nwws2mqtt containers and images"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(BLUE)[INFO]$(NC) Cleaning up Docker resources"
	@cd docker && docker compose down -v --remove-orphans 2>/dev/null || true
	@docker rm -f nwws2mqtt 2>/dev/null || true
	@docker rmi $$(docker images $(IMAGE_NAME) -q) 2>/dev/null || true
	@echo "$(GREEN)[SUCCESS]$(NC) Cleanup completed"

clean-volumes: ## Remove Docker volumes
	@echo "$(YELLOW)[WARNING]$(NC) This will remove all Docker volumes"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@docker volume rm $$(docker volume ls -q | grep -E "(mosquitto|postgres|redis|prometheus|grafana)") 2>/dev/null || true
	@echo "$(GREEN)[SUCCESS]$(NC) Volumes removed"

test: ## Run tests in container
	@echo "$(BLUE)[INFO]$(NC) Running tests"
	@docker run --rm \
		-v $(PWD)/src:/app/src \
		$(IMAGE_NAME):$(TAG) \
		python -m pytest src/tests/ -v

lint: ## Run linting in container
	@echo "$(BLUE)[INFO]$(NC) Running linting"
	@docker run --rm \
		-v $(PWD)/src:/app/src \
		$(IMAGE_NAME):$(TAG) \
		ruff check src/

format: ## Format code in container
	@echo "$(BLUE)[INFO]$(NC) Formatting code"
	@docker run --rm \
		-v $(PWD)/src:/app/src \
		$(IMAGE_NAME):$(TAG) \
		ruff format src/

check: ## Run type checking in container
	@echo "$(BLUE)[INFO]$(NC) Running type checking"
	@docker run --rm \
		-v $(PWD)/src:/app/src \
		$(IMAGE_NAME):$(TAG) \
		basedpyright src/

urls: ## Show service URLs
	@echo ""
	@echo "$(GREEN)Service URLs:$(NC)"
	@echo "  📊 NWWS2MQTT Metrics: http://localhost:8080/metrics"
	@echo "  🏥 Health Check:      http://localhost:8080/health"
	@if docker ps --format "{{.Names}}" | grep -q mosquitto; then \
		echo "  📡 MQTT Broker:       mqtt://localhost:1883"; \
		echo "  🌐 MQTT WebSocket:    ws://localhost:9001"; \
	fi
	@if docker ps --format "{{.Names}}" | grep -q postgres; then \
		echo "  🗄️  PostgreSQL:       postgresql://localhost:5432/nwws"; \
	fi
	@if docker ps --format "{{.Names}}" | grep -q prometheus; then \
		echo "  📈 Prometheus:        http://localhost:9090"; \
	fi
	@if docker ps --format "{{.Names}}" | grep -q grafana; then \
		echo "  📊 Grafana:           http://localhost:3000 (admin/admin)"; \
	fi
	@if docker ps --format "{{.Names}}" | grep -q redis; then \
		echo "  🔄 Redis:             redis://localhost:6379"; \
	fi
	@echo ""

backup: ## Backup Docker volumes
	@echo "$(BLUE)[INFO]$(NC) Backing up Docker volumes"
	@mkdir -p backups
	@if docker volume ls | grep -q mosquitto-data; then \
		docker run --rm -v docker_mosquitto-data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/mosquitto-$$(date +%Y%m%d_%H%M%S).tar.gz -C /data .; \
		echo "$(GREEN)[SUCCESS]$(NC) Mosquitto data backed up"; \
	fi
	@if docker ps --format "{{.Names}}" | grep -q postgres; then \
		docker exec postgres pg_dump -U nwws nwws > backups/postgres-$$(date +%Y%m%d_%H%M%S).sql; \
		echo "$(GREEN)[SUCCESS]$(NC) PostgreSQL data backed up"; \
	fi

dev: ## Start development environment
	@echo "$(BLUE)[INFO]$(NC) Starting development environment"
	@$(MAKE) build-dev
	@docker run -it --rm \
		-v $(PWD)/src:/app/src \
		-v $(PWD)/.env:/app/.env \
		-p 8080:8080 \
		$(IMAGE_NAME):dev

# Quick aliases
b: build     ## Alias for build
r: run       ## Alias for run
u: up        ## Alias for up
d: down      ## Alias for down
l: logs      ## Alias for logs
s: shell     ## Alias for shell
h: health    ## Alias for health
c: clean     ## Alias for clean
