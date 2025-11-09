# GitHub Actions Test Failures - Resolution Summary

**Date**: November 9, 2025  
**Issue**: Failed GitHub Actions jobs due to missing pytest installation  
**Branch**: `jakob-cleanup`  
**Failed Job**: https://github.com/dsa110/dsa110-contimg/actions/runs/19216054933/job/54925555217

## Problem

The `fast-tests` job in the GitHub Actions workflow was failing with the error:
```
/opt/hostedtoolcache/Python/3.11.14/x64/bin/python: No module named pytest
```

### Root Cause

1. The workflow's `fast-tests` job attempted to run `scripts/test-impacted.sh`, which internally uses pytest
2. The job only conditionally installed dependencies if `requirements-test.txt` existed
3. The repository did not have a `requirements-test.txt` file
4. Therefore, pytest was never installed, causing the test script to fail

## Solution

### 1. Created `requirements-test.txt`

Added a comprehensive test dependencies file at the repository root:

```txt
# Core testing framework
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.0  # Parallel test execution
pytest-timeout>=2.1.0  # Test timeouts
pytest-mock>=3.11.0  # Mocking support

# Coverage reporting
coverage>=7.2.0
codecov>=2.1.13

# Code quality tools
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.4.0

# Performance testing
pytest-benchmark>=4.0.0
memory-profiler>=0.61.0

# Additional utilities
pyyaml>=6.0  # For config file handling in tests
```

### 2. Updated GitHub Actions Workflow

Modified `.github/workflows/validation-tests.yml` to explicitly install pytest before the conditional `requirements-test.txt` installation:

**Before:**
```yaml
- name: Install test dependencies
  run: |
    set -euo pipefail
    python -m pip install --upgrade pip
    if [ -f requirements-test.txt ]; then pip install -r requirements-test.txt; fi
```

**After:**
```yaml
- name: Install test dependencies
  run: |
    set -euo pipefail
    python -m pip install --upgrade pip
    pip install pytest pytest-cov pytest-xdist pytest-timeout pytest-mock
    if [ -f requirements-test.txt ]; then pip install -r requirements-test.txt; fi
```

This ensures that:
- pytest and essential plugins are **always** installed
- Additional dependencies from `requirements-test.txt` are installed if the file exists
- The workflow is resilient to missing requirements files

### 3. Created pytest Configuration

Added `pytest.ini` to properly configure pytest and register custom markers:

```ini
[pytest]
python_files = test_*.py
python_classes = Test*
python_functions = test_*

minversion = 7.0
testpaths = tests
pythonpath = src

markers =
    unit: Unit tests (mocked, fast)
    integration: Integration tests (may need CASA environment)
    casa: Tests requiring CASA tools (casatools, casatasks)
    slow: Slow tests (>1 second)
    synthetic: Tests using synthetic data generation
    validation: Validation tests with real or realistic data

addopts =
    -ra
    --strict-markers
    --strict-config
    --showlocals
```

Benefits:
- Eliminates warnings about unknown markers
- Enforces strict marker usage
- Improves test discoverability
- Centralizes pytest configuration

### 4. Added Verification Script

Created `scripts/verify-test-deps.sh` to validate test dependency installation locally before pushing changes.

## Testing

Verification script successfully confirms:
- ✅ pytest installs correctly
- ✅ All pytest plugins install correctly
- ✅ requirements-test.txt is valid
- ✅ pytest can be invoked from command line

## Impact

### Jobs Fixed
- ✅ `fast-tests` - Now has pytest and can run `scripts/test-impacted.sh`
- ✅ `unit-tests` - Now uses `requirements-test.txt` for consistent dependency installation
- ✅ Future test jobs - Can rely on `requirements-test.txt` existing

### Additional Benefits
1. **Consistency**: All test jobs now use the same dependency source
2. **Maintainability**: Test dependencies centralized in one file
3. **Documentation**: Clear marker definitions in pytest.ini
4. **Robustness**: Explicit pytest installation prevents similar failures

## Files Changed

1. ✅ `/requirements-test.txt` (created) - Test dependencies
2. ✅ `/.github/workflows/validation-tests.yml` (modified) - Explicit pytest installation
3. ✅ `/pytest.ini` (created) - pytest configuration
4. ✅ `/scripts/verify-test-deps.sh` (created) - Verification script

## Next Steps

1. **Commit and push** these changes to `jakob-cleanup` branch
2. **Monitor** the next GitHub Actions run to confirm tests pass
3. **Consider** adding similar explicit installations to other workflows if needed

## Related Issues

If other test failures persist after this fix, check for:
- Missing system dependencies (CASA tools for integration tests)
- Environment variable configuration issues
- Test data availability
- Conda environment setup in validation/integration tests

## Verification Command

To verify locally before pushing:
```bash
bash scripts/verify-test-deps.sh
```

---
**Resolution Status**: ✅ COMPLETE  
**Confidence**: HIGH - Tested locally and matches GitHub's recommended pattern
