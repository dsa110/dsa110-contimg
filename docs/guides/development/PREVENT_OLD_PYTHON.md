# Preventing Use of Python 2.7 and 3.6 in dsa110-contimg

## Overview

This guide explains how to ensure the dsa110-contimg project **never** uses
Python 2.7.17 or Python 3.6.9, even though these versions remain on the system
for system tools.

## Why Keep System Python?

- **Python 3.6.9**: Required by Ubuntu 18.04 system tools (cloud-init, apt,
  apport, etc.)
- **Python 2.7.17**: Some legacy system packages depend on it
- **Removing them would break the system**

## Solution: Isolate Project from System Python

### 1. Always Use CASA6 Python

The project **must** use Python 3.11.13 from the casa6 conda environment:

```bash
# ✅ CORRECT - Always use this
/opt/miniforge/envs/casa6/bin/python script.py

# ❌ WRONG - Will use system Python 3.6.9
python3 script.py
python script.py
```

### 2. Update Script Shebangs

**Current Problem:** Many scripts use `#!/usr/bin/env python3` which resolves to
`/usr/bin/python3` → Python 3.6.9

**Solutions:**

#### Option A: Use CASA6 Python Explicitly (Recommended)

```python
#!/opt/miniforge/envs/casa6/bin/python
```

#### Option B: Use Version-Specific Shebang

```python
#!/usr/bin/env python3.11
```

(Only works if python3.11 is in PATH)

#### Option C: Use Version Guard

```python
#!/usr/bin/env python3
import sys
if sys.version_info < (3, 11):
    sys.exit("ERROR: Python 3.11+ required")
```

### 3. Use Validation Script

Run the validation script to check for forbidden Python usage:

```bash
./scripts/validate-python-version.sh
```

This script:

- ✅ Checks system Python installations
- ✅ Verifies CASA6 Python version
- ✅ Scans Python script shebangs
- ✅ Checks shell scripts for Python calls
- ✅ Reports errors and warnings

### 4. Add Version Guard to Python Scripts

Include this at the top of critical Python scripts:

```python
#!/usr/bin/env python3
import sys

# Version guard
if sys.version_info < (3, 11) or sys.version_info[:2] == (2, 7) or sys.version_info[:2] == (3, 6):
    sys.exit(f"ERROR: Python 3.11+ required. Found: {sys.version}")
```

Or use the provided guard module:

```python
#!/usr/bin/env python3
from scripts.python_version_guard import check_python_version
check_python_version()
```

### 5. Set Up Environment Variables

Create a setup script that sets the correct Python path:

```bash
# In your shell profile or project setup script
export CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"

# Verify
which python3  # Should point to casa6
python3 --version  # Should show 3.11.13
```

### 6. Update Makefile Targets

The Makefile already uses `CASA6_PYTHON`. Ensure all targets use it:

```makefile
CASA6_PYTHON ?= /opt/miniforge/envs/casa6/bin/python

test:
	@$(CASA6_PYTHON) -m pytest tests/

lint:
	@$(CASA6_PYTHON) -m flake8 src/
```

### 7. Update Shell Scripts

Always use the full path or CASA6_PYTHON variable:

```bash
#!/bin/bash
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Verify casa6 exists
if [ ! -x "$CASA6_PYTHON" ]; then
    echo "ERROR: casa6 Python not found"
    exit 1
fi

# Use it
"$CASA6_PYTHON" script.py
```

### 8. Pre-commit Hook

Add a pre-commit hook to validate Python versions:

```bash
#!/bin/bash
# .git/hooks/pre-commit

./scripts/validate-python-version.sh
if [ $? -ne 0 ]; then
    echo "Pre-commit hook failed: Python version validation"
    exit 1
fi
```

Or use the provided Python guard:

```python
# .git/hooks/pre-commit
#!/usr/bin/env python3
import subprocess
import sys

result = subprocess.run(
    ["/data/dsa110-contimg/scripts/validate-python-version.sh"],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(result.stdout)
    print(result.stderr)
    sys.exit(1)
```

### 9. CI/CD Validation

Add validation to CI/CD pipelines:

```yaml
# .github/workflows/ci.yml
- name: Validate Python Version
  run: |
    ./scripts/validate-python-version.sh
```

## Quick Reference

| Task                     | Command                                          |
| ------------------------ | ------------------------------------------------ |
| Validate Python versions | `./scripts/validate-python-version.sh`           |
| Check current Python     | `python3 --version`                              |
| Use CASA6 Python         | `/opt/miniforge/envs/casa6/bin/python script.py` |
| Activate casa6           | `conda activate casa6`                           |
| Verify casa6 version     | `/opt/miniforge/envs/casa6/bin/python --version` |

## Common Mistakes

1. **Using `python3` directly** → Resolves to system Python 3.6.9
2. **Shebang `#!/usr/bin/env python3`** → May resolve to wrong Python
3. **Not checking version in scripts** → Silent failures
4. **Installing packages to system Python** → Wrong environment

## Enforcement Checklist

- [ ] Run `validate-python-version.sh` regularly
- [ ] All scripts use CASA6_PYTHON or full path
- [ ] Shebangs point to correct Python
- [ ] Version guards in critical scripts
- [ ] Pre-commit hook installed
- [ ] CI/CD validates Python version
- [ ] Documentation updated

## Troubleshooting

### Script uses wrong Python

```bash
# Check what python3 resolves to
which python3
readlink -f $(which python3)

# Fix: Use full path
/opt/miniforge/envs/casa6/bin/python script.py
```

### Import errors

```bash
# Verify you're using casa6
/opt/miniforge/envs/casa6/bin/python -c "import sys; print(sys.executable)"
```

### Version mismatch

```bash
# Check casa6 version
/opt/miniforge/envs/casa6/bin/python --version
# Should be: Python 3.11.13
```

## Related Documentation

- `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`
- `docs/CASA6_ENVIRONMENT_GUIDE.md`
- `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md`
