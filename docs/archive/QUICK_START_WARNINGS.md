# ⚠️ CRITICAL WARNINGS - Quick Reference

**Read this before writing any code!**

**🛡️ AUTOMATED PROTECTIONS:** Run `./scripts/install-developer-automations.sh`
to automatically prevent most of these issues. See
`docs/how-to/AUTOMATED_PROTECTIONS.md` for details.

## 🔴 Top 5 Critical Mistakes to Avoid

### 1. Python Environment

```bash
# ❌ WRONG
python script.py

# ✅ CORRECT
/opt/miniforge/envs/casa6/bin/python script.py
```

**Why:** System Python lacks CASA dependencies. Pipeline WILL FAIL.

---

### 2. Pytest Redirection

```bash
# ❌ WRONG - Causes "ERROR: file or directory not found: 2>&1"
python -m pytest tests/ 2>&1

# ✅ CORRECT
./scripts/pytest-safe.sh tests/ -v
./scripts/run-tests.sh unit
```

**Why:** `2>&1` gets passed as test path argument.

---

### 3. Error Detection Setup

```bash
# ✅ ALWAYS do this first in agentic sessions
source /data/dsa110-contimg/scripts/developer-setup.sh
```

**Why:** Without this, test failures go undetected.

---

### 4. Test Organization

```bash
# ✅ Use template before creating tests
python scripts/test-template.py <type> <module> <feature>
```

**Why:** Pre-commit hook blocks improperly organized tests.

---

### 5. Documentation Location

```bash
# ❌ WRONG - Root directory
echo "# Status" > STATUS.md

# ✅ CORRECT - Check docs/DOCUMENTATION_QUICK_REFERENCE.md first
```

**Why:** Root markdown files get moved during cleanup.

---

## 🚨 Other Critical Warnings

- **Synthetic vs Real Data**: Always verify provenance (check file location,
  FITS headers)
- **Database Schemas**: Already exist - don't create new ones
- **Frontend/Backend**: Frontend modifies `frontend/src/`, backend is read-only
  reference
- **Command Output**: Never suppress with `2>/dev/null` unless explicitly
  requested
- **Error Acknowledgment**: Never dismiss errors - investigate and report
  accurately

---

## 📚 Full Details

**Complete handover guide:** `docs/how-to/DEVELOPER_HANDOVER_WARNINGS.md`

**Essential docs:**

- `docs/concepts/DIRECTORY_ARCHITECTURE.md` - File organization
- `docs/DOCUMENTATION_QUICK_REFERENCE.md` - Documentation location
- `docs/concepts/TEST_ORGANIZATION.md` - Test taxonomy
- `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` - Python environment

---

**Remember:** These rules exist for good reasons. Follow them to avoid hours of
debugging.
