# MS Access Serialization Implementation

**Date:** 2025-11-09  
**Purpose:** Document the implementation of MS access serialization to prevent CASA table lock conflicts

## Overview

MS access serialization has been implemented using file locking (`fcntl.flock`) to prevent CASA table lock conflicts when multiple processes try to access the same Measurement Set concurrently.

## Implementation Details

### New Module: `src/dsa110_contimg/utils/ms_locking.py`

Provides:
- `ms_lock()`: Context manager for MS access serialization
- `cleanup_stale_locks()`: Utility to clean up stale lock files from crashed processes

### Integration Points

1. **`src/dsa110_contimg/imaging/spw_imaging.py`**
   - `image_all_spws()`: Added `serialize_ms_access` parameter
   - When enabled, wraps entire SPW imaging operation in `ms_lock()` context

2. **`src/dsa110_contimg/photometry/adaptive_photometry.py`**
   - `measure_with_adaptive_binning()`: Extracts and passes `serialize_ms_access` parameter

3. **`src/dsa110_contimg/photometry/cli.py`**
   - Added `--serialize-ms-access` CLI flag to `adaptive` subcommand

## Usage

### Command Line

```bash
# Process single source (no locking needed)
python -m dsa110_contimg.photometry.cli adaptive \
  --ms /path/to/data.ms \
  --ra 124.526792 \
  --dec 54.620694 \
  --output-dir /tmp/results \
  --target-snr 5.0

# Process multiple sources in parallel (with locking)
python -m dsa110_contimg.photometry.cli adaptive \
  --ms /path/to/data.ms \
  --ra 124.526792 \
  --dec 54.620694 \
  --output-dir /tmp/results1 \
  --target-snr 5.0 \
  --serialize-ms-access &
PID1=$!

python -m dsa110_contimg.photometry.cli adaptive \
  --ms /path/to/data.ms \
  --ra 124.530000 \
  --dec 54.625000 \
  --output-dir /tmp/results2 \
  --target-snr 5.0 \
  --serialize-ms-access &
PID2=$!

wait $PID1 $PID2
```

### Python API

```python
from pathlib import Path
from dsa110_contimg.photometry.adaptive_photometry import (
    measure_with_adaptive_binning
)

result = measure_with_adaptive_binning(
    ms_path="/path/to/data.ms",
    ra_deg=124.526792,
    dec_deg=54.620694,
    output_dir=Path("/tmp/results"),
    serialize_ms_access=True,  # Enable locking
    target_snr=5.0,
)
```

## How It Works

1. **Lock File Creation**: Creates a lock file `{ms_path}.lock` in the same directory as the MS
2. **Exclusive Lock**: Uses `fcntl.flock()` with `LOCK_EX` to acquire exclusive lock
3. **Blocking Behavior**: If lock is held, waits (with timeout) until it's released
4. **Automatic Release**: Lock is automatically released when context exits
5. **Stale Lock Cleanup**: Checks for and removes stale locks (>1 hour old) before acquiring

## Benefits

- **Prevents Deadlocks**: Eliminates CASA table lock conflicts
- **Automatic**: No manual coordination needed
- **Safe**: Handles crashes gracefully (stale lock cleanup)
- **Optional**: Doesn't affect existing workflows (opt-in via flag)
- **Efficient**: Minimal overhead when not needed

## Testing

To test the implementation:

```bash
# Test with multiple sources in parallel
cd /data/dsa110-contimg

# Source 1
PYTHONPATH=src:$PYTHONPATH \
/opt/miniforge/envs/casa6/bin/python \
  -m dsa110_contimg.photometry.cli adaptive \
  --ms /stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms \
  --ra 124.526792 \
  --dec 54.620694 \
  --output-dir /tmp/test_lock1 \
  --target-snr 5.0 \
  --max-spws 4 \
  --serialize-ms-access &

# Source 2 (should wait for Source 1 to complete)
PYTHONPATH=src:$PYTHONPATH \
/opt/miniforge/envs/casa6/bin/python \
  -m dsa110_contimg.photometry.cli adaptive \
  --ms /stage/dsa110-contimg/ms/science/2025-10-28/2025-10-28T13:45:34.ms \
  --ra 124.530000 \
  --dec 54.625000 \
  --output-dir /tmp/test_lock2 \
  --target-snr 5.0 \
  --max-spws 4 \
  --serialize-ms-access &

wait
```

Expected behavior:
- Both processes start
- One acquires lock and proceeds
- Other waits until first completes
- No CASA table lock errors

## Limitations

- **Single MS Only**: Locking is per-MS, so different MS files can still be processed in parallel
- **File System Requirement**: Requires a shared file system (works on local FS, NFS, but not across separate machines)
- **Timeout**: Default timeout is 3600 seconds (1 hour); may need adjustment for very long operations

## Future Enhancements

- Configurable timeout via CLI argument
- Lock file location customization
- Lock status monitoring/debugging utilities
- Integration into pipeline orchestrator for automatic serialization

