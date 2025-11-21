# Node.js Version Requirement for Frontend Tests

**Date:** 2025-11-14

## Critical Requirement

**Frontend tests MUST use casa6 Node.js v22.6.0, NOT system Node.js v16.20.2**

## Why?

- **System Node.js v16.20.2** is incompatible with Vitest/Vite crypto
  requirements
- **Casa6 Node.js v22.6.0** provides modern JavaScript features and crypto
  support
- Tests will fail with `crypto$2.getRandomValues is not a function` if using
  system Node.js

## Safeguards

### 1. Pre-flight Check Script

`scripts/check-casa6-node.sh` automatically verifies casa6 Node.js before
running tests.

### 2. npm test Integration

The `npm test` command now includes the check:

```json
"test": "bash scripts/check-casa6-node.sh && vitest"
```

### 3. Error Detection Framework

`scripts/lib/error-detection.sh` detects frontend test context and enforces
casa6 Node.js.

## How to Use

### Correct Way (Always)

```bash
# Activate casa6 first
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Verify Node.js version
node --version  # Should be v22.6.0
which node      # Should be /opt/miniforge/envs/casa6/bin/node

# Run tests
cd frontend
npm test
```

### What Happens If You Forget?

The check script will fail with a clear error:

```
ERROR: Not using casa6 Node.js
Current: /usr/bin/node (v16.20.2)
Required: /opt/miniforge/envs/casa6/bin/node (v22.6.0)

Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6
```

## CI/CD Integration

Ensure CI/CD pipelines activate casa6 before running frontend tests:

```yaml
- name: Activate casa6
  run: |
    source /opt/miniforge/etc/profile.d/conda.sh
    conda activate casa6

- name: Run frontend tests
  run: |
    cd frontend
    npm test
```

## Verification

To manually verify casa6 Node.js is active:

```bash
which node
# Should output: /opt/miniforge/envs/casa6/bin/node

node --version
# Should output: v22.6.0
```

## Related Documentation

- `docs/dev/casa6_test_execution.md` - Complete casa6 guide
- `scripts/check-casa6-node.sh` - Pre-flight check script
- `scripts/lib/error-detection.sh` - Error detection framework
