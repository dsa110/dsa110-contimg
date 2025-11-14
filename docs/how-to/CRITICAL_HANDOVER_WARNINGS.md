# Critical Handover Warnings

**🚀 NEW: Most issues are now AUTOMATED! See `docs/how-to/AUTOMATION_GUIDE.md`**

**⚠️ READ THIS FIRST** - These are the most common pitfalls that will break your
workflow.

## 1. Python Environment - MANDATORY

**CRITICAL:** You MUST use `casa6` Python, NOT system Python.

```bash
# ✅ CORRECT
/opt/miniforge/envs/casa6/bin/python -m pytest

# ❌ WRONG - WILL FAIL
python3 -m pytest
python -m pytest
```

**Why:** System Python (3.6.9) lacks CASA dependencies. The pipeline WILL FAIL
without casa6.

**Setup:**

```bash
# Always use this path
export PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"

# Or source the agent setup
source /data/dsa110-contimg/scripts/agent-setup.sh
```

**Reference:** `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`

---

## 2. Error Detection System - Must Be Enabled

**CRITICAL:** Error detection is NOT automatically enabled in all shells.

**Problem:** Commands can fail silently or warnings can be missed.

**Solution:** Always source the setup at the start of a session:

```bash
source /data/dsa110-contimg/scripts/agent-setup.sh
```

**What it does:**

- Wraps Python/pytest commands to detect errors/warnings in real-time
- Terminates immediately on error/warning detection
- Works with both `pexpect` and `subprocess` backends

**Reference:** `docs/how-to/agentic-session-setup.md`

---

## 3. Pytest Redirection - NEVER Use `2>&1` Directly

**CRITICAL:** This will break pytest commands.

```bash
# ❌ WRONG - pytest will try to interpret "2>&1" as a test path
pytest tests/ 2>&1 | tee log.txt

# ✅ CORRECT - Use the safe wrapper
./scripts/pytest-safe.sh tests/ | tee log.txt

# ✅ CORRECT - Let the wrapper handle it
./scripts/run-tests.sh unit
```

**Why:** Pytest receives `2>&1` as a literal argument and tries to find a test
file named "2>&1".

**Reference:** `internal/docs/dev/imported/PYTEST_REDIRECTION_FIX.md`

---

## 4. Test Organization - Strict Enforcement

**CRITICAL:** All tests MUST follow the taxonomy or commits will be blocked.

**Rules:**

1. Tests must be in correct directory: `tests/<category>/<module>/test_*.py`
2. Tests must have correct pytest marker: `@pytest.mark.<category>`
3. Pre-commit hook validates and BLOCKS invalid commits

**Categories:**

- `smoke` - Quick sanity checks (< 10s)
- `unit` - Fast, isolated tests
- `integration` - Component interactions
- `science` - Science validation
- `e2e` - End-to-end workflows

**Adding New Tests:**

```bash
# Use the template generator
python scripts/test-template.py <type> <module> <feature>
```

**Reference:**

- `docs/concepts/TEST_ORGANIZATION.md`
- `docs/how-to/adding-new-tests.md`

---

## 5. Pre-commit Hooks - Multiple Validations

**CRITICAL:** Pre-commit hooks run automatically and can block commits.

**What runs:**

1. **Prettier formatting** - Formats frontend code automatically
2. **Test organization validation** - Blocks invalid test structure
3. **Git lock file cleanup** - Removes stale lock files

**If commit is blocked:**

- Fix the issues shown in the error message
- Files are auto-formatted, but you may need to re-stage them
- Test organization issues must be fixed manually

**Location:** `.githooks/pre-commit` (Git configured to use `.githooks/`)

---

## 6. Directory Structure - Don't Create Files in Root

**CRITICAL:** Documentation and data have strict location rules.

**Before creating ANY file:**

1. Check `docs/concepts/DIRECTORY_ARCHITECTURE.md`
2. Check `docs/DOCUMENTATION_QUICK_REFERENCE.md`

**Key paths:**

- Code: `/data/dsa110-contimg/`
- Data: `/stage/dsa110-contimg/` (SSD) or `/data/dsa110-contimg/` (HDD)
- Docs: `docs/` structure (see documentation rules)
- State DBs: `/data/dsa110-contimg/state/`

**Documentation locations:**

- How-to guides: `docs/how-to/`
- Concepts: `docs/concepts/`
- Reference: `docs/reference/`
- Dev notes: `internal/docs/dev/notes/`

**Reference:** `.cursor/rules/documentation-location.mdc`

---

## 7. CASA Environment - casacore Data Paths

**CRITICAL:** CASA requires specific data paths.

**Problem:**
`PermissionError: [Errno 13] Permission denied: '/usr/lib/python3/dist-packages/casacore/data'`

**Why:** Code might try to modify system Python paths instead of casa6 paths.

**Solution:** The `ensure_casa_path` utility checks for "casa6" or "miniforge"
before creating symlinks.

**Location:** `src/dsa110_contimg/utils/casa_init.py`

---

## 8. Git Lock Files - Automatic Cleanup

**CRITICAL:** `.git/index.lock` can block Git operations.

**What happens:**

- Pre-commit hook automatically removes stale lock files
- Manual fix: `./scripts/fix-git-lock.sh`

**If you see lock file errors:**

- Wait a moment (hook should clean it up)
- Or run the fix script manually
- Never delete lock files if Git is actively using them

---

## 9. Test Execution - Use Wrapper Scripts

**CRITICAL:** Don't run pytest directly.

**Use:**

```bash
# ✅ CORRECT - Uses safe wrapper
./scripts/run-tests.sh unit
./scripts/run-tests.sh integration
./scripts/run-tests.sh smoke

# ❌ WRONG - May have redirection issues
pytest tests/unit/
```

**Why:** The wrapper handles:

- Python environment (casa6)
- Redirection issues
- Error detection
- Proper argument passing

---

## 10. Mock Data vs Real Data - Always Verify

**CRITICAL:** Never assume test data is real observational data.

**Verification checklist:**

1. Check file location (tests/ = test data)
2. Check FITS headers for `DATE-OBS`, `TELESCOP`
3. Check file naming (test\_\* = synthetic)

**Real data locations:**

- `/stage/dsa110-contimg/images/`
- `/data/dsa110-contimg/products/images/`

**Reference:** `.cursor/rules/data-provenance-verification.mdc`

---

## 11. Error Acknowledgment - Never Ignore Failures

**CRITICAL:** All test failures must be acknowledged and investigated.

**Rules:**

- Never claim success when tests fail
- Never dismiss failures as "minor" without investigation
- Always report exact failure counts
- Always investigate root causes

**Reference:** `.cursor/rules/error-acknowledgment.mdc`

---

## 12. Frontend vs Backend - Read-Only Backend

**CRITICAL:** When working on dashboard features, backend is READ-ONLY.

**Rules:**

- Frontend code: `frontend/src/`
- Backend code: Reference only, don't modify
- Use Material-UI v6 (NOT Blueprint, Ant Design, etc.)
- Check `package.json` before adding dependencies

**Reference:** `.cursor/rules/dashboard-architecture.mdc`

---

## Quick Start Checklist

Before starting work:

- [ ] Source error detection: `source scripts/agent-setup.sh`
- [ ] Verify Python: `/opt/miniforge/envs/casa6/bin/python --version`
- [ ] Check test organization rules if adding tests
- [ ] Review directory structure rules if creating files
- [ ] Use wrapper scripts for pytest: `./scripts/run-tests.sh`

---

## Emergency Contacts / Resources

- **Python Environment Issues:** `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md`
- **Test Organization:** `docs/concepts/TEST_ORGANIZATION.md`
- **Error Detection:** `docs/how-to/agentic-session-setup.md`
- **Directory Structure:** `docs/concepts/DIRECTORY_ARCHITECTURE.md`
- **Pytest Issues:** `docs/dev/PYTEST_REDIRECTION_FIX.md`

---

## Most Common Mistakes (Top 5)

1. **Using system Python instead of casa6** → Pipeline fails
2. **Running pytest with `2>&1` directly** → "file not found: 2>&1" error
3. **Not sourcing error detection** → Silent failures
4. **Creating tests without proper markers/directories** → Commit blocked
5. **Creating files in wrong locations** → Violates organization rules

---

**Last Updated:** 2025-01-28
