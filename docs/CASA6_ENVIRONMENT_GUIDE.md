# casa6 Conda Environment Guide

## Critical Requirement

**ALL Python operations MUST use `/opt/miniforge/envs/casa6/bin/python`**

The system Python (3.6.9) lacks CASA dependencies and required features. The
pipeline WILL FAIL without casa6.

## Quick Reference

```bash
# Python executable
CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Verify casa6 exists
test -x /opt/miniforge/envs/casa6/bin/python || exit 1

# Activate casa6 (if conda is in PATH)
conda activate casa6

# Run Python script
/opt/miniforge/envs/casa6/bin/python script.py

# Run Python module
/opt/miniforge/envs/casa6/bin/python -m pytest tests/

# Install package in casa6
/opt/miniforge/envs/casa6/bin/pip install package_name
# OR
conda activate casa6
conda install -c conda-forge package_name
```

## Makefile Integration

The Makefile already defines `CASA6_PYTHON`:

```makefile
CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python

test-unit:
	$(CASA6_PYTHON) -m pytest tests/unit

lint:
	$(CASA6_PYTHON) -m flake8 src/
	$(CASA6_PYTHON) -m black --check src/
```

**Always use `$(CASA6_PYTHON)` in Makefile targets.**

## Development Tools Installation

### Testing Tools

```bash
# Install pytest and related tools
conda activate casa6
conda install -c conda-forge pytest pytest-cov pytest-asyncio pytest-mock

# Verify installation
/opt/miniforge/envs/casa6/bin/python -m pytest --version
```

### Code Quality Tools

```bash
# Install formatting and linting tools
conda activate casa6
conda install -c conda-forge black flake8 mypy pylint

# Install security tools
/opt/miniforge/envs/casa6/bin/pip install bandit safety
```

### Database Tools

```bash
# Install Alembic for migrations
conda activate casa6
conda install -c conda-forge alembic

# Verify installation
/opt/miniforge/envs/casa6/bin/alembic --version
```

## Pre-commit Hooks Configuration

`.pre-commit-config.yaml` must use casa6 Python paths:

```yaml
repos:
  - repo: local
    hooks:
      - id: black
        name: black (casa6)
        entry: /opt/miniforge/envs/casa6/bin/black
        language: system
        types: [python]
        args: [--check]

      - id: flake8
        name: flake8 (casa6)
        entry: /opt/miniforge/envs/casa6/bin/flake8
        language: system
        types: [python]

      - id: mypy
        name: mypy (casa6)
        entry: /opt/miniforge/envs/casa6/bin/mypy
        language: system
        types: [python]
```

## CI/CD Configuration

GitHub Actions workflows must use casa6 Python:

```yaml
# .github/workflows/pr-checks.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup casa6 Python
        run: |
          # Install miniforge if needed
          # Or use existing casa6 environment
          echo "CASA6_PYTHON=/opt/miniforge/envs/casa6/bin/python" >> $GITHUB_ENV

      - name: Install dependencies
        run: |
          ${{ env.CASA6_PYTHON }} -m pip install pytest pytest-cov

      - name: Run tests
        run: |
          ${{ env.CASA6_PYTHON }} -m pytest tests/
```

## Shell Scripts

All shell scripts must use casa6 Python:

```bash
#!/bin/bash
# scripts/run-tests.sh

CASA6_PYTHON="/opt/miniforge/envs/casa6/bin/python"

# Verify casa6 exists
if [ ! -x "$CASA6_PYTHON" ]; then
    echo "ERROR: casa6 conda environment not found"
    exit 1
fi

# Run tests
"$CASA6_PYTHON" -m pytest tests/
```

## Python Scripts

Python scripts should check for casa6:

```python
#!/usr/bin/env python3
"""Script that requires casa6 environment."""

import sys
import os

CASA6_PYTHON = "/opt/miniforge/envs/casa6/bin/python"

# Verify we're using casa6
if sys.executable != CASA6_PYTHON:
    print(f"ERROR: Must use casa6 Python: {CASA6_PYTHON}")
    print(f"Current Python: {sys.executable}")
    sys.exit(1)

# Rest of script...
```

## Environment File

Create `environment.yml` to document casa6 dependencies:

```yaml
name: casa6
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.11
  - casa6 # CASA dependencies
  # Development dependencies
  - pytest
  - pytest-cov
  - pytest-asyncio
  - black
  - flake8
  - mypy
  - alembic
  - pip
  - pip:
      - bandit
      - safety
```

## Docker Integration

Docker images must include casa6 conda environment:

```dockerfile
# Dockerfile
FROM continuumio/miniconda3:latest

# Install casa6 environment
RUN conda create -n casa6 python=3.11 -y
RUN conda install -n casa6 -c conda-forge casa6 -y

# Set casa6 as default
ENV PATH="/opt/conda/envs/casa6/bin:$PATH"

# Install additional dependencies
RUN /opt/conda/envs/casa6/bin/pip install -r requirements.txt
```

## Common Mistakes to Avoid

1. **Don't use system Python**: `python` or `python3` will fail
2. **Don't assume conda is activated**: Always use full path
3. **Don't install packages in wrong environment**: Verify casa6 before
   installing
4. **Don't forget CI/CD**: All CI steps must use casa6
5. **Don't hardcode paths**: Use `$(CASA6_PYTHON)` variable in Makefile

## Verification Checklist

- [ ] All Makefile targets use `$(CASA6_PYTHON)`
- [ ] All shell scripts use casa6 Python path
- [ ] Pre-commit hooks configured for casa6
- [ ] CI/CD workflows use casa6 Python
- [ ] Docker images include casa6 environment
- [ ] Documentation mentions casa6 requirement
- [ ] Error messages reference casa6 when Python fails

## Troubleshooting

### casa6 Not Found

```bash
# Check if casa6 exists
ls -la /opt/miniforge/envs/casa6/bin/python

# If not found, install miniforge and create casa6 environment
# (This should already be done on the system)
```

### Wrong Python Version

```bash
# Check Python version in casa6
/opt/miniforge/envs/casa6/bin/python --version

# Should be Python 3.11 or compatible (in casa6 conda environment)
```

### Missing Dependencies

```bash
# Install missing packages in casa6
/opt/miniforge/envs/casa6/bin/pip install package_name

# Or use conda
conda activate casa6
conda install -c conda-forge package_name
```

## Best Practices

1. **Always verify casa6 exists** before running Python commands
2. **Use Makefile variables** instead of hardcoding paths
3. **Document casa6 requirement** in all relevant docs
4. **Test with casa6** in CI/CD pipelines
5. **Include casa6 in Docker** images for consistency
