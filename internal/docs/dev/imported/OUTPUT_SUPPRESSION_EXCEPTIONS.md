# Output Suppression Exceptions

This document describes legitimate exceptions to the "no output suppression"
rule and how to request whitelist entries.

## Exception Categories

### 1. Error Detection Infrastructure

**Category:** `error-detection`

**When allowed:**

- Suppressing errors from error detection wrapper itself
- Preventing recursive error detection loops
- Infrastructure code that must not fail loudly

**Example:**

```bash
# EXCEPTION: Error detection infrastructure
source "/path/to/error-detection.sh" >/dev/null 2>&1
```

**Whitelist entry:**

```
scripts/auto-error-detection.sh:45:error-detection:Suppresses wrapper errors in error detection system
```

---

### 2. Optional Feature Detection

**Category:** `optional-check`

**When allowed:**

- Checking if optional tools/features exist
- Suppressing "command not found" errors
- Testing for optional dependencies

**Example:**

```bash
# EXCEPTION: Optional feature detection
if command -v optional_tool >/dev/null 2>&1; then
    # Use optional tool
fi
```

**Whitelist entry:**

```
scripts/check-environment.sh:23:optional-check:Suppresses command-not-found for optional tools
```

---

### 3. Infrastructure Setup

**Category:** `infrastructure`

**When allowed:**

- Setup scripts that may have expected errors
- Installation scripts with expected failures
- Wrapper scripts that handle errors internally

**Example:**

```bash
# EXCEPTION: Infrastructure setup
chmod +x "$SCRIPT" 2>/dev/null || true
```

**Whitelist entry:**

```
scripts/setup-developer-env.sh:12:infrastructure:Suppresses chmod errors for optional scripts
```

---

### 4. Cleanup Scripts

**Category:** `cleanup`

**When allowed:**

- Cleanup scripts that may encounter missing files
- Permission errors during cleanup
- Expected "file not found" errors

**Example:**

```bash
# EXCEPTION: Cleanup script
rm -f /tmp/old_file 2>/dev/null
```

**Whitelist entry:**

```
scripts/cleanup_casa_logs.sh:8:cleanup:Suppresses permission errors during log cleanup
```

---

## Requesting a Whitelist Entry

### Process

1. **Identify the suppression pattern**
   - File path
   - Line number
   - Pattern type (`2>/dev/null`, `>/dev/null`, `&>/dev/null`)

2. **Categorize the exception**
   - Choose appropriate category
   - Write clear reason

3. **Add to whitelist**
   - Edit `.output-suppression-whitelist`
   - Add entry: `file:line:category:reason`

4. **Document if needed**
   - Add comment in code if helpful
   - Update this document if new category needed

### Whitelist Format

```
# Format: file_path:line_number:category:reason
# Categories: error-detection, optional-check, infrastructure, cleanup

scripts/auto-error-detection.sh:45:error-detection:Suppresses wrapper errors in error detection system
scripts/agent-setup.sh:12:infrastructure:Suppresses sourcing errors for optional setup
scripts/check-environment.sh:23:optional-check:Suppresses command-not-found for optional tools
```

### Example Request

**Before (blocked by pre-commit):**

```bash
# In scripts/my-script.sh:45
command 2>/dev/null
```

**After (whitelisted):**

```bash
# In scripts/my-script.sh:45
# EXCEPTION: Optional feature detection
command 2>/dev/null
```

**Whitelist entry:**

```
scripts/my-script.sh:45:optional-check:Suppresses command-not-found for optional feature
```

---

## What's NOT Allowed

### ❌ Test Output Suppression

**Not allowed:**

```bash
# In test scripts
pytest tests/ 2>/dev/null  # WRONG - Use pytest-safe.sh instead
```

**Correct approach:**

```bash
# Use safe wrapper
./scripts/pytest-safe.sh tests/ -v
```

---

### ❌ Log File Creation Suppression

**Not allowed:**

```bash
# Suppressing errors when creating log files
echo "log" > logfile.txt 2>/dev/null  # WRONG
```

**Correct approach:**

```bash
# Handle errors explicitly
if ! echo "log" > logfile.txt 2>&1; then
    echo "ERROR: Failed to create log file" >&2
    exit 1
fi
```

---

### ❌ Error Hiding in Production Code

**Not allowed:**

```bash
# Hiding errors in production code
process_data() 2>/dev/null  # WRONG - errors should be visible
```

**Correct approach:**

```bash
# Log errors properly
process_data 2>&1 | tee process.log
```

---

## Review Process

**For new whitelist entries:**

1. **Self-review:** Does it fit a category?
2. **Code review:** Is suppression truly necessary?
3. **Documentation:** Is reason clear?

**For questionable cases:**

1. **Ask:** Could this be handled differently?
2. **Consider:** Is suppression hiding a real problem?
3. **Document:** Why is suppression necessary?

---

## Maintenance

**Regular tasks:**

1. **Audit whitelist** - Review entries periodically
2. **Remove obsolete entries** - When code changes
3. **Update categories** - As new patterns emerge
4. **Document patterns** - Common legitimate uses

**Tools:**

- `scripts/audit-output-suppression.sh` - Audit all suppressions
- `scripts/pre-commit-output-suppression-strict.sh` - Strict validation
- `.output-suppression-whitelist` - Whitelist file

---

## Questions?

If unsure whether suppression is legitimate:

1. **Check categories** - Does it fit?
2. **Ask team** - Get second opinion
3. **Document well** - Clear reason in whitelist
4. **Review later** - Revisit if pattern changes

**Remember:** The goal is to prevent hiding errors, not to make code impossible
to write. Legitimate exceptions exist and should be documented.
