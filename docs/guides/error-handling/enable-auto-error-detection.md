# Enable Auto Error Detection

## Overview

Auto error detection automatically wraps all commands with error detection,
ensuring errors are never ignored. This enforces the
Error Acknowledgment Rule at the
shell level.

## Quick Setup

### Option 1: Automatic Setup (Recommended)

```bash
# Run the setup script
./scripts/setup-auto-error-detection.sh

# Reload your shell
source ~/.bashrc  # or ~/.zshrc
```

### Option 2: Manual Setup

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Auto Error Detection
if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source /data/dsa110-contimg/scripts/auto-error-detection.sh
fi
```

Then reload:

```bash
source ~/.bashrc  # or ~/.zshrc
```

## How It Works

### Automatic Wrapping

When enabled, common commands are automatically wrapped:

```bash
# These commands are automatically wrapped:
pytest tests/ -v              # → run-with-error-detection.py pytest tests/ -v
python script.py               # → run-with-error-detection.py python script.py
make test-unit                 # → run-with-error-detection.py make test-unit
npm test                       # → run-with-error-detection.py npm test
```

### Commands That Skip Wrapping

These commands are **not** wrapped (they're shell built-ins):

- `cd`, `source`, `.`, `export`, `unset`
- `alias`, `unalias`, `set`, `shopt`
- `type`, `command`, `which`
- `help`, `man`, `info`
- `history`, `jobs`, `fg`, `bg`
- `exit`, `logout`, `clear`, `reset`
- `echo`, `printf`, `test`, `[`, `true`, `false`

## Usage

### Normal Usage

Just run commands normally - they're automatically wrapped:

```bash
# Automatically wrapped with error detection
pytest tests/ -v
python script.py
make build
```

### Skip Error Detection (Temporary)

To skip error detection for a single command:

```bash
SKIP_ERROR_DETECTION=1 pytest tests/ -v
```

### Disable Auto Detection (Temporary)

To disable auto-detection for the current session:

```bash
unset AUTO_ERROR_DETECTION
```

### Disable Auto Detection (Permanent)

Remove the auto-error-detection section from your `~/.bashrc` or `~/.zshrc`:

```bash
# Remove these lines:
# Auto Error Detection
if [ -f ".../scripts/auto-error-detection.sh" ]; then
    source ".../scripts/auto-error-detection.sh"
fi
```

## Configuration

### Environment Variables

- `AUTO_ERROR_DETECTION`: Set to `1` when enabled (auto-set by script)
- `SKIP_ERROR_DETECTION`: Set to `1` to skip for next command
- `ERROR_DETECTION_WRAPPER`: Path to wrapper script (default:
  `scripts/run-with-error-detection.py`)
- `AUTO_WRAP_COMMANDS`: Set to `1` to wrap common commands (default: `1`)

### Custom Wrapper

To use a different wrapper:

```bash
export ERROR_DETECTION_WRAPPER="scripts/run-with-error-detection.sh"
source scripts/auto-error-detection.sh
```

## Examples

### Before (Without Auto Detection)

```bash
$ pytest tests/ -v
... output ...
FAILED tests/test_example.py::test_something
... more output ...
$ echo $?
1
# Error was detected but not acted upon
```

### After (With Auto Detection)

```bash
$ pytest tests/ -v
... output ...
FAILED tests/test_example.py::test_something
[ERROR-DETECTION] Error pattern 'FAILED' detected in real-time!
[ERROR-DETECTION] Terminating command immediately...
[ERROR-DETECTION] ERROR DETECTION: Command execution failed
$ echo $?
1
# Error was detected and command was killed immediately
```

## Benefits

1. **Automatic enforcement**: No need to remember to wrap commands
2. **Consistent behavior**: All commands follow the same error detection rules
3. **Immediate feedback**: Errors are detected and acted upon immediately
4. **Time savings**: Long-running commands stop immediately on error

## Troubleshooting

### Wrapper Not Found

If you see "Error detection wrapper not found":

```bash
# Check if wrapper exists
ls -l scripts/run-with-error-detection.py

# If missing, create it or set custom path
export ERROR_DETECTION_WRAPPER="/path/to/wrapper"
```

### Commands Not Being Wrapped

If commands aren't being wrapped:

```bash
# Check if auto-detection is enabled
echo $AUTO_ERROR_DETECTION

# Re-enable
source scripts/auto-error-detection.sh
```

### Performance Impact

The wrapper adds minimal overhead:

- Real-time monitoring: ~0.1ms per line
- Error detection: ~1ms per line
- Total overhead: <5% for most commands

For very high-frequency commands, you can skip detection:

```bash
SKIP_ERROR_DETECTION=1 high_frequency_command
```

## Related Documentation

- Error Detection Wrapper - Wrapper
  documentation
- [Immediate Error Termination](./immediate-error-termination.md) - How
  immediate kill works
- Error Acknowledgment Rule - The
  rule being enforced
