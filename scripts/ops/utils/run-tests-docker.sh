#!/bin/bash
#
# Docker-based Test Execution Script for DSA-110 Dashboard
#
# This script uses Docker Compose to run E2E tests with all required services.
# Use this when you want to run tests in a completely isolated environment.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}DSA-110 Dashboard E2E Tests (Docker Compose)${NC}"
echo "=============================================="
echo ""

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose not found${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Use 'docker compose' if available, otherwise 'docker-compose'
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Change to docker directory
cd "$(dirname "$0")/../docker" || exit 1

# Parse command line arguments
COMMAND="${1:-up}"
TEST_ARGS="${@:2}"

case "$COMMAND" in
    up|run)
        echo -e "${GREEN}Starting test environment...${NC}"
        echo ""
        
        # Start services in background (if needed)
        echo "Starting frontend and API services..."
        $DOCKER_COMPOSE -f docker-compose.test.yml up -d frontend-test api-test 2>/dev/null || true
        
        # Wait for services to be ready
        echo "Waiting for services to be ready..."
        sleep 5
        
        # Run tests
        echo -e "${GREEN}Running E2E tests...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml run --rm test-runner npx playwright test $TEST_ARGS
        
        # Show results
        echo ""
        echo -e "${GREEN}Test execution complete!${NC}"
        echo ""
        echo "Test results: test-results/"
        echo "HTML report: playwright-report/index.html"
        ;;
    
    build)
        echo -e "${GREEN}Building test Docker image...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml build test-runner
        ;;
    
    down|stop)
        echo -e "${YELLOW}Stopping test services...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml down
        ;;
    
    clean)
        echo -e "${YELLOW}Cleaning up test environment...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml down -v
        docker rmi dsa110-test:latest 2>/dev/null || true
        ;;
    
    shell)
        echo -e "${GREEN}Opening test container shell...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml run --rm test-runner sh
        ;;
    
    ui)
        echo -e "${GREEN}Running Playwright UI mode...${NC}"
        $DOCKER_COMPOSE -f docker-compose.test.yml run --rm -p 9323:9323 test-runner npx playwright test --ui --host 0.0.0.0
        ;;
    
    *)
        echo "Usage: $0 [command] [test-args]"
        echo ""
        echo "Commands:"
        echo "  up, run    - Run E2E tests (default)"
        echo "  build      - Build test Docker image"
        echo "  down, stop - Stop test services"
        echo "  clean      - Clean up test environment"
        echo "  shell      - Open shell in test container"
        echo "  ui         - Run Playwright in UI mode"
        echo ""
        echo "Examples:"
        echo "  $0 up                          # Run all tests"
        echo "  $0 run --grep 'Navigation'     # Run specific tests"
        echo "  $0 ui                          # Run in UI mode"
        exit 1
        ;;
esac

