# Casa6 Environment Enforcement

**Date:** 2025-01-28  
**Status:** complete  
**Purpose**: This guide explains how to ensure casa6 is always used for Python
operations in the DSA-110 Continuum Imaging Pipeline.

**Location**: `docs/how-to/casa6-enforcement.md`  
**Related**:

- [Critical Python Environment](../../reference/CRITICAL_PYTHON_ENVIRONMENT.md)
- [Agentic Session Setup](agentic-session-setup.md)
- [Environment Dependency Enforcement Framework](../../architecture/architecture/environment_dependency_enforcement.md) -
  Conceptual framework

## Overview

The pipeline **requires** the casa6 conda environment for all Python operations.
We provide multiple layers of enforcement to prevent accidental use of system
Python:

1. **Shell Functions** (via `casa6-env.sh`) - Works in all shell types
2. **Developer Environment Setup** (via `setup-developer-env.sh`) - Configures
   `.bashrc` automatically
3. **Developer Setup** (via `developer-setup.sh`) - For agentic/automated
   sessions

## Quick Start

### For Interactive Shells (Terminal Sessions)

**Run `setup-developer-env.sh` ONCE** - it configures your `.bashrc`
permanently:

```bash
# Run this ONCE (not every time you open a shell)
./scripts/setup-developer-env.sh

# Then either:
source ~/.bashrc  # Apply immediately in current shell
# OR just open a new terminal (it will auto-source .bashrc)
```

**After running it once**, every new interactive shell will automatically:

- Source `developer-setup.sh` (error detection + casa6 enforcement)
- Have `python` and `python3` commands use casa6
- Have `sqlite3` use casa6 version

**You don't need to run it again** unless you want to reconfigure (remove the
`DSA110_CONTIMG_DEV_ENV` section from `.bashrc` first).

### For Agentic Sessions

**At the start of EVERY agentic session:**

```bash
source /data/dsa110-contimg/scripts/developer-setup.sh
```

This automatically:

1. Enforces casa6 environment (wraps `python`, `python3`, `sqlite3`, `pip`)
2. Enables error detection
3. Verifies setup

### For Shell Scripts

**At the top of EVERY shell script:**

```bash
#!/bin/bash
set -euo pipefail

# CRITICAL: Source casa6 environment enforcement
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/casa6-env.sh"

# Now python, python3, sqlite3, pip automatically use casa6
python -m dsa110_contimg.conversion.cli groups ...
sqlite3 /path/to/database.db "SELECT ..."
```

## How It Works

### Layer 1: Developer Environment Setup (Interactive Shells)

The `setup-developer-env.sh` script configures your `.bashrc` to:

1. **Source `casa6-env.sh`** - Creates wrapper functions for `python`,
   `python3`, `sqlite3`, `pip`
2. **Source `developer-setup.sh`** - Enables error detection
3. **Set PATH** - Prepends casa6 bin directory when in project directory

**This means in interactive shells, `python` automatically uses casa6.**

### Layer 2: Casa6 Environment Script (`scripts/casa6-env.sh`)

This script (sourced by both developer setup and agent setup):

1. **Verifies casa6 exists** - Checks that `/opt/miniforge/envs/casa6` exists
2. **Exports paths** - Sets `CASA6_PYTHON`, `CASA6_SQLITE3`, `CASA6_PIP`
   variables
3. **Updates PATH** - Prepends casa6 bin directory to PATH
4. **Creates wrapper functions** - Overrides `python()`, `python3()`,
   `sqlite3()`, `pip()` to always use casa6 versions
5. **Validates setup** - Checks Python version and CASA importability

**Functions work in both interactive and non-interactive shells** (unlike
aliases).

### Layer 3: Developer Setup (`scripts/developer-setup.sh`)

For agentic/automated sessions, this script:

1. Sources `casa6-env.sh` first (enforces casa6)
2. Sources error detection
3. Verifies everything is working

## Wrapper Functions

When you source `casa6-env.sh`, these commands are automatically wrapped:

- `python` → Uses `/opt/miniforge/envs/casa6/bin/python`
- `python3` → Uses `/opt/miniforge/envs/casa6/bin/python`
- `sqlite3` → Uses `/opt/miniforge/envs/casa6/bin/sqlite3`
- `pip` → Uses `/opt/miniforge/envs/casa6/bin/pip`

**This means you can write scripts naturally:**

```bash
# These automatically use casa6, no need for full paths
python -m dsa110_contimg.conversion.cli groups ...
python3 script.py
sqlite3 database.db "SELECT ..."
pip install package
```

## Setup Options

### Option 1: Developer Environment (Recommended for Interactive Use)

Run once to configure your shell:

```bash
./scripts/setup-developer-env.sh
source ~/.bashrc
```

**Benefits:**

- Works automatically in all new terminal sessions
- No need to source scripts manually
- Persistent across reboots

### Option 2: Agent Setup (For Agentic/Automated Sessions)

Source at the start of each session:

```bash
source /data/dsa110-contimg/scripts/developer-setup.sh
```

**Benefits:**

- Works in non-interactive shells
- Includes error detection
- Explicit and verifiable

### Option 3: Manual Casa6 Environment (For Scripts)

Source in individual scripts:

```bash
source scripts/casa6-env.sh
```

**Benefits:**

- Script-specific enforcement
- No shell profile changes needed
- Works in any shell

## Verification

### Check Current Python

```bash
# Should show casa6 Python
python --version
# Should output: Python 3.11.13

which python
# Should output: /opt/miniforge/envs/casa6/bin/python (or show it's a function)
```

### Check Casa6 Enforcement

```bash
# Source the environment
source /data/dsa110-contimg/scripts/casa6-env.sh

# Verify variables are set
echo "CASA6_PYTHON: $CASA6_PYTHON"
echo "CASA6_ENV_ENFORCED: $CASA6_ENV_ENFORCED"

# Verify wrappers work
python --version  # Should show Python 3.11.13 from casa6
```

### Check CASA Import

```bash
python -c "import casatools; print('CASA OK')"
# Should output: CASA OK
```

## Troubleshooting

### "python still uses system Python"

**Problem**: Wrapper functions not active

**Solutions**:

1. **For interactive shells**: Run `./scripts/setup-developer-env.sh` and
   `source ~/.bashrc`
2. **For scripts**: Add `source scripts/casa6-env.sh` at the top
3. **For agentic sessions**: Source `developer-setup.sh` at session start

### "casa6-env.sh not found"

**Problem**: Script can't find `casa6-env.sh`

**Solution**: Use absolute path or ensure you're in project directory:

```bash
source /data/dsa110-contimg/scripts/casa6-env.sh
```

### "casa6 Python not found"

**Problem**: Casa6 environment doesn't exist

**Solution**: Install casa6 conda environment:

```bash
conda create -n casa6 python=3.11.13
conda activate casa6
# Install CASA and dependencies
```

### Functions Don't Work in Subprocesses

**Problem**: Wrapper functions don't work in subprocesses (e.g.,
`$(python script.py)`)

**Solution**: Use exported variables instead:

```bash
source scripts/casa6-env.sh
"${CASA6_PYTHON}" script.py  # Works in subprocesses
```

## Best Practices

1. **Run setup-developer-env.sh once** - For interactive development
2. **Source developer-setup.sh for sessions** - For agentic/automated sessions
3. **Source casa6-env.sh in scripts** - For individual scripts
4. **Verify in CI/CD** - Add verification steps to CI/CD pipelines
5. **Document in scripts** - Add comments explaining casa6 requirement
6. **Fail fast** - Scripts should exit immediately if casa6 is not available

## See Also

- [Critical Python Environment](../../reference/CRITICAL_PYTHON_ENVIRONMENT.md) -
  Why casa6 is required
- [Agentic Session Setup](agentic-session-setup.md) - Complete session setup
  guide
- [Batch Mode Execution Guide](../workflow/batch_mode_execution_guide.md) - Using casa6 in
  batch processing
- [Environment Dependency Enforcement Framework](../../architecture/architecture/environment_dependency_enforcement.md) -
  Conceptual framework for dependency enforcement

## References

- Casa6 conda environment: `/opt/miniforge/envs/casa6`
- Enforcement scripts: `scripts/casa6-env.sh`, `scripts/developer-setup.sh`,
  `scripts/setup-developer-env.sh`
- Python wrapper: `scripts/python-wrapper.sh`
