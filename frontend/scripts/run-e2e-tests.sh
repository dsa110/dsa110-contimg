#!/bin/bash
# Run Playwright E2E tests in Docker container
# Usage: ./scripts/run-e2e-tests.sh [test-file] [--headed]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$FRONTEND_DIR"

# Parse arguments
TEST_FILE="${1:-e2e/pipeline-control.spec.ts}"
SERVICE="playwright"

if [[ "$2" == "--headed" ]] || [[ "$1" == "--headed" ]]; then
    SERVICE="playwright-headed"
    if [[ "$1" == "--headed" ]]; then
        TEST_FILE="e2e/pipeline-control.spec.ts"
    fi
fi

echo "🎭 Running Playwright E2E tests in Docker..."
echo "   Test file: $TEST_FILE"
echo "   Service: $SERVICE"
echo ""

# Build and run
docker compose -f docker/docker-compose.test.yml build "$SERVICE"
docker compose -f docker/docker-compose.test.yml run --rm "$SERVICE" \
    npx playwright test "$TEST_FILE" --reporter=html,list

echo ""
echo "✅ Tests complete! View report at: frontend/playwright-report/index.html"
