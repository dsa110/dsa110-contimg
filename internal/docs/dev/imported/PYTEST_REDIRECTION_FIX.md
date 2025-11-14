# Pytest Redirection Error Fix

## Issue

When running pytest commands with shell redirection (`2>&1`), pytest sometimes
interprets `2>&1` as a test path argument, causing:

```
ERROR: file or directory not found: 2>&1
```

## Root Cause

This happens when `2>&1` is not properly handled by the shell before being
passed to pytest, or when pytest is invoked in a way that doesn't properly
handle shell redirection.

## Solution

### Option 1: Use Proper Shell Redirection (Recommended)

When running pytest commands, ensure redirection is properly separated:

```bash
# ✅ CORRECT - Redirection handled by shell
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/simulation/test_edge_cases_comprehensive.py -v 2>&1 | tail -20

# ✅ CORRECT - Separate redirection
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/simulation/test_edge_cases_comprehensive.py -v > output.log 2>&1

# ❌ INCORRECT - May cause issues
pytest tests/ 2>&1  # If 2>&1 is somehow passed as argument
```

### Option 2: Use pytest's Built-in Output Options

Instead of shell redirection, use pytest's built-in options:

```bash
# Use pytest's --tb option for traceback control
/opt/miniforge/envs/casa6/bin/python -m pytest tests/ -v --tb=short

# Use pytest's --capture option
/opt/miniforge/envs/casa6/bin/python -m pytest tests/ -v --capture=no

# Redirect to file using pytest's --resultlog
/opt/miniforge/envs/casa6/bin/python -m pytest tests/ -v --resultlog=test_results.log
```

### Option 3: Use Python's subprocess (For Scripts)

If calling pytest from Python scripts:

```python
import subprocess
import sys

# ✅ CORRECT - Proper redirection
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # Merge stderr into stdout
    text=True
)
print(result.stdout)

# ❌ INCORRECT - May cause issues
result = subprocess.run(
    "pytest tests/ 2>&1",  # Shell command with redirection
    shell=True
)
```

## Verification

To verify the fix works:

```bash
# Test without redirection (should work)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/simulation/test_edge_cases_comprehensive.py -v

# Test with proper redirection (should work)
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/simulation/test_edge_cases_comprehensive.py -v 2>&1 | head -20
```

## Current Status

The tests are **actually running successfully** despite the error message. The
error appears to be a warning that doesn't prevent test execution. However, it's
still recommended to use proper redirection to avoid confusion.

## Related

- Pytest documentation: https://docs.pytest.org/en/stable/
- Shell redirection:
  https://www.gnu.org/software/bash/manual/html_node/Redirections.html
