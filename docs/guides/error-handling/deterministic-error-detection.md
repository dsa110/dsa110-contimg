# Deterministic Error Detection for Agentic Sessions

## Problem

In agentic/automated sessions (like AI agent terminal commands), shells are
often non-interactive and non-login, which means:

- `~/.bashrc` is **not** sourced by default
- `BASH_ENV` may not be set
- Error detection may not be enabled
- Commands run without error detection wrapper

## Solution: BASH_ENV in ~/.profile

We set `BASH_ENV` in `~/.profile`, which is sourced for **login shells**. This
ensures error detection is **always** enabled, even in fresh agentic sessions.

### How It Works

1. **BASH_ENV Script**:
   `/data/dsa110-contimg/scripts/auto-error-detection-env.sh`
   - Automatically sourced by bash for non-interactive shells when `BASH_ENV` is
     set
   - Sources the auto-error-detection script silently

2. **~/.profile Configuration**: Sets `BASH_ENV` environment variable
   - Sourced for login shells (including many agentic sessions)
   - Ensures `BASH_ENV` is exported to all child processes
   - Works even when `~/.bashrc` is not sourced

3. **~/.bashrc Configuration**: Also sets `BASH_ENV` (for interactive shells)
   - Ensures it's set even if `~/.profile` wasn't sourced
   - Provides redundancy

### Setup

Run the setup script:

```bash
./scripts/setup-auto-error-detection.sh
```

This will:

1. Create `scripts/auto-error-detection-env.sh` (BASH_ENV script)
2. Add auto-error-detection to `~/.bashrc` (for interactive shells)
3. **Set `BASH_ENV` in `~/.profile`** (for login shells/agentic sessions)
4. Set `BASH_ENV` in `~/.bashrc` (redundancy)

### Why ~/.profile?

- **Login shells** source `~/.profile` (or `~/.bash_profile` if it exists)
- **Agentic sessions** often start as login shells
- **CI/CD pipelines** may use login shells
- **System services** may use login shells

Setting `BASH_ENV` in `~/.profile` ensures it's available for all these
scenarios.

### Verification

#### Fresh Agentic Session (Login Shell)

```bash
# Simulate fresh agentic session
$ bash -l -c 'echo $BASH_ENV'
/data/dsa110-contimg/scripts/auto-error-detection-env.sh

$ bash -l -c 'bash -c "echo \$AUTO_ERROR_DETECTION"'
1

$ bash -l -c 'bash -c "type pytest"'
pytest is a function
```

#### Non-Interactive Shell (with BASH_ENV set)

```bash
# If BASH_ENV is set in environment
$ bash -c 'echo $AUTO_ERROR_DETECTION'
1
$ bash -c 'type pytest'
pytest is a function
```

#### Interactive Shell

```bash
$ echo $AUTO_ERROR_DETECTION
1
$ type pytest
pytest is a function
```

### How BASH_ENV Works

When bash starts a non-interactive shell (`bash -c 'command'`), it:

1. Checks if `BASH_ENV` environment variable is set
2. Sources the file specified by `BASH_ENV`
3. This happens **before** executing the command

By setting `BASH_ENV` in `~/.profile`, it's:

- Exported to all child processes
- Available even in non-interactive shells
- Persistent across sessions (if `~/.profile` is sourced)

### Testing

Test that it works in agentic sessions:

```bash
# Simulate fresh agentic session (login shell)
bash -l -c 'cd /data/dsa110-contimg && pytest tests/ -v'

# Should show error detection wrapper messages if tests fail
```

### Manual Setup

If you need to set it manually:

```bash
# Add to ~/.profile
export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"

# Also add to ~/.bashrc for redundancy
export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
```

### Limitations

**Note**: If an agentic session starts as a **non-login, non-interactive shell**
AND `BASH_ENV` is not set in the environment, error detection won't be enabled.
However:

- Most agentic sessions use login shells (`bash -l`)
- CI/CD systems often set environment variables
- The setup script provides redundancy by setting it in both `~/.profile` and
  `~/.bashrc`

### Benefits

- ✅ **Deterministic**: Works in fresh agentic sessions (login shells)
- ✅ **No manual steps**: Works automatically after setup
- ✅ **Agentic-friendly**: Works in AI agent terminal sessions
- ✅ **CI/CD compatible**: Works in automated pipelines
- ✅ **Backward compatible**: Doesn't break existing interactive shells
- ✅ **Redundant**: Set in both `~/.profile` and `~/.bashrc`
