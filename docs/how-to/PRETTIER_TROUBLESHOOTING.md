# Prettier Integration — Troubleshooting & Best Practices

## Critical Issues

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

## Important Warnings

**Date:** 2025-11-13  
**Audience:** Developers working with this codebase

---

## ⚠️ Critical Warnings

### 1. Pre-Commit Hook Modifies Files During Commit

**What happens:**

- Prettier **automatically formats** your staged files before commit
- Formatted files are **automatically re-staged** with `git add`
- Your commit will include formatting changes you didn't explicitly make

**Why this matters:**

- If you have uncommitted changes to the same files, they might get formatted
  unexpectedly
- The commit will include both your changes AND Prettier formatting changes
- This can make it harder to review what you actually changed vs. what Prettier
  formatted

**What to do:**

- Commit frequently to avoid large formatting diffs
- Review `git diff` after staging to see what will be formatted
- Consider running `npm run format` manually before committing if you want to
  review changes first

---

### 2. Path Handling Complexity (Frontend Files)

**The issue:** The pre-commit hook uses `sed` to strip the `frontend/` prefix
when running Prettier from inside the `frontend/` directory:

```bash
echo "$STAGED_FRONTEND_FILES" | sed 's|^frontend/||' | xargs -r npx prettier --write
```

**Why this is fragile:**

- If file paths have spaces or special characters, this could break
- The `sed` command assumes paths start with `frontend/`
- If the working directory changes, paths might be wrong

**What to watch for:**

- Files with spaces in names might not format correctly
- If you modify the hook, test with various file path patterns
- Be careful when changing directory structure

---

### 3. `xargs -r` Flag (GNU-specific)

**The issue:** The hook uses `xargs -r` which is a GNU extension (not available
on macOS by default).

**What happens:**

- On Linux: Works fine
- On macOS: May fail silently or error if GNU coreutils not installed
- The `-r` flag prevents `xargs` from running if input is empty

**Solutions:**

- Install GNU coreutils on macOS: `brew install coreutils`
- Or modify the hook to handle empty input differently
- Test the hook on your development machine

---

### 4. Error Suppression (`|| true`)

**The issue:** Several commands use `|| true` to suppress errors:

```bash
echo "$STAGED_FRONTEND_FILES" | xargs -r npx prettier --write 2>/dev/null || true
```

**Why this is dangerous:**

- Real errors (like Prettier not found) are hidden
- Network issues, permission problems, etc. are silently ignored
- You might not know formatting failed until CI catches it

**What to watch for:**

- If Prettier isn't installed, the hook will silently skip formatting
- Check CI results to catch formatting issues
- Consider removing `|| true` and handling errors explicitly

---

### 5. Prettier Runs Twice (Format + Check)

**What happens:**

1. First run: `prettier --write` (formats files)
2. Second run: `prettier --check` (verifies formatting)

**Performance impact:**

- For large commits (many files), this doubles the execution time
- Can make commits slow (especially with many TypeScript files)

**Why it's done this way:**

- Formatting might fail silently (due to `|| true`)
- The check ensures formatting actually worked
- But it's inefficient

**Considerations:**

- Large commits might take 10-30 seconds
- Consider batching commits or formatting manually for large changes

---

### 6. Only Staged Files Are Formatted

**Important:**

- Prettier only formats files you've staged (`git add`)
- Unstaged changes in the same files are NOT formatted
- This can lead to inconsistent formatting

**Example:**

```bash
# File has both staged and unstaged changes
git add src/App.tsx  # Stage some changes
# Edit src/App.tsx again (unstaged)

---
## Additional References (Archived)
- PRETTIER_ENVIRONMENT_SPECIFIC.md (archived)
- PRETTIER_FIXES_APPLIED.md (archived)
- PRETTIER_INTEGRATION.md (archived analysis)
```
