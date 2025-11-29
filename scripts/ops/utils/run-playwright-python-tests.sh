#!/bin/bash
# Script to run Playwright Python E2E tests in Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Default values
COMPOSE_FILE="docker/docker-compose.playwright-python.yml"
SERVICES_UP=false
TEST_COMMAND="pytest tests/e2e/frontend/ -v -n auto"
HEADLESS=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build|-b)
            BUILD=true
            shift
            ;;
        --up|-u)
            SERVICES_UP=true
            shift
            ;;
        --down|-d)
            SERVICES_DOWN=true
            shift
            ;;
        --command|-c)
            TEST_COMMAND="$2"
            shift 2
            ;;
        --headed)
            HEADLESS=false
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -b, --build          Rebuild Docker image"
            echo "  -u, --up             Start required services (api, dashboard-dev)"
            echo "  -d, --down           Stop services after tests"
            echo "  -c, --command CMD    Custom pytest command"
            echo "  --headed             Run in headed mode (see browser)"
            echo "  --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests"
            echo "  $0 --build                           # Rebuild image and run"
            echo "  $0 --up                              # Start services, run tests"
            echo "  $0 --command 'pytest test_dashboard.py -v'  # Run specific test"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}=== Playwright Python E2E Tests in Docker ===${NC}\n"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Start required services if requested
if [ "$SERVICES_UP" = true ]; then
    echo -e "${YELLOW}Starting required services...${NC}"
    docker compose up -d api dashboard-dev
    echo -e "${YELLOW}Waiting for services to be ready...${NC}"
    sleep 10
fi

# Build Docker image
BUILD_CMD="docker compose -f $COMPOSE_FILE --profile playwright-python build"
if [ "$BUILD" = true ] || ! docker images | grep -q "dsa110-contimg-playwright-python-tests"; then
    echo -e "${YELLOW}Building Docker image...${NC}"
    $BUILD_CMD
fi

# Run tests
echo -e "${GREEN}Running Playwright Python E2E tests...${NC}"
echo -e "Command: $TEST_COMMAND"
echo ""

# Clean up orphan containers before running
docker compose -f $COMPOSE_FILE down --remove-orphans 2>/dev/null || true

docker compose -f $COMPOSE_FILE \
    --profile playwright-python \
    run --rm \
    -e PLAYWRIGHT_HEADLESS=$HEADLESS \
    playwright-python-tests \
    sh -c "$TEST_COMMAND"

EXIT_CODE=$?

# Copy test results to host
echo -e "\n${YELLOW}Copying test results...${NC}"
mkdir -p test-results/playwright-python
docker compose -f $COMPOSE_FILE \
    --profile playwright-python \
    run --rm -v "$PROJECT_ROOT/test-results/playwright-python:/output" \
    playwright-python-tests \
    sh -c "cp -r /app/test-results/* /output/ 2>/dev/null || true"

# Stop services if requested
if [ "$SERVICES_DOWN" = true ]; then
    echo -e "${YELLOW}Stopping services...${NC}"
    docker compose down
fi

# Report results
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}:check: All tests passed!${NC}"
    echo -e "Test results: test-results/playwright-python/"
else
    echo -e "\n${RED}:cross: Some tests failed (exit code: $EXIT_CODE)${NC}"
    echo -e "Test results: test-results/playwright-python/"
fi

exit $EXIT_CODE

