# Duplicate TIME Values Investigation Report

## Problem Summary

Multiple MS files with different filenames contain **identical TIME data**, indicating a code bug in how MS files are generated.

## Evidence

### MS Files Have Duplicate TIME Values

- `2025-10-29T13:38:49.ms` → TIME: `2025-10-29T13:38:50.326` to `2025-10-29T13:43:46.679`
- `2025-10-29T13:43:59.ms` → TIME: `2025-10-29T13:38:50.326` to `2025-10-29T13:43:46.679` **(SAME!)**
- `2025-10-29T13:49:08.ms` → TIME: `2025-10-29T13:38:50.326` to `2025-10-29T13:43:46.679` **(SAME!)`

### Source UVH5 Files Have Different TIME Data

- `2025-10-29T13:38:49_sb00.hdf5` → TIME: `2025-10-29T13:38:50.326` to `2025-10-29T13:43:46.679`
- `2025-10-29T13:43:59_sb00.hdf5` → TIME: `2025-10-29T13:43:59.564` to `2025-10-29T13:48:55.917` **(DIFFERENT!)**
- `2025-10-29T13:49:08_sb00.hdf5` → TIME: `2025-10-29T13:49:08.801` to `2025-10-29T13:54:05.154` **(DIFFERENT!)**

## Root Cause Analysis

### The Bug

**MS files are being created with the WRONG source data:**
- MS filename comes from UVH5 filename (correct)
- But MS TIME data comes from a DIFFERENT observation (wrong)

### Code Flow

1. `find_subband_groups()` creates groups of UVH5 files based on filename timestamps
2. Each group should create one MS file with TIME data matching the group's files
3. **BUG**: MS files are being created with TIME data from a different group

### Possible Causes

1. **File list corruption** - Groups are being mixed up during iteration
2. **Caching issue** - Same data being reused across groups
3. **Writer bug** - Writer not using the correct file_list
4. **Grouping bug** - Wrong files being grouped together
5. **Closure issue** - Variable capture in loops causing wrong file_list to be used

## Code Locations to Investigate

### Key Functions

1. **`find_subband_groups()`** (`hdf5_orchestrator.py:169`)
   - Groups files by timestamp within tolerance (30 seconds)
   - Returns list of file groups

2. **`convert_subband_groups_to_ms()`** (`hdf5_orchestrator.py:457`)
   - Iterates over groups: `for file_list in groups_iter:`
   - Creates MS filename from first file: `base_name = os.path.splitext(first_file)[0].split("_sb")[0]`
   - Passes `file_list` to writer: `current_writer_kwargs.setdefault("file_list", sorted_file_list)`

3. **`DirectSubbandWriter.write()`** (`direct_subband.py:72`)
   - Gets file_list from kwargs: `self.file_list = self.kwargs.get("file_list", [])`
   - Uses `self.file_list` to write MS: `for sb_file in self.file_list:`

### Potential Bug Locations

1. **Line 666 in `hdf5_orchestrator.py`**: `for file_list in groups_iter:`
   - Check if `groups_iter` is being modified or reused incorrectly

2. **Line 849 in `hdf5_orchestrator.py`**: `current_writer_kwargs.setdefault("file_list", sorted_file_list)`
   - Check if `sorted_file_list` is being reused or modified

3. **Line 48 in `direct_subband.py`**: `self.file_list = self.kwargs.get("file_list", [])`
   - Check if kwargs are being shared or modified between groups

## Next Steps

1. **Add logging** to verify which file_list is being used for each MS file
2. **Check for variable reuse** - ensure `file_list` is not being modified between iterations
3. **Verify writer isolation** - ensure each writer instance uses its own file_list
4. **Test with a single group** - verify if the bug occurs with one group or only with multiple groups
5. **Check for shared state** - look for any global variables or shared state that could cause this

## Impact

- **Data Quality**: MS files contain incorrect TIME data, making them unreliable for time-based operations
- **Calibration**: Calibrator matching and transit calculations will be incorrect
- **Analysis**: Any time-dependent analysis will produce wrong results

## Status

**FIXED** - Bug identified and fixed.

## Fix Applied

### Root Cause
The bug was in `hdf5_orchestrator.py` line 847. The code was doing:
```python
current_writer_kwargs = writer_kwargs or {}
```

This creates a **reference** to the same dict if `writer_kwargs` is not None, not a copy. When `current_writer_kwargs.setdefault("file_list", sorted_file_list)` was called, it modified the original `writer_kwargs` dict. In the next iteration, `current_writer_kwargs` would still reference the same dict, which now contained the `file_list` from the previous group.

### The Fix
Changed line 847-849 to:
```python
# CRITICAL FIX: Create a copy of writer_kwargs for each iteration
# to prevent file_list from being shared between groups.
# Without this, all MS files would use the file_list from the first group,
# causing duplicate TIME values across different MS files.
current_writer_kwargs = (writer_kwargs or {}).copy()
current_writer_kwargs.setdefault("scratch_dir", scratch_dir)
current_writer_kwargs["file_list"] = sorted_file_list  # Use assignment, not setdefault
```

### Changes
1. **Create a copy**: `(writer_kwargs or {}).copy()` ensures each iteration gets its own dict
2. **Use assignment for file_list**: Changed from `setdefault()` to direct assignment to ensure `file_list` is always set to the current group's file list

### Verification
- Simulated the bug scenario and confirmed the fix works
- Each iteration now gets its own copy of `writer_kwargs`
- `file_list` is correctly set for each group

### Testing Required
- Generate new MS files with the fix and verify they have unique TIME values
- Compare MS TIME with source UVH5 TIME to confirm correctness
- Run validation checks on newly generated MS files

