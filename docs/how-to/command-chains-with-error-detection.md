# Command Chains with Error Detection

## Current Behavior

When you run command chains with `&&`:

```bash
command1 && command2 && command3
```

**Only explicitly wrapped commands are wrapped:**

- ✅ `python`, `python3` - Wrapped
- ✅ `pytest` - Wrapped
- ✅ `make` - Wrapped
- ✅ `npm`, `node` - Wrapped (if in frontend directory)
- ❌ `./script.sh` - **NOT wrapped**
- ❌ `cd`, `echo`, etc. - **NOT wrapped** (by design - these are builtins)

## Example

```bash
# Only python3 is wrapped, echo is not
echo "Starting" && python3 script.py && echo "Done"

# Only pytest is wrapped
cd /path && pytest tests/ && make build
```

## Why This Limitation?

Bash evaluates each command in a chain separately. The auto-error-detection
system works by:

1. **Function wrappers** - Overrides specific commands (`python`, `pytest`,
   etc.)
2. **command_not_found_handle** - Only catches commands that don't exist (not
   useful for existing scripts)

To wrap **all** commands in chains would require:

- Overriding the `command` builtin (very invasive)
- Using DEBUG trap (can cause performance issues)
- Parsing command lines (complex and error-prone)

## Solutions

### Option 1: Explicitly Wrap Scripts

Add wrapper functions for scripts you use frequently:

```bash
# In auto-error-detection.sh, add:
my_script() {
    _run_with_error_detection ./scripts/my_script.sh "$@"
}
```

### Option 2: Use Wrapper for Entire Chain

Wrap the entire command chain:

```bash
# Instead of:
cd /path && ./script.sh && python test.py

# Do:
run-with-error-detection.py bash -c 'cd /path && ./script.sh && python test.py'
```

### Option 3: Wrap Individual Commands

Wrap each command separately:

```bash
# Instead of:
./script.sh && python test.py

# Do:
run-with-error-detection.py ./script.sh && python test.py
```

### Option 4: Use Universal Wrapper (Experimental)

Use the universal wrapper that attempts to catch more commands:

```bash
source scripts/auto-error-detection-universal.sh
```

**Warning:** This is more aggressive and may have side effects.

## Best Practice

For command chains, wrap the **entire chain** if you want error detection on all
parts:

```bash
# Wrap entire chain
run-with-error-detection.py bash -c 'cd /path && ./script.sh && python test.py && make build'
```

This ensures:

- ✅ All commands are monitored
- ✅ Error detection works for all parts
- ✅ Chain stops immediately on error
- ✅ Consistent behavior

## Current Status

**What's wrapped automatically:**

- `python`, `python3`
- `pytest`
- `make`
- `npm`, `node` (if in frontend directory)

**What's NOT wrapped automatically:**

- Scripts (`./script.sh`, `scripts/`)
- Built-in commands (`cd`, `echo`, etc.)
- Other executables not in the wrapper list

**Recommendation:** For command chains with scripts, wrap the entire chain:

```bash
run-with-error-detection.py bash -c 'your && command && chain'
```
