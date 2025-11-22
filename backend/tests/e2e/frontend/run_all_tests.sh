#!/bin/bash
# Script to run all frontend E2E tests with various options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
TEST_DIR="tests/e2e/frontend"
PARALLEL_WORKERS=4
HEADLESS=true
BROWSER="chromium"
MARKERS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --workers|-w)
            PARALLEL_WORKERS="$2"
            shift 2
            ;;
        --headed|-h)
            HEADLESS=false
            shift
            ;;
        --browser|-b)
            BROWSER="$2"
            shift 2
            ;;
        --markers|-m)
            MARKERS="-m $2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -w, --workers N     Number of parallel workers (default: 4)"
            echo "  -h, --headed        Run in headed mode (see browser)"
            echo "  -b, --browser NAME Browser to use (chromium, firefox, webkit)"
            echo "  -m, --markers MARK  Run only tests with specific markers"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Run all tests in parallel"
            echo "  $0 --workers 8                       # Use 8 parallel workers"
            echo "  $0 --headed                          # Run with visible browser"
            echo "  $0 --markers 'e2e_critical'          # Run only critical tests"
            echo "  $0 --browser firefox                 # Use Firefox browser"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check if casa6 is activated
if [[ -z "$CONDA_DEFAULT_ENV" ]] || [[ "$CONDA_DEFAULT_ENV" != "casa6" ]]; then
    echo -e "${YELLOW}Warning: casa6 environment not activated. Activating...${NC}"
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate casa6 || {
        echo -e "${RED}Error: Could not activate casa6 environment${NC}"
        exit 1
    }
fi

# Set environment variables
export PLAYWRIGHT_HEADLESS=$HEADLESS
export PLAYWRIGHT_BROWSER=$BROWSER

# Check if frontend is running
echo -e "${YELLOW}Checking if frontend is accessible...${NC}"
FRONTEND_URL="${FRONTEND_BASE_URL:-http://localhost:5174}"
if ! curl -s -f "$FRONTEND_URL" > /dev/null 2>&1; then
    echo -e "${RED}Error: Frontend not accessible at $FRONTEND_URL${NC}"
    echo -e "${YELLOW}Please start the frontend: cd frontend && npm run dev${NC}"
    exit 1
fi
echo -e "${GREEN}Frontend is accessible${NC}"

# Check if API is running
echo -e "${YELLOW}Checking if API is accessible...${NC}"
API_URL="${API_URL:-http://localhost:8000}"
if ! curl -s -f "$API_URL/api/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: API not accessible at $API_URL${NC}"
    echo -e "${YELLOW}Some tests may be skipped${NC}"
else
    echo -e "${GREEN}API is accessible${NC}"
fi

# Run tests
echo -e "${GREEN}Running all frontend E2E tests...${NC}"
echo -e "Configuration:"
echo -e "  Workers: $PARALLEL_WORKERS"
echo -e "  Headless: $HEADLESS"
echo -e "  Browser: $BROWSER"
echo -e "  Markers: ${MARKERS:-all}"
echo ""

# Run pytest with parallel execution
pytest "$TEST_DIR" \
    -v \
    -n "$PARALLEL_WORKERS" \
    $MARKERS \
    --tb=short \
    --maxfail=5 \
    --junitxml=test-results/frontend-e2e.xml \
    --html=test-results/frontend-e2e-report.html \
    --self-contained-html

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed (exit code: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE

