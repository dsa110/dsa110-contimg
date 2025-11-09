#!/bin/bash
#
# Test Execution Script for DSA-110 Dashboard
#
# This script runs tests using Docker (required for Ubuntu 18.x compatibility).
# Tests can be run in Docker containers to avoid npm/npx compatibility issues.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_URL="http://localhost:5173"
BACKEND_URL="http://localhost:8010"
TEST_MODE="${1:-all}" # all, e2e, manual, docker-e2e
DOCKER_MODE="${2:-false}" # Use Docker for E2E tests

echo -e "${GREEN}DSA-110 Dashboard Test Suite${NC}"
echo "================================"
echo ""

# Check if services are running
check_service() {
    local url=$1
    local name=$2
    
    echo -e "${YELLOW}Checking $name...${NC}"
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $name is not running at $url${NC}"
        return 1
    fi
}

# Check prerequisites
echo "Checking prerequisites..."
echo ""

FRONTEND_OK=false
BACKEND_OK=false

if check_service "$FRONTEND_URL" "Frontend"; then
    FRONTEND_OK=true
fi

if check_service "$BACKEND_URL/api/health" "Backend"; then
    BACKEND_OK=true
fi

echo ""

if [ "$FRONTEND_OK" = false ] || [ "$BACKEND_OK" = false ]; then
    echo -e "${RED}Error: Required services are not running${NC}"
    echo ""
    echo "Please start the services:"
    echo "  - Frontend: npm run dev (in frontend/)"
    echo "  - Backend: python -m dsa110_contimg.api.main"
    echo ""
    exit 1
fi

# Check if Docker is available
check_docker() {
    if command -v docker &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Run tests in Docker
run_docker_tests() {
    echo -e "${GREEN}Running E2E tests in Docker...${NC}"
    echo ""
    
    # Check if services are running
    if [ "$FRONTEND_OK" = false ] || [ "$BACKEND_OK" = false ]; then
        echo -e "${YELLOW}Warning: Services may not be accessible from Docker container${NC}"
        echo "Make sure services are accessible at:"
        echo "  - Frontend: $FRONTEND_URL"
        echo "  - Backend: $BACKEND_URL"
        echo ""
    fi
    
    # Build test image
    echo -e "${YELLOW}Building test Docker image...${NC}"
    docker build -f docker/Dockerfile.test -t dsa110-test:latest . || {
        echo -e "${RED}Failed to build test image${NC}"
        exit 1
    }
    
    # Run tests in container
    echo -e "${GREEN}Running tests...${NC}"
    docker run --rm \
        --network host \
        --add-host=host.docker.internal:host-gateway \
        -v "$(pwd)/test-results:/app/test-results" \
        -v "$(pwd)/playwright-report:/app/playwright-report" \
        -e BASE_URL="$FRONTEND_URL" \
        -e API_URL="$BACKEND_URL" \
        dsa110-test:latest \
        npx playwright test "$@"
    
    echo ""
    echo -e "${GREEN}Test results saved to: test-results/${NC}"
    echo -e "${GREEN}HTML report: playwright-report/index.html${NC}"
}

echo ""
echo -e "${GREEN}All prerequisites met!${NC}"
echo ""

# Run tests based on mode
case "$TEST_MODE" in
    e2e|docker-e2e)
        if check_docker; then
            run_docker_tests
        else
            echo -e "${RED}Error: Docker is required for E2E tests on Ubuntu 18.x${NC}"
            echo "Please install Docker: https://docs.docker.com/get-docker/"
            exit 1
        fi
        ;;
    manual)
        echo -e "${GREEN}Opening manual test guide...${NC}"
        echo ""
        echo "See docs/testing/COMPREHENSIVE_TESTING_PLAN.md for manual test cases"
        echo ""
        echo "To run E2E tests in Docker, use: ./scripts/run-tests.sh docker-e2e"
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        echo ""
        if check_docker; then
            echo "1. Running E2E tests in Docker..."
            run_docker_tests || echo -e "${YELLOW}Some E2E tests failed${NC}"
        else
            echo -e "${YELLOW}Docker not available. Skipping E2E tests.${NC}"
            echo "Install Docker to run E2E tests: https://docs.docker.com/get-docker/"
        fi
        echo ""
        echo "2. Manual test cases available in:"
        echo "   docs/testing/COMPREHENSIVE_TESTING_PLAN.md"
        ;;
    *)
        echo -e "${RED}Unknown test mode: $TEST_MODE${NC}"
        echo "Usage: $0 [all|e2e|docker-e2e|manual]"
        echo ""
        echo "Modes:"
        echo "  all        - Run all tests (E2E in Docker + show manual guide)"
        echo "  e2e        - Run E2E tests in Docker (same as docker-e2e)"
        echo "  docker-e2e - Run E2E tests in Docker"
        echo "  manual     - Show manual test guide"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Test execution complete!${NC}"

