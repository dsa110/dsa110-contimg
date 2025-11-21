# Agentic Session Setup for Error Detection

## Problem

In fresh agentic sessions, error detection may not be enabled because:

- `~/.bashrc` is not sourced for non-interactive shells
- `BASH_ENV` may not be set in the environment
- Login shells may not source `~/.profile` in all cases

## Solution: Agent Setup Script

Source the agent setup script at the start of any agentic session to ensure
error detection is **always** enabled.

### Quick Setup

At the start of any agentic session, run:

```bash
source /data/dsa110-contimg/scripts/developer-setup.sh
```

This will:

1. Set `BASH_ENV` if not already set
2. Enable auto error detection
3. Verify the setup

### What the Script Does

The `developer-setup.sh` script:

- Sets `BASH_ENV` to point to the error detection environment script
- Sources the auto-error-detection script to enable wrapping
- Provides verification output

### Usage in Agentic Sessions

**For AI agents or automated scripts:**

```bash
# At the start of the session
source /data/dsa110-contimg/scripts/developer-setup.sh

# Now all commands are wrapped with error detection
pytest tests/ -v
python script.py
make build
```

### Alternative: Set BASH_ENV Explicitly

If you can't source the script, set `BASH_ENV` explicitly:

```bash
export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
```

Then all subsequent `bash -c` commands will have error detection enabled.

### Verification

After sourcing the setup script:

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

### Why This Is Needed

Even though we set `BASH_ENV` in `~/.profile` and `~/.bashrc`:

- Non-interactive shells don't source `~/.bashrc`
- Login shells may not always source `~/.profile` in all environments
- Agentic sessions may start with a clean environment

The agent setup script ensures error detection is enabled **regardless** of
shell type or profile sourcing.

### Best Practice

**For maximum determinism**, always source the agent setup script at the start
of agentic sessions:

```bash
# Always do this first
source /data/dsa110-contimg/scripts/developer-setup.sh

# Then run your commands
pytest tests/ -v
```

This guarantees error detection is enabled, regardless of:

- Shell type (interactive/non-interactive)
- Login status
- Profile file sourcing
- Environment variables
