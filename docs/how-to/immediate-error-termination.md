# Immediate Error Termination

## Overview

The error detection wrappers support **immediate termination** of commands when
errors are detected. This prevents wasted time and resources by killing
processes as soon as an error pattern is found.

## How It Works

### Python Version (`run-with-error-detection.py`)

Uses **pexpect** for real-time monitoring and aggressive process termination:

1. **Real-time monitoring**: Reads output character-by-character as it's
   produced
2. **Immediate detection**: Checks each line for error patterns as soon as it's
   complete
3. **Multi-method termination**: Uses multiple kill methods to ensure process
   dies:
   - `child.terminate(force=True)` - Graceful termination
   - `child.kill(signal.SIGKILL)` - Force kill
   - `os.killpg(pgid, SIGKILL)` - Kill process group
   - `os.kill(pid, SIGKILL)` - Direct PID kill

**Example:**

```python
# Error detected in line
error_result = detect_error_in_line(line)
if error_result:
    # Kill immediately using multiple methods
    child.terminate(force=True)
    if child.isalive():
        child.kill(signal.SIGKILL)
    if child.isalive():
        os.killpg(os.getpgid(child.pid), signal.SIGKILL)
    break  # Exit monitoring loop immediately
```

### Bash Version (`run-with-error-detection.sh`)

Uses **trap** and **signal handling** for immediate termination:

1. **Background execution**: Runs command in background
2. **Line-by-line monitoring**: Reads output as it's produced
3. **Signal-based kill**: Uses `kill -TERM` then `kill -KILL` for immediate
   termination

**Example:**

```bash
# Error detected
if check_line_for_errors "$line"; then
    kill_command  # Sends TERM, then KILL if needed
    break
fi
```

## Usage

### Python Version (Recommended)

```bash
# Basic usage - kills immediately on error
./scripts/run-with-error-detection.py pytest tests/ -v

# Long-running command - saves time by killing early
./scripts/run-with-error-detection.py python long_script.py
```

### Bash Version

```bash
# Alternative bash implementation
./scripts/run-with-error-detection-immediate-kill.sh pytest tests/ -v
```

## Termination Methods

The Python version uses a **cascading kill strategy**:

1. **Graceful** (`SIGTERM`): Allows process to clean up
2. **Force** (`SIGKILL`): Immediate termination
3. **Process Group** (`killpg`): Kills entire process tree
4. **Direct PID**: Last resort direct kill

This ensures the process dies even if:

- It ignores SIGTERM
- It spawns child processes
- It's in a process group
- Normal termination fails

## Benefits

1. **Time savings**: Don't wait for long-running commands to finish after error
2. **Resource savings**: Stop CPU/memory usage immediately
3. **Faster feedback**: Get error notification as soon as it occurs
4. **Prevents cascading errors**: Stop before more errors accumulate

## Example Scenarios

### Long Test Suite

```bash
# Without immediate kill: Runs all 1000 tests, fails at test 50, wastes time
pytest tests/ -v

# With immediate kill: Stops at test 50 when error detected
./scripts/run-with-error-detection.py pytest tests/ -v
```

### Build Process

```bash
# Without immediate kill: Continues building after compilation error
make build

# With immediate kill: Stops immediately when compilation error detected
./scripts/run-with-error-detection.py make build
```

### Data Processing

```bash
# Without immediate kill: Processes entire dataset after error
python process_data.py --input huge_file.csv

# With immediate kill: Stops immediately when data error detected
./scripts/run-with-error-detection.py python process_data.py --input huge_file.csv
```

## Exit Codes

- **0**: Command completed successfully, no errors detected
- **1**: Error detected and command terminated
- **130**: User interrupt (Ctrl+C)

## Limitations

1. **Subprocess handling**: Some processes spawn children that may continue
   running
2. **Signal handling**: Processes that catch and ignore signals may not
   terminate
3. **Process groups**: Some processes may be in protected process groups

The multi-method kill approach handles most of these cases, but some edge cases
may require manual cleanup.

## Related Documentation

- [Error Detection Wrapper](../scripts/README-error-detection.md) - Full error
  detection documentation
- [Output Suppression Rules](../.cursor/rules/output-suppression.mdc) - Output
  handling rules
