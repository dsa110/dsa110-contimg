# Node.js v16 Compatibility Issue - Prevention Safeguards

**Date:** 2025-11-14

## Problem

Frontend tests fail with `crypto$2.getRandomValues is not a function` when using
system Node.js v16.20.2 instead of casa6 Node.js v22.6.0.

## Solution: Multi-Layer Safeguards

### Layer 1: Pre-flight Check Script ✅

**File**: `frontend/scripts/check-casa6-node.sh`

- **Purpose**: Verifies casa6 Node.js is active before running tests
- **Integration**: Automatically runs via `npm test` command
- **Behavior**: Fails fast with clear error message if wrong Node.js detected

**Example Error**:

```
ERROR: Not using casa6 Node.js
Current: /usr/bin/node (v16.20.2)
Required: /opt/miniforge/envs/casa6/bin/node (v22.6.0)

Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6
```

### Layer 2: npm test Integration ✅

**File**: `frontend/package.json`

```json
"test": "bash scripts/check-casa6-node.sh && vitest"
```

- **Purpose**: Ensures check runs before every test execution
- **Behavior**: Prevents tests from running with wrong Node.js version
- **Impact**: Cannot accidentally run tests without casa6

### Layer 3: Error Detection Framework ✅

**File**: `scripts/lib/error-detection.sh`

- **Purpose**: Detects frontend test context and enforces casa6 Node.js
- **Behavior**: Checks for `package.json` + `vitest.config.ts` to identify
  frontend tests
- **Integration**: Used by `run-safe.sh` wrapper script
- **Impact**: Catches issue during pre-flight checks in CI/CD

### Layer 4: Documentation ✅

**Files**:

- `frontend/NODE_VERSION_REQUIREMENT.md` - User guide
- `docs/dev/casa6_test_execution.md` - Complete casa6 guide
- `frontend/UNIT_TEST_STATUS.md` - Test status with solution

## How It Works

### Normal Flow (Correct)

```bash
# User activates casa6
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Runs npm test
cd frontend
npm test

# ✅ check-casa6-node.sh passes
# ✅ Tests run with Node.js v22.6.0
```

### Error Flow (Wrong Node.js)

```bash
# User forgets to activate casa6
cd frontend
npm test

# ❌ check-casa6-node.sh fails
# ❌ Error message displayed
# ❌ Tests never run
```

## Testing the Safeguards

### Test 1: Correct Node.js (Should Pass)

```bash
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
cd frontend
bash scripts/check-casa6-node.sh
# Expected: ✓ Using casa6 Node.js: 22.6.0
```

### Test 2: Wrong Node.js (Should Fail)

```bash
conda deactivate  # Use system Node.js
cd frontend
bash scripts/check-casa6-node.sh
# Expected: ERROR: Not using casa6 Node.js
```

### Test 3: npm test Integration

```bash
conda deactivate
cd frontend
npm test
# Expected: Check fails, tests never run
```

## CI/CD Integration

Ensure CI/CD pipelines activate casa6:

```yaml
- name: Activate casa6
  run: |
    source /opt/miniforge/etc/profile.d/conda.sh
    conda activate casa6

- name: Run frontend tests
  run: |
    cd frontend
    npm test  # Automatically checks casa6 Node.js
```

## Why Multiple Layers?

1. **Pre-flight Script**: Fast, explicit check that's easy to understand
2. **npm Integration**: Automatic enforcement for all test runs
3. **Error Detection Framework**: Catches issue in broader workflows
4. **Documentation**: Helps users understand why and how

## Maintenance

- **Check Script**: Update if casa6 path changes
- **Error Detection**: Update if frontend test detection logic changes
- **Documentation**: Keep in sync with actual implementation

## Related Files

- `frontend/scripts/check-casa6-node.sh` - Pre-flight check
- `frontend/package.json` - npm test integration
- `scripts/lib/error-detection.sh` - Error detection framework
- `docs/dev/casa6_test_execution.md` - Complete guide
