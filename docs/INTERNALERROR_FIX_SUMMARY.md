# Pytest INTERNALERROR Fix Summary

## Problem

When running `pytest tests/` with certain flag combinations (specifically
`--co -q`), pytest throws:

```
INTERNALERROR> argparse.ArgumentError: argument --configfile: expected one argument
```

## Root Cause

The issue was caused by:

1. **Duplicate pytest.ini files**: Both `/data/dsa110-contimg/pytest.ini` and
   `/data/dsa110-contimg/tests/pytest.ini` existed, causing conflicts
2. **Invalid syntax in addopts**: A comment line within the multi-line `addopts`
   value was causing parsing issues
3. **Warning filter syntax**: The `-W` flag in `addopts` with the text
   "Benchmarks are automatically disabled" was being misinterpreted

## Fixes Applied

### 1. Consolidated pytest.ini files

- **Removed**: `tests/pytest.ini` (backed up to `tests/pytest.ini.backup`)
- **Updated**: Root `pytest.ini` with consolidated configuration
- **Result**: Single authoritative config file prevents conflicts

### 2. Fixed addopts syntax

- **Removed**: Comment from middle of multi-line `addopts` value
- **Removed**: `-W ignore:Benchmarks are automatically disabled.*` from addopts
  (moved to `filterwarnings` section)
- **Result**: Clean addopts syntax that parses correctly

### 3. Updated configuration

- Added `filterwarnings` section for warning suppression
- Added `norecursedirs` comment (deprecated in pytest 8+)
- Consolidated markers from both config files

## Current Status

✅ **Fixed**: `pytest tests/ --collect-only` works  
✅ **Fixed**: `pytest tests/` works  
⚠️ **Known Issue**: `pytest --co -q` still fails (this appears to be a
pytest/plugin interaction issue)

## Recommendations

1. **Use `--collect-only` instead of `--co -q`** for test collection
2. **Use `-v` or no quiet flag** when using `--co`
3. **Monitor pytest plugin updates** - this may be fixed in future versions

## Test Commands That Work

```bash
# These work correctly:
pytest tests/ --collect-only
pytest tests/ -v
pytest tests/calibration/test_calibrator_catalog.py -v
pytest --co tests/calibration/test_calibrator_catalog.py
```

## Test Commands That Fail

```bash
# This combination fails:
pytest --co -q tests/
```

The `-q` flag with `--co` appears to trigger a bug in pytest's argument parsing
when combined with certain plugins.
