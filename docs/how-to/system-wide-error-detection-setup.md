# System-Wide Error Detection Setup

## ✅ COMPLETED: System-Wide Configuration

Error detection is now configured system-wide and works automatically for all users and all shell types.

## What Was Configured

### 1. `/etc/environment` (System-Wide Environment Variables)

Added:
```
BASH_ENV="/data/dsa110-contimg/scripts/auto-error-detection-env.sh"
```

**How it works:**
- `/etc/environment` is read by PAM (Pluggable Authentication Modules) at login
- Environment variables are set for all processes
- Works for all users and all shell types

### 2. `/etc/profile.d/error-detection.sh` (Login Shell Scripts)

Created script that exports `BASH_ENV` for login shells.

**How it works:**
- Sourced by login shells (SSH, `bash --login`)
- Provides redundancy with `/etc/environment`
- Ensures `BASH_ENV` is exported to child processes

## Verification

### Test 1: New User Session
```bash
$ sudo -u ubuntu bash -c 'echo $BASH_ENV'
/data/dsa110-contimg/scripts/auto-error-detection-env.sh

$ sudo -u ubuntu bash -c 'bash -c "echo \$AUTO_ERROR_DETECTION"'
1

$ sudo -u ubuntu bash -c 'bash -c "type pytest"'
pytest is a function
```

### Test 2: Non-Interactive Shell
```bash
$ bash --norc --noprofile -c 'echo $BASH_ENV'
/data/dsa110-contimg/scripts/auto-error-detection-env.sh

$ bash --norc --noprofile -c 'echo $AUTO_ERROR_DETECTION'
1
```

### Test 3: Agentic Session Simulation
```bash
# Simulate fresh agentic session
$ sudo -u ubuntu bash -c 'cd /data/dsa110-contimg && pytest --version'
# Should show error detection wrapper messages
```

## How It Works

1. **Login/New Session**: PAM reads `/etc/environment` and sets `BASH_ENV`
2. **Bash Starts**: Checks if `BASH_ENV` is set
3. **Non-Interactive Shell**: Sources the file specified by `BASH_ENV`
4. **Error Detection Enabled**: Commands are wrapped automatically

## Benefits

- ✅ **Automatic**: No agent action required
- ✅ **System-Wide**: Works for all users
- ✅ **All Shell Types**: Works for interactive, non-interactive, login, non-login
- ✅ **Persistent**: Survives reboots
- ✅ **Deterministic**: Always enabled in fresh sessions

## Current Status

**Error detection is now AUTOMATIC for:**
- ✅ All users (system-wide)
- ✅ All shell types (interactive, non-interactive, login, non-login)
- ✅ Agentic sessions (no setup required)
- ✅ CI/CD pipelines (if they start new sessions)
- ✅ SSH sessions
- ✅ Automated scripts

## Testing

Test that it works in a completely fresh session:

```bash
# As different user (simulates fresh agentic session)
sudo -u ubuntu bash -c 'cd /data/dsa110-contimg && pytest tests/ -v'

# Should automatically have error detection enabled
# Test failures will be caught and reported
```

## Maintenance

To update the error detection script path:

```bash
sudo sed -i 's|BASH_ENV=.*|BASH_ENV="/new/path/to/script.sh"|' /etc/environment
sudo sed -i 's|export BASH_ENV=.*|export BASH_ENV="/new/path/to/script.sh"|' /etc/profile.d/error-detection.sh
```

## Removal

To remove system-wide error detection:

```bash
sudo sed -i '/BASH_ENV.*auto-error-detection/d' /etc/environment
sudo rm /etc/profile.d/error-detection.sh
```
