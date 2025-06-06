#!/bin/bash
# Docker convenience script for NWWS2MQTT
# This script provides easy access to Docker operations from the project root

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$SCRIPT_DIR/docker"
PROJECT_ROOT="$SCRIPT_DIR"

# Default values
PYTHON_VERSION="${PYTHON_VERSION:-3.13}"
IMAGE_NAME="${IMAGE_NAME:-nwws2mqtt}"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
NWWS2MQTT Docker Management Script

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  build [tag]           Build Docker image (default tag: latest)
  run                   Run container with basic setup
  compose [command]     Run docker compose commands
  up [profile]          Start services with docker compose
  down                  Stop and remove containers
  logs [service]        Show logs (default: nwws2mqtt)
  shell                 Open shell in running container
  health                Check container health
  clean                 Remove containers, images, and volumes
  init                  Initialize environment file
  help                  Show this help message

Profiles for 'up' command:
  default               App (default)
  mqtt                  App + MQTT broker
  database              Add PostgreSQL database
  monitoring            Add Prometheus + Grafana
  full                  All services

Examples:
  $0 build              Build with default settings
  $0 build dev          Build with 'dev' tag
  $0 up                 Start default services
  $0 up monitoring      Start with monitoring stack
  $0 compose ps         Show running containers
  $0 logs               Show nwws2mqtt logs
  $0 shell              Open shell in container
  $0 clean              Clean up everything

Environment Variables:
  PYTHON_VERSION        Python version for build (default: 3.13)
  IMAGE_NAME            Docker image name (default: nwws2mqtt)

EOF
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

check_compose() {
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        exit 1
    fi
}

init_env() {
    local env_file="$PROJECT_ROOT/.env"
    local env_example="$PROJECT_ROOT/.env.example"

    if [[ -f "$env_file" ]]; then
        log_warning ".env file already exists"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing .env file"
            return 0
        fi
    fi

    if [[ -f "$env_example" ]]; then
        cp "$env_example" "$env_file"
        log_success "Created .env file from template"
        log_info "Please edit .env file with your NWWS credentials:"
        log_info "  - NWWS_USERNAME=your_username"
        log_info "  - NWWS_PASSWORD=your_password"
    else
        log_error ".env.example file not found"
        exit 1
    fi
}

build_image() {
    local tag="${1:-latest}"
    local full_tag="$IMAGE_NAME:$tag"

    log_info "Building Docker image: $full_tag"
    log_info "Python version: $PYTHON_VERSION"

    docker build \
        -f "$DOCKER_DIR/Dockerfile" \
        --build-arg PYTHON_VERSION="$PYTHON_VERSION" \
        -t "$full_tag" \
        "$PROJECT_ROOT"

    log_success "Image built successfully: $full_tag"
}

run_container() {
    local env_file="$PROJECT_ROOT/.env"

    if [[ ! -f "$env_file" ]]; then
        log_warning ".env file not found. Creating from template..."
        init_env
    fi

    log_info "Running container with basic setup"

    docker run -d \
        --name nwws2mqtt \
        -p 8080:8080 \
        --env-file "$env_file" \
        --restart unless-stopped \
        "$IMAGE_NAME:latest"

    log_success "Container started successfully"
    log_info "Access metrics at: http://localhost:8080/api/v1/metrics"
    log_info "Check health at: http://localhost:8080/api/v1/health"
}

compose_up() {
    local profile="${1:-default}"
    local compose_args=()

    if [[ "$profile" != "default" ]]; then
        compose_args+=("--profile" "$profile")
    fi

    log_info "Starting services with profile: $profile"

    cd "$DOCKER_DIR"
    docker compose "${compose_args[@]}" up -d

    log_success "Services started successfully"
    show_service_urls "$profile"
}

compose_down() {
    log_info "Stopping and removing containers"

    cd "$DOCKER_DIR"
    docker compose down

    log_success "Containers stopped and removed"
}

show_logs() {
    local service="${1:-nwws2mqtt}"

    log_info "Showing logs for service: $service"

    cd "$DOCKER_DIR"
    docker compose logs -f "$service"
}

open_shell() {
    local container_name="nwws2mqtt"

    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        log_error "Container '$container_name' is not running"
        exit 1
    fi

    log_info "Opening shell in container: $container_name"
    docker exec -it "$container_name" /bin/sh
}

check_health() {
    local container_name="nwws2mqtt"

    if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        log_error "Container '$container_name' is not running"
        exit 1
    fi

    log_info "Checking container health"

    # Check container status
    local status=$(docker inspect --format="{{.State.Status}}" "$container_name")
    log_info "Container status: $status"

    # Use the dedicated health check script
    log_info "Running comprehensive health check"
    if docker exec "$container_name" python /app/healthcheck.py; then
        log_success "Health check passed"
    else
        log_error "Health check failed"
        exit 1
    fi

    # Show basic stats
    docker stats --no-stream "$container_name"
}

clean_docker() {
    log_warning "This will remove all nwws2mqtt containers, images, and volumes"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleanup cancelled"
        return 0
    fi

    log_info "Cleaning up Docker resources"

    # Stop and remove containers
    cd "$DOCKER_DIR"
    docker compose down -v --remove-orphans 2>/dev/null || true

    # Remove containers
    docker rm -f nwws2mqtt 2>/dev/null || true

    # Remove images
    docker rmi $(docker images "$IMAGE_NAME" -q) 2>/dev/null || true

    # Remove volumes (optional)
    read -p "Remove Docker volumes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker volume rm $(docker volume ls -q | grep -E "(mosquitto|postgres|redis|prometheus|grafana)") 2>/dev/null || true
    fi

    log_success "Cleanup completed"
}

show_service_urls() {
    local profile="$1"

    echo
    log_info "Service URLs:"
    echo "  📊 NWWS2MQTT Metrics: http://localhost:8080/metrics"
    echo "  🏥 Health Check:      http://localhost:8080/health"

    if [[ "$profile" == *"mqtt"* ]] || [[ "$profile" == "default" ]] || [[ "$profile" == "full" ]]; then
        echo "  📡 MQTT Broker:       mqtt://localhost:1883"
        echo "  🌐 MQTT WebSocket:    ws://localhost:9001"
    fi

    if [[ "$profile" == *"database"* ]] || [[ "$profile" == "full" ]]; then
        echo "  🗄️  PostgreSQL:       postgresql://localhost:5432/nwws"
    fi

    if [[ "$profile" == *"monitoring"* ]] || [[ "$profile" == "full" ]]; then
        echo "  📈 Prometheus:        http://localhost:9090"
        echo "  📊 Grafana:           http://localhost:3000 (admin/admin)"
    fi

    echo
}

run_compose_command() {
    cd "$DOCKER_DIR"
    docker compose "$@"
}

# Main script logic
main() {
    check_docker

    case "${1:-help}" in
        build)
            build_image "$2"
            ;;
        run)
            run_container
            ;;
        compose)
            check_compose
            shift
            run_compose_command "$@"
            ;;
        up)
            check_compose
            compose_up "$2"
            ;;
        down)
            check_compose
            compose_down
            ;;
        logs)
            check_compose
            show_logs "$2"
            ;;
        shell)
            open_shell
            ;;
        health)
            check_health
            ;;
        clean)
            clean_docker
            ;;
        init)
            init_env
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "Unknown command: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
