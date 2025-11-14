# Prettier Integration - Critical Issues for This Machine

**Date:** 2025-11-13  
**Environment:** Linux Ubuntu, Git 2.17.1, Node.js/npm

---

## 🚨 CRITICAL: Prettier Not Installed

**Status:** ❌ **MUST FIX**

**Problem:**

- Prettier is **NOT** in `frontend/package.json` devDependencies
- `npx prettier` will download Prettier on first run (~10MB download)
- First commit will be **slow** and requires **internet connection**

**Fix:**

```bash
cd frontend
npm install --save-dev prettier
```

**Verify:**

```bash
cd frontend
npm list prettier
# Should show prettier@<version>
```

**Why this matters:**

- Without explicit installation, first commit downloads Prettier
- Offline development won't work on first commit
- CI might fail if Prettier isn't available

---

## ⚠️ WARNING: Git Hooks Path Configuration

**Status:** ⚠️ **VERIFY**

**Current setup:**

- Git config: `core.hooksPath=.githooks`
- Hooks location: `.husky/` directory
- Husky manages the `.githooks` symlink

**What to check:**

```bash
# Verify Husky is managing hooks
ls -la .githooks
# Should be a symlink or directory managed by Husky

# Verify hook exists
test -f .husky/pre-commit && echo "OK" || echo "MISSING"
```

**If hooks don't run:**

```bash
# Re-initialize Husky
npx husky install
```

---

## ⚠️ WARNING: Git File Mode Disabled

**Status:** ⚠️ **MINOR ISSUE**

**Problem:**

- `core.filemode=false` is set
- Git ignores file permission changes
- Hook executable bit might not be preserved after clone

**Impact:**

- New developers cloning repo might have non-executable hook
- Hook won't run if not executable

**Fix after clone:**

```bash
chmod +x .husky/pre-commit
```

**Or add to setup script:**

```bash
# scripts/setup-dev.sh
chmod +x .husky/pre-commit
```

---

## ⚠️ WARNING: Fragile Directory Changes

**Status:** ⚠️ **FRAGILE**

**Problem:** The hook changes directory **7 times**:

1. `cd frontend` - Format files
2. `cd ..` - Git add
3. `cd frontend` - Check formatting
4. `cd ..` - Back to root
5. `cd frontend` - Error detection checks
6. `cd ..` - Final return

**Impact:**

- If any `cd` fails, hook exits
- If you commit from subdirectory, paths break
- Very fragile if directory structure changes

**What to watch:**

- Always commit from repo root
- Don't reorganize directories without testing hook
- Consider refactoring to reduce `cd` operations

---

## ⚠️ WARNING: Error Suppression

**Status:** ⚠️ **SILENT FAILURES**

**Problem:** Multiple commands suppress errors:

```bash
npx prettier --write 2>/dev/null || true
git add 2>/dev/null || true
```

**Impact:**

- If Prettier isn't found, hook silently continues
- If git add fails, hook continues anyway
- Real errors hidden until CI catches them

**What happens:**

- Hook might "succeed" but formatting didn't actually run
- CI will catch it, but you'll need to fix and re-commit
- Wastes time

**Recommendation:**

- Remove `|| true` from critical commands
- Add explicit error checking
- Fail fast on missing dependencies

---

## ✅ What Works on This Machine

1. **`xargs -r` works** - GNU xargs available (not macOS issue)
2. **Shell compatibility** - `sh` (dash) works fine
3. **Error detection scripts exist** - Dependencies available
4. **Hook is executable** - Permissions correct
5. **Node.js/npm available** - Can run npx commands

---

## Quick Setup for New Developers

```bash
# 1. Install dependencies (including Prettier)
cd frontend
npm install

# 2. Install Prettier explicitly (if not in package.json)
npm install --save-dev prettier

# 3. Make hook executable
cd ..
chmod +x .husky/pre-commit

# 4. Verify everything works
cd frontend
npx prettier --version
npm run format:check
```

---

## Most Critical Issue

**Prettier not installed** - This will cause:

- Slow first commit (downloads Prettier)
- Requires internet on first run
- Potential CI failures

**Fix immediately:**

```bash
cd frontend
npm install --save-dev prettier
```

---

## Summary

**For developers on this machine:**

1. 🚨 **Install Prettier** - Add to devDependencies
2. ⚠️ **Verify hook executable** - After clone, run `chmod +x .husky/pre-commit`
3. ⚠️ **Test first commit** - Will be slow (downloads Prettier)
4. ⚠️ **Commit from repo root** - Hook assumes you're in root
5. ⚠️ **Watch for silent failures** - Check CI results

**The #1 issue:** Prettier needs to be added to `package.json` devDependencies.
