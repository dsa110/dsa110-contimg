#!/bin/bash
# Index HDF5 files from /data/incoming/ into hdf5.sqlite3
# This enables fast database queries instead of filesystem scans

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default paths
INPUT_DIR="${CONTIMG_INPUT_DIR:-/data/incoming}"
HDF5_DB="${HDF5_DB_PATH:-/data/dsa110-contimg/state/hdf5.sqlite3}"
MAX_FILES="${MAX_FILES:-}"  # No limit by default
FORCE_RESCAN="${FORCE_RESCAN:-false}"

echo ":card_index:  HDF5 File Indexing Script"
echo "============================"
echo ""
echo "Input directory: $INPUT_DIR"
echo "HDF5 database:   $HDF5_DB"
echo "Force rescan:    $FORCE_RESCAN"

if [ -n "$MAX_FILES" ]; then
    echo "Max files:       $MAX_FILES (development mode)"
else
    echo "Max files:       unlimited (full scan)"
fi

echo ""

# Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo ":cross: Error: Input directory does not exist: $INPUT_DIR"
    exit 1
fi

# Count total HDF5 files
echo ":chart: Counting HDF5 files in $INPUT_DIR..."
TOTAL_FILES=$(find "$INPUT_DIR" -name "*.hdf5" -type f 2>/dev/null | wc -l)
echo "   Found: $TOTAL_FILES HDF5 files"
echo ""

# Estimate time
if [ -n "$MAX_FILES" ]; then
    FILES_TO_PROCESS=$MAX_FILES
else
    FILES_TO_PROCESS=$TOTAL_FILES
fi

ESTIMATED_SECONDS=$((FILES_TO_PROCESS / 100))  # ~100 files/sec estimate
ESTIMATED_MINUTES=$((ESTIMATED_SECONDS / 60))

echo ":stopwatch:  Estimated time: ~$ESTIMATED_MINUTES minutes for $FILES_TO_PROCESS files"
echo ""

# Build command (use casa6 Python if available, else system Python)
if [ -x "/opt/miniforge/envs/casa6/bin/python" ]; then
    PYTHON="/opt/miniforge/envs/casa6/bin/python"
else
    PYTHON="python3"
fi

CMD="$PYTHON -m dsa110_contimg.database.cli index-hdf5"
CMD="$CMD --input-dir $INPUT_DIR"
CMD="$CMD --hdf5-db $HDF5_DB"

if [ "$FORCE_RESCAN" = "true" ]; then
    CMD="$CMD --force"
fi

if [ -n "$MAX_FILES" ]; then
    CMD="$CMD --max-files $MAX_FILES"
fi

# Run indexing
echo ":rocket: Starting indexing..."
echo "   Command: $CMD"
echo ""

cd "$PROJECT_ROOT"

# Run with unbuffered output for real-time progress
PYTHONUNBUFFERED=1 $CMD

echo ""
echo ":check: Indexing complete!"
echo ""

# Show summary
if [ -f "$HDF5_DB" ]; then
    echo ":chart_up: Database summary:"
    python3 -c "
import sqlite3
conn = sqlite3.connect('$HDF5_DB')
cursor = conn.execute('SELECT COUNT(*) FROM hdf5_file_index WHERE stored = 1')
total = cursor.fetchone()[0]
print(f'   Total indexed files: {total:,}')

cursor = conn.execute('SELECT MIN(timestamp_mjd), MAX(timestamp_mjd) FROM hdf5_file_index WHERE stored = 1')
min_mjd, max_mjd = cursor.fetchone()
if min_mjd and max_mjd:
    print(f'   Time range: MJD {min_mjd:.2f} to {max_mjd:.2f}')
    print(f'   Duration: {max_mjd - min_mjd:.2f} days')
"
    echo ""
fi

echo ":party_popper: Done!"
