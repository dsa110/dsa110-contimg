# Finding and Imaging Peak Transit of 0834+555

Based on the repository's architecture, here's a comprehensive workflow to find and process the earliest ~4.5-min group containing the peak transit of calibrator 0834+555:

---

## Step 1: Find Transit Time for 0834+555

The pipeline has a **precomputed calibrator transit database**. Check if 0834+555 transits are already calculated:

```bash
conda activate casa6
cd /data/dsa110-contimg

# Query the precomputed transits
sqlite3 state/db/pipeline.sqlite3 "
SELECT
    source_name,
    transit_mjd,
    datetime(transit_mjd + 2400000.5 - 2440587.5, 'unixepoch') as transit_utc
FROM calibrator_transits
WHERE source_name LIKE '%0834%' OR source_name LIKE '%J0834%'
ORDER BY transit_mjd
LIMIT 10;
"
```

**If not precomputed**, calculate transit using the pointing module:

```python
from dsa110_contimg.pointing.transit import calculate_transit_time
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u

# 0834+555 coordinates (J2000)
source = SkyCoord(ra="08h34m54.9s", dec="+55d34m21s", frame='icrs')

# DSA-110 location (Owens Valley)
dsa_lat = 37.233386 * u.deg
dsa_lon = -118.283401 * u.deg

# Find transits in a date range
start_time = Time('2024-01-01T00:00:00', format='isot', scale='utc')
end_time = Time('2025-12-04T00:00:00', format='isot', scale='utc')

transits = []
current_time = start_time
while current_time < end_time:
    transit_mjd = calculate_transit_time(
        source,
        current_time.mjd,
        latitude=dsa_lat.value,
        longitude=dsa_lon.value
    )
    transits.append(transit_mjd)
    current_time = Time(transit_mjd + 1, format='mjd')  # Next day

# Get earliest transit
earliest_transit_mjd = min(transits)
earliest_transit_utc = Time(earliest_transit_mjd, format='mjd').isot
print(f"Earliest transit: {earliest_transit_utc}")
```

---

## Step 2: Find Data Groups Near Peak Transit

Search the HDF5 file index for groups within ±2.25 minutes of transit:

```python
from astropy.time import Time
import sqlite3

# Transit time (from Step 1)
transit_mjd = earliest_transit_mjd
transit_unix = (transit_mjd - 40587) * 86400  # Convert MJD to Unix timestamp

# Search window: ±2.25 min = ±135 seconds
window_sec = 135

db_path = "state/db/pipeline.sqlite3"
conn = sqlite3.connect(db_path)

# Query for groups near transit
query = """
SELECT
    group_id,
    obstime_unix,
    datetime(obstime_unix, 'unixepoch') as obs_utc,
    ABS(obstime_unix - ?) as time_diff_sec,
    num_subbands,
    state,
    processing_stage
FROM ingest_queue
WHERE ABS(obstime_unix - ?) <= ?
ORDER BY time_diff_sec ASC
LIMIT 5;
"""

cursor = conn.execute(query, (transit_unix, transit_unix, window_sec))
groups = cursor.fetchall()

for row in groups:
    print(f"Group: {row[0]}, Time: {row[2]}, Offset: {row[3]:.1f}s, "
          f"Subbands: {row[4]}, State: {row[5]}, Stage: {row[6]}")

# Get the earliest group with peak transit
target_group_id = groups[0][0] if groups else None
conn.close()

print(f"\nTarget group for processing: {target_group_id}")
```

**Alternative: Query by file timestamp directly**

```bash
# If files are in /data/incoming/
cd /data/incoming

# Find files near transit time (example: 2024-03-15 12:34:00)
find . -name "*2024-03-15T12:3*_sb*.hdf5" | head -20

# Or search HDF5 file index
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 "
SELECT
    filepath,
    obstime_unix,
    datetime(obstime_unix, 'unixepoch') as obs_utc
FROM hdf5_file_index
WHERE obstime_unix BETWEEN ${transit_unix - 135} AND ${transit_unix + 135}
ORDER BY obstime_unix
LIMIT 20;
"
```

---

## Step 3: Locate Existing MS or Convert from UVH5

### Option A: Check if MS Already Exists

```python
import sqlite3

db_path = "state/db/pipeline.sqlite3"
conn = sqlite3.connect(db_path)

# Query ms_index for this group
query = """
SELECT
    ms_path,
    stage,
    calibrated,
    imaged
FROM ms_index
WHERE group_id = ?
"""

cursor = conn.execute(query, (target_group_id,))
ms_record = cursor.fetchone()
conn.close()

if ms_record:
    ms_path = ms_record[0]
    print(f"MS already exists: {ms_path}")
    print(f"Stage: {ms_record[1]}, Calibrated: {ms_record[2]}, Imaged: {ms_record[3]}")
else:
    print("MS does not exist - need to convert from UVH5")
```

### Option B: Convert UVH5 to MS

If the MS doesn't exist, convert using the orchestrator:

```bash
conda activate casa6

# Get list of HDF5 files for this group
sqlite3 state/db/pipeline.sqlite3 "
SELECT filepath
FROM hdf5_file_index
WHERE group_id = '${target_group_id}'
ORDER BY subband_id;
" > /tmp/hdf5_files.txt

# Convert using direct-subband writer
python -m dsa110_contimg.conversion.hdf5_orchestrator \
  --input-files $(cat /tmp/hdf5_files.txt | tr '\n' ' ') \
  --output-ms /stage/dsa110-contimg/ms/0834_transit_${target_group_id}.ms \
  --staging-dir /dev/shm/staging_0834 \
  --writer-type direct-subband \
  --log-level INFO
```

**Or use the CLI wrapper:**

```bash
python -m dsa110_contimg.conversion.cli groups \
  --group-id ${target_group_id} \
  --output-dir /stage/dsa110-contimg/ms \
  --staging tmpfs
```

---

## Step 4: Calibrate the MS

### Check for Existing Calibration

```python
# Query calibration_tables for solutions near this time
query = """
SELECT
    table_path,
    source_name,
    valid_from_mjd,
    valid_until_mjd
FROM calibration_tables
WHERE source_name LIKE '%0834%'
  AND valid_from_mjd <= ?
  AND valid_until_mjd >= ?
ORDER BY valid_from_mjd DESC
LIMIT 1;
"""

cursor = conn.execute(query, (transit_mjd, transit_mjd))
caltable = cursor.fetchone()
```

### Generate New Calibration Solutions

If no suitable caltable exists:

```python
from dsa110_contimg.calibration.calibration import calibrate_ms

ms_path = "/stage/dsa110-contimg/ms/0834_transit_${target_group_id}.ms"
caltable_dir = "/stage/dsa110-contimg/caltables"

# Run calibration
caltable_paths = calibrate_ms(
    ms_path=ms_path,
    output_dir=caltable_dir,
    reference_antenna='ea01',  # Or appropriate DSA-110 antenna
    solve_bandpass=True,
    solve_gain=True,
    solint='inf',  # For calibrator, solve for full scan
    refant='ea01'
)

print(f"Generated caltables: {caltable_paths}")

# Register in database
from dsa110_contimg.database.registry import register_caltable

for caltable_path in caltable_paths:
    register_caltable(
        table_path=caltable_path,
        source_name='0834+555',
        valid_from_mjd=transit_mjd - 0.1,  # ±2.4 hours validity
        valid_until_mjd=transit_mjd + 0.1
    )
```

### Apply Calibration

```python
from dsa110_contimg.calibration.applycal import apply_calibration

apply_calibration(
    ms_path=ms_path,
    caltable_paths=caltable_paths,
    gaintable=caltable_paths['G'],  # Gain table
    bandpass=caltable_paths['B'],   # Bandpass table
    interp='linear',
    applymode='calflag'
)

print(f"Calibration applied to {ms_path}")
```

---

## Step 5: Image the Calibrated MS

### Quick Imaging with WSClean

```bash
conda activate casa6

MS_PATH="/stage/dsa110-contimg/ms/0834_transit_${target_group_id}.ms"
IMG_OUT="/stage/dsa110-contimg/images/0834_transit_${target_group_id}"

# Fast imaging with WSClean
wsclean \
  -size 2048 2048 \
  -scale 1asec \
  -weight briggs 0.5 \
  -niter 1000 \
  -auto-threshold 3 \
  -mgain 0.8 \
  -data-column CORRECTED_DATA \
  -name ${IMG_OUT} \
  ${MS_PATH}

# Output: ${IMG_OUT}-image.fits
```

### Or Use Pipeline Imaging Module

```python
from dsa110_contimg.imaging.fast_imaging import image_ms_wsclean

image_path = image_ms_wsclean(
    ms_path=ms_path,
    output_dir="/stage/dsa110-contimg/images",
    imsize=2048,
    cell='1arcsec',
    robust=0.5,
    niter=1000,
    threshold='3mJy',
    data_column='CORRECTED_DATA',
    prefix=f'0834_transit_{target_group_id}'
)

print(f"Image created: {image_path}")

# Register in database
from dsa110_contimg.database.registry import register_image

register_image(
    image_path=image_path,
    ms_path=ms_path,
    image_type='continuum',
    frequency_hz=1.4e9,  # Central frequency
    bandwidth_hz=250e6    # DSA-110 bandwidth
)
```

---

## Step 6: Forced Photometry at 0834+555 Position

### Extract Flux at Known Position

```python
from dsa110_contimg.photometry.forced import measure_forced_photometry
from astropy.coordinates import SkyCoord
from astropy.io import fits
import numpy as np

# 0834+555 position
source_coord = SkyCoord(ra="08h34m54.9s", dec="+55d34m21s", frame='icrs')

image_path = f"{IMG_OUT}-image.fits"

# Load image
with fits.open(image_path) as hdul:
    image_data = hdul[0].data
    header = hdul[0].header

    # Get pixel coordinates
    from astropy.wcs import WCS
    wcs = WCS(header)
    px, py = wcs.world_to_pixel(source_coord)

    # Define aperture (e.g., 5-pixel radius)
    aperture_radius = 5
    y, x = np.ogrid[-py:image_data.shape[0]-py, -px:image_data.shape[1]-px]
    mask = x**2 + y**2 <= aperture_radius**2

    # Measure flux
    source_flux = np.sum(image_data[mask])

    # Estimate noise from off-source region
    # Use corners of image
    corner_region = image_data[:100, :100]
    rms_noise = np.std(corner_region)

    snr = source_flux / rms_noise

    print(f"Source flux: {source_flux:.6f} Jy")
    print(f"RMS noise: {rms_noise:.6f} Jy/beam")
    print(f"SNR: {snr:.1f}")
```

### Or Use Pipeline Photometry Module

```python
from dsa110_contimg.photometry.photometry import perform_forced_photometry

results = perform_forced_photometry(
    image_path=image_path,
    source_coord=source_coord,
    aperture_radius=5.0,  # pixels
    local_background=True,
    background_annulus=(10, 15)  # inner, outer radius in pixels
)

print(f"Peak flux: {results['peak_flux']:.6f} Jy/beam")
print(f"Integrated flux: {results['integrated_flux']:.6f} Jy")
print(f"RMS: {results['rms']:.6f} Jy/beam")
print(f"SNR: {results['snr']:.1f}")

# Store in database
from dsa110_contimg.database.registry import register_photometry

register_photometry(
    image_id=image_path,
    source_name='0834+555',
    ra_deg=source_coord.ra.deg,
    dec_deg=source_coord.dec.deg,
    peak_flux=results['peak_flux'],
    integrated_flux=results['integrated_flux'],
    rms_noise=results['rms'],
    measurement_time_mjd=transit_mjd
)
```

---

## Complete End-to-End Script

Here's a consolidated script that automates the entire workflow:

```python
#!/usr/bin/env python
"""
Find and process earliest 0834+555 transit data.
"""
import sqlite3
from pathlib import Path
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u

from dsa110_contimg.pointing.transit import calculate_transit_time
from dsa110_contimg.conversion.hdf5_orchestrator import convert_group
from dsa110_contimg.calibration.calibration import calibrate_ms
from dsa110_contimg.calibration.applycal import apply_calibration
from dsa110_contimg.imaging.fast_imaging import image_ms_wsclean
from dsa110_contimg.photometry.forced import measure_forced_photometry

# Configuration
SOURCE_NAME = '0834+555'
SOURCE_COORD = SkyCoord(ra="08h34m54.9s", dec="+55d34m21s", frame='icrs')
DSA_LAT = 37.233386 * u.deg
DSA_LON = -118.283401 * u.deg
DB_PATH = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
OUTPUT_BASE = Path("/stage/dsa110-contimg")

def find_earliest_transit():
    """Find earliest transit time."""
    start_time = Time('2024-01-01', format='isot')
    end_time = Time.now()

    transits = []
    current = start_time
    while current < end_time:
        transit_mjd = calculate_transit_time(
            SOURCE_COORD, current.mjd,
            latitude=DSA_LAT.value,
            longitude=DSA_LON.value
        )
        transits.append(transit_mjd)
        current = Time(transit_mjd + 1, format='mjd')

    return min(transits)

def find_data_group(transit_mjd):
    """Find data group closest to transit."""
    transit_unix = (transit_mjd - 40587) * 86400
    window_sec = 135  # ±2.25 min

    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT group_id, obstime_unix, ABS(obstime_unix - ?) as diff
    FROM ingest_queue
    WHERE ABS(obstime_unix - ?) <= ?
    ORDER BY diff ASC
    LIMIT 1
    """
    cursor = conn.execute(query, (transit_unix, transit_unix, window_sec))
    result = cursor.fetchone()
    conn.close()

    if not result:
        raise ValueError(f"No data found near transit {transit_mjd}")

    return result[0]

def process_group(group_id, transit_mjd):
    """Convert, calibrate, image, and measure photometry."""

    # 1. Check for existing MS
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        "SELECT ms_path FROM ms_index WHERE group_id = ?",
        (group_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        ms_path = Path(result[0])
        print(f"Using existing MS: {ms_path}")
    else:
        # 2. Convert from UVH5
        print(f"Converting group {group_id}...")
        ms_path = OUTPUT_BASE / "ms" / f"{SOURCE_NAME}_{group_id}.ms"
        convert_group(
            group_id=group_id,
            output_ms=ms_path,
            staging_dir="/dev/shm/staging",
            writer_type="direct-subband"
        )

    # 3. Calibrate
    print("Calibrating MS...")
    caltable_dir = OUTPUT_BASE / "caltables"
    caltables = calibrate_ms(
        ms_path=str(ms_path),
        output_dir=str(caltable_dir),
        reference_antenna='ea01'
    )

    apply_calibration(
        ms_path=str(ms_path),
        caltable_paths=caltables
    )

    # 4. Image
    print("Imaging MS...")
    image_dir = OUTPUT_BASE / "images"
    image_path = image_ms_wsclean(
        ms_path=str(ms_path),
        output_dir=str(image_dir),
        imsize=2048,
        cell='1arcsec',
        robust=0.5,
        niter=1000,
        prefix=f"{SOURCE_NAME}_{group_id}"
    )

    # 5. Forced photometry
    print("Performing forced photometry...")
    results = measure_forced_photometry(
        image_path=image_path,
        source_coord=SOURCE_COORD,
        aperture_radius=5.0,
        local_background=True
    )

    print(f"\n=== Results for {SOURCE_NAME} ===")
    print(f"Transit MJD: {transit_mjd:.6f}")
    print(f"Group ID: {group_id}")
    print(f"MS: {ms_path}")
    print(f"Image: {image_path}")
    print(f"Peak flux: {results['peak_flux']:.6f} Jy/beam")
    print(f"Integrated flux: {results['integrated_flux']:.6f} Jy")
    print(f"SNR: {results['snr']:.1f}")

    return results

if __name__ == "__main__":
    # Execute workflow
    transit_mjd = find_earliest_transit()
    print(f"Earliest transit: {Time(transit_mjd, format='mjd').isot}")

    group_id = find_data_group(transit_mjd)
    print(f"Found data group: {group_id}")

    results = process_group(group_id, transit_mjd)
```

**Run the script:**

```bash
conda activate casa6
cd /data/dsa110-contimg
python scripts/process_0834_transit.py
```

---

## Quick Reference Command

For a rapid workflow using existing scripts:

```bash
conda activate casa6

# Use the existing 0834 processing script as a template
# (see scripts/process_0834_lightcurve.py and scripts/run_0834_pipeline.py)

python scripts/run_0834_pipeline.py \
  --find-earliest-transit \
  --source 0834+555 \
  --window 135 \
  --output-dir /stage/dsa110-contimg/0834_analysis
```

---

This workflow leverages the pipeline's:

- **Precomputed transit database** for rapid lookup
- **Unified SQLite database** for tracking all artifacts
- **Direct-subband writer** for fast parallel conversion
- **WSClean integration** for GPU-accelerated imaging
- **Forced photometry module** for precise flux measurement

The entire process—from finding the transit to measuring flux—can be completed in **~10-15 minutes** depending on data volume and system load.
