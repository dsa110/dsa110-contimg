#!/bin/bash
# Integration Tests for Error Detection Framework
# Tests the complete workflow end-to-end

# Don't use set -e here - we need to test failure cases

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

test_start() {
  TESTS_RUN=$((TESTS_RUN + 1))
  echo -n "Integration Test $TESTS_RUN: $1 ... "
}

test_pass() {
  TESTS_PASSED=$((TESTS_PASSED + 1))
  echo -e "${GREEN}PASS${NC}"
}

test_fail() {
  TESTS_FAILED=$((TESTS_FAILED + 1))
  echo -e "${RED}FAIL${NC}"
  echo "  Error: $1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
RUN_SAFE="$ROOT_DIR/scripts/run-safe.sh"

echo "=== Error Detection Framework Integration Tests ==="
echo ""

# Test 1: run-safe.sh should fail without command
test_start "run-safe.sh without command"
if ! "$RUN_SAFE" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when no command provided"
fi

# Test 2: run-safe.sh should work with valid command
test_start "run-safe.sh with valid command"
# Need to be in a directory with package.json for pre-flight checks
cd "$ROOT_DIR/frontend" 2>/dev/null || cd "$ROOT_DIR"
if "$RUN_SAFE" "echo 'test'" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass with valid command"
fi

# Test 3: run-safe.sh should detect command failure
test_start "run-safe.sh with failing command"
set +e
"$RUN_SAFE" "false" > /dev/null 2>&1
RESULT=$?
set -e
if [ $RESULT -ne 0 ]; then
  test_pass
else
  test_fail "Should detect command failure"
fi

# Test 4: run-safe.sh should detect errors in output
test_start "run-safe.sh with error in output"
ERROR_CMD="echo 'npm ERR! test' && exit 0"
if ! "$RUN_SAFE" "$ERROR_CMD" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should detect errors in output"
fi

echo ""
echo "=== Integration Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
  echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
  echo -e "Tests failed: ${GREEN}$TESTS_FAILED${NC}"
fi

if [ $TESTS_FAILED -eq 0 ]; then
  echo ""
  echo -e "${GREEN}All integration tests passed!${NC}"
  exit 0
else
  echo ""
  echo -e "${RED}Some integration tests failed!${NC}"
  exit 1
fi

