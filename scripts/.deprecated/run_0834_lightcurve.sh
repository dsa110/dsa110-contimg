#!/bin/bash
set -e

# 0834+555 Lightcurve End-to-End Script
# Usage: ./scripts/run_0834_lightcurve.sh [num_transits]

NUM_TRANSITS=${1:-10}

echo "============================================================"
echo "0834+555 Lightcurve Pipeline"
echo "============================================================"
echo "Will process $NUM_TRANSITS transits"
echo ""

# Activate environment
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

cd /data/dsa110-contimg

# Step 1: Find transits with data and create JSON
echo "[Step 1/2] Finding transits with available data..."
python - <<EOF
import json
from datetime import datetime, timedelta
from pathlib import Path
from astropy.time import Time

from dsa110_contimg.calibration.transit import upcoming_transits
from dsa110_contimg.database.hdf5_index import query_subband_groups

# 0834+555 coordinates
ra_deg = 128.7287

# Data availability window
data_start = datetime(2025, 10, 2)
data_end = datetime(2025, 11, 18, 23, 59, 59)

# Calculate transits
delta_days = (data_end - data_start).days + 1
start_time = Time(data_start)
transits = upcoming_transits(ra_deg, start_time=start_time, n=int(delta_days * 1.05))
valid_transits = [t for t in transits if data_start <= t.datetime <= data_end]

print(f"Found {len(valid_transits)} transits in date range")

# Find transits with data
db_path = "/data/incoming/hdf5_file_index.sqlite3"
matches = []
window_minutes = 10.0

for t in valid_transits:
    window_start = (t.datetime - timedelta(minutes=window_minutes)).isoformat()
    window_end = (t.datetime + timedelta(minutes=window_minutes)).isoformat()
    
    groups = query_subband_groups(
        db_path=db_path,
        start_time=window_start,
        end_time=window_end,
        cluster_tolerance_s=60.0,
    )
    
    complete = [g for g in groups if len(g) == 16]
    
    if complete:
        # Pick the first complete group
        best_group = complete[0]
        delta_from_transit_min = (
            datetime.fromisoformat(Path(best_group[0]).stem.split('_sb')[0]) - t.datetime
        ).total_seconds() / 60.0
        
        matches.append({
            'timestamp': t.iso,
            'delta_from_transit_min': delta_from_transit_min,
            'files': best_group
        })
        print(f"  ✓ {t.iso}: {len(complete)} groups available")
        
        if len(matches) >= ${NUM_TRANSITS}:
            break

print(f"\nSelected {len(matches)} transits with complete data")

# Save to JSON
output_file = '/tmp/selected_transit_groups.json'
with open(output_file, 'w') as f:
    json.dump(matches, f, indent=2)

print(f"Saved transit list to {output_file}")
EOF

# Check if we have transits
if [ ! -f /tmp/selected_transit_groups.json ]; then
    echo "ERROR: Failed to create transit list"
    exit 1
fi

NUM_FOUND=$(python -c "import json; print(len(json.load(open('/tmp/selected_transit_groups.json'))))")
echo "Found $NUM_FOUND transits with complete 16-subband data"
echo ""

if [ "$NUM_FOUND" -eq 0 ]; then
    echo "ERROR: No transits found with data!"
    exit 1
fi

# Step 2: Run the pipeline
echo "[Step 2/2] Running lightcurve pipeline..."
echo ""
python /data/dsa110-contimg/scripts/process_0834_lightcurve.py

echo ""
echo "============================================================"
echo "COMPLETE"
echo "============================================================"
echo "Results in: /stage/dsa110-contimg/images/0834_lightcurve/"
echo "  - 0834_lightcurve.png (plot)"
echo "  - 0834_measurements.json (data)"
