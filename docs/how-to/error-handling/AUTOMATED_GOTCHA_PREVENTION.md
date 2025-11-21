# Automated Gotcha Prevention

**Date:** 2025-11-13  
**Purpose:** Automated checks and fixes to prevent common developer gotchas

---

## Overview

We've automated prevention and fixing of common gotchas so new developers never
encounter them. This document describes what's automated and how it works.

---

## Automated Checks

### 1. Environment Validation Script

**Script:** `scripts/check-environment.sh`

**What it checks:**

- ✅ Python environment (casa6 vs system Python)
- ✅ Git hooks executable permissions
- ✅ Prettier installation
- ✅ Frontend dependencies (node_modules)
- ✅ Documentation structure (markdown files in root)
- ✅ Test organization validity
- ✅ Setup script availability
- ✅ Error detection library

**Usage:**

```bash
./scripts/check-environment.sh
# Or via Makefile
make check-env
# Or via npm
cd frontend && npm run check-env
```

**Output:**

- ✅ Green checkmarks for passing checks
- ⚠️ Yellow warnings for non-critical issues
- ❌ Red errors for critical problems

**Exit codes:**

- `0` - All checks passed (or only warnings)
- `1` - Errors found

---

### 2. Auto-Fix Script

**Script:** `scripts/auto-fix-gotchas.sh`

**What it fixes automatically:**

- ✅ Makes git hooks executable (`chmod +x`)
- ✅ Installs Prettier if missing (if in package.json)
- ✅ Initializes Husky if needed
- ⚠️ Warns about Python environment (can't auto-fix)

**Usage:**

```bash
./scripts/auto-fix-gotchas.sh
# Or via Makefile
make auto-fix
# Or via npm
cd frontend && npm run auto-fix
```

**When it runs:**

- Manually via command
- Automatically in `setup-dev.sh`
- Automatically after `git checkout` (post-checkout hook)

---

### 3. Enhanced Setup Script

**Script:** `scripts/setup-dev.sh`

**What it does:**

1. Makes git hooks executable
2. Initializes Husky
3. Installs frontend dependencies
4. Verifies/installs Prettier
5. **NEW:** Runs auto-fix script
6. **NEW:** Runs environment check

**Usage:**

```bash
./scripts/setup-dev.sh
# Or via Makefile
make setup-dev
```

**Result:**

- Fully automated setup
- Validates everything at the end
- Reports any remaining issues

---

### 4. Pre-commit Hook Enhancements

**File:** `.husky/pre-commit`

**New checks (warnings, not failures):**

- ⚠️ Warns if using wrong Python environment
- ⚠️ Warns if markdown files found in root directory

**Why warnings instead of failures:**

- Some operations don't need Python (Prettier formatting)
- Documentation location is a warning, not a blocker
- Allows commit to proceed while alerting developer

**Example output:**

```
Warning: Using wrong Python environment: /usr/bin/python
  Should be: /opt/miniforge/envs/casa6/bin/python
  Some checks may fail. Run: conda activate casa6
```

---

### 5. Post-checkout Hook

**File:** `.git/hooks/post-checkout`

**What it does:**

- Automatically runs `auto-fix-gotchas.sh` after `git checkout`
- Fixes hook permissions if they were lost
- Ensures Prettier is available

**Why:**

- Git `core.filemode=false` can cause hooks to lose executable bit
- New developers cloning repo get automatic fixes
- No manual intervention needed

**Note:** This hook is in `.git/hooks/` (not `.husky/`) so it runs even if Husky
isn't initialized.

---

## Integration Points

### Makefile Targets

**New targets:**

```makefile
make check-env      # Check environment
make setup-dev      # Full setup
make auto-fix       # Auto-fix gotchas
```

### npm Scripts

**New scripts in `frontend/package.json`:**

```json
"check-env": "bash ../scripts/check-environment.sh",
"auto-fix": "bash ../scripts/auto-fix-gotchas.sh"
```

**Usage:**

```bash
cd frontend
npm run check-env
npm run auto-fix
```

---

## What Gets Prevented

### ✅ Fully Automated (No Developer Action Needed)

1. **Git hook permissions** - Auto-fixed by postinstall and post-checkout
2. **Prettier installation** - Auto-installed if in package.json
3. **Husky initialization** - Auto-initialized if needed

### ⚠️ Warned About (Developer Must Fix)

1. **Python environment** - Can't auto-fix (requires conda activation)
2. **Documentation location** - Warned in pre-commit, but commit proceeds
3. **Missing dependencies** - Warned, but can auto-install

### ❌ Blocked (Prevents Bad Commits)

1. **Test organization** - Pre-commit hook validates (already existed)
2. **Prettier formatting** - Pre-commit hook enforces (already existed)
3. **Type errors** - Pre-commit hook checks (already existed)
4. **Lint errors** - Pre-commit hook checks (already existed)

---

## Developer Workflow

### First Time Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd dsa110-contimg

# 2. Run setup (automated)
./scripts/setup-dev.sh

# That's it! Everything is set up and validated.
```

**What happens:**

- Hooks made executable ✅
- Dependencies installed ✅
- Prettier installed ✅
- Environment validated ✅
- Any issues reported ✅

### Daily Development

```bash
# Before starting work
make check-env  # Quick validation

# If issues found
make auto-fix   # Auto-fix what can be fixed

# Make changes, commit
git commit -m "Your message"
# Pre-commit hook automatically:
# - Formats code
# - Validates tests
# - Warns about Python/docs if needed
```

### After Git Operations

```bash
# After checkout, pull, etc.
# Post-checkout hook automatically:
# - Fixes hook permissions
# - Ensures Prettier available
# (No action needed)
```

---

## Error Messages

### Clear, Actionable Errors

**Before (manual):**

```
Error: python not found
```

**After (automated):**

```
❌ ERROR: Using wrong Python: /usr/bin/python
   Should be: /opt/miniforge/envs/casa6/bin/python
   Fix: conda activate casa6
   Or: export PATH="/opt/miniforge/envs/casa6/bin:$PATH"
```

### Warnings vs Errors

**Warnings (non-blocking):**

- Documentation location issues
- Python environment (for non-Python operations)
- Missing optional dependencies

**Errors (blocking):**

- Critical Python environment (for Python operations)
- Test organization violations
- Prettier formatting failures
- Type/lint errors

---

## Testing the Automation

### Test Environment Check

```bash
# Should pass after setup
./scripts/check-environment.sh
# Expected: All checks pass
```

### Test Auto-Fix

```bash
# Remove executable bit
chmod -x .husky/pre-commit

# Run auto-fix
./scripts/auto-fix-gotchas.sh

# Verify
test -x .husky/pre-commit && echo "Fixed!" || echo "Failed"
```

### Test Post-Checkout

```bash
# Remove executable bit
chmod -x .husky/pre-commit

# Simulate checkout
git checkout HEAD

# Verify (hook should have run)
test -x .husky/pre-commit && echo "Fixed!" || echo "Failed"
```

---

## Maintenance

### Adding New Checks

**To add a new check:**

1. Add check to `scripts/check-environment.sh`:

```bash
echo ""
echo "N. Checking <feature>..."
if [ condition ]; then
  success "<feature> is correct"
else
  error "<feature> is wrong"
  info "   Fix: <instructions>"
fi
```

2. Add auto-fix to `scripts/auto-fix-gotchas.sh` (if fixable):

```bash
if [ condition ]; then
  # fix command
  fix "Fixed <feature>"
fi
```

3. Update this documentation

### Updating Warnings

**To add pre-commit warning:**

Edit `.husky/pre-commit`:

```bash
# Check for issue
if [ condition ]; then
  echo "Warning: <issue>" >&2
  echo "  <instructions>" >&2
fi
```

---

## Summary

**Automated:**

- ✅ Git hook permissions
- ✅ Prettier installation
- ✅ Husky initialization
- ✅ Environment validation
- ✅ Post-checkout fixes

**Warned About:**

- ⚠️ Python environment (can't auto-fix)
- ⚠️ Documentation location (non-blocking)

**Blocked:**

- ❌ Test organization violations
- ❌ Prettier formatting failures
- ❌ Type/lint errors

**Result:** New developers encounter far fewer gotchas, and remaining issues
have clear, actionable error messages.

---

## Related Documentation

- `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md` - Full warnings list
- `docs/how-to/PRETTIER_WARNINGS.md` - Prettier-specific warnings
- `docs/how-to/QUICK_REFERENCE_WARNINGS.md` - Quick reference
