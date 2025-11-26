# Batch Mode Execution Guide

**Purpose**: Practical guide for executing batch processing workflows with the
DSA-110 Continuum Imaging Pipeline.

**Location**: `docs/how-to/batch_mode_execution_guide.md`  
**Related**:

- [Batch Mode Guide](batch_mode_guide.md) - Complete batch mode documentation
- [Using the Orchestrator CLI](USING_ORCHESTRATOR_CLI.md) - Conversion
  orchestrator details

## Quick Start

### Step 1: Check Available Data

First, find what data is available:

```bash
# Find earliest data in the system
python scripts/find_earliest_data.py

# List files in incoming directory
ls -lh /data/incoming | head -20

# Check for specific date ranges
find /data/incoming -name "2025-10-02*" -type f | head -10
```

### Step 2: Run Batch Conversion

Process a time window (discovers and converts all complete subband groups):

```bash
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-02 00:00:00" \
    "2025-10-02 01:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4
```

**What this does:**

- Discovers all complete subband groups in the time window
- Converts each group to MS format
- Organizes output: `ms/science/YYYY-MM-DD/<timestamp>.ms` or
  `ms/calibrators/YYYY-MM-DD/<timestamp>.ms`
- Processes multiple groups in parallel (batch mode)

### Step 3: Verify Output

Check that MS files were created:

```bash
# List converted MS files
find /stage/dsa110-contimg/ms -name "*.ms" -type d | head -10

# Check database for processed files (use casa6 sqlite3)
/opt/miniforge/envs/casa6/bin/sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
    "SELECT path, start_mjd, status FROM ms_index ORDER BY start_mjd LIMIT 10;"
```

**Note**: Always use casa6's sqlite3 (`/opt/miniforge/envs/casa6/bin/sqlite3`)
for database queries. The system sqlite3 may not be available or may be a
different version.

## Common Batch Processing Scenarios

### Scenario 1: Process One Night of Data

```bash
# Process entire night (24 hours)
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-02 00:00:00" \
    "2025-10-03 00:00:00" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4 \
    --skip-existing
```

**Note**: Use `--skip-existing` to avoid reprocessing already-converted groups.

### Scenario 2: Process Multiple Days

```bash
# Process multiple days in a loop
for date in 2025-10-02 2025-10-03 2025-10-04; do
    echo "Processing $date..."
    /opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
        /data/incoming \
        /stage/dsa110-contimg/ms \
        "${date} 00:00:00" \
        "${date} 23:59:59" \
        --writer parallel-subband \
        --stage-to-tmpfs \
        --skip-existing
done
```

### Scenario 3: Calibrator Transit Processing

Process data centered on a calibrator transit:

```bash
# Find and process most recent calibrator transit
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --window-minutes 60 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**What this does:**

- Finds the most recent transit of calibrator 0834+555
- Processes ±30 minutes around transit (60 minute window)
- Automatically calculates time window

### Scenario 4: Specific Calibrator Transit Date

```bash
# Process specific calibrator transit on a known date
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-02 \
    --window-minutes 60 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

## Testing Before Full Processing

### Dry Run

See what would be processed without actually converting:

```bash
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-10-02 00:00:00" \
    "2025-10-02 01:00:00" \
    --dry-run
```

### Find-Only Mode (Calibrator)

Find calibrator transit without converting:

```bash
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0835+555 \
    --find-only
```

## Complete Batch Workflow Example

Here's a complete workflow for processing one night of data:

```bash
#!/bin/bash
# Complete batch workflow: Conversion → Calibration → Imaging

set -euo pipefail

INPUT_DIR="/data/incoming"
MS_DIR="/stage/dsa110-contimg/ms"
PRODUCTS_DB="/data/dsa110-contimg/state/products.sqlite3"
DATE="2025-10-02"
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"

# Step 1: Convert UVH5 to MS (batch processing)
echo "Step 1: Converting UVH5 to MS..."
$PYTHON_BIN -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    "$INPUT_DIR" \
    "$MS_DIR" \
    "${DATE} 00:00:00" \
    "${DATE} 23:59:59" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --skip-existing

# Step 2: Find all MS files created
echo "Step 2: Finding MS files..."
MS_FILES=$(find "$MS_DIR" -name "*.ms" -type d -newer "$MS_DIR/.timestamp" 2>/dev/null || \
           find "$MS_DIR/science/${DATE}" -name "*.ms" -type d 2>/dev/null)

if [ -z "$MS_FILES" ]; then
    echo "No MS files found. Exiting."
    exit 1
fi

echo "Found $(echo "$MS_FILES" | wc -l) MS files"

# Step 3: Batch calibrate (via API - requires API server running)
# See batch_mode_guide.md for API-based batch calibration

# Step 4: Batch image (via API - requires API server running)
# See batch_mode_guide.md for API-based batch imaging

echo "Batch workflow complete!"
```

## Performance Tips

### 1. Use tmpfs Staging

Always use `--stage-to-tmpfs` for faster I/O:

```bash
--stage-to-tmpfs  # Default: enabled
```

### 2. Adjust Parallel Workers

Match to your system:

```bash
--max-workers 4   # Default: 4, adjust based on CPU cores
```

### 3. Skip Existing Files

For reprocessing or resuming:

```bash
--skip-existing   # Skip groups that already have MS files
```

### 4. Use Checkpoint Files

For long-running batch jobs:

```bash
--checkpoint-file /tmp/conversion_checkpoint.json
```

This allows resuming if the process is interrupted.

## Monitoring Batch Processing

### Check Progress

```bash
# Watch MS files being created
watch -n 5 'find /stage/dsa110-contimg/ms -name "*.ms" -type d | wc -l'

# Check database for processed files
watch -n 5 'sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
    "SELECT COUNT(*) FROM ms_index WHERE status = '\''completed'\'';"'
```

### Check Logs

The orchestrator outputs progress information. For more detailed logs:

```bash
--log-level DEBUG  # More verbose output
```

## Troubleshooting

### No Groups Found

If no groups are found in the time window:

1. **Check data availability:**

   ```bash
   find /data/incoming -name "*2025-10-02*" -type f | head -10
   ```

2. **Verify time format:**
   - Use format: `"YYYY-MM-DD HH:MM:SS"`
   - Time is in UTC

3. **Check for complete groups:**
   - All 16 subbands must be present for a group to be converted
   - Use `--dry-run` to see what groups would be found

### Conversion Failures

If individual groups fail:

1. **Check error messages** in the output
2. **Verify disk space:**
   ```bash
   df -h /stage/dsa110-contimg
   ```
3. **Check tmpfs space:**
   ```bash
   df -h /dev/shm
   ```

### Slow Processing

If batch processing is slow:

1. **Reduce parallel workers** if system is overloaded
2. **Process smaller time windows** (1-2 hours instead of 24 hours)
3. **Use faster storage** (SSD or tmpfs)
4. **Check system resources:**
   ```bash
   htop  # or top
   iostat -x 1  # disk I/O
   ```

## Next Steps

After batch conversion:

1. **Batch Calibration**: See [Batch Mode Guide](batch_mode_guide.md) for
   API-based batch calibration
2. **Batch Imaging**: See [Batch Mode Guide](batch_mode_guide.md) for API-based
   batch imaging
3. **Mosaic Creation**: See [Mosaic Quickstart](mosaic_quickstart.md) for
   creating mosaics

## Related Documentation

- [Batch Mode Guide](batch_mode_guide.md) - Complete batch mode documentation
  with API examples
- [Using the Orchestrator CLI](USING_ORCHESTRATOR_CLI.md) - Detailed
  orchestrator documentation
- [Pipeline Testing Guide](PIPELINE_TESTING_GUIDE.md) - Testing batch workflows
