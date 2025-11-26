# Quick Reference - Critical Warnings

**For:** Developers taking over this project  
**Full details:** See `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md`

---

## 🚨 Top 5 Critical Warnings

### 1. **ALWAYS Use casa6 Python**

```bash
# WRONG
python script.py

# CORRECT
/opt/miniforge/envs/casa6/bin/python script.py
```

**Why:** System Python (3.6.9) is too old. CASA dependencies only in casa6.

---

### 2. **Never Create Files in Root**

```bash
# WRONG
echo "# Status" > STATUS.md

# CORRECT
echo "# Status" > docs/dev/status/2025-11/status.md
```

**Why:** Documentation organization is enforced. Root files will be moved.

---

### 3. **Run Setup Script After Clone**

```bash
./scripts/setup-dev.sh
```

**Why:** Makes hooks executable, installs dependencies, verifies Prettier.

---

### 4. **Never Ignore Test Failures**

```bash
# WRONG
"32 tests passed, mostly works" (when 7 failed)

# CORRECT
"32 passed, 7 failed. Status: FAILURE. Investigating..."
```

**Why:** Error acknowledgment is enforced. All failures must be reported.

---

### 5. **Check Existing Code Before Adding**

- **API endpoints:** 100+ already exist - check before creating new ones
- **UI libraries:** Use Material-UI v6 only - don't suggest alternatives
- **Database schemas:** Don't modify when working on frontend
- **Test organization:** Pre-commit hook enforces structure

---

## 🔧 Quick Setup Checklist

```bash
# 1. Verify Python
which python  # Should be /opt/miniforge/envs/casa6/bin/python

# 2. Setup environment
./scripts/setup-dev.sh

# 3. Verify Prettier
cd frontend && npm run format:check

# 4. Verify tests
make test-unit
```

---

## 📚 Essential Docs

1. `docs/concepts/DIRECTORY_ARCHITECTURE.md` - File organization
2. `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` - Python setup
3. `docs/DOCUMENTATION_QUICK_REFERENCE.md` - Where to put docs
4. `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md` - Full warnings

---

## 🚫 Common Mistakes

| Mistake                             | Fix                                        |
| ----------------------------------- | ------------------------------------------ |
| Using `python` instead of casa6     | Use `/opt/miniforge/envs/casa6/bin/python` |
| Creating files in root              | Use `docs/` structure                      |
| Ignoring test failures              | Report all failures                        |
| Not running setup script            | Run `./scripts/setup-dev.sh`               |
| Modifying backend for frontend work | Backend is read-only context               |

---

**Full details:** `docs/how-to/DEVELOPER_HANDOFF_WARNINGS.md`
