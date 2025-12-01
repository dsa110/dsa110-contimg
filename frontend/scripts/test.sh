#!/bin/bash
# Frontend testing script using Docker
# Usage: ./test.sh [watch|ui|coverage]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Build Docker image if it doesn't exist
IMAGE_NAME="dsa110-frontend-test"
if ! docker images | grep -q "$IMAGE_NAME"; then
  echo "Building Docker image..."
  docker build -t "$IMAGE_NAME" -f Dockerfile.dev .
fi

# Run tests based on argument
case "${1:-}" in
  watch)
    echo "Running tests in watch mode..."
    docker run --rm -it \
      -v "$SCRIPT_DIR:/app" \
      -v /app/node_modules \
      "$IMAGE_NAME" \
      npm test -- --watch
    ;;
  ui)
    echo "Running tests with UI (access at http://localhost:51204)..."
    docker run --rm -it \
      -v "$SCRIPT_DIR:/app" \
      -v /app/node_modules \
      -p 51204:51204 \
      "$IMAGE_NAME" \
      npm test -- --ui
    ;;
  coverage)
    echo "Running tests with coverage..."
    docker run --rm \
      -v "$SCRIPT_DIR:/app" \
      -v /app/node_modules \
      "$IMAGE_NAME" \
      npm run test:coverage
    ;;
  *)
    echo "Running tests..."
    docker run --rm \
      -v "$SCRIPT_DIR:/app" \
      -v /app/node_modules \
      "$IMAGE_NAME" \
      npm test
    ;;
esac

