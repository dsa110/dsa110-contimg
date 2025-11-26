#!/bin/bash
# Unit Tests for Error Detection Framework
# Run with: bash scripts/lib/__tests__/error-detection.test.sh

# Don't use set -e here - we need to test failure cases

# Colors for test output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test helper functions
test_start() {
  TESTS_RUN=$((TESTS_RUN + 1))
  echo -n "Test $TESTS_RUN: $1 ... "
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

# Source the library
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")"
source "$LIB_DIR/error-detection.sh" || {
  echo "Failed to source error-detection.sh"
  exit 1
}

# Create temporary test directory
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR" || exit 1

# Cleanup function
cleanup() {
  cd /tmp
  rm -rf "$TEST_DIR"
}
trap cleanup EXIT

echo "=== Error Detection Framework Unit Tests ==="
echo ""

# Test 1: check_node_version - should pass with valid version
test_start "check_node_version with valid version"
if check_node_version "16.0.0" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass with Node.js >= 16.0.0"
fi

# Test 2: verify_required_files - should fail without package.json
test_start "verify_required_files without package.json"
if ! verify_required_files > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when package.json missing"
fi

# Test 3: verify_required_files - should pass with package.json
test_start "verify_required_files with package.json"
echo '{"name": "test"}' > package.json
if verify_required_files > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass when package.json exists"
fi

# Test 4: check_dependencies - should fail without node_modules
test_start "check_dependencies without node_modules"
rm -rf node_modules 2>/dev/null || true
if ! check_dependencies > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when node_modules missing"
fi

# Test 5: check_dependencies - should pass with node_modules
test_start "check_dependencies with node_modules"
mkdir -p node_modules/react node_modules/react-dom node_modules/vite
if check_dependencies > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass when dependencies exist"
fi

# Test 6: check_permissions - should pass with write permission
test_start "check_permissions with write permission"
if check_permissions > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass when directory is writable"
fi

# Test 7: detect_errors - should detect error patterns
test_start "detect_errors with error in output"
ERROR_OUTPUT="npm ERR! code ENOENT"
if ! detect_errors "$ERROR_OUTPUT"; then
  test_pass
else
  test_fail "Should detect errors in output"
fi

# Test 8: detect_errors - should not false positive
test_start "detect_errors with false positive exclusion"
FALSE_POSITIVE="No errors found in the code"
if detect_errors "$FALSE_POSITIVE"; then
  test_pass
else
  test_fail "Should not false positive on 'No errors'"
fi

# Test 9: detect_critical_warnings - should detect critical warnings
test_start "detect_critical_warnings with critical warning"
WARNING_OUTPUT="failed to resolve module"
if ! detect_critical_warnings "$WARNING_OUTPUT"; then
  test_pass
else
  test_fail "Should detect critical warnings"
fi

# Test 10: validate_build_output - should fail without dist
test_start "validate_build_output without dist directory"
rm -rf dist 2>/dev/null || true
if ! validate_build_output > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when dist directory missing"
fi

# Test 11: validate_build_output - should fail without index.html
test_start "validate_build_output without index.html"
mkdir -p dist
if ! validate_build_output > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when index.html missing"
fi

# Test 12: validate_build_output - should fail with empty index.html
test_start "validate_build_output with empty index.html"
touch dist/index.html
if ! validate_build_output > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when index.html is empty"
fi

# Test 13: validate_build_output - should pass with valid build
test_start "validate_build_output with valid build"
echo '<div id="root"></div>' > dist/index.html
if validate_build_output > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass with valid build output"
fi

# Test 14: validate_test_results - should detect no tests found
test_start "validate_test_results with no tests found"
NO_TESTS="No tests found in the test suite"
if ! validate_test_results "$NO_TESTS" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when no tests found"
fi

# Test 15: validate_test_results - should detect test failures
test_start "validate_test_results with test failures"
FAILED_TESTS="5 passed, 2 failed"
if ! validate_test_results "$FAILED_TESTS" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should fail when tests failed"
fi

# Test 16: validate_test_results - should pass with all tests passing
test_start "validate_test_results with all tests passing"
PASSED_TESTS="10 passed, 0 failed"
if validate_test_results "$PASSED_TESTS" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass when all tests pass"
fi

# Test 17: execute_with_monitoring - should detect command failure
test_start "execute_with_monitoring with failing command"
# Temporarily disable exit on error for this test
set +e
OUTPUT=$(execute_with_monitoring "exit 1" 2>&1)
RESULT=$?
set -e
# Function should return non-zero for failing command
if [ $RESULT -ne 0 ]; then
  test_pass
else
  test_fail "Should detect command failure (got exit $RESULT)"
fi

# Test 18: execute_with_monitoring - should pass with successful command
test_start "execute_with_monitoring with successful command"
if execute_with_monitoring "echo 'success'" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass with successful command"
fi

# Test 19: execute_with_monitoring - should detect errors in output
test_start "execute_with_monitoring with error in output"
# Create a command that outputs error but exits 0
ERROR_CMD="echo 'npm ERR! test error' && exit 0"
if ! execute_with_monitoring "$ERROR_CMD" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should detect errors in output even with exit 0"
fi

# Test 20: preflight_checks - should pass in valid environment
test_start "preflight_checks in valid test environment"
# Setup valid environment
echo '{"name": "test"}' > package.json
mkdir -p node_modules/react node_modules/react-dom node_modules/vite
if preflight_checks > /dev/null 2>&1; then
  test_pass
else
  test_fail "Should pass pre-flight checks in valid environment"
fi

echo ""
echo "=== Test Summary ==="
echo "Tests run: $TESTS_RUN"
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
  echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
else
  echo -e "Tests failed: ${GREEN}$TESTS_FAILED${NC}"
fi

if [ $TESTS_FAILED -eq 0 ]; then
  echo ""
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
else
  echo ""
  echo -e "${RED}Some tests failed!${NC}"
  exit 1
fi

