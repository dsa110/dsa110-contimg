# Subband Filename Normalization

This document describes the algorithm for normalizing subband filenames during ingest to eliminate fuzzy time-based clustering.

## The Problem

The DSA-110 correlator writes 16 subband files per observation, but due to I/O timing variations, these files arrive with slightly different timestamps:

```
2025-01-15T12:00:00_sb00.hdf5   # First subband
2025-01-15T12:00:01_sb01.hdf5   # 1 second later
2025-01-15T12:00:00_sb02.hdf5   # Same as first
2025-01-15T12:00:02_sb03.hdf5   # 2 seconds later
...
```

Previously, the pipeline used **±60 second fuzzy clustering** to group these files together. This approach had several drawbacks:

1. **Complex queries**: Required window functions or self-joins to find groups
2. **Non-deterministic**: Edge cases where files could cluster differently
3. **Hidden relationships**: Filesystem didn't show which files belong together
4. **SubbandGroup complexity**: Had to track multiple timestamps per group

## The Solution: Normalize on Ingest

When a subband file arrives, if it clusters with an existing group in the database, **rename the file** to use the canonical group_id (the timestamp of the first subband that arrived):

```
BEFORE (as written by correlator):         AFTER (normalized):
2025-01-15T12:00:00_sb00.hdf5       →      2025-01-15T12:00:00_sb00.hdf5  (canonical)
2025-01-15T12:00:01_sb01.hdf5       →      2025-01-15T12:00:00_sb01.hdf5  (renamed)
2025-01-15T12:00:00_sb02.hdf5       →      2025-01-15T12:00:00_sb02.hdf5  (unchanged)
2025-01-15T12:00:02_sb03.hdf5       →      2025-01-15T12:00:00_sb03.hdf5  (renamed)
```

### How It Works

1. **File arrives**: Watchdog detects new `*_sb??.hdf5` file
2. **Parse filename**: Extract timestamp and subband index
3. **Query database**: Check if a group exists within ±60s tolerance
4. **First arrival wins**: If no existing group, this file's timestamp becomes canonical
5. **Normalize**: If group exists, rename file to use canonical timestamp
6. **Record in database**: Store with normalized path and canonical group_id

### Algorithm Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  New file: 2025-01-15T12:00:02_sb05.hdf5                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Parse: group_id="2025-01-15T12:00:02", subband_idx=5           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Query: SELECT group_id FROM processing_queue                   │
│         WHERE ABS(julianday(?) - julianday(group_id)) * 86400   │
│               <= 60.0                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────────────┐
│  No existing group       │    │  Found: canonical="T12:00:00"    │
│  → Use this timestamp    │    │  → Rename file to canonical      │
│    as canonical          │    │                                  │
└──────────────────────────┘    └──────────────────────────────────┘
              │                               │
              └───────────────┬───────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Result: 2025-01-15T12:00:00_sb05.hdf5                          │
│  All 16 subbands now share the same timestamp                   │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits

| Aspect           | Before (Fuzzy Clustering)                | After (Normalization)                         |
| ---------------- | ---------------------------------------- | --------------------------------------------- |
| **Grouping**     | Complex SQL with tolerance windows       | Simple `GROUP BY group_id`                    |
| **Filesystem**   | Mixed timestamps, unclear membership     | Self-documenting: same timestamp = same group |
| **Queries**      | `ABS(julianday(a) - julianday(b)) <= 60` | `WHERE group_id = ?`                          |
| **SubbandGroup** | Tracked multiple timestamps              | Single canonical timestamp                    |
| **Idempotency**  | N/A                                      | Safe to re-run normalizer                     |

## Implementation

### Core Functions

Located in `dsa110_contimg.conversion.streaming.normalize`:

```python
from dsa110_contimg.conversion.streaming import (
    normalize_subband_path,      # Rename single file
    normalize_subband_on_ingest, # Entry point for streaming
    normalize_directory,         # Batch normalize historical files
)

# During ingest (automatic)
new_path = normalize_subband_on_ingest(
    path=Path("/data/incoming/2025-01-15T12:00:02_sb05.hdf5"),
    target_group_id="2025-01-15T12:00:00",  # From database lookup
    source_group_id="2025-01-15T12:00:02",  # From filename
)
# Returns: Path("/data/incoming/2025-01-15T12:00:00_sb05.hdf5")

# Batch normalize historical files
stats = normalize_directory(
    directory=Path("/data/incoming"),
    cluster_tolerance_s=60.0,
    dry_run=True,  # Preview changes
)
print(f"Would rename {stats['files_renamed']} of {stats['files_scanned']} files")
```

### CLI Tool

```bash
# Preview what would be renamed
python -m dsa110_contimg.conversion.streaming.normalize_cli \
    --dry-run --verbose /data/incoming

# Actually perform renames
python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming

# Custom tolerance
python -m dsa110_contimg.conversion.streaming.normalize_cli \
    --tolerance 30 /data/incoming
```

### Integration Points

1. **Streaming Handler** (`streaming_converter.py`):

   - `_FSHandler._maybe_record()` calls `normalize_subband_on_ingest()`
   - Happens automatically when files arrive

2. **QueueDB** (`streaming_converter.py`):

   - `find_target_group()` queries for existing groups within tolerance
   - Returns canonical group_id if found

3. **FUSE Lock Manager** (optional):
   - Coordinates with file validators during rename
   - Uses write lock for atomic rename operations

## Error Handling

- **Rename fails**: Original path is returned, ingest continues
- **Target exists**: Raises `OSError` (shouldn't happen in normal operation)
- **Invalid filename**: Returns original path unchanged
- **Lock timeout**: Proceeds without lock (rename is still atomic on POSIX)

## Backward Compatibility

Historical files with mixed timestamps can be normalized using the batch CLI:

```bash
# Step 1: Dry-run to preview
python -m dsa110_contimg.conversion.streaming.normalize_cli \
    --dry-run /data/incoming 2>&1 | tee normalize-preview.log

# Step 2: Review the preview output

# Step 3: Apply normalization
python -m dsa110_contimg.conversion.streaming.normalize_cli /data/incoming
```

After normalization, queries that previously required fuzzy matching will work with exact `group_id` comparisons.

## Related Documentation

- [Streaming Pipeline Operations](../backend/docs/ops/streaming-pipeline.md)
- [Subband Grouping](../backend/src/dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md)
