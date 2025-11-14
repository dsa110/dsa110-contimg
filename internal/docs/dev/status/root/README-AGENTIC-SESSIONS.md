# Agentic Session Setup - Error Detection

## Quick Start

**At the start of ANY agentic session, run:**

```bash
source /data/dsa110-contimg/scripts/developer-setup.sh
```

This ensures error detection is **always** enabled, regardless of shell type or
environment.

## Why This Is Needed

Agentic sessions may start as:

- Non-interactive shells (don't source `~/.bashrc`)
- Non-login shells (don't source `~/.profile`)
- Clean environments (no environment variables set)

The agent setup script ensures error detection works in **all** these scenarios.

## What It Does

1. Sets `BASH_ENV` environment variable
2. Enables auto error detection
3. Wraps commands (`pytest`, `python`, `make`, etc.) with error detection
4. Verifies the setup

## Verification

After sourcing:

```bash
$ source /data/dsa110-contimg/scripts/developer-setup.sh
✅ Error detection enabled for agentic session
   BASH_ENV=/data/dsa110-contimg/scripts/auto-error-detection-env.sh
   AUTO_ERROR_DETECTION=1

$ echo $AUTO_ERROR_DETECTION
1

$ type pytest
pytest is a function
```

## Usage

```bash
# Start of agentic session
source /data/dsa110-contimg/scripts/developer-setup.sh

# Now all commands are automatically wrapped
pytest tests/ -v              # → Wrapped with error detection
python script.py               # → Wrapped with error detection
make test-unit                 # → Wrapped with error detection
```

## Alternative: Manual Setup

If you can't source the script, set `BASH_ENV` explicitly:

```bash
export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
```

Then all `bash -c` commands will have error detection enabled.

## Documentation

- [Agentic Session Setup Guide](docs/how-to/agentic-session-setup.md)
- [Deterministic Error Detection](docs/how-to/deterministic-error-detection.md)
- [Enable Auto Error Detection](docs/how-to/enable-auto-error-detection.md)
