# Casa6 Test Execution Guide

## Overview

All Python tests MUST use the casa6 conda environment, which provides:
- Python with CASA dependencies
- Node.js v22.6.0 (for frontend tests)
- Required scientific computing libraries

## Python Tests (Integration/Unit)

### Required Environment

```bash
# Activate casa6 environment
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Verify Python path
which python
# Should output: /opt/miniforge/envs/casa6/bin/python

# Verify Node.js version
node --version
# Should output: v22.6.0
```

### Running Tests

```bash
# Integration tests (uses casa6 Python automatically via Makefile)
make test-integration

# Parallel integration tests
make test-integration-parallel

# Fast integration tests only
make test-integration-fast

# Direct pytest (must use casa6 Python)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/integration/ -v
```

### Makefile Integration

The Makefile automatically:
1. Checks for casa6 Python at `/opt/miniforge/envs/casa6/bin/python`
2. Uses it for all Python test execution
3. Provides clear error messages if casa6 is not found

## Frontend Tests (Unit/E2E)

### Node.js Version

Frontend tests use Node.js from casa6:
- **System Node.js:** v16.20.2 (too old, incompatible)
- **Casa6 Node.js:** v22.6.0 (required)

### Running Frontend Tests

```bash
# Activate casa6 first
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Verify Node.js version
node --version  # Should be v22.6.0

# Run unit tests
cd frontend
npm test

# Run E2E tests
npx playwright test
```

### Why Casa6 Node.js?

- System Node.js v16.20.2 is incompatible with:
  - Modern npm packages
  - Vitest/Vite requirements
  - Playwright requirements
- Casa6 Node.js v22.6.0 provides:
  - Modern JavaScript features
  - Compatible with all test tools
  - Consistent environment

## Verification

### Check Casa6 Availability

```bash
# Python
test -x /opt/miniforge/envs/casa6/bin/python && echo "✓ casa6 Python OK" || echo "✗ casa6 Python missing"

# Node.js
/opt/miniforge/envs/casa6/bin/node --version && echo "✓ casa6 Node.js OK" || echo "✗ casa6 Node.js missing"

# npm
/opt/miniforge/envs/casa6/bin/npm --version && echo "✓ casa6 npm OK" || echo "✗ casa6 npm missing"
```

### Test Execution Verification

All test commands should show:
- Python: `/opt/miniforge/envs/casa6/bin/python`
- Node.js: `v22.6.0`
- No compatibility warnings

## Troubleshooting

### Error: "casa6 Python not found"

```bash
# Check if casa6 exists
ls -la /opt/miniforge/envs/casa6/bin/python

# If missing, install casa6 environment
# (See project setup documentation)
```

### Error: "crypto$2.getRandomValues is not a function"

This indicates Node.js version mismatch:
```bash
# Use casa6 Node.js
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
node --version  # Should be v22.6.0
```

### Error: "npm warn cli npm v10.8.2 does not support Node.js v16.20.2"

This means system Node.js is being used:
```bash
# Ensure casa6 is activated
conda activate casa6
which node  # Should be /opt/miniforge/envs/casa6/bin/node
```

## Best Practices

1. **Always activate casa6 before running tests**
   ```bash
   source /opt/miniforge/etc/profile.d/conda.sh
   conda activate casa6
   ```

2. **Use Makefile targets** (they handle casa6 automatically)
   ```bash
   make test-integration
   make test-unit  # For Python unit tests
   ```

3. **Verify environment before testing**
   ```bash
   which python  # Should show casa6 path
   node --version  # Should be v22.6.0
   ```

4. **For frontend tests, ensure casa6 Node.js**
   ```bash
   conda activate casa6
   cd frontend
   npm test
   ```

## CI/CD Considerations

In CI/CD pipelines:
- Ensure casa6 environment is available
- Use casa6 Python for all Python tests
- Use casa6 Node.js for all frontend tests
- Verify environment before test execution

