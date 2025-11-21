# Test Organization Enforcement System

## Overview

The test organization system is **automatically enforced** through multiple
mechanisms to ensure all tests follow the established taxonomy. This is not just
documentation - it's a **mandatory system** that prevents improperly organized
tests from being committed.

## Enforcement Mechanisms

### 1. Pre-Commit Hook (Automatic)

**Location:** `.git/hooks/pre-commit`

**What it does:**

- Automatically runs when you commit test files
- Validates only staged test files (fast)
- Blocks commit if validation fails
- Provides clear error messages

**Installation:**

```bash
./scripts/test-organization-enforcer.sh install
```

**How it works:**

- Detects staged test files (`tests/**/test_*.py`)
- Runs `scripts/validate-test-organization.py --staged-only`
- Fails commit if validation errors found
- Allows commit if validation passes

### 2. Validation Script (Manual/CI)

**Location:** `scripts/validate-test-organization.py`

**What it does:**

- Validates all test files or staged files only
- Checks file location matches test type
- Verifies pytest markers are present and correct
- Reports errors and warnings

**Usage:**

```bash
# Validate all tests
./scripts/validate-test-organization.py

# Validate only staged files (for pre-commit)
./scripts/validate-test-organization.py --staged-only

# Strict mode (warnings become errors)
./scripts/validate-test-organization.py --strict
```

**What it checks:**

- ✅ Test file is in correct directory for its type
- ✅ Test file has appropriate pytest marker
- ✅ Marker matches file location
- ✅ Test file contains actual test functions/classes

### 3. Test Template Generator (Prevention)

**Location:** `scripts/test-template.py`

**What it does:**

- Generates properly organized test files
- Includes correct markers and structure
- Ensures correct directory placement
- Provides boilerplate code

**Usage:**

```bash
# Create unit test
python scripts/test-template.py unit api new_endpoint

# Create integration test
python scripts/test-template.py integration new_workflow

# Create smoke test
python scripts/test-template.py smoke critical_path
```

**Benefits:**

- Prevents mistakes by starting with correct structure
- Saves time with boilerplate
- Ensures consistency

### 4. CI/CD Integration (Automated)

**Location:** `.github/workflows/test-organization.yml`

**What it does:**

- Runs on every PR that modifies test files
- Validates all tests in strict mode
- Fails CI if validation fails
- Prevents merging improperly organized tests

**Triggers:**

- Pull requests with changes to `tests/**/*.py`
- Pushes to main/develop branches

### 5. Makefile Targets (Convenience)

**Location:** `Makefile`

**Targets:**

- `make test-validate` - Run validation
- `make test-org-install` - Install pre-commit hook
- `make test-org-check` - Check organization

## Validation Rules

### Rule 1: Location Must Match Type

**Enforced:** ✅ Automatic

Tests must be in the correct directory:

- Unit tests → `tests/unit/<module>/`
- Integration tests → `tests/integration/`
- Smoke tests → `tests/smoke/`
- Science tests → `tests/science/`
- E2E tests → `tests/e2e/`

**Violation Example:**

```
ERROR: tests/test_my_feature.py
  Test file not in expected location. Expected one of: tests/unit/, tests/integration/, etc.
```

### Rule 2: Marker Must Match Location

**Enforced:** ✅ Automatic

Tests must have the correct pytest marker:

- `tests/unit/` → `@pytest.mark.unit`
- `tests/integration/` → `@pytest.mark.integration`
- `tests/smoke/` → `@pytest.mark.smoke`
- `tests/science/` → `@pytest.mark.science`
- `tests/e2e/` → `@pytest.mark.e2e`

**Violation Example:**

```
WARNING: tests/unit/api/test_endpoint.py
  Marker mismatch: has @pytest.mark.integration but location suggests @pytest.mark.unit
```

### Rule 3: Marker Must Be Present

**Enforced:** ✅ Automatic (warning, strict mode = error)

All tests must have appropriate markers.

**Violation Example:**

```
WARNING: tests/unit/api/test_endpoint.py
  Missing pytest marker. Expected @pytest.mark.unit for tests in tests/unit/
```

### Rule 4: Unit Tests Must Be in Module Subdirectories

**Enforced:** ✅ Automatic

Unit tests must be in appropriate module subdirectory:

- API tests → `tests/unit/api/`
- Calibration tests → `tests/unit/calibration/`
- etc.

**Violation Example:**

```
WARNING: tests/unit/test_api_feature.py
  Unit test in unexpected subdirectory. Expected one of: api, calibration, catalog, ...
```

## Workflow for Adding Tests

### Step 1: Use Template (Recommended)

```bash
python scripts/test-template.py unit api new_feature
```

This creates:

- Correct directory structure
- Proper file naming
- Correct pytest markers
- Boilerplate code

### Step 2: Implement Tests

Edit the generated file to add your test logic.

### Step 3: Validate

```bash
./scripts/validate-test-organization.py
```

### Step 4: Commit

The pre-commit hook will automatically validate before commit.

## Bypassing Enforcement (Not Recommended)

If you need to bypass enforcement temporarily:

1. **Skip pre-commit hook:**

   ```bash
   git commit --no-verify
   ```

   ⚠️ **Warning:** This bypasses all hooks, not just test validation

2. **Fix violations later:**
   - Validation will still run in CI
   - PRs will be blocked if violations exist

## Troubleshooting

### Pre-commit hook not running

```bash
# Reinstall hook
./scripts/test-organization-enforcer.sh install

# Check if hook exists
ls -la .git/hooks/pre-commit
```

### Validation script errors

```bash
# Run with verbose output
python scripts/validate-test-organization.py -v

# Check specific file
python scripts/validate-test-organization.py | grep <filename>
```

### Template generator errors

```bash
# Check valid modules
python scripts/test-template.py unit  # Shows usage

# Check if directory exists
ls tests/unit/<module>/
```

## Summary

The test organization enforcement system ensures:

1. ✅ **Automatic validation** - No manual checking needed
2. ✅ **Pre-commit blocking** - Prevents bad commits
3. ✅ **CI/CD integration** - Catches issues in PRs
4. ✅ **Template generation** - Prevents mistakes
5. ✅ **Clear documentation** - Easy to follow rules

**Result:** All future tests will be properly organized automatically.
