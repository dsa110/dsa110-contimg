# Auto Error Detection

## Quick Start

Enable automatic error detection for all commands:

```bash
# Option 1: Run setup script (recommended)
./scripts/setup-auto-error-detection.sh
source ~/.bashrc  # or ~/.zshrc

# Option 2: Manual setup
source scripts/auto-error-detection.sh
```

## What It Does

When enabled, **all commands are automatically wrapped** with error detection:

- ✅ Detects errors in real-time
- ✅ Kills commands immediately when errors are found
- ✅ Prevents ignoring errors
- ✅ Enforces error acknowledgment rules

## Example

**Before:**

```bash
$ pytest tests/ -v
... 1000 tests run ...
FAILED test_example.py::test_something
... continues running ...
```

**After (with auto-detection):**

```bash
$ pytest tests/ -v
... tests running ...
FAILED test_example.py::test_something
[ERROR-DETECTION] Error detected! Terminating immediately...
# Command stops immediately, saves time
```

## Commands Automatically Wrapped

- `pytest` - Test execution
- `python` / `python3` - Python scripts
- `make` - Build commands
- `npm` / `node` - Frontend commands (if in frontend directory)
- All shell scripts in `scripts/`

## Skip Detection (If Needed)

To skip error detection for a single command:

```bash
SKIP_ERROR_DETECTION=1 pytest tests/ -v
```

## Disable (Temporary)

```bash
unset AUTO_ERROR_DETECTION
```

## Documentation

- [Enable Auto Error Detection](docs/how-to/enable-auto-error-detection.md) -
  Full setup guide
- [Error Detection Wrapper](scripts/README-error-detection.md) - Wrapper
  documentation
- [Error Acknowledgment Rule](.cursor/rules/error-acknowledgment.mdc) - The rule
  being enforced
