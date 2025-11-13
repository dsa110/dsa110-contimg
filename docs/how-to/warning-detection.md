# Warning Detection and Termination

## Overview

The error detection system now **also terminates commands when warning messages are detected**, not just errors.

## What Triggers Termination

### Error Patterns (Existing)
- Python exceptions (Traceback, Exception, etc.)
- Test failures (FAILED, FAILURE, etc.)
- System errors (Permission denied, etc.)
- Database errors (OperationalError, etc.)

### Warning Patterns (New)
- **Deprecation warnings**: `DeprecationWarning`, `PendingDeprecationWarning`, `FutureWarning`
- **Test warnings**: `WARNING.*test.*skipped`, `WARNING.*test.*failed`
- **Database warnings**: `WARNING.*database`, `WARNING.*table`, `WARNING.*column`, `WARNING.*schema`
- **CASA warnings**: `WARNING.*SEVERE`, `WARNING.*Exception`
- **Build warnings**: `WARNING.*build`, `WARNING.*compilation`
- **System warnings**: `WARNING.*Permission`, `WARNING.*Access`, `WARNING.*denied`
- **Critical warnings**: `WARNING.*CRITICAL`, `WARNING.*FATAL`, `WARNING.*Error`, `WARNING.*Failed`
- **Data quality warnings**: `WARNING.*invalid`, `WARNING.*corrupt`, `WARNING.*missing`, `WARNING.*not found`
- **Configuration warnings**: `WARNING.*config`, `WARNING.*setting`, `WARNING.*parameter`

## Behavior

When a warning pattern is detected:
1. **Immediate termination**: Command is killed immediately (same as error detection)
2. **Error reported**: Warning is reported as an error condition
3. **Exit code**: Process exits with code 1

## Examples

### Deprecation Warning
```bash
$ python script.py
WARNING: database table has no column
[ERROR-DETECTION] Warning pattern 'WARNING.*column' detected in real-time!
[ERROR-DETECTION] Terminating command immediately due to warning...
```

### Test Warning
```bash
$ pytest tests/
WARNING: test skipped due to missing dependency
[ERROR-DETECTION] Warning pattern 'WARNING.*test.*skipped' detected in real-time!
[ERROR-DETECTION] Terminating command immediately due to warning...
```

## Rationale

Warnings often indicate:
- **Serious issues** that need immediate attention
- **Deprecated features** that will break in future versions
- **Data quality problems** that could lead to incorrect results
- **Configuration issues** that prevent proper operation

By terminating on warnings, we ensure:
- **Early detection** of problems
- **Prevention** of incorrect results
- **Consistency** in error handling

## Configuration

Warning detection is **always enabled** when using the error detection wrapper. There is no option to disable it separately from error detection.

## False Positives

The system uses the same false positive detection as error patterns:
- Excludes comments and documentation
- Excludes function/class definitions
- Excludes safe contexts

If you encounter false positives, you can:
1. Adjust the warning patterns in `scripts/run-with-error-detection.py`
2. Use `SKIP_ERROR_DETECTION=1` to bypass detection for specific commands

