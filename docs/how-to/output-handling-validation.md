# Output Handling Validation

## Overview

This project enforces strict rules about output handling to ensure errors are
never suppressed. All scripts must follow the output suppression rules defined
in `.cursor/rules/output-suppression.mdc`.

## Rules Summary

1. **NEVER suppress output**: No `2>/dev/null`, `>/dev/null`, `&>/dev/null`
2. **`2>&1` is ALLOWED** when combining streams (e.g.,
   `command 2>&1 | tee logfile.log`)
3. **`2>&1` is FORBIDDEN** when used for suppression (e.g.,
   `command 2>&1 > /dev/null`)
4. **Exceptions must be documented** with comments explaining why suppression is
   acceptable

## Validation Methods

### 1. Pre-commit Hook

A Git pre-commit hook automatically validates output handling before each
commit:

```bash
# The hook runs automatically on commit
git commit -m "Your message"
# If violations are found, commit is blocked
```

**Location**: `.git/hooks/pre-commit`

**Bypass** (not recommended):

```bash
git commit --no-verify
```

### 2. Manual Validation

Run the validation script manually:

```bash
./scripts/validate-output-handling.sh
```

**Exit codes**:

- `0`: No violations found
- `1`: Violations detected

### 3. CI/CD Validation

GitHub Actions automatically validates output handling on:

- Push to `main` or `dev` branches
- Pull requests targeting `main` or `dev`
- Changes to `scripts/**` or `.cursor/rules/output-suppression.mdc`

**Workflow**: `.github/workflows/output-handling-validation.yml`

## Documenting Exceptions

If you need to suppress output (rare exceptions), document it with a comment:

```bash
# ❌ BAD - No explanation
rm -rf node_modules 2>/dev/null

# ✅ GOOD - Exception documented
# Note: Suppressing rm errors here is acceptable - we handle failure explicitly
# This is an exception: cleanup operation with explicit error handling
rm -rf node_modules 2>/dev/null || {
    echo "Warning: Cleanup failed, continuing..."
}
```

**Exception keywords** recognized by validator:

- `# Note:`
- `# exception`
- `# acceptable`

## Common Patterns

### ✅ Correct: Combining Streams

```bash
# Combining stdout and stderr for logging
command 2>&1 | tee logfile.log

# Combining streams for processing
command 2>&1 | grep "pattern"
```

### ✅ Correct: Documented Exceptions

```bash
# Note: Suppressing version check errors - we only care if version is readable
NODE_VERSION=$(node --version 2>/dev/null | sed 's/v//')
```

### ❌ Incorrect: Suppression Without Documentation

```bash
# This will fail validation
rm -rf node_modules 2>/dev/null
```

### ❌ Incorrect: Using 2>&1 for Suppression

```bash
# This will fail validation
command 2>&1 > /dev/null
```

## Fixing Violations

1. **Review the violation**: Check what the validator found
2. **Determine if exception is needed**: Most violations can be fixed by
   removing suppression
3. **If exception is needed**: Add a comment explaining why
4. **Re-run validation**: `./scripts/validate-output-handling.sh`

## Examples

### Port Checking (Exception)

```bash
# Note: fuser output is suppressed here because we only care about exit code
# This is an exception: checking port availability, not suppressing errors
if fuser $port/tcp >/dev/null 2>&1; then
    return 0
fi
```

### Cleanup Operations (Exception)

```bash
# Note: Suppressing cleanup errors is acceptable - we handle failure explicitly
# This is an exception: cleanup operation with explicit error handling
rm -rf node_modules 2>/dev/null || {
    echo "Warning: Cleanup failed, continuing..."
}
```

### Version Detection (Exception)

```bash
# Note: Suppressing version check errors - we only care if version is readable
# This is an exception: version detection, not suppressing actual errors
VERSION=$(command --version 2>/dev/null | sed 's/v//')
```

## Related Documentation

- [Output Suppression Rules](../.cursor/rules/output-suppression.mdc) - Full
  rule specification
- [Error Detection Wrapper](../scripts/README-error-detection.md) - Error
  detection wrapper documentation
