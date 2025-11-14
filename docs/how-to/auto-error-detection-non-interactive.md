# Auto Error Detection in Non-Interactive Shells

## Solution Implemented

Auto error detection has been moved **before** the interactive shell check in
`~/.bashrc`, so it now works in both interactive and non-interactive shells.

### What Changed

The auto error detection block was moved from line ~261 (after the interactive
check) to line 6 (before the interactive check):

**Before:**

```bash
# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# ... other interactive-only stuff ...

# Auto Error Detection (line ~261)
if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source "/data/dsa110-contimg/scripts/auto-error-detection.sh"
fi
```

**After:**

```bash
# Auto Error Detection - Load BEFORE interactive check so it works in non-interactive shells too
# This ensures error detection works for automated scripts, CI/CD, and manual commands
if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source "/data/dsa110-contimg/scripts/auto-error-detection.sh"
fi

# If not running interactively, don't do anything else
case $- in
    *i*) ;;
      *) return;;
esac
```

## Verification

### Non-Interactive Shell (Now Works!)

```bash
$ bash -c 'source ~/.bashrc >/dev/null 2>&1; echo $AUTO_ERROR_DETECTION'
1
$ bash -c 'source ~/.bashrc >/dev/null 2>&1; type pytest'
pytest is a function
```

### Interactive Shell (Still Works)

```bash
$ echo $AUTO_ERROR_DETECTION
1
$ type pytest
pytest is a function
```

## Benefits

- ✅ **Works in automated scripts**: `bash -c 'command'` now has error detection
- ✅ **Works in CI/CD**: Non-interactive shells get error detection
- ✅ **Works in interactive terminals**: Normal terminal usage still works
- ✅ **No breaking changes**: All existing functionality preserved

## Testing

Test that error detection works in non-interactive shells:

```bash
# This should now detect test failures
bash -c 'cd /data/dsa110-contimg && source ~/.bashrc >/dev/null 2>&1 && pytest tests/ -v'
```

If tests fail, the error detection wrapper will catch them and exit with code 1.
