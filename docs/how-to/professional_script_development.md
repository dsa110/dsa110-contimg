# Professional Approach to Script Development

**Purpose**: This document explains how a professional software developer would
approach script development, particularly addressing import path issues and
script robustness.

**Location**: `docs/how-to/professional_script_development.md`

## The Problem We Encountered

When developing `scripts/find_earliest_data.py`, we encountered a common issue:
**import order matters**. The script tried to import `dsa110_contimg` modules
before adding the project's `src` directory to Python's path, causing
`ModuleNotFoundError`.

## Current Project Approach (Pragmatic)

The project currently uses `sys.path.insert()` in scripts, which is a
**pragmatic solution** for a development environment where the package isn't
installed:

```python
# Add project root to path BEFORE importing dsa110_contimg modules
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

# Import dsa110_contimg modules AFTER path setup
from dsa110_contimg.api.data_access import fetch_observation_timeline
from dsa110_contimg.database.products import ensure_products_db
```

**Why this works:**

- Scripts can be run from any directory
- No package installation required
- Works in development environments
- Consistent with existing project patterns (60+ scripts use this approach)

## Professional Software Developer Approach

A professional developer would consider several improvements:

### 1. Proper Package Installation (Ideal)

**Best practice**: Install the package in development mode using
`pip install -e .`

**Benefits:**

- No `sys.path` manipulation needed
- Imports work from anywhere
- Proper dependency management
- Works with IDEs and tools
- Standard Python practice

**Implementation would require:**

- `setup.py` or `pyproject.toml` with package metadata
- `pip install -e /data/dsa110-contimg` in the casa6 environment
- Scripts can then import directly without path manipulation

**Example `pyproject.toml`:**

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "dsa110-contimg"
version = "0.1.0"
description = "DSA-110 Continuum Imaging Pipeline"
requires-python = ">=3.8"
dependencies = [
    "astropy",
    "numpy",
    # ... other dependencies
]

[tool.setuptools.packages.find]
where = ["src"]
```

**Then scripts would simply:**

```python
from dsa110_contimg.api.data_access import fetch_observation_timeline
# No sys.path manipulation needed!
```

### 2. Shared Import Helper (Better)

**Current improvement**: Create a shared utility function for path setup:

```python
# scripts/_common.py
import sys
from pathlib import Path

def setup_project_path():
    """Add project src to Python path if not already present."""
    repo_root = Path(__file__).parent.parent
    src_path = str(repo_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
```

**Then scripts use:**

```python
from _common import setup_project_path
setup_project_path()

from dsa110_contimg.api.data_access import fetch_observation_timeline
```

**Benefits:**

- DRY (Don't Repeat Yourself)
- Consistent behavior across scripts
- Single place to update if structure changes
- Can add validation/error handling

### 3. Robust Error Handling (Essential)

**Professional approach**: Add clear error messages and validation:

```python
import sys
from pathlib import Path

# Add project root to path
repo_root = Path(__file__).parent.parent
src_path = repo_root / "src"

if not src_path.exists():
    sys.stderr.write(
        f"ERROR: Project src directory not found: {src_path}\n"
        f"Current script location: {Path(__file__).absolute()}\n"
        f"Expected project root: {repo_root}\n"
    )
    sys.exit(1)

sys.path.insert(0, str(src_path))

# Verify import works
try:
    from dsa110_contimg.api.data_access import fetch_observation_timeline
except ImportError as e:
    sys.stderr.write(
        f"ERROR: Failed to import dsa110_contimg modules: {e}\n"
        f"Python path: {sys.path}\n"
        f"Please ensure you're running from the project root or install the package.\n"
    )
    sys.exit(1)
```

### 4. Use Entry Points (Production)

**For production scripts**: Define entry points in `setup.py`:

```python
# setup.py
from setuptools import setup

setup(
    name="dsa110-contimg",
    entry_points={
        "console_scripts": [
            "find-earliest-data=dsa110_contimg.scripts.find_earliest_data:main",
        ],
    },
)
```

**Benefits:**

- Scripts become system commands: `find-earliest-data`
- No need to specify Python or script path
- Properly installed in PATH
- Works across environments

### 5. Environment Detection (Robust)

**Professional approach**: Detect and handle different environments:

```python
import os
import sys
from pathlib import Path

def setup_imports():
    """Setup imports with environment detection."""
    # Check if package is installed
    try:
        import dsa110_contimg
        return  # Already available
    except ImportError:
        pass

    # Development mode: add src to path
    repo_root = Path(__file__).parent.parent
    src_path = repo_root / "src"

    if src_path.exists():
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
    else:
        raise RuntimeError(
            f"Cannot find project source directory: {src_path}\n"
            f"Please install the package with 'pip install -e .' or run from project root."
        )

setup_imports()
from dsa110_contimg.api.data_access import fetch_observation_timeline
```

### 6. Testing from Multiple Locations (Validation)

**Professional practice**: Test scripts from different directories:

```python
# Test script should work from:
# - Project root: python scripts/find_earliest_data.py
# - Scripts dir: cd scripts && python find_earliest_data.py
# - Anywhere: python /absolute/path/to/script.py
```

**Our fix ensures this works** by using `Path(__file__)` which is always
relative to the script location.

## Comparison: Current vs Professional

| Aspect                   | Current (Pragmatic)                | Professional (Ideal)             |
| ------------------------ | ---------------------------------- | -------------------------------- |
| **Package Installation** | No installation needed             | `pip install -e .`               |
| **Import Handling**      | `sys.path.insert()` in each script | Direct imports after install     |
| **Error Messages**       | Basic Python errors                | Clear, actionable error messages |
| **Reusability**          | Copy-paste pattern                 | Shared utility or entry points   |
| **IDE Support**          | May need path configuration        | Works automatically              |
| **Deployment**           | Scripts must include path setup    | Standard Python package          |
| **Testing**              | Works but requires path setup      | Standard import testing          |

## Recommendation for This Project

**Given the current project structure:**

1. **Short term (current fix)**: ✅ **Keep the current approach** - it works and
   is consistent with 60+ existing scripts
2. **Medium term**: Create `scripts/` with shared `setup_project_path()`
   function
3. **Long term**: Add `pyproject.toml` and install package in development mode

**Why not change everything now?**

- Consistency: 60+ scripts already use this pattern
- Works: Current approach is functional and tested
- Low risk: No breaking changes needed
- Time investment: Package setup requires testing across all scripts

## Key Takeaways

1. **Import order matters**: Always set up paths before importing project
   modules
2. **Use `Path(__file__)`**: Makes scripts location-independent
3. **Add error handling**: Clear messages help users debug issues
4. **Consider package installation**: For production, proper package setup is
   best
5. **Test from multiple locations**: Ensures scripts are robust
6. **Follow project conventions**: Consistency matters more than perfect
   patterns

## Related Documentation

- [Using the Orchestrator CLI](USING_ORCHESTRATOR_CLI.md)
- [Directory Architecture](../concepts/DIRECTORY_ARCHITECTURE.md)
- [Critical Python Environment](../reference/CRITICAL_PYTHON_ENVIRONMENT.md)
