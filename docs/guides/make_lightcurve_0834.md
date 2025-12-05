---

## **How to Create a Lightcurve of 0834+555 from Multiple Transits**

Great news! The repository **already has a dedicated script** for exactly this: `scripts/process_0834_lightcurve.py`. Here's how to use it with both ABSURD and the batch processor:

---

## **Quick Answer: Use the Existing Lightcurve Script**

```bash
conda activate casa6
cd /data/dsa110-contimg

# The script processes 10 transits automatically
python scripts/process_0834_lightcurve.py
```

This script will:

1. ✅ Convert UVH5 → MS (batch processor)
2. ✅ Calibrate each MS
3. ✅ Image each transit
4. ✅ Perform forced photometry
5. ✅ Generate lightcurve plot with error bars

**Output**:

- `/stage/dsa110-contimg/images/0834_lightcurve/0834_lightcurve.png`
- `/stage/dsa110-contimg/images/0834_lightcurve/0834_measurements.json`

---

## **Option 1: Using the Existing Script (Recommended)**

### **Step 1: Find Transit Groups**

First, identify which transit data you have:

```python
from astropy.time import Time
from astropy.coordinates import SkyCoord
import sqlite3
import json

# 0834+555 coordinates
ra_deg = 128.7287  # 08h34m54.9s
dec_deg = 55.5725  # +55d34m21s

# Query your HDF5 file index for available data
db_path = "state/db/pipeline.sqlite3"
conn = sqlite3.connect(db_path)

# Find all groups within ±2.25 min of each transit
# (You'd calculate transits first using pointing.transit module)

# Example: Get all groups with 0834 data
query = """
SELECT DISTINCT group_id, obstime_unix, datetime(obstime_unix, 'unixepoch') as obs_time
FROM ingest_queue
WHERE obstime_unix BETWEEN ? AND ?
ORDER BY obstime_unix;
"""

# Save selected groups
selected_groups = []  # List of dicts with {timestamp, files, delta_from_transit_min}

with open('/tmp/selected_transit_groups.json', 'w') as f:
    json.dump(selected_groups, f, indent=2)
```

### **Step 2: Run the Lightcurve Pipeline**

```bash
# The script reads /tmp/selected_transit_groups.json
python scripts/process_0834_lightcurve.py
```

**What it does**:

- Converts each transit group to MS using `write_ms_from_subbands` (batch processor)
- Calibrates with fast settings (`--timebin 30s --chanbin 4`)
- Images with development-tier quality for speed
- Measures forced photometry at known 0834 position
- Plots lightcurve with statistics

---

## **Option 2: Using ABSURD for Automated Processing**

ABSURD can process transits automatically as they arrive:

### **Step 1: Configure ABSURD for 0834 Monitoring**

Create a custom processing configuration:

```python
# scripts/absurd_0834_config.json
{
  "sources": [
    {
      "name": "0834+555",
      "ra_deg": 128.7287,
      "dec_deg": 55.5725,
      "flux_jy": 5.0,
      "track_lightcurve": true,
      "imaging": {
        "imsize": 512,
        "quality_tier": "development",
        "forced_photometry": true
      }
    }
  ],
  "transit_window_min": 2.25,
  "output_dir": "/stage/dsa110-contimg/0834_monitoring"
}
```

### **Step 2: Submit Jobs via ABSURD API**

```python
from dsa110_contimg.absurd.client import AbsurdClient

client = AbsurdClient()

# Submit conversion jobs for each transit
for transit_time in transit_times:
    job_id = client.submit_job({
        "type": "conversion",
        "start_time": transit_time - timedelta(minutes=2.25),
        "end_time": transit_time + timedelta(minutes=2.25),
        "priority": "high",
        "callback": {
            "on_complete": "chain_imaging"  # Auto-chain to imaging
        }
    })

    print(f"Submitted job {job_id} for transit {transit_time}")
```

### **Step 3: Monitor Progress via Dashboard**

```bash
# Check ABSURD worker status
systemctl status absurd-worker@*

# Or via web dashboard
firefox http://localhost:8000/absurd/jobs
```

---

## **Option 3: Manual Batch Processing (Full Control)**

For complete control over each step:

### **Step 1: Batch Convert All Transits**

```bash
# Create a list of time windows
cat > transit_windows.txt << EOF
2024-11-01T12:34:00 2024-11-01T12:38:30
2024-11-02T12:30:15 2024-11-02T12:34:45
2024-11-03T12:26:30 2024-11-03T12:31:00
EOF

# Convert each window in parallel
while read START END; do
  python -m dsa110_contimg.execution.cli convert \
    --input-dir /data/incoming \
    --output-dir /stage/dsa110-contimg/ms/0834_transits \
    --start-time "$START" \
    --end-time "$END" \
    --group-id "0834_transit_$(date -d "$START" +%Y%m%d_%H%M%S)" \
    --execution-mode subprocess \
    --timeout 1800 &
done < transit_windows.txt

wait  # Wait for all conversions to complete
```

### **Step 2: Batch Calibrate**

```bash
for MS in /stage/dsa110-contimg/ms/0834_transits/*.ms; do
  python -m dsa110_contimg.calibration.cli calibrate \
    --ms "$MS" \
    --field 0 \
    --fast \
    --timebin 30s \
    --chanbin 4 \
    --no-plot-bandpass &
done
wait
```

### **Step 3: Batch Image**

```bash
for MS in /stage/dsa110-contimg/ms/0834_transits/*.ms; do
  BASENAME=$(basename "$MS" .ms)
  python -m dsa110_contimg.imaging.cli image \
    --ms "$MS" \
    --imagename "/stage/dsa110-contimg/images/0834_transits/$BASENAME" \
    --imsize 512 \
    --niter 500 \
    --quality-tier development \
    --phasecenter "J2000 08h34m54.9s +55d34m21.1s" &
done
wait
```

### **Step 4: Extract Photometry & Plot Lightcurve**

```python
from dsa110_contimg.photometry.forced import measure_forced_peak
from astropy.time import Time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 0834+555 position
ra_deg, dec_deg = 128.7287, 55.5725

# Measure all transits
measurements = []
for fits_path in sorted(Path('/stage/dsa110-contimg/images/0834_transits').glob('*.pbcor.fits')):
    result = measure_forced_peak(
        str(fits_path),
        ra_deg, dec_deg,
        box_size_pix=7
    )

    # Extract MJD from filename
    timestamp_str = fits_path.stem.split('_')[2]  # Assuming naming convention
    mjd = Time(timestamp_str).mjd

    measurements.append({
        'mjd': mjd,
        'flux_jy': result.peak_jyb,
        'flux_err_jy': result.peak_err_jyb
    })

# Sort by time
measurements.sort(key=lambda x: x['mjd'])

# Plot lightcurve
mjds = [m['mjd'] for m in measurements]
fluxes = [m['flux_jy'] * 1000 for m in measurements]  # Convert to mJy
errors = [m['flux_err_jy'] * 1000 for m in measurements]

plt.figure(figsize=(12, 6))
plt.errorbar(mjds, fluxes, yerr=errors, fmt='o', capsize=3, markersize=8)
plt.axhline(np.mean(fluxes), color='r', linestyle='--', label=f'Mean: {np.mean(fluxes):.1f} mJy')
plt.xlabel('MJD')
plt.ylabel('Flux Density (mJy)')
plt.title('0834+555 Lightcurve from DSA-110')
plt.grid(True, alpha=0.3)
plt.legend()
plt.savefig('/stage/dsa110-contimg/images/0834_transits/lightcurve.png', dpi=150)
print("Lightcurve saved!")
```

---

## **Comparison: ABSURD vs Batch Processor**

| Feature         | ABSURD                       | Batch Processor (`execution.cli`) |
| --------------- | ---------------------------- | --------------------------------- |
| **Use Case**    | Automated streaming pipeline | Manual batch processing           |
| **Speed**       | Processes as data arrives    | Process historical data           |
| **Control**     | Config-driven, less manual   | Full CLI control per job          |
| **Parallelism** | Worker pool auto-manages     | Must script parallelism           |
| **Monitoring**  | Web dashboard + database     | CLI output + logs                 |
| **Best For**    | Production monitoring        | Historical analysis, debugging    |

---

## **Recommended Workflow**

**For existing transit data**:

```bash
# 1. Use existing script (fastest)
python scripts/process_0834_lightcurve.py

# 2. Or batch process manually
# See Option 3 above for full control
```

**For future monitoring**:

```bash
# Configure ABSURD to auto-process 0834 transits
# See Option 2 above
```

---

## **Expected Output**

After processing ~10 transits, you'll get:

```
/stage/dsa110-contimg/images/0834_lightcurve/
├── 0834_lightcurve.png          # Lightcurve plot
├── 0834_measurements.json        # All measurements
├── 0834_2024-11-01T12-34-00.ms  # Individual MSs
├── 0834_2024-11-01T12-34-00.pbcor.fits
└── ...
```

**Sample lightcurve statistics**:

```
Mean flux: 4850.2 mJy
Std dev:   125.3 mJy (~2.6% variability)
N points:  10
MJD range: 60252.523 - 60261.519
```

The entire workflow takes **~5-10 minutes per transit** on modern hardware!
