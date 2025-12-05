# Error Detection Wrapper

## Overview

`run-with-error-detection.sh` is a wrapper script that runs any command and
**automatically kills execution** if errors are detected in the output.

## Features

- :check: **Comprehensive error pattern detection** - Recognizes 50+ common error
  words/phrases
- :check: **Context-aware detection** - Distinguishes real errors from comments, test
  names, and documentation
- :check: **Exit code checking** - Fails on non-zero exit codes (with exceptions for
  commands like `grep`)
- :check: **Structured test parsing** - Supports pytest `--junitxml` for reliable
  test result parsing
- :check: **Test result parsing** - Specifically checks pytest/test output for
  failures
- :check: **Full output preservation** - Unbuffered output with simultaneous logging
- :check: **False positive filtering** - Excludes common non-error patterns
  (comments, function names, etc.)
- :check: **Trap-based error handling** - Better error context with line numbers

## Usage

```bash
# Basic usage
./scripts/run-with-error-detection.sh <command> [args...]

# Examples
./scripts/run-with-error-detection.sh pytest tests/ -v
./scripts/run-with-error-detection.sh python script.py
./scripts/run-with-error-detection.sh make test-unit
```

## Error Patterns Detected

The script detects common error indicators including:

- **Python errors**: `Traceback`, `Exception:`, `Error:`, `TypeError`,
  `ValueError`, etc.
- **Test failures**: `FAILED`, `failed`, `test.*failed`, `.*tests? failed`
- **Shell errors**: `command not found`, `Permission denied`, `Cannot`,
  `Failed to`
- **Database errors**: `OperationalError`, `IntegrityError`,
  `table.*has no column`
- **CASA errors**: `SEVERE`, `Exception Reported`, `Table.*does not exist`
- **General errors**: `CRITICAL`, `FATAL`, `Segmentation fault`, `Aborted`

## Behavior

### On Success

- Command runs normally
- Output is displayed and logged
- Script exits with code 0

### On Error Detection

- Command output is still displayed (full output preserved)
- Error patterns are highlighted
- Script exits with code 1
- Log file location is reported

## Log Files

Log files are automatically created in `/tmp/` with format:

```
/tmp/error-detection-YYYYMMDD_HHMMSS.log
```

Set `LOG_DIR` environment variable to change location:

```bash
LOG_DIR=/path/to/logs ./scripts/run-with-error-detection.sh pytest tests/
```

## Examples

### Successful Command

```bash
$ ./scripts/run-with-error-detection.sh echo "Success"
[INFO] Running command: echo Success
Success
[SUCCESS] Command completed successfully
```

### Failed Command (Exit Code)

```bash
$ ./scripts/run-with-error-detection.sh false
[INFO] Running command: false
[ERROR-DETECTION] Command exited with non-zero code: 1
[ERROR-DETECTION] ERROR DETECTION: Command execution failed
```

### Failed Command (Error Pattern)

```bash
$ ./scripts/run-with-error-detection.sh python3 -c 'raise ValueError("test")'
[INFO] Running command: python3 -c 'raise ValueError("test")'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ValueError: test
[ERROR-DETECTION] Error patterns detected in command output
[ERROR-DETECTION] ERROR DETECTION: Command execution failed
```

### Test Failure

```bash
$ ./scripts/run-with-error-detection.sh pytest tests/ -v
...
FAILED tests/test_example.py::test_something
[ERROR-DETECTION] Command exited with non-zero code: 1
[ERROR-DETECTION] Test failures detected: 1 failed, 0 errors
[ERROR-DETECTION] ERROR DETECTION: Command execution failed
```

## Integration with CI/CD

Use in CI/CD pipelines to ensure no errors slip through:

```yaml
# GitHub Actions example
- name: Run tests with error detection
  run: ./scripts/run-with-error-detection.sh pytest tests/ -v
```

## Compliance with Output Suppression Rules

This script follows the output suppression rules:

- :check: Uses unbuffered output (`stdbuf -oL -eL`)
- :check: Preserves full output (no filtering)
- :check: Simultaneous logging with `tee`
- :check: Captures both stdout and stderr (`2>&1`)

## Advanced Features

### Context-Aware Error Detection

The script uses context-aware detection to avoid false positives:

- **Comments**: `# Error: comment` is ignored
- **Function names**: `def test_error_handling()` is ignored
- **Test names**: `test_error_recovery` is ignored
- **Documentation**: Error words in documentation strings are ignored

### Expected Non-Zero Exit Codes

Some commands legitimately exit with non-zero codes:

- `grep` - exits 1 when pattern not found
- `diff` - exits 1 when files differ
- `test` / `[` - exits 1 when condition is false

The script recognizes these and only warns (doesn't fail) for expected non-zero
exits.

### JUnit XML Support

For pytest, use `--junitxml` for more reliable parsing:

```bash
./scripts/run-with-error-detection.sh pytest tests/ -v --junitxml=results.xml
```

The script will parse the XML file instead of text output, reducing false
positives.

## Edge Cases Handled

- :check: Commands that exit non-zero but are expected (`grep`, `diff`)
- :check: Error words in comments (`# Error: comment`)
- :check: Error words in function/test names (`def test_error()`)
- :check: Multi-line error messages
- :check: Empty test results
- :check: JUnit XML parsing
- :check: Numeric comparison edge cases

## Related

- [Error Acknowledgment Rule](../.cursor/rules/error-acknowledgment.mdc) - Never
  ignore errors
- [Output Suppression Rules](../.cursor/rules/output-suppression.mdc) - Preserve
  full output
