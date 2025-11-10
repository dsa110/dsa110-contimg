#!/bin/bash
#
# DSA-110 Continuum Imaging Pipeline Deployment Script
#
# Usage:
#   ./ops/deploy.sh [--mode streaming|manual|both] [--env-file path/to/.env]
#
# This script provides clean deployment of the pipeline with different modes:
#   - streaming: Deploy with streaming service enabled
#   - manual: Deploy API and frontend only (no streaming)
#   - both: Deploy everything (default)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOCKER_DIR="${REPO_ROOT}/ops/docker"

# Default values
MODE="both"
ENV_FILE="${DOCKER_DIR}/.env"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--mode streaming|manual|both] [--env-file path/to/.env]"
      echo ""
      echo "Modes:"
      echo "  streaming: Deploy with streaming service enabled"
      echo "  manual:    Deploy API and frontend only (no streaming)"
      echo "  both:      Deploy everything (default)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Validate mode
if [[ ! "$MODE" =~ ^(streaming|manual|both)$ ]]; then
  echo "Error: Invalid mode '$MODE'. Must be one of: streaming, manual, both"
  exit 1
fi

# Check if .env file exists
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: Environment file not found: $ENV_FILE"
  echo "Please create it from .env.example or specify with --env-file"
  exit 1
fi

# Source environment variables
set -a
source "$ENV_FILE"
set +a

# Validate required environment variables
REQUIRED_VARS=(
  "CONTIMG_API_PORT"
  "CONTIMG_INPUT_DIR"
  "CONTIMG_OUTPUT_DIR"
  "CONTIMG_QUEUE_DB"
  "CONTIMG_REGISTRY_DB"
  "CONTIMG_PRODUCTS_DB"
  "CONTIMG_STATE_DIR"
)

MISSING_VARS=()
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    MISSING_VARS+=("$var")
  fi
done

if [[ ${#MISSING_VARS[@]} -gt 0 ]]; then
  echo "Error: Missing required environment variables:"
  printf '  - %s\n' "${MISSING_VARS[@]}"
  exit 1
fi

# Validate directories
echo "Validating directories..."
for dir in "$CONTIMG_INPUT_DIR" "$CONTIMG_OUTPUT_DIR" "$CONTIMG_STATE_DIR"; do
  if [[ ! -d "$dir" ]]; then
    echo "Warning: Directory does not exist: $dir"
    echo "  Creating directory..."
    mkdir -p "$dir" || {
      echo "Error: Failed to create directory: $dir"
      exit 1
    }
  fi
done

# Check Docker and docker-compose
if ! command -v docker &> /dev/null; then
  echo "Error: Docker is not installed or not in PATH"
  exit 1
fi

if ! command -v docker-compose &> /dev/null; then
  echo "Error: docker-compose is not installed or not in PATH"
  exit 1
fi

# Check if casa6 Python exists
CASA6_PYTHON_BIN="${CASA6_PYTHON_BIN:-/opt/miniforge/envs/casa6/bin/python}"
CASA6_PYTHON="${CASA6_PYTHON_BIN} -W ignore::DeprecationWarning"
if [[ ! -x "$CASA6_PYTHON_BIN" ]]; then
  echo "Error: CASA6 Python not found at: $CASA6_PYTHON_BIN"
  echo "Please set CASA6_PYTHON environment variable or install casa6 conda environment"
  exit 1
fi

echo "✓ CASA6 Python found: $CASA6_PYTHON"

# Change to docker directory
cd "$DOCKER_DIR"

# Determine which services to start
SERVICES=("api" "frontend")

case "$MODE" in
  streaming)
    SERVICES+=("stream" "scheduler")
    echo "Deploying in STREAMING mode..."
    ;;
  manual)
    echo "Deploying in MANUAL mode (API + Frontend only)..."
    ;;
  both)
    SERVICES+=("stream" "scheduler")
    echo "Deploying in BOTH mode (all services)..."
    ;;
esac

# Build images
echo ""
echo "Building Docker images..."
docker-compose build "${SERVICES[@]}"

# Start services
echo ""
echo "Starting services: ${SERVICES[*]}..."
docker-compose up -d "${SERVICES[@]}"

# Wait for services to be ready
echo ""
echo "Waiting for services to be ready..."
sleep 5

# Health checks
echo ""
echo "Performing health checks..."

# Check API
API_URL="http://localhost:${CONTIMG_API_PORT}"
MAX_RETRIES=30
RETRY_COUNT=0

while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
  if curl -sf "${API_URL}/api/status" > /dev/null 2>&1; then
    echo "✓ API is healthy"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  sleep 2
done

if [[ $RETRY_COUNT -eq $MAX_RETRIES ]]; then
  echo "✗ API health check failed after ${MAX_RETRIES} retries"
  echo "  Check logs with: docker-compose logs api"
  exit 1
fi

# Check frontend
FRONTEND_URL="http://localhost:5173"
RETRY_COUNT=0

while [[ $RETRY_COUNT -lt $MAX_RETRIES ]]; do
  if curl -sf "${FRONTEND_URL}" > /dev/null 2>&1; then
    echo "✓ Frontend is healthy"
    break
  fi
  RETRY_COUNT=$((RETRY_COUNT + 1))
  sleep 2
done

if [[ $RETRY_COUNT -eq $MAX_RETRIES ]]; then
  echo "✗ Frontend health check failed after ${MAX_RETRIES} retries"
  echo "  Check logs with: docker-compose logs frontend"
  exit 1
fi

# Check streaming service (if deployed)
if [[ "$MODE" == "streaming" ]] || [[ "$MODE" == "both" ]]; then
  echo "Checking streaming service status..."
  sleep 3
  
  # Check if streaming container is running
  if docker-compose ps stream | grep -q "Up"; then
    echo "✓ Streaming service container is running"
  else
    echo "✗ Streaming service container is not running"
    echo "  Check logs with: docker-compose logs stream"
  fi
fi

# Summary
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Mode: $MODE"
echo "Services deployed: ${SERVICES[*]}"
echo ""
echo "Access points:"
echo "  - Frontend: http://localhost:5173"
echo "  - API:      http://localhost:${CONTIMG_API_PORT}"
echo ""
echo "Useful commands:"
echo "  - View logs:    docker-compose logs -f [service]"
echo "  - Stop all:     docker-compose down"
echo "  - Restart:      docker-compose restart [service]"
echo "  - Status:       docker-compose ps"
echo ""
if [[ "$MODE" == "streaming" ]] || [[ "$MODE" == "both" ]]; then
  echo "Streaming service can be controlled via the dashboard at:"
  echo "  http://localhost:5173/streaming"
  echo ""
fi

