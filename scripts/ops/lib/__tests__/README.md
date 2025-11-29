# Error Detection Framework - Test Suite

## Overview

Comprehensive test suite for the error detection framework, covering unit tests
and integration tests.

---

## Test Files

### Unit Tests (`error-detection.test.sh`)

Tests individual functions from the error detection library:

- **Pre-flight checks** (6 tests)
  - Node.js version check
  - Required files check
  - Dependencies check
  - Permissions check
- **Execution monitoring** (4 tests)
  - Error detection patterns
  - False positive exclusion
  - Critical warning detection
  - Command execution monitoring

- **Post-execution validation** (6 tests)
  - Build output validation
  - Test result parsing
  - File integrity checks

- **Error detection patterns** (4 tests)
  - Error pattern matching
  - False positive handling
  - Critical warning detection

**Total: 20 unit tests**

---

### Integration Tests (`integration.test.sh`)

Tests the complete workflow end-to-end:

- **run-safe.sh wrapper** (4 tests)
  - Command validation
  - Successful execution
  - Failure detection
  - Error output detection

**Total: 4 integration tests**

---

## Running Tests

### Run All Tests

```bash
# Unit tests
npm run test:error-detection

# Integration tests
npm run test:error-detection:integration

# Or directly
bash scripts/lib/__tests__/error-detection.test.sh
bash scripts/lib/__tests__/integration.test.sh
```

### Run Individual Test Files

```bash
cd /data/dsa110-contimg
bash scripts/lib/__tests__/error-detection.test.sh
bash scripts/lib/__tests__/integration.test.sh
```

---

## Test Coverage

### Pre-Flight Checks

- :check: Node.js version validation
- :check: Required files verification
- :check: Dependencies check
- :check: Permissions validation
- :check: Memory check
- :check: Process conflict detection

### Execution Monitoring

- :check: Exit code detection
- :check: Error pattern matching
- :check: False positive exclusion
- :check: Critical warning detection

### Post-Execution Validation

- :check: Build output validation
- :check: Test result parsing
- :check: File integrity checks

### Integration

- :check: Complete workflow testing
- :check: Error propagation
- :check: Wrapper script functionality

---

## Test Design Principles

1. **Isolation**: Each test runs in a temporary directory
2. **Speed**: Tests complete in seconds
3. **Clarity**: Clear test names and error messages
4. **Coverage**: Tests cover all major functions
5. **Real-world**: Tests based on actual error scenarios

---

## Adding New Tests

### Unit Test Template

```bash
test_start "description of test"
# Setup
# Execute
if condition; then
  test_pass
else
  test_fail "Error message"
fi
```

### Integration Test Template

```bash
test_start "description of test"
if "$RUN_SAFE" "command" > /dev/null 2>&1; then
  test_pass
else
  test_fail "Error message"
fi
```

---

## Test Results

Tests output:

- Test number and description
- PASS/FAIL status
- Summary with counts
- Exit code (0 = all passed, 1 = failures)

---

## Continuous Integration

Tests can be integrated into CI/CD:

```yaml
- name: Run error detection tests
  run: |
    npm run test:error-detection
    npm run test:error-detection:integration
```

---

## Troubleshooting

### Tests Fail to Source Library

```bash
# Check library path
ls -la scripts/lib/error-detection.sh

# Verify sourcing works
source scripts/lib/error-detection.sh
```

### Tests Fail in CI

- Ensure bash is available
- Check file permissions (chmod +x)
- Verify test directory creation works

---

## Status

:check: **Test Suite Complete**

- 20 unit tests
- 4 integration tests
- All tests passing
- Ready for CI/CD integration
