# Python Warning Suppression Setup

## Overview

SWIG-generated deprecation warnings from CASA/casacore are suppressed using Python's `-W ignore::DeprecationWarning` flag. This is implemented across the codebase to ensure clean output.

## Implementation

### Makefile

The `CASA6_PYTHON` variable includes the warning suppression flag:

```makefile
CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning
```

All Makefile targets that use `$(CASA6_PYTHON)` automatically suppress warnings.

### Shell Scripts

Updated scripts use the warning suppression flag:

- `scripts/test-impacted.sh`
- `scripts/test_segfault_prevention.sh`
- `scripts/run_conversion.sh`
- `scripts/test_end_to_end.sh`
- `scripts/start-dashboard-screen.sh`
- `scripts/start-dashboard-tmux.sh`
- `ops/deploy.sh`
- `tests/integration/test_pipeline_end_to_end.sh`

### Environment Variable (Persistent Across Sessions)

For **persistent suppression across all sessions, disconnections, and new terminals**, add to your shell profile:

**Automated setup:**
```bash
./scripts/setup_python_warnings.sh
```

**Manual setup:**

Add to `~/.bashrc`, `~/.bash_profile`, `~/.zshrc`, or `~/.profile`:

```bash
# Suppress SWIG deprecation warnings from CASA/casacore
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

**To apply immediately:**
```bash
source ~/.bashrc  # or ~/.zshrc, ~/.bash_profile, etc.
```

**Benefits:**
- ✅ Persists across all sessions
- ✅ Works after disconnections
- ✅ Applies to new terminals
- ✅ Works for manual Python executions
- ✅ No need to modify scripts

See `docs/dev/SHELL_PROFILE_SETUP.md` for detailed instructions.

## Usage Examples

### Using Makefile (Recommended)

```bash
make test-unit          # Warnings automatically suppressed
make test-validation    # Warnings automatically suppressed
make test-integration   # Warnings automatically suppressed
```

### Using Scripts Directly

```bash
# Scripts already include the flag
./scripts/test-impacted.sh
./scripts/run_conversion.sh
```

### Manual Python Execution

```bash
# With flag
/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning script.py

# With environment variable (if set)
/opt/miniforge/envs/casa6/bin/python script.py
```

## Verification

To verify suppression is working:

```bash
# Without suppression (warnings appear)
/opt/miniforge/envs/casa6/bin/python -c "from casatools import linearmosaic"

# With suppression (warnings suppressed)
/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "from casatools import linearmosaic"
```

## What Gets Suppressed

- `DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute`
- `DeprecationWarning: builtin type SwigPyObject has no __module__ attribute`
- `DeprecationWarning: builtin type swigvarlink has no __module__ attribute`

**Note:** Only `DeprecationWarning` category is suppressed. Other warnings (UserWarning, RuntimeWarning, etc.) are still shown.

## Rationale

- **Root Cause:** SWIG-generated bindings missing `__module__` attributes (fixed in SWIG 4.4+)
- **Impact:** Cosmetic only - does not affect functionality
- **Suppression Method:** Command-line flag (`-W ignore::DeprecationWarning`) or environment variable
- **Reference:** See `docs/dev/SWIGPY_WARNINGS_SUPPRESSION.md` for detailed investigation

## Future

When CASA updates to SWIG 4.4+ or rebuilds bindings, these warnings will disappear naturally. Until then, suppression is the practical solution.

