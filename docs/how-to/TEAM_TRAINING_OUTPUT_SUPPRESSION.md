# Team Training: Output Suppression Prevention

**Purpose:** Ensure all developers understand the output suppression prevention
system and how to work with it.

---

## Quick Reference Card

### ✅ DO

```bash
# Write code without suppression
echo "log" > logfile.txt

# Handle errors explicitly
if ! echo "log" > logfile.txt 2>&1; then
    echo "ERROR: Failed to create log file" >&2
    exit 1
fi

# Use safe wrapper for pytest
./scripts/pytest-safe.sh tests/ -v
```

### ❌ DON'T

```bash
# Don't suppress output
command 2>/dev/null  # Will be blocked by pre-commit

# Don't hide errors
process_data() 2>/dev/null  # Will be blocked

# Don't suppress test output
pytest tests/ 2>/dev/null  # Use pytest-safe.sh instead
```

---

## How the System Works

### 1. Pre-Commit Hook

**What it does:**

- Scans all staged shell scripts (`.sh` files)
- Detects output suppression patterns: `2>/dev/null`, `>/dev/null`,
  `&>/dev/null`
- Checks if suppression is in whitelist
- Blocks commit if not whitelisted

**When it runs:**

- Automatically on every `git commit`
- Before commit is finalized

**What happens if blocked:**

```
ERROR: Found output suppression pattern in script.sh:45:
  Pattern: 2>/dev/null
  Line: command 2>/dev/null

This project requires full output for error detection.

To allow this exception, add to .output-suppression-whitelist:
  script.sh:45:category:reason
```

---

## Working with the Whitelist

### When You Need Suppression

**Step 1: Identify the need**

- Is this truly necessary?
- Could errors be handled explicitly instead?
- Is this hiding a real problem?

**Step 2: Categorize** Choose the appropriate category:

- `error-detection` - Error detection infrastructure
- `infrastructure` - Setup/installation scripts
- `optional-check` - Optional feature detection
- `cleanup` - Cleanup scripts

**Step 3: Add to whitelist** Edit `.output-suppression-whitelist`:

```
scripts/my-script.sh:45:infrastructure:Suppresses chmod errors for optional setup
```

**Step 4: Commit** The pre-commit hook will validate your entry.

---

## Common Scenarios

### Scenario 1: Optional Feature Check

**Before (blocked):**

```bash
if command -v optional_tool >/dev/null 2>&1; then
    # Use tool
fi
```

**After (whitelisted):**

```bash
# In .output-suppression-whitelist:
scripts/my-script.sh:23:optional-check:Suppresses command-not-found for optional tool

# In code:
if command -v optional_tool >/dev/null 2>&1; then
    # Use tool
fi
```

---

### Scenario 2: Cleanup Script

**Before (blocked):**

```bash
rm -f /tmp/old_file 2>/dev/null
```

**After (whitelisted):**

```bash
# In .output-suppression-whitelist:
scripts/cleanup.sh:45:cleanup:Suppresses rm errors during cleanup - expected for missing files

# In code:
rm -f /tmp/old_file 2>/dev/null
```

---

### Scenario 3: Error Detection Infrastructure

**Before (blocked):**

```bash
source "/path/to/error-detection.sh" >/dev/null 2>&1
```

**After (whitelisted):**

```bash
# In .output-suppression-whitelist:
scripts/setup.sh:12:error-detection:Suppresses sourcing errors for optional error detection setup

# In code:
source "/path/to/error-detection.sh" >/dev/null 2>&1
```

---

## Best Practices

### 1. Prefer Explicit Error Handling

**Instead of:**

```bash
command 2>/dev/null
```

**Use:**

```bash
if ! command 2>&1; then
    echo "ERROR: Command failed" >&2
    exit 1
fi
```

---

### 2. Use Appropriate Categories

**Error Detection:**

- Only for error detection system itself
- Prevents recursive error loops

**Infrastructure:**

- Setup/installation scripts
- Optional operations that may fail

**Optional Check:**

- Checking for optional tools/features
- Command-not-found scenarios

**Cleanup:**

- Cleanup scripts
- Expected "file not found" errors

---

### 3. Document Clearly

**Good whitelist entry:**

```
scripts/my-script.sh:45:infrastructure:Suppresses chmod errors for optional Git hooks setup
```

**Bad whitelist entry:**

```
scripts/my-script.sh:45:infrastructure:Suppresses errors
```

---

## Troubleshooting

### Pre-Commit Hook Blocks My Commit

**Problem:** Pre-commit hook blocks commit with suppression pattern

**Solution:**

1. Check if suppression is truly necessary
2. If yes, add to whitelist with clear reason
3. If no, remove suppression and handle errors explicitly

---

### Whitelist Entry Not Working

**Problem:** Added to whitelist but still blocked

**Check:**

1. Format is correct: `file:line:category:reason`
2. File path is relative to repo root
3. Line number matches actual line
4. No extra spaces or typos

**Example:**

```
# Correct
scripts/my-script.sh:45:infrastructure:Reason

# Wrong (extra space)
scripts/my-script.sh: 45:infrastructure:Reason

# Wrong (absolute path)
/data/dsa110-contimg/scripts/my-script.sh:45:infrastructure:Reason
```

---

### Need to Bypass (Emergency Only)

**If you really need to bypass (not recommended):**

```bash
git commit --no-verify -m "Emergency commit"
```

**Warning:** This bypasses ALL protections. Use only in emergencies and fix
properly afterward.

---

## Tools Available

### Audit Tool

**Run audit:**

```bash
./scripts/audit-output-suppression.sh
```

**What it does:**

- Finds all suppression patterns
- Categorizes them automatically
- Shows which need review

---

### Fix Tool

**Find problematic suppressions:**

```bash
./scripts/fix-non-legitimate-suppressions.sh
```

**What it does:**

- Identifies non-legitimate suppressions
- Suggests fixes
- Helps prioritize cleanup

---

## Regular Maintenance

### Weekly Audit

**Run:**

```bash
./scripts/audit-output-suppression.sh > audit-$(date +%Y%m%d).txt
```

**Review:**

- Check for new suppressions
- Verify whitelist entries are still valid
- Remove obsolete entries

---

### When Code Changes

**If you modify a file with whitelisted suppression:**

1. Check if suppression is still needed
2. Update line number if code moved
3. Remove entry if suppression removed

---

### Whitelist Review

**Monthly:**

- Review all whitelist entries
- Remove obsolete entries
- Update categories if needed
- Document new patterns

---

## Questions?

**Common questions:**

**Q: Can I suppress output in Python scripts?** A: The pre-commit hook only
checks shell scripts (`.sh`). Python has its own error handling.

**Q: What about comments with suppression patterns?** A: Comments are ignored.
Only actual code is checked.

**Q: Can I suppress output in test scripts?** A: Use `./scripts/pytest-safe.sh`
for pytest. For other test tools, add to whitelist if legitimate.

**Q: What if I'm not sure if suppression is legitimate?** A: Ask the team or add
a comment explaining why. Better to be explicit.

---

## Resources

- **Whitelist:** `.output-suppression-whitelist`
- **Pre-commit hook:** `.git/hooks/pre-commit`
- **Audit tool:** `scripts/audit-output-suppression.sh`
- **Fix tool:** `scripts/fix-non-legitimate-suppressions.sh`
- **Documentation:** `docs/dev/OUTPUT_SUPPRESSION_EXCEPTIONS.md`

---

**Remember:** The goal is to prevent hiding errors, not to make code impossible
to write. Legitimate exceptions exist and should be documented in the whitelist.
