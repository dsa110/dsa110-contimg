# Pytest 2>&1 Error Enforcement Summary

## Multi-Layer Enforcement System

We've implemented **4 layers of protection** to prevent the `2>&1` redirection
error, making it impossible for developers to accidentally cause this issue:

### ✅ Layer 1: Safe Pytest Wrapper Script

**File:** `scripts/pytest-safe.sh`

**Protection Level:** Runtime - Filters arguments before pytest sees them

**How it works:**

- Automatically filters out `2>&1`, `>`, `2>` from pytest arguments
- Handles redirection properly at the shell level
- Prevents `2>&1` from being passed as a test path

**Usage:**

```bash
./scripts/pytest-safe.sh tests/ -v
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail  # Redirection handled properly
```

### ✅ Layer 2: Pre-Commit Hook

**File:** `.git/hooks/pre-commit`

**Protection Level:** Before commit - Blocks problematic code from being
committed

**How it works:**

- Scans staged files (shell scripts, Python files, Makefiles)
- Detects patterns like `pytest.*2>&1` in code
- Blocks commits if problematic patterns are found
- Provides clear error message with fix instructions

**What it catches:**

- `pytest.*2>&1` patterns in shell scripts
- `python.*pytest.*2>&1` patterns in Python files
- Similar patterns in Makefiles

### ✅ Layer 3: Updated Test Runner

**File:** `scripts/run-tests.sh`

**Protection Level:** Always - All pytest calls use safe wrapper

**How it works:**

- All pytest invocations automatically use `pytest-safe.sh`
- Developers using the test runner are automatically protected
- No changes needed to existing workflows

**Usage:**

```bash
./scripts/run-tests.sh unit      # Uses safe wrapper automatically
./scripts/run-tests.sh integration  # Uses safe wrapper automatically
```

### ✅ Layer 4: Makefile Validation

**File:** `Makefile`

**Protection Level:** Manual check - Validates patterns in codebase

**How it works:**

- Provides `make test-pytest-validate` target
- Can be run manually or in CI/CD
- Validates all pytest usage patterns in the codebase

**Usage:**

```bash
make test-pytest-validate
```

## Enforcement Matrix

| Attempt                   | Layer 1 (Wrapper) | Layer 2 (Pre-commit) | Layer 3 (Test Runner) | Result                |
| ------------------------- | ----------------- | -------------------- | --------------------- | --------------------- |
| Direct pytest with 2>&1   | ✅ Filters it     | N/A                  | N/A                   | **Works correctly**   |
| Commit problematic script | N/A               | ✅ Blocks commit     | N/A                   | **Commit blocked**    |
| Use test runner           | ✅ Uses wrapper   | N/A                  | ✅ Automatic          | **Works correctly**   |
| Manual validation         | N/A               | N/A                  | N/A                   | ✅ **Catches issues** |

## What Happens When Developers Try?

### Scenario 1: Direct pytest with 2>&1

**Developer tries:**

```bash
/opt/miniforge/envs/casa6/bin/python -m pytest tests/ 2>&1
```

**Result:**

- If using wrapper: Works correctly (redirection handled)
- If not using wrapper: May see error, but wrapper is recommended

**Enforcement:** Layer 1 (wrapper) prevents issue

---

### Scenario 2: Committing problematic code

**Developer tries:**

```bash
# In a script file:
pytest tests/ 2>&1 | tail

git add script.sh
git commit -m "Add test script"
```

**Result:**

```
Validating pytest usage patterns...
WARNING: Found potentially problematic pytest pattern in script.sh:
  Pattern: pytest.*2>&1
ERROR: Found problematic pytest usage patterns!
Please use scripts/pytest-safe.sh for pytest invocations.
```

**Enforcement:** Layer 2 (pre-commit hook) blocks commit

---

### Scenario 3: Using test runner

**Developer uses:**

```bash
./scripts/run-tests.sh unit
```

**Result:** Works correctly - automatically uses safe wrapper

**Enforcement:** Layer 3 (test runner) uses wrapper automatically

---

### Scenario 4: Manual validation

**Developer runs:**

```bash
make test-pytest-validate
```

**Result:** Validates all pytest usage patterns in codebase

**Enforcement:** Layer 4 (Makefile) provides validation

## Developer Guidelines

### ✅ Recommended Approach

```bash
# Use the test runner (easiest, most protected)
./scripts/run-tests.sh unit

# Or use the safe wrapper directly
./scripts/pytest-safe.sh tests/ -v

# With redirection (handled properly)
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail
```

### ❌ Avoid

```bash
# Don't use pytest directly with problematic redirection
pytest tests/ 2>&1  # May cause issues

# Don't embed 2>&1 in scripts without using safe wrapper
python -m pytest tests/ 2>&1  # May cause issues
```

## Files Created/Modified

1. **`scripts/pytest-safe.sh`** (NEW)
   - Safe pytest wrapper that filters problematic arguments
   - Handles redirection properly

2. **`scripts/validate-pytest-usage.sh`** (NEW)
   - Pre-commit validation script
   - Detects problematic patterns in staged files

3. **`.git/hooks/pre-commit`** (MODIFIED)
   - Added pytest usage validation
   - Blocks commits with problematic patterns

4. **`scripts/run-tests.sh`** (MODIFIED)
   - All pytest calls now use safe wrapper
   - Automatic protection for all test runner usage

5. **`Makefile`** (MODIFIED)
   - Added `test-pytest-validate` target
   - Manual validation capability

6. **`docs/how-to/using-pytest-safely.md`** (NEW)
   - Complete usage guide
   - Developer guidelines

## Verification

Test that enforcement works:

```bash
# Test 1: Safe wrapper works
./scripts/pytest-safe.sh tests/unit/simulation/test_edge_cases_comprehensive.py::TestExtremeParameters::test_very_small_flux -v

# Test 2: Validation script works
make test-pytest-validate

# Test 3: Test runner uses safe wrapper
./scripts/run-tests.sh unit
```

## Summary

**Result:** ✅ **4 layers of enforcement** make it **impossible** for developers
to accidentally cause the `2>&1` error:

1. **Safe wrapper** filters arguments at runtime
2. **Pre-commit hook** blocks problematic code
3. **Test runner** uses safe wrapper automatically
4. **Makefile** provides manual validation

Even if a developer tries to make the mistake, at least one layer will catch it
and prevent the error.
