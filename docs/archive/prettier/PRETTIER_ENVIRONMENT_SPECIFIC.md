# Prettier Integration - Environment-Specific Warnings

**Date:** 2025-11-13  
**Environment:** Linux (Ubuntu), Git 2.17.1, Node.js/npm available

---

## ⚠️ Critical Issues for This Machine

### 1. Prettier Not Installed in node_modules

**Status:** ❌ **CRITICAL ISSUE**

**Problem:**

- Prettier is NOT installed in `frontend/node_modules/.bin/prettier`
- The hook uses `npx prettier` which will download Prettier on first run
- This makes the first commit slow and requires internet connection

**Impact:**

- First commit will be slow (downloads Prettier)
- Requires internet connection for first run
- Subsequent runs will use cached version (faster)

**Solution:**

```bash
cd frontend
npm install
# This should install prettier as a dev dependency
```

**Verify:**

```bash
cd frontend
test -f node_modules/.bin/prettier && echo "Installed" || echo "Missing"
```

---

### 2. Git Hooks Path Configuration Mismatch

**Status:** ⚠️ **POTENTIAL ISSUE**

**Problem:**

- Git is configured to use `.githooks` as hooks path: `core.hooksPath=.githooks`
- But hooks are actually in `.husky/` directory
- Husky should handle this, but it's worth verifying

**Impact:**

- Hooks might not run if Husky isn't properly initialized
- Need to ensure Husky is set up correctly

**Verify:**

```bash
git config --get core.hooksPath
# Should be .githooks (Husky manages this)
ls -la .husky/
# Should contain pre-commit hook
```

**If hooks don't run:**

```bash
# Re-initialize Husky
npx husky install
```

---

### 3. Git File Mode Disabled

**Status:** ⚠️ **MINOR ISSUE**

**Problem:**

- `core.filemode=false` is set
- This means Git ignores file permission changes
- The hook's executable bit might not be tracked

**Impact:**

- If someone clones the repo, the hook might not be executable
- Need to ensure hook is executable after clone

**Solution:**

```bash
# Make sure hook is executable
chmod +x .husky/pre-commit

# Or add to setup script
```

---

### 4. Multiple Directory Changes in Hook

**Status:** ⚠️ **FRAGILE**

**Problem:** The hook changes directory multiple times:

```bash
cd frontend || exit 1
# ... format files ...
cd .. || exit 1
# ... git add ...
cd frontend || exit 1
# ... check formatting ...
cd .. || exit 1
```

**Impact:**

- If any `cd` fails, the hook exits
- If you're not in repo root when hook runs, paths break
- Fragile if directory structure changes

**What to watch:**

- Always run git commands from repo root
- Don't modify directory structure without updating hook
- Test hook after any directory changes

---

### 5. Shell Compatibility (sh vs bash)

**Status:** ✅ **OK**

**Current setup:**

- Hook uses `#!/usr/bin/env sh`
- System has `/bin/sh` (dash on Ubuntu)
- System also has `/bin/bash` (GNU bash 4.4.20)

**Impact:**

- Should work fine - `sh` is POSIX compliant
- But some bash-specific features won't work
- The hook uses mostly POSIX-compliant code

**Note:**

- `xargs -r` works because it's GNU xargs (not shell feature)
- All commands should work with `sh`

---

### 6. Dependencies on External Scripts

**Status:** ⚠️ **REQUIRES SETUP**

**Dependencies:**

- `scripts/lib/error-detection.sh` - ✅ Exists
- `scripts/lib/anti-pattern-detection.sh` - ✅ Exists

**Impact:**

- If these scripts are missing, hook will warn but continue
- Prettier formatting will still run
- But error detection and anti-pattern checks will be skipped

**What to watch:**

- Don't delete these scripts
- If moving scripts, update hook paths
- Test hook after any script reorganization

---

### 7. Working Directory Assumptions

**Status:** ⚠️ **ASSUMPTION**

**Problem:** The hook assumes:

1. You're in repo root when committing
2. `frontend/` directory exists
3. `frontend/package.json` exists
4. `scripts/lib/` directory exists

**Impact:**

- If you commit from a subdirectory, hook might fail
- If directory structure changes, hook breaks
- Paths are relative to repo root

**What to do:**

- Always commit from repo root (or let Git handle it)
- Don't reorganize directories without updating hook
- Test hook after structural changes

---

### 8. Network Dependency for First Run

**Status:** ⚠️ **FIRST RUN ONLY**

**Problem:**

- `npx prettier` will download Prettier on first run if not installed
- Requires internet connection
- Subsequent runs use cached version

**Impact:**

- First commit might be slow (downloads ~10MB)
- Won't work offline on first run
- After first run, works offline

**Solution:**

```bash
# Install Prettier explicitly to avoid first-run download
cd frontend
npm install --save-dev prettier
```

---

### 9. Error Suppression Hides Real Issues

**Status:** ⚠️ **SILENT FAILURES**

**Problem:** Multiple commands use `|| true` or `2>/dev/null`:

```bash
npx prettier --write 2>/dev/null || true
git add 2>/dev/null || true
```

**Impact:**

- If Prettier isn't found, hook silently continues
- If git add fails, hook continues anyway
- Real errors are hidden until CI catches them

**What to watch:**

- Check CI results to catch formatting issues
- Don't ignore hook warnings
- Consider removing `|| true` for critical commands

---

### 10. Path Handling with Spaces

**Status:** ⚠️ **POTENTIAL BREAKAGE**

**Problem:** The hook uses `sed` and `xargs` which might break with:

- File paths containing spaces
- File paths with special characters
- Very long paths

**Example of potential issue:**

```bash
# If file is: "frontend/src/my file with spaces.ts"
# sed strips to: "src/my file with spaces.ts"
# xargs might split on spaces incorrectly
```

**What to watch:**

- Avoid spaces in file/directory names
- Test with files that have special characters
- Consider using `find -print0` and `xargs -0` for better handling

---

## Setup Checklist for New Developers

### Initial Setup

1. **Install dependencies:**

   ```bash
   cd frontend
   npm install
   ```

2. **Verify Prettier is installed:**

   ```bash
   cd frontend
   npx prettier --version
   # Should show version number
   ```

3. **Verify Husky is set up:**

   ```bash
   git config --get core.hooksPath
   # Should show .githooks
   ls -la .husky/pre-commit
   # Should exist and be executable
   ```

4. **Make hook executable (if needed):**

   ```bash
   chmod +x .husky/pre-commit
   ```

5. **Test the hook:**
   ```bash
   # Make a small change
   echo "// test" >> frontend/src/App.tsx
   git add frontend/src/App.tsx
   git commit -m "Test commit"
   # Should see Prettier running
   ```

### Verify Everything Works

```bash
# 1. Check Prettier
cd frontend && npx prettier --version

# 2. Check hook is executable
test -x ../.husky/pre-commit && echo "OK" || echo "NOT EXECUTABLE"

# 3. Check dependencies
test -f ../scripts/lib/error-detection.sh && echo "OK" || echo "MISSING"
test -f ../scripts/lib/anti-pattern-detection.sh && echo "OK" || echo "MISSING"

# 4. Test formatting
cd frontend
npm run format:check
```

---

## Troubleshooting for This Environment

### Hook Doesn't Run

**Check:**

```bash
# 1. Verify Husky is initialized
git config --get core.hooksPath

# 2. Check hook exists and is executable
ls -la .husky/pre-commit

# 3. Re-initialize if needed
npx husky install
chmod +x .husky/pre-commit
```

### Prettier Not Found

**Check:**

```bash
cd frontend
npm list prettier
# If not listed, install it
npm install --save-dev prettier
```

### Hook Fails Silently

**Check:**

```bash
# Run hook manually to see errors
bash .husky/pre-commit

# Check if scripts exist
test -f scripts/lib/error-detection.sh
test -f scripts/lib/anti-pattern-detection.sh
```

### Path Issues

**If files aren't being formatted:**

```bash
# Check if files match the pattern
git diff --cached --name-only | grep -E "\.(ts|tsx)$"

# Test Prettier manually
cd frontend
npx prettier --check "src/App.tsx"
```

---

## Environment-Specific Recommendations

### For This Linux Environment

1. ✅ **`xargs -r` works** - No need to change (GNU xargs available)
2. ⚠️ **Install Prettier explicitly** - Add to `package.json` devDependencies
3. ⚠️ **Verify hook executable** - Check after clone
4. ⚠️ **Test first commit** - First run downloads Prettier (slow)
5. ⚠️ **Watch for path issues** - Spaces in filenames might break

### Recommended Improvements

1. **Add Prettier to package.json:**

   ```bash
   cd frontend
   npm install --save-dev prettier
   ```

2. **Add setup script:**

   ```bash
   # scripts/setup-dev.sh
   chmod +x .husky/pre-commit
   cd frontend && npm install
   ```

3. **Better error handling:**
   - Remove `|| true` from critical commands
   - Add explicit error messages
   - Fail fast on missing dependencies

---

## Summary

**For developers on this machine:**

1. ⚠️ **Prettier not installed** - Run `npm install` in frontend/
2. ⚠️ **First commit will be slow** - Prettier downloads on first run
3. ✅ **xargs -r works** - No macOS compatibility issues
4. ⚠️ **Multiple cd operations** - Fragile, test after directory changes
5. ⚠️ **Error suppression** - Real errors might be hidden
6. ⚠️ **Path handling** - Spaces in filenames might break
7. ⚠️ **Dependencies on scripts** - Don't delete error-detection scripts
8. ⚠️ **Working directory** - Commit from repo root

**Most critical:** Install Prettier explicitly to avoid first-run download
delay.
