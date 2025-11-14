# Fixing CodeQL Security Issues

## Overview

This guide explains how to fix the high-priority security issues identified by
CodeQL analysis.

## High Priority Issues

### 1. Path Injection (186 findings, 184 in src/)

**Issue**: User input used directly in file paths without validation.

**Risk**: Path traversal attacks allowing access to files outside intended
directories.

**Solution**: Use the path validation utilities in
`src/dsa110_contimg/utils/path_validation.py`.

#### Before (Vulnerable):

```python
user_path = request.args.get('path')
file_path = f"/data/images/{user_path}"  # Vulnerable!
with open(file_path, 'r') as f:
    content = f.read()
```

#### After (Secure):

```python
from dsa110_contimg.utils.path_validation import validate_path, get_safe_path

user_path = request.args.get('path')
try:
    # Validate against base directory
    safe_path = get_safe_path(
        user_path,
        base_dir="/data/images",
        subdirectory="user_uploads"
    )
    with open(safe_path, 'r') as f:
        content = f.read()
except ValueError as e:
    return {"error": str(e)}, 400
```

#### Common Patterns to Fix:

1. **API Routes** (`src/dsa110_contimg/api/routes.py`):

   ```python
   # Instead of:
   file_path = os.path.join(base_dir, user_input)

   # Use:
   from dsa110_contimg.utils.path_validation import validate_path
   file_path = validate_path(user_input, base_dir)
   ```

2. **File Operations**:

   ```python
   # Instead of:
   output_path = f"{output_dir}/{filename}"

   # Use:
   from dsa110_contimg.utils.path_validation import sanitize_filename, get_safe_path
   safe_filename = sanitize_filename(filename)
   output_path = get_safe_path(safe_filename, output_dir)
   ```

### 2. Shell Command from Input (153 findings, 0 in src/)

**Status**: ✅ No issues found in active `src/` codebase.

All shell command usage in `src/` uses `subprocess.run()` with argument lists
(not shell=True), which is secure.

### 3. Clear Text Logging (99 findings, 0 in src/)

**Status**: ✅ No issues found in active `src/` codebase.

All logging issues are in `archive/` (legacy code).

## Implementation Plan

### Phase 1: API Routes (Priority 1)

Files with most issues:

- `src/dsa110_contimg/api/routes.py` (33 issues)
- `src/dsa110_contimg/api/visualization_routes.py` (32 issues)

**Action**: Add path validation to all file path operations in API routes.

### Phase 2: Other Modules (Priority 2)

Files with moderate issues:

- `src/dsa110_contimg/qa/casa_ms_qa.py` (9 issues)
- Other modules with < 5 issues

**Action**: Review and fix path handling in these modules.

### Phase 3: Verification

After fixes:

1. Re-run CodeQL analysis
2. Verify path injection count decreases
3. Test API endpoints with malicious inputs
4. Update tests to include path validation

## Testing Path Validation

### Test Cases

```python
import pytest
from dsa110_contimg.utils.path_validation import validate_path, sanitize_filename

def test_path_traversal_prevention():
    """Test that path traversal attempts are blocked."""
    with pytest.raises(ValueError):
        validate_path("../../../etc/passwd", "/data/images")

def test_safe_path_allowed():
    """Test that safe paths are allowed."""
    path = validate_path("user123/image.fits", "/data/images")
    assert str(path).startswith("/data/images")

def test_filename_sanitization():
    """Test filename sanitization."""
    with pytest.raises(ValueError):
        sanitize_filename("../../../etc/passwd")

    safe = sanitize_filename("image.fits")
    assert safe == "image.fits"
```

## CodeQL False Positives

Some CodeQL findings may be false positives:

1. **Internal APIs**: If paths are only used internally (not from user input)
2. **Validated Inputs**: If paths are validated elsewhere in the code
3. **Trusted Sources**: If input comes from trusted sources only

**Action**: Document exceptions with comments:

```python
# CodeQL: py/path-injection - False positive: input validated in validate_request()
# and only used internally
file_path = construct_path(validated_input)
```

## Resources

- Path validation utilities: `src/dsa110_contimg/utils/path_validation.py`
- CodeQL results: `CODEQL_RESULTS_SUMMARY.md`
- Security best practices:
  [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
