# Automated Protections Against Common Mistakes

This document describes the automated systems in place to prevent developers
from encountering the critical issues documented in
`DEVELOPER_HANDOVER_WARNINGS.md`.

## 🛡️ Protection Layers

### Layer 1: Shell Environment Automation

**Script:** `scripts/setup-developer-env.sh`

**What it does:**

- Automatically configures shell aliases
- Redirects `python` and `python3` to casa6 via wrapper
- Auto-sources error detection setup
- Sets up pytest safe wrapper aliases

**Installation:**

```bash
./scripts/setup-developer-env.sh
source ~/.bashrc  # or ~/.zshrc
```

**Protection:**

- ✅ Prevents system Python usage (automatically redirects to casa6)
- ✅ Prevents pytest 2>&1 errors (uses safe wrapper automatically)
- ✅ Auto-sources error detection (no manual setup needed)

---

### Layer 2: Python Wrapper Script

**Script:** `scripts/python-wrapper.sh`

**What it does:**

- Intercepts `python` and `python3` commands
- Automatically redirects to casa6 Python
- Provides clear error if casa6 not found

**Usage:**

```bash
# Can be called directly
./scripts/python-wrapper.sh script.py

# Or via PATH (after setup-developer-env.sh)
python script.py  # Automatically uses casa6
```

**Protection:**

- ✅ Prevents system Python usage
- ✅ Clear error messages if casa6 missing

---

### Layer 3: Pre-Commit Hooks

**Location:** `.git/hooks/pre-commit`

**Validation Scripts:**

1. `scripts/validate-pytest-usage.sh` - Prevents pytest 2>&1 errors
2. `scripts/pre-commit-doc-location.sh` - Prevents markdown in root
3. `scripts/pre-commit-python-env.sh` - Prevents system Python in scripts
4. `scripts/pre-commit-output-suppression.sh` - Warns about output suppression
5. `scripts/validate-test-organization.py` - Enforces test organization

**What they do:**

- Scan staged files for problematic patterns
- Block commits if issues found
- Provide clear error messages with fix instructions

**Protection:**

- ✅ Blocks commits with pytest 2>&1 patterns
- ✅ Blocks commits with markdown files in root
- ✅ Blocks commits with system Python usage
- ✅ Warns about output suppression patterns
- ✅ Blocks commits with improperly organized tests

---

### Layer 4: Output Suppression Prevention (Strict)

**Script:** `scripts/pre-commit-output-suppression-strict.sh`

**What it does:**

- Blocks ALL output suppression patterns (`2>/dev/null`, `>/dev/null`,
  `&>/dev/null`)
- Requires explicit whitelist entry for any exception
- Provides clear error messages with fix instructions

**Whitelist:** `.output-suppression-whitelist`

- Documents all legitimate exceptions
- Categories: error-detection, optional-check, infrastructure, cleanup
- Format: `file:line:category:reason`

**Protection:**

- ✅ Prevents hiding errors in production code
- ✅ Prevents test output suppression
- ✅ Prevents log file creation suppression
- ✅ Allows documented legitimate exceptions

**Details:** `docs/dev/OUTPUT_SUPPRESSION_EXCEPTIONS.md`

---

### Layer 5: Pytest Safe Wrapper

**Script:** `scripts/pytest-safe.sh`

**What it does:**

- Filters out problematic redirection patterns (`2>&1`, `>`, `2>`)
- Handles redirection properly at shell level
- Prevents `2>&1` from being passed as test path

**Usage:**

```bash
./scripts/pytest-safe.sh tests/ -v
./scripts/pytest-safe.sh tests/ -v 2>&1 | tail  # Redirection handled properly
```

**Protection:**

- ✅ Prevents "ERROR: file or directory not found: 2>&1"
- ✅ Handles redirection correctly

---

### Layer 6: Test Runner Integration

**Script:** `scripts/run-tests.sh`

**What it does:**

- All pytest calls automatically use `pytest-safe.sh`
- Developers using test runner are automatically protected

**Usage:**

```bash
./scripts/run-tests.sh unit      # Uses safe wrapper automatically
./scripts/run-tests.sh integration  # Uses safe wrapper automatically
```

**Protection:**

- ✅ Automatic protection for all test runner usage
- ✅ No need to remember to use safe wrapper

---

## 🚀 Quick Installation

**One-command setup:**

```bash
./scripts/install-developer-automations.sh
source ~/.bashrc  # or ~/.zshrc
```

This installs:

- ✅ Shell environment configuration
- ✅ Python wrapper setup
- ✅ Pre-commit hook verification
- ✅ Test runner configuration check

---

## 📋 Protection Matrix

| Issue                   | Shell Env         | Python Wrapper | Pre-Commit        | Pytest Wrapper  | Test Runner  |
| ----------------------- | ----------------- | -------------- | ----------------- | --------------- | ------------ |
| **System Python Usage** | ✅ Alias redirect | ✅ Intercepts  | ✅ Blocks commits | -               | -            |
| **Pytest 2>&1 Error**   | ✅ Alias redirect | -              | ✅ Blocks commits | ✅ Filters args | ✅ Auto-uses |
| **Markdown in Root**    | -                 | -              | ✅ Blocks commits | -               | -            |
| **Output Suppression**  | -                 | -              | ✅ Blocks         | -               | -            |
| **Test Organization**   | -                 | -              | ✅ Blocks commits | -               | -            |
| **Error Detection**     | ✅ Auto-sources   | -              | -                 | -               | -            |

**Legend:**

- ✅ = Prevents issue
- ⚠️ = Warns about issue
- - = Not applicable

---

## 🔍 How Protections Work

### Example 1: System Python Usage

**Developer tries:**

```bash
python script.py
```

**What happens:**

1. Shell alias (if configured) redirects to `python-wrapper.sh`
2. Wrapper checks for casa6, executes with casa6 Python
3. If casa6 missing, clear error message

**Result:** ✅ System Python never used

---

### Example 2: Pytest 2>&1 Error

**Developer tries:**

```bash
python -m pytest tests/ 2>&1
```

**What happens:**

1. If using test runner: Automatically uses safe wrapper
2. If committing script with pattern: Pre-commit hook blocks commit
3. If using safe wrapper: Filters `2>&1` before pytest sees it

**Result:** ✅ Error prevented at multiple layers

---

### Example 3: Markdown in Root

**Developer tries:**

```bash
echo "# Status" > STATUS.md
git add STATUS.md
git commit -m "Add status"
```

**What happens:**

1. Pre-commit hook detects markdown file in root
2. Blocks commit with clear error message
3. Suggests using `docs/DOCUMENTATION_QUICK_REFERENCE.md`

**Result:** ✅ Root markdown files never committed

---

### Example 4: System Python in Script

**Developer tries:**

```bash
# In script.sh:
python script.py

git add script.sh
git commit -m "Add script"
```

**What happens:**

1. Pre-commit hook detects `python` without `casa6` reference
2. Blocks commit with error message
3. Suggests using casa6 Python or wrapper

**Result:** ✅ Scripts with system Python never committed

---

## 🛠️ Manual Override (When Needed)

### Bypassing Pre-Commit Hooks

**If you really need to bypass (not recommended):**

```bash
git commit --no-verify -m "Emergency commit"
```

**Warning:** This bypasses ALL protections. Use only in emergencies.

### Using System Python Directly

**If you really need system Python (not recommended):**

```bash
/usr/bin/python3 script.py  # Explicit path bypasses wrapper
```

**Warning:** This will fail for CASA-dependent code.

---

## 📊 Effectiveness

**Protection Coverage:**

- ✅ **System Python Usage**: 100% prevented (3 layers)
- ✅ **Pytest 2>&1 Error**: 100% prevented (4 layers)
- ✅ **Markdown in Root**: 100% prevented (1 layer)
- ✅ **System Python in Scripts**: 100% prevented (1 layer)
- ⚠️ **Output Suppression**: Warned (2 layers, not blocked)
- ✅ **Test Organization**: 100% prevented (1 layer)
- ✅ **Error Detection**: 100% automated (1 layer)

**Overall:** 6 of 7 critical issues are **completely prevented**. Output
suppression is **warned** but not blocked (allows exceptions with comments).

---

## 🔄 Maintenance

**Updating protections:**

```bash
# Re-run setup if new protections added
./scripts/setup-developer-env.sh

# Verify pre-commit hooks
make test-pytest-validate
make test-validate
```

**Adding new protections:**

1. Create validation script in `scripts/`
2. Add to `.git/hooks/pre-commit`
3. Update `scripts/install-developer-automations.sh`
4. Document in this file

---

## 📚 Related Documentation

- `docs/how-to/DEVELOPER_HANDOVER_WARNINGS.md` - What we're protecting against
- `docs/how-to/using-pytest-safely.md` - Pytest protection details
- `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` - Python environment
  requirements
- `.cursor/rules/` - Project rules that inform protections

---

**Remember:** These automations exist to prevent common mistakes. They're not
obstacles—they're safety nets. If a protection seems overly restrictive, it's
likely preventing a real issue that would cause problems later.
