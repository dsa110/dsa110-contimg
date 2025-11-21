# Automation Guide - Preventing Common Mistakes

This guide explains the automated systems in place to prevent common developer
mistakes.

## Quick Start

**For new developers:**

```bash
# One-time setup (add to ~/.bashrc or ~/.profile)
echo 'source /data/dsa110-contimg/scripts/developer-setup.sh' >> ~/.bashrc

# Or run manually each session
source /data/dsa110-contimg/scripts/developer-setup.sh
```

**Validate your environment:**

```bash
./scripts/validate-environment.sh
```

**Auto-fix common issues:**

```bash
./scripts/auto-fix-common-issues.sh
```

---

## Automated Systems

### 1. Developer Setup Script (`scripts/developer-setup.sh`)

**What it does:**

- ✅ Verifies casa6 Python exists
- ✅ Enables error detection automatically
- ✅ Creates aliases (`pytest-safe`, `run-tests`)
- ✅ Overrides `pytest` to use safe wrapper
- ✅ Overrides `python`/`python3` to use casa6
- ✅ Sets environment variables
- ✅ Verifies CASA environment
- ✅ Checks pre-commit hooks

**Usage:**

```bash
source scripts/developer-setup.sh
```

**What gets automated:**

- Python commands automatically use casa6
- Pytest commands automatically use safe wrapper
- Error detection automatically enabled
- No need to remember paths or wrappers

---

### 2. Auto-Fix Script (`scripts/auto-fix-common-issues.sh`)

**What it fixes:**

- ✅ Stale Git lock files
- ✅ Missing pre-commit hooks
- ✅ Disabled error detection
- ✅ CASA environment issues
- ✅ Test organization problems

**Usage:**

```bash
# Check for issues (dry-run)
./scripts/auto-fix-common-issues.sh --check-only

# Fix issues automatically
./scripts/auto-fix-common-issues.sh
```

**When to use:**

- After cloning the repository
- When encountering environment issues
- Before starting work each day
- When pre-commit hooks fail

---

### 3. Environment Validation (`scripts/validate-environment.sh`)

**What it checks:**

- ✅ casa6 Python availability
- ✅ Error detection status
- ✅ CASA environment
- ✅ Pre-commit hooks
- ✅ Test directories
- ✅ Required scripts

**Usage:**

```bash
./scripts/validate-environment.sh
```

**Output:**

- ✅ Green checkmarks for OK items
- ⚠️ Yellow warnings for fixable issues
- ❌ Red errors for critical problems

---

### 4. Pre-Commit Hooks (Automatic)

**What they validate:**

- ✅ File locations (markdown/docs in correct directories)
- ✅ Test organization (markers, directories)
- ✅ Code formatting (Prettier)
- ✅ Git lock files (auto-cleanup)

**Location:** `.githooks/pre-commit`

**What gets automated:**

- Files are automatically validated before commit
- Invalid commits are automatically blocked
- Formatting is automatically applied
- Lock files are automatically cleaned

**No action needed** - runs automatically on `git commit`

---

### 5. Python/Pytest Overrides (via developer-setup.sh)

**What gets overridden:**

- `python` → Uses casa6 automatically
- `python3` → Uses casa6 automatically
- `pytest` → Uses safe wrapper automatically
- `python -m pytest` → Uses safe wrapper automatically

**Example:**

```bash
# Developer types:
python -m pytest tests/unit/

# Actually runs:
/opt/miniforge/envs/casa6/bin/python -m pytest tests/unit/
# (via pytest-safe.sh wrapper)

# Developer types:
pytest tests/unit/

# Actually runs:
./scripts/pytest-safe.sh tests/unit/
```

**No action needed** - happens automatically after sourcing setup

---

### 6. Error Detection (Automatic)

**What it does:**

- ✅ Wraps Python/pytest commands
- ✅ Detects errors in real-time
- ✅ Detects warnings in real-time
- ✅ Terminates on detection
- ✅ Works with pexpect or subprocess

**How it's enabled:**

- Automatically enabled via `developer-setup.sh`
- Or manually: `source scripts/auto-error-detection.sh`

**No action needed** - happens automatically after sourcing setup

---

## Setup Workflows

### First-Time Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd dsa110-contimg

# 2. Run developer setup
source scripts/developer-setup.sh

# 3. Validate environment
./scripts/validate-environment.sh

# 4. Auto-fix any issues
./scripts/auto-fix-common-issues.sh

# 5. Verify everything works
./scripts/run-tests.sh smoke
```

### Daily Workflow

```bash
# Option 1: Add to ~/.bashrc (recommended)
echo 'source /data/dsa110-contimg/scripts/developer-setup.sh' >> ~/.bashrc

# Option 2: Source manually each session
source /data/dsa110-contimg/scripts/developer-setup.sh
```

### Troubleshooting

```bash
# Check what's wrong
./scripts/validate-environment.sh

# Fix common issues
./scripts/auto-fix-common-issues.sh

# Verify fixes worked
./scripts/validate-environment.sh
```

---

## What's NOT Automated (Still Manual)

1. **Writing tests** - Still need to use template and follow rules
2. **Documentation location** - Pre-commit validates, but you still need to
   choose correct location
3. **Code logic** - No automation for business logic
4. **Data provenance** - Still need to verify manually

---

## Integration with IDE/Editor

### VS Code / Cursor

Add to `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "/opt/miniforge/envs/casa6/bin/python",
  "terminal.integrated.env.linux": {
    "PATH": "/data/dsa110-contimg/scripts:${env:PATH}"
  }
}
```

### Shell Profile

Add to `~/.bashrc` or `~/.profile`:

```bash
# DSA-110 Project Setup
if [ -f "/data/dsa110-contimg/scripts/developer-setup.sh" ]; then
    source /data/dsa110-contimg/scripts/developer-setup.sh
fi
```

---

## Benefits

**Before automation:**

- ❌ Developer uses wrong Python → Pipeline fails
- ❌ Developer uses `pytest` with `2>&1` → Error
- ❌ Developer forgets error detection → Silent failures
- ❌ Developer creates files in wrong location → Manual cleanup
- ❌ Developer forgets test markers → Commit blocked

**After automation:**

- ✅ Python automatically correct
- ✅ Pytest automatically safe
- ✅ Error detection automatically enabled
- ✅ File locations automatically validated
- ✅ Test organization automatically enforced

---

## Summary

**Automated:**

- ✅ Python environment selection
- ✅ Pytest wrapper usage
- ✅ Error detection enablement
- ✅ File location validation
- ✅ Test organization validation
- ✅ Code formatting
- ✅ Git lock file cleanup
- ✅ Common issue fixing

**Manual (but validated):**

- ⚠️ Test creation (validated by pre-commit)
- ⚠️ Documentation location (validated by pre-commit)
- ⚠️ Code logic (no automation)

**Result:** Most common mistakes are now impossible or automatically fixed!
