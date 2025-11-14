# Using Pytest Safely: Preventing 2>&1 Redirection Errors

## Problem

When using shell redirection with pytest, `2>&1` can be incorrectly passed as a
test path argument, causing:

```
ERROR: file or directory not found: 2>&1
```

## Solution: Multi-Layer Enforcement

We've implemented **multiple layers of protection** to prevent this error, even
if developers try to make the mistake:

### Layer 1: Safe Pytest Wrapper Script ✅

**File:** `scripts/pytest-safe.sh`

This script automatically filters out problematic redirection patterns before
they reach pytest.

**Usage:**

```bash
# ✅ CORRECT - Use the safe wrapper
./scripts/pytest-safe.sh tests/ -v

# ✅ CORRECT - Redirection handled properly
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail

# ✅ CORRECT - Output to file
./scripts/pytest-safe.sh tests/ -v > output.log 2>&1
```

**How it works:**

- Filters out `2>&1`, `>`, `2>` from pytest arguments
- Handles redirection properly at the shell level
- Prevents `2>&1` from being passed as a test path

### Layer 2: Pytest Plugin Validation ✅

**File:** `tests/conftest.py`

A pytest plugin that validates arguments during pytest startup and exits with a
clear error message if problematic patterns are detected.

**How it works:**

- Checks all pytest arguments during `pytest_configure`
- Detects `2>&1` patterns in arguments
- Exits with helpful error message before test collection

### Layer 3: Pre-Commit Hook ✅

**File:** `.git/hooks/pre-commit`

Validates staged files for problematic pytest usage patterns before allowing
commits.

**How it works:**

- Scans staged shell scripts, Python files, and Makefiles
- Detects patterns like `pytest.*2>&1` in code
- Blocks commits if problematic patterns are found
- Provides clear error message with fix instructions

### Layer 4: Updated Test Runner ✅

**File:** `scripts/run-tests.sh`

All pytest invocations now use the safe wrapper automatically.

**Usage:**

```bash
# All these now use pytest-safe.sh automatically
./scripts/run-tests.sh unit
./scripts/run-tests.sh integration
./scripts/run-tests.sh all
```

### Layer 5: Makefile Targets ✅

**File:** `Makefile`

Added validation target for pytest usage patterns.

**Usage:**

```bash
make test-pytest-validate
```

## Enforcement Summary

| Layer               | When It Catches | Action                                 |
| ------------------- | --------------- | -------------------------------------- |
| **Safe Wrapper**    | Runtime         | Filters arguments, handles redirection |
| **Pytest Plugin**   | Test collection | Exits with error if pattern detected   |
| **Pre-commit Hook** | Before commit   | Blocks commit, shows error             |
| **Test Runner**     | Always          | Uses safe wrapper automatically        |
| **Makefile**        | Manual check    | Validates patterns in codebase         |

## Developer Guidelines

### ✅ DO

```bash
# Use the safe wrapper
./scripts/pytest-safe.sh tests/ -v

# Use the test runner (uses safe wrapper automatically)
./scripts/run-tests.sh unit

# Proper shell redirection with safe wrapper
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail
```

### ❌ DON'T

```bash
# Don't use pytest directly with problematic redirection
pytest tests/ 2>&1  # May cause error

# Don't embed 2>&1 in scripts without using safe wrapper
python -m pytest tests/ 2>&1  # May cause error
```

## What Happens If You Try?

### Scenario 1: Direct pytest with 2>&1

```bash
$ /opt/miniforge/envs/casa6/bin/python -m pytest tests/ 2>&1
ERROR: Detected shell redirection pattern in pytest arguments: 2>&1
This indicates improper shell redirection handling.
Use scripts/pytest-safe.sh instead...
```

**Result:** Pytest plugin catches it and exits with clear error.

### Scenario 2: Committing problematic code

```bash
$ git commit -m "Add test script"
Validating pytest usage patterns...
WARNING: Found potentially problematic pytest pattern in scripts/my-test.sh:
  Pattern: pytest.*2>&1
ERROR: Found problematic pytest usage patterns!
Please use scripts/pytest-safe.sh for pytest invocations.
```

**Result:** Pre-commit hook blocks the commit.

### Scenario 3: Using safe wrapper

```bash
$ ./scripts/pytest-safe.sh tests/ -v 2>&1 | tail
============================= test session starts ==============================
...
29 passed in 2.41s
```

**Result:** Works correctly - redirection handled properly.

## Migration Guide

If you have existing scripts with pytest calls:

### Before:

```bash
#!/bin/bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/ -v 2>&1 | tail
```

### After:

```bash
#!/bin/bash
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail
```

Or use the test runner:

```bash
#!/bin/bash
./scripts/run-tests.sh all
```

## Verification

Test that enforcement works:

```bash
# Test 1: Safe wrapper works
./scripts/pytest-safe.sh tests/unit/simulation/test_edge_cases_comprehensive.py::TestExtremeParameters::test_very_small_flux -v

# Test 2: Validation script works
make test-pytest-validate

# Test 3: Pre-commit hook works (try committing problematic code)
# (Will be caught by pre-commit hook)
```

## Related Documentation

- `docs/dev/PYTEST_REDIRECTION_FIX.md` - Detailed explanation of the issue
- `scripts/pytest-safe.sh` - Safe wrapper implementation
- `scripts/validate-pytest-usage.sh` - Validation script
- `.git/hooks/pre-commit` - Pre-commit hook
