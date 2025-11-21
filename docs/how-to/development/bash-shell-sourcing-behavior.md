# Bash Shell Sourcing Behavior

## Key Fact: Non-Interactive Shells Source NOTHING by Default

**Non-interactive shells** (like `bash -c 'command'`) do **NOT** source:

- ❌ `~/.bashrc`
- ❌ `~/.bash_profile`
- ❌ `~/.profile`
- ❌ `/etc/bash.bashrc`
- ❌ `/etc/profile`

They **ONLY** source the file specified by `BASH_ENV` (if `BASH_ENV` is set).

## Shell Types and What They Source

### Interactive Login Shell

**Example:** `bash --login` or SSH session

Sources (in order):

1. `/etc/profile`
2. `~/.bash_profile` OR `~/.bash_login` OR `~/.profile` (first one found)
3. `~/.bashrc` (if sourced by one of the above)

### Interactive Non-Login Shell

**Example:** Terminal window, `bash` command

Sources:

1. `~/.bashrc`
2. `/etc/bash.bashrc` (if `~/.bashrc` doesn't exist)

### Non-Interactive Shell

**Example:** `bash -c 'command'`, scripts

Sources:

1. **ONLY** the file specified by `BASH_ENV` (if set)
2. **NOTHING** if `BASH_ENV` is not set

## Implications for Error Detection

### The Problem

For error detection to work in non-interactive shells (agentic sessions),
`BASH_ENV` must be:

1. **Set in the environment** before bash starts
2. **Exported** so child processes inherit it

### Why ~/.profile Helps (But Isn't Perfect)

Setting `BASH_ENV` in `~/.profile`:

- ✅ Works for **login shells** (SSH, `bash --login`)
- ✅ Exports to child processes
- ❌ **Doesn't work** if the session isn't a login shell

### Why ~/.bashrc Helps (But Isn't Perfect)

Setting `BASH_ENV` in `~/.bashrc`:

- ✅ Works for **interactive shells**
- ✅ Exports to child processes
- ❌ **Doesn't work** for non-interactive shells (they don't source `~/.bashrc`)

### The Solution: Agent Setup Script

The **most reliable** approach is to have agents explicitly source the setup
script:

```bash
source /data/dsa110-contimg/scripts/developer-setup.sh
```

This:

1. Sets `BASH_ENV` in the current environment
2. Exports it to child processes
3. Enables error detection immediately
4. Works regardless of shell type

## Testing

### Test 1: Non-Interactive Without BASH_ENV

```bash
$ bash -c 'echo $AUTO_ERROR_DETECTION'
not set
# Nothing was sourced
```

### Test 2: Non-Interactive With BASH_ENV

```bash
$ export BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
$ bash -c 'echo $AUTO_ERROR_DETECTION'
1
# BASH_ENV file was sourced
```

### Test 3: After Agent Setup

```bash
$ source /data/dsa110-contimg/scripts/developer-setup.sh
✅ Error detection enabled for agentic session
$ bash -c 'echo $AUTO_ERROR_DETECTION'
1
# BASH_ENV is set, so child shells get error detection
```

## Conclusion

**Non-interactive shells source nothing by default** - they only source
`BASH_ENV` if it's set.

To make error detection deterministic:

1. **Best:** Agents source `developer-setup.sh` at session start
2. **Fallback:** `BASH_ENV` set in `~/.profile` (for login shells)
3. **Fallback:** `BASH_ENV` set in `~/.bashrc` (for interactive shells)

But the **only** way to guarantee it works in **all** non-interactive shells is
to ensure `BASH_ENV` is set in the environment before bash starts.
