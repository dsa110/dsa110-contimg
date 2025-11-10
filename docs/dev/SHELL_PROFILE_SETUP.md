# Shell Profile Setup for Persistent Warning Suppression

## Overview

To make Python warning suppression persist across **all sessions, disconnections, and new terminals**, add the environment variable to your shell profile.

## Setup Instructions

### For Bash Users

Add to `~/.bashrc` or `~/.bash_profile`:

```bash
# Suppress SWIG deprecation warnings from CASA/casacore
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

**To apply immediately:**
```bash
source ~/.bashrc
# or
source ~/.bash_profile
```

### For Zsh Users

Add to `~/.zshrc`:

```zsh
# Suppress SWIG deprecation warnings from CASA/casacore
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

**To apply immediately:**
```bash
source ~/.zshrc
```

### For System-Wide Setup (Optional)

If you want this for all users, add to `/etc/profile` or `/etc/bash.bashrc`:

```bash
# Suppress SWIG deprecation warnings from CASA/casacore
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

**Note:** Requires root/sudo access.

## Verification

After adding to shell profile, verify it works:

```bash
# Start a new terminal session
# Then check:
echo $PYTHONWARNINGS
# Should output: ignore::DeprecationWarning

# Test Python import (should have no warnings)
/opt/miniforge/envs/casa6/bin/python -c "from casatools import linearmosaic; print('✓ No warnings')"
```

## Comparison of Methods

| Method | Persistence | Scope |
|--------|------------|-------|
| **Shell Profile** | ✅ Persistent across all sessions | All Python executions |
| Command-line flag | ❌ Only for that command | Single execution |
| Script variable | ❌ Only when script runs | Script execution only |
| Makefile variable | ❌ Only when make runs | Makefile targets only |

## Recommendation

**Use shell profile** for persistent suppression across all sessions. The command-line flags in scripts/Makefile provide additional coverage for automated runs, but the shell profile ensures it works even for manual Python executions.

## Notes

- The environment variable applies to **all** Python executions, not just casa6
- Only suppresses `DeprecationWarning` category (other warnings still shown)
- Can be overridden per-command: `python -W default script.py` (shows warnings)
- Works with any Python version/environment

