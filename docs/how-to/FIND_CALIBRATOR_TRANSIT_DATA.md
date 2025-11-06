# Finding Calibrator Transit Data with HDF5 File Lists

**CRITICAL**: This document explains the **canonical method** for finding calibrator transit data and obtaining the list of 16 subband HDF5 files. This is frequently misunderstood by AI agents, so read carefully.

**Location**: `docs/howto/FIND_CALIBRATOR_TRANSIT_DATA.md`  
**Related**: See also `docs/reports/memory.md` line 45 for the underlying method.

## Quick Answer

**Question**: How do I get the list of 16 subband HDF5 files containing a calibrator transit?

**Answer**: Use `CalibratorMSGenerator.find_transit()` or `generate_from_transit()`. The file list is in `transit_info['files']`.

```python
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

config = CalibratorMSConfig.from_env()
service = CalibratorMSGenerator.from_config(config)

# Method 1: Find transit and get files directly
transit_info = service.find_transit("0834+555")
if transit_info:
    hdf5_files = transit_info['files']  # List of 16 HDF5 file paths
    print(f"Found {len(hdf5_files)} subband files")

# Method 2: Generate MS and access files from result
result = service.generate_from_transit("0834+555")
if result.success:
    hdf5_files = result.transit_info['files']  # List of 16 HDF5 file paths
    ms_path = result.ms_path  # MS path (may already exist)
```

## What NOT to Do

**❌ Don't manually reimplement the logic:**
- Don't call `load_vla_catalog()`, `previous_transits()`, and `find_subband_groups()` separately
- Don't manually search for MS files using glob patterns
- Don't try to parse timestamps from filenames yourself

**✓ Use `list_available_transits()` to get ALL transits with file lists:**
- This method returns file lists for ALL available transits in one call
- Each transit dict includes `'files'` with the complete 16-subband HDF5 file list

## The Proper Method (From `docs/reports/memory.md` Line 45)

The canonical workflow is:

1. **Load calibrator coordinates** via `load_vla_catalog()` (SQLite preferred)
2. **Calculate transit times** using `previous_transits(ra_deg=..., start_time=Time.now(), n=5)`
3. **Calculate search window** (±30-60 minutes around transit)
4. **CRITICAL: Verify data exists** using `find_subband_groups()` from `hdf5_orchestrator`
5. **Select the group whose 5-minute window contains the transit time**

`CalibratorMSGenerator` implements this entire workflow for you. Use it.

## Understanding CalibratorMSGenerator Methods

### `find_transit()` - Returns Transit Info WITH File List

```python
transit_info = service.find_transit("0834+555", max_days_back=30)

if transit_info:
    print(f"Transit: {transit_info['transit_iso']}")
    print(f"Group ID: {transit_info['group_id']}")  # e.g., "2025-11-02T13:34:54"
    print(f"Files: {len(transit_info['files'])}")  # List of 16 HDF5 paths
    
    # Access the file list
    hdf5_files = transit_info['files']
    # Example: ['/data/incoming/2025-11-02T13:34:54_sb00.hdf5', ...]
```

**Returns:**
- `transit_info['files']`: **List of 16 HDF5 file paths** ✓
- `transit_info['group_id']`: Timestamp string (e.g., "2025-11-02T13:34:54")
- `transit_info['transit_iso']`: Transit time in ISO format
- Other metadata (delta_minutes, start_iso, end_iso, etc.)

### `generate_from_transit()` - Creates MS, Returns Result WITH File List

```python
result = service.generate_from_transit("0834+555")

if result.success:
    # MS path (may already exist)
    ms_path = result.ms_path
    
    # File list is in transit_info
    hdf5_files = result.transit_info['files']  # List of 16 HDF5 paths
    
    # Other info
    group_id = result.group_id
    already_exists = result.already_exists  # True if MS was pre-existing
```

**Returns:**
- `result.transit_info['files']`: **List of 16 HDF5 file paths** ✓
- `result.ms_path`: Path to MS file (created or found existing)
- `result.group_id`: Group timestamp
- `result.already_exists`: Whether MS already existed
- `result.metrics`: Conversion metrics, subband count, etc.

### `list_available_transits()` - Lists ALL Transits WITH File Lists

```python
transits = service.list_available_transits("0834+555", max_days_back=30)

for transit in transits:
    print(f"Transit: {transit['transit_iso']}")
    print(f"Group: {transit['group_id']}")
    print(f"Has MS: {transit['has_ms']}")
    print(f"Files: {len(transit['files'])} subband files")  # ✓ File list included!
    
    # Access the file list
    hdf5_files = transit['files']  # List of 16 HDF5 paths
```

**Returns:**
- List of dicts with transit metadata AND file lists
- **`'files'` field**: List of 16 HDF5 file paths for each transit ✓
- Also includes: transit_iso, group_id, has_ms, subband_count, delta_minutes, etc.
- **Use this to get file lists for ALL available transits in one call**

## Complete Example: Getting File Lists for ALL Transits

```python
#!/usr/bin/env python3
"""
Example: Get file lists for ALL 0834+555 transits with data in /data/incoming/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

def main():
    # Initialize service
    config = CalibratorMSConfig.from_env()
    service = CalibratorMSGenerator.from_config(config)
    
    # Get ALL available transits with file lists
    transits = service.list_available_transits("0834+555", max_days_back=60)
    
    if not transits:
        print("No transits found with data")
        return 1
    
    print(f"Found {len(transits)} transits with complete 16-subband groups:\n")
    
    for i, transit in enumerate(transits, 1):
        print(f"Transit {i}: {transit['transit_iso']}")
        print(f"  Group ID: {transit['group_id']}")
        print(f"  Files: {len(transit['files'])} subband files")
        print(f"  Has MS: {transit['has_ms']}")
        print(f"  Days ago: {transit['days_ago']:.1f}")
        
        # Access the file list
        hdf5_files = transit['files']  # List of 16 HDF5 paths
        print(f"  First file: {Path(hdf5_files[0]).name}")
        print(f"  Last file: {Path(hdf5_files[-1]).name}")
        print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Complete Example: Finding One Transit and Getting Files

```python
#!/usr/bin/env python3
"""
Example: Find 0834+555 transit data and get the HDF5 file list.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

def main():
    # Initialize service
    config = CalibratorMSConfig.from_env()
    service = CalibratorMSGenerator.from_config(config)
    
    # Find transit (returns file list)
    transit_info = service.find_transit("0834+555", max_days_back=30)
    
    if not transit_info:
        print("No transit found with data")
        return 1
    
    # Extract file list
    hdf5_files = transit_info['files']
    
    print(f"Found transit: {transit_info['transit_iso']}")
    print(f"Group ID: {transit_info['group_id']}")
    print(f"Subband files ({len(hdf5_files)}):")
    for i, fpath in enumerate(sorted(hdf5_files)):
        print(f"  {i+1:2d}: {Path(fpath).name}")
    
    # Verify it's a complete 16-subband group
    if len(hdf5_files) == 16:
        print("\n✓ Complete 16-subband group")
    else:
        print(f"\n✗ Incomplete group: {len(hdf5_files)} files")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Why This Method?

1. **Implements the canonical workflow** from `docs/reports/memory.md` line 45
2. **Checks data availability** before proceeding
3. **Finds the correct group** whose 5-minute window contains the transit
4. **Returns the complete file list** as part of transit info
5. **Handles edge cases** (missing files, incomplete groups, declination matching)

## Common Mistakes

### Mistake 1: Not knowing which method to use
```python
# ✓ Correct - get file list for one transit
transit_info = service.find_transit("0834+555")
files = transit_info['files']  # Works!

# ✓ Also correct - get file lists for ALL transits
transits = service.list_available_transits("0834+555")
files = transits[0]['files']  # Also works! (returns file list for each transit)
```

### Mistake 2: Manually searching for files
```python
# ❌ Wrong - don't do this
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups
groups = find_subband_groups("/data/incoming", start, end)
# Then trying to figure out which group matches transit...

# ✓ Correct - use the service
transit_info = service.find_transit("0834+555")
# It handles all the logic above automatically
```

### Mistake 3: Forgetting that file list is in `transit_info`
```python
# ❌ Wrong
result = service.generate_from_transit("0834+555")
files = result.files  # AttributeError! Result doesn't have .files

# ✓ Correct
result = service.generate_from_transit("0834+555")
files = result.transit_info['files']  # File list is here
```

## Integration with Test Scripts

When writing test scripts, use this pattern:

```python
from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig

# Find transit with data
config = CalibratorMSConfig.from_env()
service = CalibratorMSGenerator.from_config(config)
transit_info = service.find_transit("0834+555", max_days_back=30)

if not transit_info:
    raise RuntimeError("No 0834 transit data found")

# Get file list and group info
hdf5_files = transit_info['files']
group_id = transit_info['group_id']

# Optionally check if MS already exists
result = service.generate_from_transit("0834+555")
if result.success:
    ms_path = result.ms_path
    # Use existing MS or convert from files
else:
    # Convert files to MS
    service.convert_group(hdf5_files, output_ms_path)
```

## Summary

| Method | Returns File List? | Use Case |
|--------|-------------------|----------|
| `find_transit()` | ✓ Yes (`transit_info['files']`) | Get file list for **one** transit (most recent with data) |
| `generate_from_transit()` | ✓ Yes (`result.transit_info['files']`) | Get file list AND create/get MS for **one** transit |
| `list_available_transits()` | ✓ Yes (`transit['files']` for each) | Get file lists for **ALL** available transits at once |

**Use `list_available_transits()` when you need file lists for multiple transits. Use `find_transit()` for just the most recent transit.**

## References

- **Canonical Method**: `docs/reports/memory.md` line 45
- **Service Implementation**: `src/dsa110_contimg/conversion/calibrator_ms_service.py`
- **Config**: `src/dsa110_contimg/conversion/config.py`

