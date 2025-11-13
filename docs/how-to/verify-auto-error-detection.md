# Verify Auto Error Detection Setup

## Quick Check

After running the setup script, verify it's working:

```bash
# Check if configuration is in ~/.bashrc
grep -A 5 "Auto Error Detection" ~/.bashrc

# Reload shell configuration
source ~/.bashrc

# Verify it's enabled
echo $AUTO_ERROR_DETECTION
# Should output: 1

# Check wrapper path
echo $ERROR_DETECTION_WRAPPER
# Should output: /data/dsa110-contimg/scripts/run-with-error-detection.py
```

## Test It

Try running a command that will trigger error detection:

```bash
# This should be automatically wrapped
python3 -c 'raise ValueError("test error")'

# You should see:
# [ERROR-DETECTION] Error pattern 'ValueError' detected in real-time!
# [ERROR-DETECTION] Terminating command immediately...
```

## What's in ~/.bashrc

The setup script adds this to your `~/.bashrc`:

```bash
# Auto Error Detection (added by setup-auto-error-detection.sh)
# Automatically wraps commands with error detection
if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source "/data/dsa110-contimg/scripts/auto-error-detection.sh"
fi
```

## Troubleshooting

### Not Enabled After Reload

If `AUTO_ERROR_DETECTION` is not set after reloading:

1. Check if script exists:
   ```bash
   ls -l /data/dsa110-contimg/scripts/auto-error-detection.sh
   ```

2. Check if wrapper exists:
   ```bash
   ls -l /data/dsa110-contimg/scripts/run-with-error-detection.py
   ```

3. Manually source to see errors:
   ```bash
   source /data/dsa110-contimg/scripts/auto-error-detection.sh
   ```

### Commands Not Being Wrapped

If commands aren't being wrapped:

1. Check if functions are defined:
   ```bash
   type pytest
   type python
   ```

2. Check if AUTO_WRAP_COMMANDS is set:
   ```bash
   echo ${AUTO_WRAP_COMMANDS:-not set}
   ```

3. Re-enable:
   ```bash
   source /data/dsa110-contimg/scripts/auto-error-detection.sh
   ```

## Disable

### Temporarily
```bash
unset AUTO_ERROR_DETECTION
```

### Permanently
Remove these lines from `~/.bashrc`:
```bash
# Auto Error Detection (added by setup-auto-error-detection.sh)
# Automatically wraps commands with error detection
if [ -f "/data/dsa110-contimg/scripts/auto-error-detection.sh" ]; then
    source "/data/dsa110-contimg/scripts/auto-error-detection.sh"
fi
```

