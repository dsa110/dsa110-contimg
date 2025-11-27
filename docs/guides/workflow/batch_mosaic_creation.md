# Batch Mosaic Creation Guide

**Date:** 2025-11-14  
**Status:** complete  
**Related:**

- create_mosaic_centered.py -
  Base script
- [Batch Mode Guide](batch_mode_guide.md) - General batch processing
- [Mosaic Quickstart](mosaic.md) - Single mosaic creation

---

## Overview

This guide explains how to run the DSA-110 Continuum Imaging Pipeline in batch
mode to create multiple mosaics centered on calibrator transits. The workflow is
based on `scripts/mosaic/create_mosaic_centered.py`, which orchestrates the
complete end-to-end pipeline from HDF5 data to published science-ready mosaics.

**What this guide covers:**

- Running single mosaics (foundation)
- Processing multiple calibrators sequentially
- Processing multiple calibrators in parallel
- Monitoring batch execution
- Error handling and recovery
- Best practices for production batch runs

---

## Prerequisites

1. **Environment Setup:**

   ```bash
   source /data/dsa110-contimg/scripts/developer-setup.sh
   ```

2. **Verify casa6 Python:**

   ```bash
   test -x /opt/miniforge/envs/casa6/bin/python || exit 1
   ```

3. **Check Available Data:**
   ```bash
   # List available calibrator transits
   /opt/miniforge/envs/casa6/bin/python -c "
   from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSService
   service = CalibratorMSService()
   transits = service.list_available_transits('0834+555')
   print(f'Found {len(transits)} transits for 0834+555')
   "
   ```

---

## Single Mosaic Creation (Foundation)

Before running batch mode, understand the single-mosaic workflow:

### Basic Usage

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src \
/opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 50
```

**What happens:**

1. Finds earliest transit for calibrator `0834+555`
2. Calculates ±25 minute window centered on transit
3. Ensures MS files exist (converts HDF5 if needed)
4. Forms group, solves/applies calibration
5. Images all MS files
6. Creates mosaic
7. Validates and publishes
8. Waits until published (default behavior)

### Options

- `--calibrator NAME` - Calibrator name (required, e.g., `0834+555`)
- `--timespan-minutes N` - Mosaic duration in minutes (default: 50)
- `--no-wait` - Return immediately after creation, don't wait for publishing
- `--poll-interval SECONDS` - Polling interval for published status (default: 5)
- `--max-wait-hours HOURS` - Maximum wait time (default: 24.0)

### Example: Non-blocking Single Mosaic

```bash
PYTHONPATH=/data/dsa110-contimg/src \
/opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 50 \
    --no-wait
```

This returns immediately after mosaic creation, allowing you to submit multiple
jobs without waiting.

---

## Batch Mode: Sequential Processing

### Method 1: Simple Loop (Multiple Calibrators)

Process multiple calibrators one at a time:

```bash
#!/bin/bash
# batch_sequential_calibrators.sh

set -euo pipefail
IFS=$'\n\t'

CALIBRATORS=("0834+555" "3C48" "3C147" "3C286")
TIMESPAN=50

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src

for cal in "${CALIBRATORS[@]}"; do
    echo "Processing calibrator: $cal"

    /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
        --calibrator "$cal" \
        --timespan-minutes "$TIMESPAN" \
        --max-wait-hours 24.0

    if [ $? -eq 0 ]; then
        echo "SUCCESS: Mosaic for $cal completed"
    else
        echo "FAILED: Mosaic for $cal failed - check logs"
        # Continue to next calibrator (or exit on first failure)
    fi
done
```

`set -euo pipefail` ensures unexpected failures stop the run immediately instead
of continuing with stale state.

**Execution:**

```bash
chmod +x batch_sequential_calibrators.sh
./batch_sequential_calibrators.sh
```

### Method 2: Calibrator List from File

For larger batches, use a file:

```bash
# calibrators.txt
0834+555
3C48
3C147
3C286
J0132-169
```

```bash
#!/bin/bash
# batch_from_file.sh

CALIBRATOR_FILE="calibrators.txt"
TIMESPAN=50

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src

while IFS= read -r cal; do
    # Skip empty lines and comments
    [[ -z "$cal" || "$cal" =~ ^# ]] && continue

    echo "Processing: $cal"

    /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
        --calibrator "$cal" \
        --timespan-minutes "$TIMESPAN"

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed for $cal - continuing..."
    fi
done < "$CALIBRATOR_FILE"
```

### Method 3: Multiple Transits of Same Calibrator

Process multiple transits for a single calibrator:

```bash
#!/bin/bash
# batch_multiple_transits.sh

CALIBRATOR="0834+555"
TIMESPAN=50
MAX_MOSAICS=10  # Limit number of mosaics

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src

# Use orchestrator's sequential processing with overlap
/opt/miniforge/envs/casa6/bin/python -c "
from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator
import logging

logging.basicConfig(level=logging.INFO)
orchestrator = MosaicOrchestrator()

# Process sequential mosaics with sliding window overlap
published_paths = orchestrator.process_sequential_mosaics_with_overlap(
    max_mosaics=$MAX_MOSAICS,
    timespan_minutes=$TIMESPAN,
    wait_for_published=True
)

print(f'Created {len(published_paths)} mosaics')
for path in published_paths:
    print(f'  - {path}')
"
```

---

## Batch Mode: Parallel Processing

### Method 1: Background Jobs (Simple Parallel)

Run multiple calibrators in parallel using background jobs:

```bash
#!/bin/bash
# batch_parallel_simple.sh

set -euo pipefail
IFS=$'\n\t'

CALIBRATORS=("0834+555" "3C48" "3C147" "3C286")
TIMESPAN=50
MAX_PARALLEL=2  # Limit concurrent jobs

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src

declare -A JOBS=()  # Track PID -> calibrator name

reap_finished_jobs() {
    for pid in "${!JOBS[@]}"; do
        if ! kill -0 "$pid"; then
            if wait "$pid"; then
                echo "Job $pid (${JOBS[$pid]}) completed successfully"
            else
                status=$?
                echo "Job $pid (${JOBS[$pid]}) FAILED with exit code $status"
            fi
            unset 'JOBS[$pid]'
        fi
    done
}

for cal in "${CALIBRATORS[@]}"; do
    # Wait if we've hit the parallel limit
    while [ "${#JOBS[@]}" -ge "$MAX_PARALLEL" ]; do
        reap_finished_jobs
        sleep 5
    done

    echo "Starting mosaic for $cal (PID will be logged)"

    # Run in background with no-wait to avoid blocking
    (
        /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
            --calibrator "$cal" \
            --timespan-minutes "$TIMESPAN" \
            --no-wait > "mosaic_${cal}.log" 2>&1
    ) &

    pid=$!
    JOBS["$pid"]="$cal"
    echo "Started job for $cal (PID: $pid)"
done

# Wait for all remaining jobs
echo "Waiting for all jobs to complete..."
while [ "${#JOBS[@]}" -gt 0 ]; do
    reap_finished_jobs
    sleep 5
done

echo "All batch jobs finished"
```

Do not redirect `kill` or `wait` errors—seeing those messages helps catch
orphaned or crashed jobs quickly.

### Method 2: GNU Parallel (Advanced)

For more sophisticated parallel execution:

```bash
# Install GNU parallel if needed
# sudo apt-get install parallel

# Create job list
cat > job_list.txt <<EOF
0834+555
3C48
3C147
3C286
EOF

# Run with GNU parallel
cat job_list.txt | parallel -j 2 \
    "cd /data/dsa110-contimg && \
     PYTHONPATH=/data/dsa110-contimg/src \
     /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
         --calibrator {} \
         --timespan-minutes 50 \
         --no-wait \
         > mosaic_{}.log 2>&1"
```

### Method 3: Python-Based Parallel Execution

Use Python's multiprocessing for better control:

```python
#!/usr/bin/env python3
"""
batch_parallel_mosaics.py - Parallel batch mosaic creation
"""
import logging
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple

from dsa110_contimg.mosaic.orchestrator import MosaicOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_single_mosaic(calibrator: str, timespan: int = 50) -> Tuple[str, bool, str]:
    """Create a single mosaic, returns (calibrator, success, path_or_error)."""
    try:
        orchestrator = MosaicOrchestrator()
        published_path = orchestrator.create_mosaic_centered_on_calibrator(
            calibrator_name=calibrator,
            timespan_minutes=timespan,
            wait_for_published=True,
        )
        if published_path:
            return (calibrator, True, published_path)
        else:
            return (calibrator, False, "No path returned")
    except Exception as e:
        return (calibrator, False, str(e))


def main():
    calibrators = ["0834+555", "3C48", "3C147", "3C286"]
    timespan = 50
    max_workers = 2  # Limit concurrent mosaics

    logger.info(f"Processing {len(calibrators)} calibrators with {max_workers} workers")

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(create_single_mosaic, cal, timespan): cal
            for cal in calibrators
        }

        for future in as_completed(futures):
            cal = futures[future]
            try:
                result = future.result()
                results.append(result)
                cal_name, success, path = result
                if success:
                    logger.info(f"SUCCESS: {cal_name} -> {path}")
                else:
                    logger.error(f"FAILED: {cal_name} -> {path}")
            except Exception as e:
                logger.error(f"EXCEPTION for {cal}: {e}")
                results.append((cal, False, str(e)))

    # Summary
    successful = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]

    logger.info(f"\nSummary: {len(successful)} succeeded, {len(failed)} failed")
    if failed:
        logger.error("Failed calibrators:")
        for cal, _, error in failed:
            logger.error(f"  - {cal}: {error}")

    return 0 if len(failed) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Usage:**

```bash
PYTHONPATH=/data/dsa110-contimg/src \
/opt/miniforge/envs/casa6/bin/python batch_parallel_mosaics.py
```

Each worker spins up its own `MosaicOrchestrator` (and SQLite connections), so
start with `max_workers=1` or `2` and increase only after confirming you are not
hitting `database is locked` warnings.

---

## Monitoring Batch Execution

### Check Mosaic Status

```bash
# Query database for mosaic status
/opt/miniforge/envs/casa6/bin/sqlite3 /data/dsa110-contimg/state/products.sqlite3 <<EOF
SELECT
    group_id,
    stage,
    status,
    created_at,
    cal_applied
FROM mosaic_groups
ORDER BY created_at DESC
LIMIT 20;
EOF
```

### Check Published Mosaics

```bash
# List published mosaics
/opt/miniforge/envs/casa6/bin/sqlite3 /data/dsa110-contimg/state/data_registry.sqlite3 <<EOF
SELECT
    data_id,
    status,
    published_path,
    published_at
FROM data_registry
WHERE data_type = 'mosaic' AND status = 'published'
ORDER BY published_at DESC
LIMIT 20;
EOF
```

### Monitor Log Files

```bash
# Watch log files in real-time
tail -f mosaic_*.log

# Check for errors across all logs
grep -i error mosaic_*.log

# Count successes/failures
grep -c "SUCCESS" mosaic_*.log
grep -c "FAILED" mosaic_*.log
```

### Check System Resources

```bash
# Monitor CPU/memory during batch processing
watch -n 5 'ps aux | grep create_mosaic_centered | grep -v grep'

# Check disk space (mosaics can be large)
df -h /stage/dsa110-contimg /data/dsa110-contimg/products
```

---

## Error Handling and Recovery

### Handling Individual Failures

The script returns exit code 0 on success, 1 on failure. Handle failures in your
batch script:

```bash
#!/bin/bash
# batch_with_error_handling.sh

CALIBRATORS=("0834+555" "3C48" "3C147")
FAILED=()

for cal in "${CALIBRATORS[@]}"; do
    if ! /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
        --calibrator "$cal" \
        --timespan-minutes 50; then
        FAILED+=("$cal")
        echo "Failed: $cal - will retry later"
    fi
done

# Retry failed calibrators
if [ ${#FAILED[@]} -gt 0 ]; then
    echo "Retrying failed calibrators: ${FAILED[*]}"
    for cal in "${FAILED[@]}"; do
        # Retry with longer timeout
        /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
            --calibrator "$cal" \
            --timespan-minutes 50 \
            --max-wait-hours 48.0
    done
fi
```

### Checkpoint/Resume Pattern

For very large batches, implement checkpointing:

```bash
#!/bin/bash
# batch_with_checkpoints.sh

CALIBRATOR_FILE="calibrators.txt"
COMPLETED_FILE="completed.txt"
FAILED_FILE="failed.txt"

# Load completed list
if [ -f "$COMPLETED_FILE" ]; then
    COMPLETED=$(cat "$COMPLETED_FILE")
else
    COMPLETED=""
fi

while IFS= read -r cal; do
    [[ -z "$cal" || "$cal" =~ ^# ]] && continue

    # Skip if already completed
    if echo "$COMPLETED" | grep -q "^${cal}$"; then
        echo "Skipping already completed: $cal"
        continue
    fi

    echo "Processing: $cal"

    if /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
        --calibrator "$cal" \
        --timespan-minutes 50; then
        echo "$cal" >> "$COMPLETED_FILE"
    else
        echo "$cal" >> "$FAILED_FILE"
    fi
done < "$CALIBRATOR_FILE"
```

---

## Best Practices

### 1. Resource Management

- **Limit parallel jobs:** Don't run more than 2-3 mosaics simultaneously (each
  uses significant CPU/memory)
- **Monitor disk space:** Mosaics can be 100+ MB each
- **Use `--no-wait` for parallel:** Prevents blocking on publishing

### 2. Time Management

- **Use `--max-wait-hours`:** Set reasonable timeouts (24-48 hours)
- **Monitor long-running jobs:** Check logs periodically
- **Plan for failures:** Allow time for retries

### 3. Logging

- **Redirect output:** Always log to files for batch runs
- **Use timestamps:** Include timestamps in log filenames
- **Separate logs:** One log file per calibrator/mosaic

### 4. Database Considerations

- **Single orchestrator per process:** Don't share `MosaicOrchestrator`
  instances across processes
- **Check database locks:** SQLite may lock under heavy parallel load
- **Monitor database size:** `products.sqlite3` grows with each mosaic

### 5. Production Batch Script Template

```bash
#!/bin/bash
# production_batch_mosaics.sh
# Comprehensive batch processing script

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
CALIBRATOR_FILE="${1:-calibrators.txt}"
TIMESPAN="${2:-50}"
LOG_DIR="logs/$(date +%Y%m%d_%H%M%S)"
MAX_PARALLEL=2

# Setup
mkdir -p "$LOG_DIR"
cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/src

# Verify environment
if ! test -x /opt/miniforge/envs/casa6/bin/python; then
    echo "ERROR: casa6 Python not found"
    exit 1
fi

# Process calibrators
declare -a PIDS=()
while IFS= read -r cal; do
    [[ -z "$cal" || "$cal" =~ ^# ]] && continue

    # Wait for slot
    while [ ${#PIDS[@]} -ge $MAX_PARALLEL ]; do
        for pid in "${!PIDS[@]}"; do
            if ! kill -0 "${PIDS[$pid]}" 2>/dev/null; then
                unset PIDS[$pid]
            fi
        done
        PIDS=("${PIDS[@]}")  # Reindex
        sleep 5
    done

    # Launch job
    (
        echo "Starting: $cal at $(date)"
        /opt/miniforge/envs/casa6/bin/python scripts/mosaic/create_mosaic_centered.py \
            --calibrator "$cal" \
            --timespan-minutes "$TIMESPAN" \
            --no-wait \
            > "$LOG_DIR/mosaic_${cal}.log" 2>&1
        echo "Finished: $cal at $(date) (exit: $?)"
    ) &

    PIDS+=($!)
done < "$CALIBRATOR_FILE"

# Wait for completion
for pid in "${PIDS[@]}"; do
    wait "$pid"
done

echo "Batch processing complete. Logs in: $LOG_DIR"
```

---

## Troubleshooting

### Common Issues

1. **"Could not find transit window"**
   - Verify calibrator name is correct
   - Check that data exists for that calibrator
   - Query available transits programmatically

2. **"Only N MS files available, need at least 3"**
   - Insufficient data in time window
   - Try longer `--timespan-minutes` or different calibrator

3. **Database locked errors**
   - Too many parallel processes accessing SQLite
   - Reduce `MAX_PARALLEL` or use sequential processing

4. **Disk space errors**
   - Check `/stage/` and `/data/` disk usage
   - Clean up old staging files: `find /stage -name "*.ms" -mtime +7 -type d`

5. **Timeout errors**
   - Increase `--max-wait-hours`
   - Check if calibration/imaging is stuck
   - Review logs for specific failure points

### Debug Mode

Run with verbose logging:

```bash
PYTHONPATH=/data/dsa110-contimg/src \
/opt/miniforge/envs/casa6/bin/python -u scripts/mosaic/create_mosaic_centered.py \
    --calibrator 0834+555 \
    --timespan-minutes 50 \
    2>&1 | tee debug_mosaic.log
```

---

## See Also

- create_mosaic_centered.py -
  Base script implementation
- Mosaic Orchestrator - Core
  orchestrator class
- [Batch Mode Guide](batch_mode_guide.md) - General batch processing patterns
- [Mosaic Quickstart](mosaic.md) - Single mosaic creation tutorial

---

## Workflow Summary

The `create_mosaic_centered.py` script orchestrates a 12-phase pipeline:

1. **Initialize** - Database connections, calibrator service
2. **Transit Discovery** - Find earliest transit, calculate window
3. **MS Availability** - Query/convert HDF5 to MS if needed
4. **Group Formation** - Create mosaic group, register in DB
5. **Calibration Solving** - Solve BP/GP tables (CASA)
6. **Calibration Application** - Apply to all MS files
7. **Imaging** - Image each calibrated MS (WSClean/tclean)
8. **Mosaic Creation** - Plan grid, combine tiles (PB-weighted)
9. **Validation/QA** - Automatic tile consistency checks
10. **Publishing** - Move to `/data/.../products/mosaics/`
11. **Wait Loop** - Poll until published (if `--no-wait` not set)
12. **Completion** - Return published path or error

Batch mode simply repeats this workflow for multiple calibrators, with options
for sequential or parallel execution.
