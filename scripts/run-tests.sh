#!/bin/bash
# Test runner script - organizes tests into logical groups
# Usage: ./scripts/run-tests.sh [category] [options]
#
# Categories (organized by test taxonomy - see docs/concepts/TEST_ORGANIZATION.md):
#   smoke         - Smoke tests (quick sanity checks, < 10s)
#   unit          - All unit tests (fast, isolated)
#   unit-api      - API unit tests
#   unit-calibration - Calibration unit tests
#   unit-conversion - Conversion unit tests
#   unit-database - Database unit tests
#   unit-photometry - Photometry unit tests
#   unit-qa       - QA unit tests
#   integration   - Integration tests (component interactions)
#   integration-streaming - Streaming integration tests
#   integration-pipeline - Pipeline integration tests
#   integration-workflow - Workflow integration tests
#   science       - Science validation tests
#   e2e           - End-to-end tests (full workflows)
#   all           - All tests (default)
#
# Options are passed directly to pytest

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

PYTEST_SAFE="$SCRIPT_DIR/pytest-safe.sh"

# Validate pytest-safe.sh exists
if [ ! -f "$PYTEST_SAFE" ]; then
    echo "Error: pytest-safe.sh not found at $PYTEST_SAFE" >&2
    exit 1
fi
if [ ! -x "$PYTEST_SAFE" ]; then
    echo "Error: pytest-safe.sh is not executable" >&2
    exit 1
fi

# Default category
CATEGORY="${1:-all}"
shift || true  # Remove category from args, keep rest for pytest

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Running tests: ${CATEGORY}${NC}"
echo ""

case "$CATEGORY" in
    smoke)
        echo -e "${GREEN}Running smoke tests (quick sanity checks)...${NC}"
        "$PYTEST_SAFE" tests/smoke/ -m smoke "$@"
        ;;
    unit)
        echo -e "${GREEN}Running all unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/ "$@"
        ;;
    unit-api)
        echo -e "${GREEN}Running API unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/api/ "$@"
        ;;
    unit-calibration)
        echo -e "${GREEN}Running calibration unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/calibration/ "$@"
        ;;
    unit-conversion)
        echo -e "${GREEN}Running conversion unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/conversion/ "$@"
        ;;
    unit-database)
        echo -e "${GREEN}Running database unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/database/ "$@"
        ;;
    unit-photometry)
        echo -e "${GREEN}Running photometry unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/photometry/ "$@"
        ;;
    unit-qa)
        echo -e "${GREEN}Running QA unit tests...${NC}"
        "$PYTEST_SAFE" tests/unit/qa/ "$@"
        ;;
    integration)
        echo -e "${GREEN}Running all integration tests...${NC}"
        "$PYTEST_SAFE" tests/integration/ "$@"
        ;;
    integration-streaming)
        echo -e "${GREEN}Running streaming integration tests...${NC}"
        "$PYTEST_SAFE" tests/integration/test_streaming*.py "$@"
        ;;
    integration-pipeline)
        echo -e "${GREEN}Running pipeline integration tests...${NC}"
        "$PYTEST_SAFE" tests/integration/test_orchestrator*.py tests/integration/test_stage*.py "$@"
        ;;
    integration-workflow)
        echo -e "${GREEN}Running workflow integration tests...${NC}"
        "$PYTEST_SAFE" tests/integration/test_end_to_end*.py "$@"
        ;;
    science)
        echo -e "${GREEN}Running science validation tests...${NC}"
        "$PYTEST_SAFE" tests/science/ "$@"
        ;;
    root)
        echo -e "${GREEN}Running root-level tests...${NC}"
        echo -e "${YELLOW}Note: No root-level test files found. Tests are organized in subdirectories.${NC}"
        "$PYTEST_SAFE" tests/ "$@"
        ;;
    e2e)
        echo -e "${GREEN}Running end-to-end tests...${NC}"
        "$PYTEST_SAFE" tests/e2e/ -m e2e "$@"
        ;;
    quick)
        echo -e "${GREEN}Running quick tests (smoke + unit, no slow tests)...${NC}"
        "$PYTEST_SAFE" tests/smoke/ tests/unit/ -m "not slow" "$@"
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        "$PYTEST_SAFE" tests/ "$@"
        ;;
    *)
        echo -e "${YELLOW}Unknown category: $CATEGORY${NC}"
        echo ""
        echo "Available categories:"
        echo "  smoke, unit, unit-api, unit-calibration, unit-conversion, unit-database"
        echo "  unit-photometry, unit-qa, integration, integration-streaming"
        echo "  integration-pipeline, integration-workflow, science, e2e, quick, all"
        echo ""
        echo "Usage: $0 [category] [pytest-options]"
        exit 1
        ;;
esac
