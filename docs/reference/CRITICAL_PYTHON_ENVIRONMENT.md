# CRITICAL: Python Environment Requirements

## ⚠️ MANDATORY: Always Use casa6 Environment

**ALL Python execution in the DSA-110 continuum imaging pipeline MUST use the `casa6` conda environment.**

### The Only Valid Python Path

```
/opt/miniforge/envs/casa6/bin/python
```

**Python Version:** 3.11.13  
**Environment Name:** `casa6`  
**Location:** `/opt/miniforge/envs/casa6`

### Why This Is Critical

1. **CASA Dependencies**: The pipeline requires CASA 6.7 (casatools, casatasks, casacore) which are only available in the casa6 environment
2. **Python Version**: System Python (3.6.9) is too old and lacks required features (e.g., `from __future__ import annotations`)
3. **Package Dependencies**: pyuvdata, astropy, and other scientific packages are installed in casa6, not system Python
4. **Consistency**: All pipeline scripts, tests, and tools expect casa6 environment

### What Happens If You Use System Python

- ❌ Import errors: `No module named 'casatools'`
- ❌ Syntax errors: `future feature annotations is not defined` (Python 3.6 doesn't support it)
- ❌ Missing dependencies: pyuvdata, astropy, etc. not found
- ❌ Pipeline failures: Conversion, calibration, and imaging will all fail

### How to Use casa6 in Makefile

The Makefile defines `CASA6_PYTHON` variable that **must** be used for all Python execution:

```makefile
CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python
```

**All Makefile targets automatically:**
1. Check that casa6 Python exists
2. Fail with clear error message if missing
3. Use casa6 Python for execution

### How to Use casa6 in Shell Scripts

Always set `PYTHON_BIN` at the top of shell scripts:

```bash
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: casa6 Python not found at ${PYTHON_BIN}"
  exit 1
fi

# Then use ${PYTHON_BIN} instead of python3
"${PYTHON_BIN}" -m dsa110_contimg.conversion.strategies.hdf5_orchestrator ...
```

### How to Use casa6 in Python Code

When calling subprocess or executing Python from Python code:

```python
import subprocess
import os

CASA6_PYTHON = "/opt/miniforge/envs/casa6/bin/python"
if not os.path.isfile(CASA6_PYTHON):
    raise RuntimeError(f"casa6 Python not found at {CASA6_PYTHON}")

subprocess.run([CASA6_PYTHON, "-m", "dsa110_contimg.some.module", ...])
```

### Verification

To verify casa6 is available:

```bash
# Check if Python exists
test -x /opt/miniforge/envs/casa6/bin/python && echo "OK" || echo "MISSING"

# Check Python version
/opt/miniforge/envs/casa6/bin/python --version
# Should output: Python 3.11.13 (from casa6 conda environment)

# Check CASA is available
/opt/miniforge/envs/casa6/bin/python -c "import casatools; print('CASA OK')"
```

### For AI Agents

**When writing or modifying code that executes Python:**

1. **NEVER** use `python3` or `python` directly
2. **ALWAYS** use `/opt/miniforge/envs/casa6/bin/python`
3. **ALWAYS** check that the path exists before using it
4. **ALWAYS** fail with a clear error message if casa6 is missing
5. **ALWAYS** reference this document when in doubt

### Makefile Pattern

All Makefile targets follow this pattern:

```makefile
target-name:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@$(CASA6_PYTHON) script_or_module.py [args...]
```

### Shell Script Pattern

All shell scripts should follow this pattern:

```bash
#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "ERROR: casa6 Python not found at ${PYTHON_BIN}" >&2
  echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6" >&2
  exit 1
fi

# Use ${PYTHON_BIN} for all Python execution
"${PYTHON_BIN}" -m dsa110_contimg.module ...
```

### Summary

- ✅ **DO**: Use `/opt/miniforge/envs/casa6/bin/python`
- ❌ **DON'T**: Use `python3`, `python`, or any other Python
- ✅ **DO**: Check that casa6 exists before using it
- ❌ **DON'T**: Assume system Python will work
- ✅ **DO**: Fail fast with clear error messages
- ❌ **DON'T**: Silently fall back to system Python

**This is not optional. The pipeline will not work without casa6.**

