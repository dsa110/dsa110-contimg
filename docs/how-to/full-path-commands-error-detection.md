# Full Path Commands and Error Detection

## Question

**Will error detection run if the command is run from `/opt/miniforge/envs/casa6/bin/python`?**

## Answer

**Yes, error detection WILL run** when using full paths like `/opt/miniforge/envs/casa6/bin/python`.

## How It Works

The auto-error-detection system uses a **DEBUG trap** to intercept commands before they execute. When it detects a full path to a Python executable (e.g., `/opt/miniforge/envs/casa6/bin/python`), it wraps the command with error detection.

## Current Behavior

When you run:
```bash
/opt/miniforge/envs/casa6/bin/python -c "print('test')"
```

The DEBUG trap:
1. Detects the full path to Python executable
2. Wraps it with error detection
3. Executes the command through the wrapper

**Note:** There may be duplicate output because bash still executes the original command after the trap. This is a known limitation of DEBUG traps.

## Supported Full Paths

The system detects and wraps:
- `/opt/miniforge/envs/casa6/bin/python`
- `/opt/miniforge/envs/casa6/bin/python3`
- `/usr/bin/python`
- `/usr/bin/python3`
- Any path containing `/python` or `/python3`
- Any path containing `/pytest`

## Examples

### Success Case
```bash
$ /opt/miniforge/envs/casa6/bin/python -c "print('test')"
[INFO] Running command: /opt/miniforge/envs/casa6/bin/python -c "print('test')"
[INFO] Log file: /tmp/error-detection-*.log
test
[SUCCESS] Command completed successfully
```

### Error Detection
```bash
$ /opt/miniforge/envs/casa6/bin/python -c "raise Exception('error')"
[INFO] Running command: /opt/miniforge/envs/casa6/bin/python -c "raise Exception('error')"
[INFO] Log file: /tmp/error-detection-*.log
Traceback (most recent call last):
  File "<string>", line 1, in module
Exception: error
[ERROR] Error patterns detected in command output
[ERROR] ERROR DETECTION: Command execution failed
```

## Alternative: Use Command Name

For cleaner output, you can use the command name instead of the full path:

```bash
# Instead of:
/opt/miniforge/envs/casa6/bin/python script.py

# Use:
python script.py  # If python points to casa6/bin/python
```

The function wrapper approach (for `python`, `python3`, `pytest`) avoids the duplicate output issue.

## Technical Details

The DEBUG trap:
- Runs before each command execution
- Checks if the command matches Python executable patterns
- Wraps matching commands with error detection
- Uses `extdebug` mode to enable trap functionality

## Limitations

1. **Duplicate Output**: DEBUG traps can't prevent bash from executing the original command, so output may appear twice.

2. **Performance**: DEBUG traps run for every command, which can have a small performance impact.

3. **Complex Commands**: Very complex command lines may not be fully parsed by the trap handler.

## Recommendation

**For best results, use command names instead of full paths:**
- `python` instead of `/opt/miniforge/envs/casa6/bin/python`
- `pytest` instead of `/opt/miniforge/envs/casa6/bin/pytest`

This avoids the duplicate output issue and is cleaner.

