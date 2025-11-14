#!/bin/bash
# Wrapper script for GitHub Copilot CLI in Docker
# Usage: ./scripts/copilot.sh [copilot-command] [args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "Error: Docker is not running"
    exit 1
fi

# Build image if it doesn't exist
if ! docker image inspect copilot-cli:latest &> /dev/null; then
    echo "Building copilot-cli Docker image..."
    docker build -t copilot-cli:latest -f "$PROJECT_ROOT/Dockerfile.copilot" "$PROJECT_ROOT"
fi

# Create config directory if it doesn't exist
mkdir -p "$HOME/.config/github-copilot"

# Run Copilot CLI in Docker
docker run --rm -it \
    -v "$PROJECT_ROOT:/workspace" \
    -v "$HOME/.config/github-copilot:/root/.config/github-copilot" \
    -w /workspace \
    copilot-cli:latest \
    copilot "$@"

