# Edge Case Error Detection - Silent Failures & Missed Errors

## Overview

This document identifies edge cases where errors might occur but not be flagged
by standard error detection mechanisms (exit codes, error prefixes, etc.). We'll
find ways to catch these scenarios.

---

## Category 1: Silent Failures (Exit Code 0, But Wrong)

### Scenario 1.1: Dev Server Starts But Wrong Port

**Problem:**

```bash
npm run dev
# Exit code: 0 (success)
# But server might be on wrong port, or not accessible
```

**Detection Gap:**

- Exit code is 0 (success)
- No error message
- But functionality is broken

**Solution:**

```bash
# After starting dev server, verify it's actually running
npm run dev &
SERVER_PID=$!
sleep 5  # Wait for server to start

# Check if server is responding
if ! curl -f http://localhost:5173 > /dev/null 2>&1; then
  echo "[ERROR] Dev server not responding on expected port"
  kill $SERVER_PID
  exit 1
fi

# Verify correct port
if ! curl -f http://localhost:5173/api/status > /dev/null 2>&1; then
  echo "[ERROR] Server not accessible on expected URL"
  kill $SERVER_PID
  exit 1
fi
```

**Detection Method:** HTTP health check after startup

---

### Scenario 1.2: Build Succeeds But Produces Empty/Broken Files

**Problem:**

```bash
npm run build
# Exit code: 0 (success)
# But dist/ files might be empty, missing, or corrupted
```

**Detection Gap:**

- Build completes successfully
- No error messages
- But output files are invalid

**Solution:**

```bash
npm run build
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
  echo "[ERROR] Build failed"
  exit 1
fi

# Verify build output exists and is valid
if [ ! -d "dist" ]; then
  echo "[ERROR] Build output directory missing"
  exit 1
fi

# Check for critical files
CRITICAL_FILES=("dist/index.html" "dist/assets/index-*.js")
MISSING_FILES=()

for file_pattern in "${CRITICAL_FILES[@]}"; do
  if ! ls $file_pattern > /dev/null 2>&1; then
    MISSING_FILES+=("$file_pattern")
  fi
done

if [ ${#MISSING_FILES[@]} -ne 0 ]; then
  echo "[ERROR] Critical build files missing: ${MISSING_FILES[@]}"
  exit 1
fi

# Verify files are not empty
for file in dist/index.html dist/assets/*.js; do
  if [ -f "$file" ] && [ ! -s "$file" ]; then
    echo "[ERROR] Empty build file: $file"
    exit 1
  fi
done

# Verify HTML contains expected content
if ! grep -q "<div id=\"root\">" dist/index.html; then
  echo "[ERROR] Build output appears corrupted (missing root element)"
  exit 1
fi
```

**Detection Method:** Post-build validation of output files

---

### Scenario 1.3: Tests Pass But Don't Actually Test Anything

**Problem:**

```bash
npx playwright test
# Exit code: 0 (success)
# But tests might be skipped, or test file doesn't exist
```

**Detection Gap:**

- Test command succeeds
- But no tests actually ran

**Solution:**

```bash
TEST_OUTPUT=$(npx playwright test tests/playwright/js9-refactoring.spec.ts 2>&1)
TEST_EXIT=$?

if [ $TEST_EXIT -ne 0 ]; then
  echo "[ERROR] Tests failed"
  exit 1
fi

# Check if tests actually ran
if echo "$TEST_OUTPUT" | grep -q "No tests found"; then
  echo "[ERROR] No tests found - test file might not exist"
  exit 1
fi

if echo "$TEST_OUTPUT" | grep -q "0 passed"; then
  echo "[WARNING] Tests ran but 0 passed - might be skipped or empty"
  # Decide if this is an error or warning
fi

# Verify test count
TEST_COUNT=$(echo "$TEST_OUTPUT" | grep -oP "\d+ passed" | grep -oP "\d+" | head -1)
if [ -z "$TEST_COUNT" ] || [ "$TEST_COUNT" -eq 0 ]; then
  echo "[ERROR] No tests executed"
  exit 1
fi
```

**Detection Method:** Parse test output to verify tests actually ran

---

## Category 2: Partial Failures

### Scenario 2.1: Some Tests Pass, Some Fail, But Exit Code is 0

**Problem:**

```bash
npx playwright test
# Exit code: 0
# But some tests might have been skipped or failed silently
```

**Detection Gap:**

- Overall exit code is 0
- But individual test failures might be ignored

**Solution:**

```bash
TEST_OUTPUT=$(npx playwright test --reporter=json 2>&1)
TEST_EXIT=$?

# Parse JSON output for failures
FAILED_COUNT=$(echo "$TEST_OUTPUT" | jq '.stats.failures' 2>/dev/null || echo "0")
SKIPPED_COUNT=$(echo "$TEST_OUTPUT" | jq '.stats.skipped' 2>/dev/null || echo "0")

if [ "$FAILED_COUNT" -gt 0 ]; then
  echo "[ERROR] $FAILED_COUNT tests failed"
  exit 1
fi

if [ "$SKIPPED_COUNT" -gt 0 ]; then
  echo "[WARNING] $SKIPPED_COUNT tests skipped - investigate why"
fi
```

**Detection Method:** Parse detailed test output for failures/skips

---

### Scenario 2.2: Build Succeeds But Warnings Indicate Problems

**Problem:**

```bash
npm run build
# Exit code: 0
# But warnings indicate potential issues
```

**Detection Gap:**

- Build succeeds
- But warnings suggest problems

**Solution:**

```bash
BUILD_OUTPUT=$(npm run build 2>&1)
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
  echo "[ERROR] Build failed"
  exit 1
fi

# Check for critical warnings
CRITICAL_WARNINGS=(
  "failed to resolve"
  "cannot find module"
  "deprecated"
  "out of memory"
)

for warning in "${CRITICAL_WARNINGS[@]}"; do
  if echo "$BUILD_OUTPUT" | grep -qi "$warning"; then
    echo "[ERROR] Critical warning detected: $warning"
    echo "$BUILD_OUTPUT" | grep -i "$warning"
    exit 1
  fi
done

# Count warnings
WARNING_COUNT=$(echo "$BUILD_OUTPUT" | grep -ci "warning" || echo "0")
if [ "$WARNING_COUNT" -gt 10 ]; then
  echo "[WARNING] High number of warnings: $WARNING_COUNT"
  # Decide if this should be an error
fi
```

**Detection Method:** Parse build output for warnings

---

## Category 3: Environment Issues

### Scenario 3.1: Wrong Node.js Version

**Problem:**

```bash
npm run dev
# Exit code: 0
# But might be using wrong Node.js version
```

**Detection Gap:**

- Command succeeds
- But wrong environment

**Solution:**

```bash
# Check Node.js version before running commands
REQUIRED_NODE_VERSION="18.0.0"
CURRENT_NODE_VERSION=$(node --version | sed 's/v//')

if [ "$(printf '%s\n' "$REQUIRED_NODE_VERSION" "$CURRENT_NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_NODE_VERSION" ]; then
  echo "[ERROR] Node.js version $CURRENT_NODE_VERSION is below required $REQUIRED_NODE_VERSION"
  exit 1
fi

# Check npm version
REQUIRED_NPM_VERSION="9.0.0"
CURRENT_NPM_VERSION=$(npm --version)

if [ "$(printf '%s\n' "$REQUIRED_NPM_VERSION" "$CURRENT_NPM_VERSION" | sort -V | head -n1)" != "$REQUIRED_NPM_VERSION" ]; then
  echo "[ERROR] npm version $CURRENT_NPM_VERSION is below required $REQUIRED_NPM_VERSION"
  exit 1
fi
```

**Detection Method:** Pre-flight environment checks

---

### Scenario 3.2: Missing Dependencies

**Problem:**

```bash
npm run dev
# Exit code: 0
# But node_modules might be incomplete or outdated
```

**Detection Gap:**

- Command succeeds
- But dependencies might be missing

**Solution:**

```bash
# Check if node_modules exists and is populated
if [ ! -d "node_modules" ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  echo "[ERROR] node_modules missing or empty - run npm install"
  exit 1
fi

# Check for critical dependencies
CRITICAL_DEPS=("react" "react-dom" "vite" "playwright")
MISSING_DEPS=()

for dep in "${CRITICAL_DEPS[@]}"; do
  if [ ! -d "node_modules/$dep" ]; then
    MISSING_DEPS+=("$dep")
  fi
done

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
  echo "[ERROR] Missing critical dependencies: ${MISSING_DEPS[@]}"
  echo "Run: npm install"
  exit 1
fi

# Verify package-lock.json matches node_modules
if [ -f "package-lock.json" ]; then
  if ! npm ci --dry-run > /dev/null 2>&1; then
    echo "[WARNING] node_modules out of sync with package-lock.json"
    echo "Consider running: npm ci"
  fi
fi
```

**Detection Method:** Dependency validation before execution

---

## Category 4: Race Conditions & Timing Issues

### Scenario 4.1: Server Starts But Not Ready

**Problem:**

```bash
npm run dev &
# Exit code: 0 (background process started)
# But server might not be ready yet
```

**Detection Gap:**

- Process starts successfully
- But server not ready to accept connections

**Solution:**

```bash
npm run dev &
SERVER_PID=$!

# Wait for server to be ready (with timeout)
MAX_WAIT=30
WAITED=0
READY=false

while [ $WAITED -lt $MAX_WAIT ]; do
  if curl -f http://localhost:5173 > /dev/null 2>&1; then
    READY=true
    break
  fi
  sleep 1
  WAITED=$((WAITED + 1))
done

if [ "$READY" = false ]; then
  echo "[ERROR] Server not ready after $MAX_WAIT seconds"
  kill $SERVER_PID 2>/dev/null
  exit 1
fi

echo "[SUCCESS] Server ready after $WAITED seconds"
```

**Detection Method:** Health check with timeout

---

### Scenario 4.2: Tests Run Before Server Ready

**Problem:**

```bash
npm run dev &
npx playwright test  # Runs immediately
# Tests fail because server not ready
```

**Detection Gap:**

- Both commands succeed individually
- But tests fail due to timing

**Solution:**

```bash
# Start server
npm run dev &
SERVER_PID=$!

# Wait for server ready
wait_for_server() {
  local max_wait=30
  local waited=0

  while [ $waited -lt $max_wait ]; do
    if curl -f http://localhost:5173/api/status > /dev/null 2>&1; then
      return 0
    fi
    sleep 1
    waited=$((waited + 1))
  done

  return 1
}

if ! wait_for_server; then
  echo "[ERROR] Server not ready for tests"
  kill $SERVER_PID 2>/dev/null
  exit 1
fi

# Now run tests
npx playwright test
TEST_EXIT=$?

# Cleanup
kill $SERVER_PID 2>/dev/null

exit $TEST_EXIT
```

**Detection Method:** Explicit wait for readiness before dependent commands

---

## Category 5: Resource Exhaustion

### Scenario 5.1: Out of Memory (Silent Failure)

**Problem:**

```bash
npm run build
# Exit code: 0
# But build might have failed due to memory issues
```

**Detection Gap:**

- Build completes
- But might have hit memory limits

**Solution:**

```bash
# Check available memory before build
AVAILABLE_MEM=$(free -m | awk 'NR==2{print $7}')
MIN_REQUIRED_MEM=2048  # 2GB

if [ "$AVAILABLE_MEM" -lt "$MIN_REQUIRED_MEM" ]; then
  echo "[ERROR] Insufficient memory: ${AVAILABLE_MEM}MB available, ${MIN_REQUIRED_MEM}MB required"
  exit 1
fi

# Monitor build for memory issues
BUILD_OUTPUT=$(npm run build 2>&1)
BUILD_EXIT=$?

if echo "$BUILD_OUTPUT" | grep -qi "out of memory\|ENOMEM\|allocation failed"; then
  echo "[ERROR] Build failed due to memory issues"
  exit 1
fi
```

**Detection Method:** Pre-flight resource checks and output monitoring

---

## Category 6: Network Issues

### Scenario 6.1: API Calls Fail But Tests Pass

**Problem:**

```bash
npx playwright test
# Tests pass
# But API calls might be failing (network issues, wrong URL)
```

**Detection Gap:**

- Tests pass
- But API not actually working

**Solution:**

```bash
# Verify API is accessible before tests
API_URL="http://localhost:8010/api/status"

if ! curl -f "$API_URL" > /dev/null 2>&1; then
  echo "[ERROR] API not accessible at $API_URL"
  echo "Check if backend server is running"
  exit 1
fi

# Verify API returns expected response
API_RESPONSE=$(curl -s "$API_URL")
if ! echo "$API_RESPONSE" | jq . > /dev/null 2>&1; then
  echo "[ERROR] API returned invalid JSON"
  exit 1
fi

# Now run tests
npx playwright test
```

**Detection Method:** Pre-test API health check

---

## Category 7: File System Issues

### Scenario 7.1: Permissions Issues (Silent Failure)

**Problem:**

```bash
npm run build
# Exit code: 0
# But files might not be writable
```

**Detection Gap:**

- Build succeeds
- But output directory might have permission issues

**Solution:**

```bash
# Check write permissions before build
if [ ! -w "." ]; then
  echo "[ERROR] No write permission in current directory"
  exit 1
fi

# Check if dist directory is writable (create if needed)
mkdir -p dist
if [ ! -w "dist" ]; then
  echo "[ERROR] dist directory not writable"
  exit 1
fi

npm run build
```

**Detection Method:** Pre-flight permission checks

---

## Comprehensive Edge Case Detection Script

```bash
#!/bin/bash
# comprehensive-error-detection.sh

set -e  # Exit on error
set -o pipefail  # Catch errors in pipes

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
  exit 1
}

warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Pre-flight checks
echo "=== Pre-Flight Checks ==="

# Check Node.js version
REQUIRED_NODE="18.0.0"
CURRENT_NODE=$(node --version | sed 's/v//')
if [ "$(printf '%s\n' "$REQUIRED_NODE" "$CURRENT_NODE" | sort -V | head -n1)" != "$REQUIRED_NODE" ]; then
  error "Node.js version $CURRENT_NODE < required $REQUIRED_NODE"
fi
success "Node.js version OK: $CURRENT_NODE"

# Check dependencies
if [ ! -d "node_modules" ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
  error "node_modules missing - run npm install"
fi
success "Dependencies installed"

# Check permissions
if [ ! -w "." ]; then
  error "No write permission in current directory"
fi
success "Permissions OK"

# Check memory
AVAILABLE_MEM=$(free -m | awk 'NR==2{print $7}')
MIN_MEM=2048
if [ "$AVAILABLE_MEM" -lt "$MIN_MEM" ]; then
  warning "Low memory: ${AVAILABLE_MEM}MB (recommended: ${MIN_MEM}MB)"
fi

echo ""
echo "=== Running Command ==="

# Run command with comprehensive error detection
COMMAND="$@"
echo "Command: $COMMAND"

# Capture output
OUTPUT=$(eval "$COMMAND" 2>&1)
EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -ne 0 ]; then
  error "Command failed with exit code $EXIT_CODE"
fi

# Check for warnings in output
if echo "$OUTPUT" | grep -qi "warning"; then
  WARNING_COUNT=$(echo "$OUTPUT" | grep -ci "warning")
  warning "Found $WARNING_COUNT warnings in output"
fi

# Check for critical patterns
CRITICAL_PATTERNS=(
  "failed to resolve"
  "cannot find module"
  "out of memory"
  "ENOMEM"
)

for pattern in "${CRITICAL_PATTERNS[@]}"; do
  if echo "$OUTPUT" | grep -qi "$pattern"; then
    error "Critical issue detected: $pattern"
  fi
done

success "Command completed successfully"

# Post-execution validation (if applicable)
if [[ "$COMMAND" == *"build"* ]]; then
  echo ""
  echo "=== Post-Build Validation ==="

  if [ ! -d "dist" ]; then
    error "Build output directory missing"
  fi

  if [ ! -f "dist/index.html" ]; then
    error "Build output file missing: dist/index.html"
  fi

  if [ ! -s "dist/index.html" ]; then
    error "Build output file is empty: dist/index.html"
  fi

  success "Build output validated"
fi

if [[ "$COMMAND" == *"test"* ]]; then
  echo ""
  echo "=== Test Validation ==="

  if echo "$OUTPUT" | grep -qi "no tests found"; then
    error "No tests found"
  fi

  PASSED=$(echo "$OUTPUT" | grep -oP "\d+ passed" | grep -oP "\d+" | head -1 || echo "0")
  FAILED=$(echo "$OUTPUT" | grep -oP "\d+ failed" | grep -oP "\d+" | head -1 || echo "0")

  if [ "$FAILED" -gt 0 ]; then
    error "$FAILED tests failed"
  fi

  success "Tests passed: $PASSED"
fi

echo ""
success "All checks passed"
```

---

## Implementation Plan

### Phase 1: Add Pre-Flight Checks

- [ ] Node.js version check
- [ ] Dependency validation
- [ ] Permission checks
- [ ] Memory checks

### Phase 2: Add Post-Execution Validation

- [ ] Build output validation
- [ ] Test result parsing
- [ ] Warning detection
- [ ] Critical pattern detection

### Phase 3: Add Timing/Readiness Checks

- [ ] Server readiness checks
- [ ] API health checks
- [ ] Timeout handling

### Phase 4: Create Comprehensive Wrapper

- [ ] Combine all checks into single script
- [ ] Make it reusable
- [ ] Add to CI/CD pipeline

---

## Summary

**Edge Cases Identified:**

1. ✓ Silent failures (exit 0, but wrong)
2. ✓ Partial failures (some succeed, some fail)
3. ✓ Environment issues (wrong version, missing deps)
4. ✓ Race conditions (timing issues)
5. ✓ Resource exhaustion (memory, disk)
6. ✓ Network issues (API not accessible)
7. ✓ File system issues (permissions)

**Solutions Provided:**

- Pre-flight checks
- Post-execution validation
- Output parsing
- Health checks
- Comprehensive wrapper script

**Next Steps:**

- Implement pre-flight checks
- Add post-execution validation
- Create comprehensive wrapper
- Integrate into workflow
