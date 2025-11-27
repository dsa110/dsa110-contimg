# Package Installation Guide

**Purpose**: This guide explains how to install the **dsa110-contimg** package
(version 0.1.0) as a proper Python package.

**Location**: `docs/how-to/package_installation.md`  
**Related**:

- [Professional Script Development](professional_script_development.md)
- [Critical Python Environment](../../reference/CRITICAL_PYTHON_ENVIRONMENT.md)

## Overview

The **dsa110-contimg** pipeline is now configured as a proper Python package
using `pyproject.toml`. This allows:

- **Direct imports** without `sys.path` manipulation
- **CLI entry points** as system commands
- **Proper dependency management** via pip
- **IDE support** for autocomplete and type checking
- **Standard Python practices** for development and deployment

## Installation

### Prerequisites

- **Python 3.11+** (required)
- **casa6 conda environment** (see
  [Critical Python Environment](../../reference/CRITICAL_PYTHON_ENVIRONMENT.md))
- **pip** (included with conda)

### Development Installation (Recommended)

Install the package in **editable mode** (development mode):

```bash
# Activate casa6 environment (if not already active)
conda activate casa6

# Install package in editable mode
cd /data/dsa110-contimg
/opt/miniforge/envs/casa6/bin/pip install -e .
```

**What this does:**

- Installs the package in "editable" mode
- Changes to source code are immediately available (no reinstall needed)
- Adds the package to Python's import path
- Creates CLI entry points (see below)

### Verify Installation

Test that imports work:

```bash
# From any directory
/opt/miniforge/envs/casa6/bin/python -c "from dsa110_contimg.api.data_access import fetch_observation_timeline; print('Success!')"
```

### CLI Entry Points

After installation, you can use CLI commands directly:

```bash
# Conversion
dsa110-convert --help

# Calibration
dsa110-calibrate --help

# Imaging
dsa110-image --help

# Mosaicking
dsa110-mosaic --help

# Photometry
dsa110-photometry --help

# Registry management
dsa110-registry --help

# Streaming converter
dsa110-streaming --help
```

**Note**: These commands use the casa6 Python automatically if installed in that
environment.

## Benefits of Package Installation

### 1. Clean Imports

**Before (with sys.path manipulation):**

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from dsa110_contimg.api.data_access import fetch_observation_timeline
```

**After (with package installed):**

```python
from dsa110_contimg.api.data_access import fetch_observation_timeline
```

### 2. Works from Any Directory

Scripts can be run from any location:

```bash
# From project root
python scripts/find_earliest_data.py

# From any directory
python /data/dsa110-contimg/scripts/find_earliest_data.py

# From /tmp
cd /tmp
python /data/dsa110-contimg/scripts/find_earliest_data.py
```

### 3. IDE Support

IDEs (VS Code, PyCharm, etc.) can now:

- Provide autocomplete for `dsa110_contimg` modules
- Show type hints and documentation
- Navigate to source code
- Detect import errors

### 4. Dependency Management

Dependencies are properly declared in `pyproject.toml`:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Install all optional dependencies
pip install -e ".[all]"
```

## Script Compatibility

Scripts are designed to work **both with and without** package installation:

```python
# Try importing directly (works if package is installed)
try:
    from dsa110_contimg.api.data_access import fetch_observation_timeline
except ImportError:
    # Fallback: add project root to path for development mode
    repo_root = Path(__file__).parent.parent
    src_path = repo_root / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        from dsa110_contimg.api.data_access import fetch_observation_timeline
    else:
        sys.stderr.write("ERROR: Package not installed and src/ not found\n")
        sys.exit(1)
```

This ensures:

- **With package installed**: Direct imports work
- **Without package installed**: Falls back to path manipulation
- **Clear error messages**: Tells user to install package if needed

## Updating the Package

After making changes to the source code:

```bash
# No reinstall needed in editable mode!
# Changes are immediately available

# If you modify pyproject.toml (dependencies, entry points, etc.):
pip install -e . --force-reinstall
```

## Uninstalling

To remove the package:

```bash
pip uninstall dsa110-contimg
```

## Package Structure

The `pyproject.toml` defines:

- **Package name**: `dsa110-contimg`
- **Version**: `0.1.0`
- **Python requirement**: `>=3.11`
- **Dependencies**: Listed in `[project]` section
- **Optional dependencies**: `[project.optional-dependencies]` (dev, casa, all)
- **CLI entry points**: `[project.scripts]` section
- **Package discovery**: Finds all packages in `src/dsa110_contimg/`

## Troubleshooting

### Import Errors After Installation

1. **Verify installation:**

   ```bash
   pip show dsa110-contimg
   ```

2. **Check Python environment:**

   ```bash
   which python
   # Should be: /opt/miniforge/envs/casa6/bin/python
   ```

3. **Reinstall if needed:**
   ```bash
   pip install -e . --force-reinstall
   ```

### CLI Commands Not Found

1. **Verify entry points:**

   ```bash
   pip show -f dsa110-contimg | grep -A 10 "Entry-points"
   ```

2. **Check PATH:**

   ```bash
   echo $PATH | grep casa6
   ```

3. **Use full path:**
   ```bash
   /opt/miniforge/envs/casa6/bin/dsa110-convert --help
   ```

### Dependency Conflicts

If you encounter dependency conflicts:

1. **Check installed versions:**

   ```bash
   pip list | grep -E "astropy|numpy|fastapi"
   ```

2. **Update dependencies:**

   ```bash
   pip install -e . --upgrade
   ```

3. **Recreate environment** (if needed):
   ```bash
   conda env remove -n casa6
   # Recreate from environment.yml
   ```

## Migration from sys.path Approach

Existing scripts continue to work, but you can optionally update them:

1. **Remove sys.path manipulation** (if package is installed)
2. **Add try/except ImportError** for backward compatibility
3. **Test from multiple directories** to ensure robustness

See `scripts/find_earliest_data.py` for an example of the hybrid approach.

## Related Documentation

- [Professional Script Development](professional_script_development.md) - Best
  practices for script development
- [Critical Python Environment](../../reference/CRITICAL_PYTHON_ENVIRONMENT.md) -
  casa6 environment requirements
- Using the Orchestrator CLI - CLI usage examples
