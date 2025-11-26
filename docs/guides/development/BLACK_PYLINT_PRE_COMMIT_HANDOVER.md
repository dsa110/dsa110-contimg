# Black & Pylint Pre-commit Hooks - Developer Handover Guide

**Date:** 2025-01-13  
**Status:** Active - Hooks run automatically on `git commit`

## Critical Warnings

### 1. **CASA6 Python Environment is MANDATORY**

**CRITICAL:** All hooks MUST use casa6 Python. Never use system Python or other
environments.

- **Path:** `/opt/miniforge/envs/casa6/bin/python`
- **Why:** System Python (3.6.9) lacks CASA dependencies. Pipeline WILL FAIL
  without casa6.
- **Verification:**
  `test -x /opt/miniforge/envs/casa6/bin/black || echo "Black not in casa6!"`

**If hooks fail with "command not found":**

```bash
# Install in casa6 (if missing)
/opt/miniforge/envs/casa6/bin/pip install black pylint pre-commit
# OR
conda install -c conda-forge black pylint -n casa6
```

### 2. **Black & isort Auto-Format on Commit**

**IMPORTANT:** Both Black and isort **automatically format** files during
pre-commit.

**What happens (in order):**

1. **isort** sorts and organizes imports automatically
2. **Black** formats code (including the sorted imports)
3. Formatted files are re-staged automatically
4. Commit proceeds with formatted code
5. **No manual intervention needed** - formatting happens transparently

**Why isort before Black?**

- isort handles import organization
- Black then formats the entire file (including imports)
- This order prevents conflicts between the two tools

**Note:** CI still uses `--check` mode to verify formatting, but pre-commit
auto-formats to prevent formatting issues from blocking commits.

### 3. **Git HooksPath Configuration**

**WARNING:** This project uses custom git hooks via `core.hooksPath = .githooks`

- Pre-commit hooks are **integrated** into `.githooks/pre-commit`
- **DO NOT** run `pre-commit install` - it will fail
- Hooks run automatically via `.githooks/pre-commit` integration
- Manual runs: `/opt/miniforge/envs/casa6/bin/pre-commit run --files <file>`

**If you see:**
`[ERROR] Cowardly refusing to install hooks with core.hooksPath set`

- This is **expected** - hooks are already integrated
- No action needed

### 4. **Pylint Only Checks Errors (Not Warnings)**

**Configuration:** Pylint uses `--errors-only` mode

- **Only reports:** Fatal errors and actual code errors
- **Ignores:** Style warnings, convention violations, refactoring suggestions
- **Why:** Reduces noise, focuses on critical issues
- **Test files:** Excluded from Pylint (too noisy)

**To see all Pylint issues (including warnings):**

```bash
/opt/miniforge/envs/casa6/bin/pylint src/dsa110_contimg/api/__init__.py
```

### 5. **Exclusion Patterns**

**Files excluded from hooks:**

- `archive/` - Legacy code
- `notebooks/` - Jupyter notebooks
- `*.venv/`, `venv/`, `env/` - Virtual environments
- `tests/.*test_.*\.py` - Test files (Pylint only; Black still checks them)

**If you need to check excluded files:**

```bash
# Manual Black check
/opt/miniforge/envs/casa6/bin/black --check archive/some_file.py

# Manual Pylint check
/opt/miniforge/envs/casa6/bin/pylint --errors-only archive/some_file.py
```

## Hook Execution Order

When you run `git commit`, hooks execute in this order:

1. **Prettier** (frontend files: `.js`, `.ts`, `.tsx`, `.json`, etc.)
2. **Black & Pylint** (Python files: `.py`) ← **NEW**
3. **Test Organization Validation** (test files: `tests/**/test_*.py`)

**If any step fails, commit is blocked.**

## Common Issues & Solutions

### Issue: "Black not found" or "Pylint not found"

**Solution:**

```bash
# Check if installed
/opt/miniforge/envs/casa6/bin/black --version
/opt/miniforge/envs/casa6/bin/pylint --version

# Install if missing
/opt/miniforge/envs/casa6/bin/pip install black pylint
```

### Issue: "pre-commit not found"

**Solution:**

```bash
# Install pre-commit in casa6
/opt/miniforge/envs/casa6/bin/pip install pre-commit
```

### Issue: Black formats file but commit still fails

**Likely cause:** Pylint found errors, or test organization validation failed

**Solution:**

```bash
# Check what actually failed (Black should have auto-formatted)
# If Pylint failed, fix the errors shown
# If test organization failed, check the validation output
```

### Issue: Pylint fails with cryptic error

**Solution:**

```bash
# Run Pylint directly to see full error
/opt/miniforge/envs/casa6/bin/pylint --errors-only <file>

# If it's a false positive, you can add a comment:
# pylint: disable=<error-code>
```

### Issue: Hook runs but doesn't check my file

**Check:**

1. Is file staged? `git status`
2. Is file excluded? Check `.pre-commit-config.yaml` exclude patterns
3. Is it a Python file? Only `.py` files are checked

### Issue: Want to bypass hooks temporarily

**WARNING:** Only do this if absolutely necessary (e.g., emergency hotfix)

```bash
# Skip hooks (NOT RECOMMENDED)
git commit --no-verify -m "Emergency fix"

# Better: Fix the issues first
/opt/miniforge/envs/casa6/bin/black <file>
git add <file>
git commit
```

## Manual Testing

**Test hooks manually (without committing):**

```bash
# Test on specific files
/opt/miniforge/envs/casa6/bin/pre-commit run --files src/dsa110_contimg/api/__init__.py

# Test all hooks on all files (slow)
/opt/miniforge/envs/casa6/bin/pre-commit run --all-files

# Test specific hook
/opt/miniforge/envs/casa6/bin/pre-commit run black --files src/dsa110_contimg/api/__init__.py
/opt/miniforge/envs/casa6/bin/pre-commit run pylint --files src/dsa110_contimg/api/__init__.py
```

## Configuration Files

**Key files:**

- `.pre-commit-config.yaml` - Pre-commit hook definitions
- `.githooks/pre-commit` - Git hook that calls pre-commit (integrated)
- `requirements-test.txt` - Lists `black>=23.0.0` and `pylint>=3.0.0`

**To modify hooks:**

1. Edit `.pre-commit-config.yaml`
2. Test: `/opt/miniforge/envs/casa6/bin/pre-commit run --all-files`
3. Commit changes

## CI Integration

**CI also runs Black (but not Pylint yet):**

- Location: `.github/workflows/validation-tests.yml`
- CI uses: `black --check --diff` (same as pre-commit)
- CI also runs: `flake8`, `isort`, `mypy` (not in pre-commit hooks)

**Why CI doesn't run Pylint:**

- Flake8 already covers linting in CI
- Pylint is more comprehensive but slower
- Pre-commit catches issues early (faster feedback)

## Differences: Pre-commit vs CI

| Tool   | Pre-commit            | CI                   | Notes                           |
| ------ | --------------------- | -------------------- | ------------------------------- |
| Black  | Yes (auto-format)     | Yes (`--check`)      | Pre-commit formats, CI verifies |
| isort  | Yes (auto-format)     | Yes (`--check-only`) | Pre-commit formats, CI verifies |
| Pylint | Yes (`--errors-only`) | No                   | Pre-commit only                 |
| Flake8 | No                    | Yes                  | CI only                         |
| mypy   | No                    | Yes (optional)       | CI only                         |

## Best Practices

1. **Black and isort auto-format on commit** - no need to format manually before
   committing

2. **Check Pylint before committing (optional):**

   ```bash
   /opt/miniforge/envs/casa6/bin/pylint --errors-only src/dsa110_contimg/api/__init__.py
   ```

3. **Run hooks before committing (optional, for testing):**

   ```bash
   /opt/miniforge/envs/casa6/bin/pre-commit run --files <your-file>
   ```

4. **Don't bypass hooks** - Fix issues instead

5. **Keep casa6 environment updated:**
   ```bash
   /opt/miniforge/envs/casa6/bin/pip install --upgrade black isort pylint pre-commit
   ```

## Troubleshooting Checklist

- [ ] Is casa6 Python available? `test -x /opt/miniforge/envs/casa6/bin/python`
- [ ] Are tools installed? `which black pylint pre-commit` (in casa6)
- [ ] Is file staged? `git status`
- [ ] Is file excluded? Check `.pre-commit-config.yaml`
- [ ] Run manually:
      `/opt/miniforge/envs/casa6/bin/pre-commit run --files <file>`
- [ ] Check hook logs: Look at git commit output

## Related Documentation

- **CASA6 Environment:** `docs/CASA6_ENVIRONMENT_GUIDE.md`
- **Code Quality:** `docs/DEVELOPMENT_ROADMAP.md` (section 3.1)
- **Test Organization:** `docs/concepts/TEST_ORGANIZATION.md`
- **Pre-commit Framework:** https://pre-commit.com

## Quick Reference

```bash
# Format a file manually (usually not needed - auto-formats on commit)
/opt/miniforge/envs/casa6/bin/isort <file>  # Sort imports first
/opt/miniforge/envs/casa6/bin/black <file>  # Then format code

# Check formatting without changes (for CI/verification)
/opt/miniforge/envs/casa6/bin/isort --check-only <file>
/opt/miniforge/envs/casa6/bin/black --check <file>

# Run pre-commit on specific files (tests hooks)
/opt/miniforge/envs/casa6/bin/pre-commit run --files <file1> <file2>

# Run all pre-commit hooks (tests all files)
/opt/miniforge/envs/casa6/bin/pre-commit run --all-files

# Check Pylint errors manually
/opt/miniforge/envs/casa6/bin/pylint --errors-only <file>

# Install/update tools
/opt/miniforge/envs/casa6/bin/pip install --upgrade black pylint pre-commit
```

---

**Remember:** These hooks are here to help maintain code quality. If they're
blocking you, fix the issues rather than bypassing them. The time spent fixing
formatting/linting issues is much less than debugging issues in production.
