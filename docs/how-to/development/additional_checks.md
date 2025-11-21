# Additional Automated Checks and Fixes

**Date:** 2025-11-13  
**Purpose:** Additional proactive checks to prevent code quality issues

---

## New Automated Checks

### 1. Code Quality Validation

**Script:** `scripts/check-code-quality.sh`

**What it checks:**

- ✅ Console.log/debug statements in production code
- ✅ Python shebang issues (wrong Python path)
- ✅ Markdown files in root directory
- ✅ Test files in wrong locations
- ✅ Large files that might be accidentally committed
- ✅ Potential hardcoded secrets
- ✅ Frontend environment variables without VITE\_ prefix

**Usage:**

```bash
./scripts/check-code-quality.sh
# Or via Makefile
make check-code-quality
# Or via npm
cd frontend && npm run check-code-quality
```

**Output:**

- ✅ Green checkmarks for passing checks
- ⚠️ Yellow warnings for non-critical issues
- ❌ Red errors for critical problems

---

### 2. Pre-commit Hook Enhancements

**File:** `.husky/pre-commit`

**New checks (warnings, not failures):**

- ⚠️ Warns about console.log statements in frontend code
- ⚠️ Lists markdown files found in root (not just count)

**Why warnings instead of failures:**

- Console.log might be intentional for debugging
- Documentation location is a warning, not a blocker
- Allows commit to proceed while alerting developer

---

### 3. Git Attributes

**File:** `.gitattributes`

**What it does:**

- Ensures consistent line endings (LF) across platforms
- Prevents line ending issues on Windows/Mac/Linux
- Marks binary files correctly

**Impact:**

- No more line ending conflicts
- Consistent file formatting
- Better cross-platform compatibility

---

### 4. Enhanced Setup Script

**Script:** `scripts/setup-dev.sh`

**New step:**

- Runs code quality check after environment setup
- Reports code quality issues (non-blocking)

---

## What Gets Checked

### Console.log Statements

**Issue:** Debug statements left in production code

**Check:**

```bash
grep -r "console\.log\|console\.debug" frontend/src
```

**Warning threshold:** More than 10 found (to avoid noise)

**Fix:** Manual removal or use proper logging

---

### Python Shebang Issues

**Issue:** Python scripts using wrong shebang

**Problem:**

```python
#!/usr/bin/env python  # Wrong - uses system Python
```

**Should be:**

```python
#!/opt/miniforge/envs/casa6/bin/python  # Correct
```

**Check:**

```bash
find scripts src tests -name "*.py" -exec head -1 {} \;
```

**Fix:** Manual update (requires review)

---

### Markdown Files in Root

**Issue:** Documentation files created in root directory

**Check:**

```bash
find . -maxdepth 1 -name "*.md" ! -name "README.md"
```

**Fix:** Move to `docs/` structure (manual, with guidance)

---

### Test Files in Wrong Locations

**Issue:** Test files not following taxonomy

**Check:**

```bash
find tests -name "test_*.py" ! -path "tests/unit/*" ! -path "tests/integration/*" ...
```

**Fix:** Move to correct location (manual, with guidance)

---

### Large Files

**Issue:** Large files accidentally committed

**Check:**

```bash
find . -type f -size +5M ! -path "*/node_modules/*" ...
```

**Warning:** Files larger than 5MB (excluding known large file locations)

**Fix:** Ensure in .gitignore

---

### Hardcoded Secrets

**Issue:** Secrets hardcoded in source code

**Check:**

```bash
grep -ri "password\s*=\s*['\"].*['\"]" src/ frontend/src/
```

**Exclusions:**

- Test files
- Known safe defaults (e.g., "demodemo")

**Fix:** Use environment variables

---

### Frontend Environment Variables

**Issue:** Using `process.env` without `VITE_` prefix

**Problem:**

```typescript
const apiUrl = process.env.API_URL; // Wrong - won't work
```

**Should be:**

```typescript
const apiUrl = import.meta.env.VITE_API_URL; // Correct
```

**Check:**

```bash
grep -r "process\.env\." frontend/src | grep -v "VITE_"
```

**Fix:** Use `import.meta.env.VITE_*` instead

---

## Integration

### Makefile

**New target:**

```makefile
make check-code-quality  # Check code quality
```

### npm Scripts

**New script:**

```json
"check-code-quality": "bash ../scripts/check-code-quality.sh"
```

**Usage:**

```bash
cd frontend
npm run check-code-quality
```

### Setup Script

**Enhanced:** `scripts/setup-dev.sh` now runs code quality check

---

## Developer Workflow

### Daily Development

```bash
# Before committing
make check-code-quality  # Check for code quality issues

# Fix issues, then commit
git commit -m "Your message"
# Pre-commit hook will also warn about console.log
```

### Pre-commit Warnings

**What you'll see:**

```
Warning: Found 3 console.log/debug statement(s) in frontend code
  Consider removing or using proper logging
```

**Action:** Review and remove or use proper logging

---

## What Can't Be Auto-Fixed

### Requires Manual Review

1. **Console.log statements** - Need to decide if intentional
2. **Python shebangs** - Need to verify casa6 path is correct
3. **Markdown file location** - Need to determine correct docs/ location
4. **Test file location** - Need to determine correct taxonomy
5. **Hardcoded secrets** - Need to verify if actually secret
6. **Large files** - Need to verify if should be in repo

### Can Be Auto-Fixed

1. **Git attributes** - Already in place
2. **Line endings** - Handled by .gitattributes
3. **Hook permissions** - Already automated

---

## Summary

**New checks:**

- ✅ Console.log detection
- ✅ Python shebang validation
- ✅ Documentation location
- ✅ Test organization
- ✅ Large file detection
- ✅ Secret detection
- ✅ Environment variable validation

**Integration:**

- ✅ Pre-commit hook warnings
- ✅ Setup script integration
- ✅ Makefile targets
- ✅ npm scripts

**Result:** More proactive detection of code quality issues before they become
problems.

---

## Related Documentation

- `docs/how-to/AUTOMATED_GOTCHA_PREVENTION.md` - Main automation doc
- `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md` - Full warnings list
- `docs/how-to/PRETTIER_WARNINGS.md` - Prettier-specific warnings
