# Troubleshooting Quick Reference

**For:** Developers who see errors and need quick fixes

---

## "I see this error, what do I do?"

### Error: "Using wrong Python environment"

**What you see:**

```
Error: Using wrong Python: /usr/bin/python
Should be: /opt/miniforge/envs/casa6/bin/python
```

**Quick fix:**

```bash
conda activate casa6
# Or
export PATH="/opt/miniforge/envs/casa6/bin:$PATH"
```

**Or use wrapper:**

```bash
./scripts/run-python.sh your_script.py
```

**Why:** System Python is too old. Must use casa6.

---

### Error: "Pre-commit hook is not executable"

**What you see:**

```
Error: Pre-commit hook is not executable
```

**Quick fix:**

```bash
chmod +x .husky/pre-commit
# Or run setup:
./scripts/setup-dev.sh
```

**Why:** Git `core.filemode=false` doesn't track executable bits.

---

### Error: "Prettier not found"

**What you see:**

```
Error: Prettier not found
```

**Quick fix:**

```bash
cd frontend
npm install
# Or
npm install --save-dev prettier
```

**Why:** Prettier needs to be installed in node_modules.

---

### Warning: "Found console.log statements"

**What you see:**

```
Warning: Found 5 console.log statements in frontend code
```

**Quick fix:**

```bash
# Find them:
grep -r "console\.log" frontend/src

# Remove or replace with proper logging
# Use a logging library or remove debug statements
```

**Why:** Debug statements shouldn't be in production code.

---

### Warning: "Markdown files in root directory"

**What you see:**

```
Warning: Found 3 markdown file(s) in root directory
```

**Quick fix:**

```bash
# Move to docs/ structure:
mv YOUR_FILE.md docs/dev/status/$(date +%Y-%m)/your_file.md

# See docs/DOCUMENTATION_QUICK_REFERENCE.md for correct location
```

**Why:** Documentation has organized structure.

---

### Error: "Test organization validation failed"

**What you see:**

```
Error: Test organization validation failed
```

**Quick fix:**

```bash
# Check what's wrong:
make test-validate

# Move test to correct location:
# tests/<type>/<module>/test_*.py
# Types: unit, integration, smoke, science, e2e
```

**Why:** Tests must follow taxonomy for organization.

---

### Error: "Type check failed"

**What you see:**

```
Error: Type check failed
```

**Quick fix:**

```bash
cd frontend
npm run type-check
# Fix the errors shown
```

**Why:** TypeScript type errors must be fixed.

---

### Error: "Lint check failed"

**What you see:**

```
Error: Lint check failed
```

**Quick fix:**

```bash
cd frontend
npm run lint
# Fix the errors shown
# Or auto-fix:
npm run lint -- --fix
```

**Why:** Code style must be consistent.

---

### Error: "Failed to get staged files"

**What you see:**

```
Error: Failed to get staged files
```

**Quick fix:**

```bash
# Make sure you're in the repo root:
cd /data/dsa110-contimg

# Check git status:
git status
```

**Why:** Pre-commit hook needs to be in repo root.

---

### Warning: "Environment issues detected"

**What you see:**

```
⚠️  Post-commit check: Environment issues detected
```

**Quick fix:**

```bash
./scripts/setup-dev.sh
# Or check details:
./scripts/check-environment.sh
```

**Why:** Setup wasn't run or environment changed.

---

## Common Mistakes

### "I used `python` instead of casa6"

**Problem:** Code fails or uses wrong dependencies.

**Fix:**

```bash
# Always use:
/opt/miniforge/envs/casa6/bin/python script.py

# Or use wrapper:
./scripts/run-python.sh script.py
```

---

### "I didn't run setup-dev.sh"

**Problem:** Hooks don't work, dependencies missing.

**Fix:**

```bash
./scripts/setup-dev.sh
```

---

### "I created a file in the wrong place"

**Problem:** File doesn't follow conventions.

**Fix:**

- Check `docs/concepts/DIRECTORY_ARCHITECTURE.md`
- Check `docs/DOCUMENTATION_QUICK_REFERENCE.md`
- Move file to correct location

---

### "I ignored a warning and now CI fails"

**Problem:** Warnings become errors in CI.

**Fix:**

- Read the warning message
- Fix the issue
- Re-commit

---

## Still Stuck?

1. **Check the full documentation:**
   - `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md`
   - `docs/how-to/AUTOMATED_GOTCHA_PREVENTION.md`

2. **Run diagnostics:**

   ```bash
   ./scripts/check-environment.sh
   ./scripts/check-code-quality.sh
   ```

3. **Check error messages:**
   - Read the full error
   - Look for "Fix:" instructions
   - Follow the suggested steps

4. **Ask for help:**
   - Include full error message
   - Include output of check scripts
   - Include what you've tried

---

## Prevention

**Before starting work:**

```bash
./scripts/setup-dev.sh
./scripts/check-environment.sh
```

**Before committing:**

```bash
make check-code-quality
git status  # Check what you're committing
```

**After committing:**

- Read post-commit warnings
- Fix issues before pushing
