# DSA-110 Pipeline Walkthrough: ABSURD Ingestion to Bandpass Calibration

This document captures the complete workflow from raw HDF5 files through ABSURD
ingestion to MS creation, and the diagnostic commands used to analyze the resulting
Measurement Set for bandpass calibration.

---

## Phase 1: ABSURD Ingestion (HDF5 → MS Conversion)

### 1.1 Check Available Subband Groups

First, query the HDF5 file index to find complete 16-subband groups:

**Command:**

```bash
sqlite3 /data/incoming/hdf5_file_index.sqlite3 << 'EOF'
SELECT timestamp, COUNT(*) as n_subbands
FROM hdf5_file_index
WHERE timestamp >= '2025-11-18'
GROUP BY timestamp
HAVING n_subbands = 16
ORDER BY timestamp DESC
LIMIT 10;
EOF
```

### 1.2 Trigger ABSURD Ingestion via API

**Command:**

```bash
# Check ABSURD API status
curl -s http://localhost:8000/api/absurd/status | python3 -m json.tool

# Trigger ingestion for a specific timestamp
curl -X POST http://localhost:8000/api/absurd/ingest \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2025-11-18T23:50:25", "priority": "normal"}'
```

### 1.3 Monitor Ingestion Progress

**Command:**

```bash
# Watch the job queue
curl -s http://localhost:8000/api/absurd/jobs?status=pending | python3 -m json.tool

# Check specific job status
curl -s http://localhost:8000/api/absurd/jobs/{job_id} | python3 -m json.tool
```

### 1.4 Alternative: CLI Batch Conversion

For manual/batch conversion without ABSURD:

**Command:**

```bash
conda activate casa6
cd /data/dsa110-contimg/backend

# Convert a specific time range
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-18T23:00:00" \
    "2025-11-19T00:00:00"

# Or dry-run to preview
python -m dsa110_contimg.conversion.cli groups --dry-run \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-11-18T23:00:00" "2025-11-19T00:00:00"
```

### 1.5 Verify MS Creation

**Command:**

```bash
# Check the output MS exists
ls -lh /stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms/

# Quick validation with casacore
conda activate casa6 && python3 << 'EOF'
from casacore.tables import table
ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"
with table(ms, ack=False) as tb:
    print(f"Rows: {tb.nrows()}")
    print(f"Columns: {tb.colnames()}")
EOF
```

**Result:**

```
/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms (2.1 GB)
Rows: 1,787,904
```

---

## Phase 2: MS Structure Analysis

### Target MS

```
/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms (2.1 GB)
```

---

### 2.1 Spectral Window Structure

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(f"{ms}::SPECTRAL_WINDOW", ack=False) as tspw:
    n_spw = tspw.nrows()
    num_chan = tspw.getcol("NUM_CHAN")
    ref_freq = tspw.getcol("REF_FREQUENCY")
    chan_width = tspw.getcol("CHAN_WIDTH")

print(f"Number of SPWs: {n_spw}")
print(f"Channels per SPW: {num_chan[0]}")
print(f"Total channels: {np.sum(num_chan)}")
print(f"Frequency range: {ref_freq[0]/1e9:.4f} - {ref_freq[-1]/1e9:.4f} GHz")
print(f"Channel width: {chan_width[0][0]/1e3:.2f} kHz")
EOF
```

**Result:**
| Parameter | Value |
|-----------|-------|
| SPWs | 16 |
| Channels per SPW | 48 |
| Total channels | 768 |
| Frequency range | 1.3114 – 1.4986 GHz |
| Channel width | 244.14 kHz |
| Total bandwidth | 187.2 MHz |

---

### 2.2 Integration Time and Field Structure

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(ms, ack=False) as tb:
    exposure = tb.getcol("EXPOSURE")
    time_arr = tb.getcol("TIME")
    field_id = tb.getcol("FIELD_ID")

print(f"Exposure time: {np.unique(exposure)[0]:.2f} seconds")
print(f"Number of fields: {len(np.unique(field_id))}")
print(f"Total observation span: {(time_arr.max() - time_arr.min())/60:.2f} minutes")
EOF
```

**Result:**
| Parameter | Value |
|-----------|-------|
| Integration per field | 12.88 seconds |
| Number of fields | 24 |
| Total observation | 4.94 minutes (296 s) |

---

### 2.3 Baseline and Antenna Count

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(ms, ack=False) as tb:
    antenna1 = tb.getcol("ANTENNA1")
    antenna2 = tb.getcol("ANTENNA2")

n_ants = len(np.unique(np.concatenate([antenna1, antenna2])))
auto_mask = antenna1 == antenna2
n_cross = np.sum(~auto_mask)
unique_bl = len(set(zip(antenna1[~auto_mask], antenna2[~auto_mask])))

print(f"Antennas: {n_ants}")
print(f"Cross-correlation rows: {n_cross}")
print(f"Unique baseline pairs: {unique_bl}")
print(f"Expected (N*(N-1)/2): {n_ants * (n_ants - 1) // 2}")
EOF
```

**Result:**
| Parameter | Value |
|-----------|-------|
| Active antennas | 96 |
| Cross-correlations | 1,751,040 rows |
| Unique baselines | 4,560 |
| Baselines per antenna | 95 |

---

### 2.4 Amplitude Structure Across SPWs (Bandpass Shape)

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(ms, ack=False) as tb:
    data = tb.getcol("DATA")
    data_desc_id = tb.getcol("DATA_DESC_ID")
    antenna1 = tb.getcol("ANTENNA1")
    antenna2 = tb.getcol("ANTENNA2")

cross_mask = antenna1 != antenna2

print("SPW  | Low Edge | Center | High Edge | Edge/Center Ratio")
print("-" * 60)
for spw in [0, 7, 15]:
    mask = cross_mask & (data_desc_id == spw)
    spw_data = np.abs(data[mask])

    low_edge = np.mean(spw_data[:, 0:3, :])    # channels 0-2
    center = np.mean(spw_data[:, 22:26, :])    # channels 22-25
    high_edge = np.mean(spw_data[:, 45:48, :]) # channels 45-47

    print(f"SPW {spw:2d} | {low_edge:.4f}   | {center:.4f} | {high_edge:.4f}    | {low_edge/center:.2f} / {high_edge/center:.2f}")
EOF
```

**Result:**
| SPW | Low Edge | Center | High Edge | Low/Center | High/Center |
|-----|----------|--------|-----------|------------|-------------|
| 0 | 0.036 | 0.046 | 0.049 | 0.79 | 1.08 |
| 7 | 0.046 | 0.046 | 0.295 | 1.01 | 6.45 |
| 15 | 0.036 | 0.045 | 0.030 | 0.80 | 0.67 |

**Interpretation:**

- SPW 0: ~21% roll-off at low-frequency edge (typical bandpass)
- SPW 7: **Anomalous** 6.45× high edge — likely RFI or hardware issue
- SPW 15: ~20% roll-off at low edge, ~33% at high edge
- **Conclusion:** Each SPW has distinct bandpass shape; `combine_spw=False` is required

---

### 2.5 Field Directions and Calibrator Identification

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(f"{ms}::FIELD", ack=False) as tf:
    names = tf.getcol("NAME")
    phase_dir = tf.getcol("PHASE_DIR")

print("Field | Name                 | RA (h)   | Dec (°)")
print("-" * 55)
for i, (name, pd) in enumerate(zip(names, phase_dir)):
    ra_h = np.degrees(pd[0, 0]) / 15
    dec_deg = np.degrees(pd[0, 1])
    print(f"{i:5d} | {name:20s} | {ra_h:7.3f}  | {dec_deg:+7.3f}")
    if i >= 5:
        print("  ... (24 fields total)")
        break

print(f"\nObservation Declination: {np.degrees(phase_dir[0, 0, 1]):+.3f}°")
EOF
```

**Result:**

- All 24 fields named `meridian_icrs_t0` through `meridian_icrs_t23`
- RA range: 19.821h – 19.903h (meridian drift)
- **Observation Declination: +16.2°**

---

### 2.6 Nearest VLA Calibrators

**Command:**

```bash
sqlite3 /data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3 << 'EOF'
SELECT name, ra_deg/15 as ra_h, dec_deg, position_code
FROM calibrators
WHERE dec_deg BETWEEN 10 AND 25
AND ra_deg BETWEEN 290 AND 305
ORDER BY ABS(dec_deg - 16.2)
LIMIT 5;
EOF
```

**Result:**
| Name | RA (h) | Dec (°) | Separation | Code |
|------|--------|---------|------------|------|
| 2016+165 | 20.27 | +16.54 | ~0.4° | A |
| 1924+156 | 19.41 | +15.68 | ~0.7° | A |
| 1955+139 | 19.92 | +13.97 | ~2.4° | A |

**Conclusion:** This MS is at Dec +16.2° but the nearest calibrator (2016+165) is not
at the observed RA. This is a **science observation**, not a calibrator transit.

---

### 2.7 SNR Estimation for Bandpass Calibration

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(ms, ack=False) as tb:
    data = tb.getcol("DATA")
    field_id = tb.getcol("FIELD_ID")
    data_desc_id = tb.getcol("DATA_DESC_ID")
    antenna1 = tb.getcol("ANTENNA1")
    antenna2 = tb.getcol("ANTENNA2")

# Single field, single SPW, cross-correlations only
mask = (field_id == 12) & (data_desc_id == 8) & (antenna1 != antenna2)
field_data = np.abs(data[mask])

n_baselines = np.sum(mask)
per_chan_mean = np.mean(field_data, axis=(0, 2))
per_chan_std = np.std(field_data, axis=(0, 2))

# Per-baseline SNR (rough)
per_bl_snr = np.mean(per_chan_mean / per_chan_std)

# Antenna-based SNR (what CASA minsnr checks)
# SNR scales as sqrt(N_baselines_per_antenna) = sqrt(95)
antenna_snr = per_bl_snr * np.sqrt(95)

print(f"Baselines in selection: {n_baselines}")
print(f"Per-baseline SNR: {per_bl_snr:.2f}")
print(f"Antenna-based SNR: {antenna_snr:.2f}")
print(f"With 24 fields combined: {antenna_snr * np.sqrt(24):.2f}")
EOF
```

**Result:**
| Configuration | Per-Baseline SNR | Antenna SNR | vs minsnr=5.0 |
|---------------|------------------|-------------|---------------|
| Single field | ~0.7 | ~6.8 | Marginal ✓ |
| 24 fields combined | ~3.4 | ~33 | Comfortable ✓ |

**Key insight from Perplexity:** CASA's `minsnr` applies to **antenna-based solutions**,
not per-baseline. With 95 baselines per antenna, the aggregate SNR is ~10× higher than
per-baseline SNR.

---

### 2.8 Data Column Status

**Command:**

```bash
conda activate casa6 && python3 << 'EOF'
from casacore.tables import table

ms = "/stage/dsa110-contimg/ms/2025-11-18T23:50:25.ms"

with table(ms, ack=False) as tb:
    cols = tb.colnames()
    print(f"DATA: {'DATA' in cols}")
    print(f"CORRECTED_DATA: {'CORRECTED_DATA' in cols}")
    print(f"MODEL_DATA: {'MODEL_DATA' in cols}")
EOF
```

**Result:**

- DATA: ✓
- CORRECTED_DATA: ✗
- MODEL_DATA: ✗ (must be populated before bandpass calibration)

---

## Phase 3: Calibrator MS Creation

The science MS (`2025-11-18T23:50:25.ms`) is at Dec +16.2°. To calibrate it,
we need a separate MS containing a calibrator transit at the same declination,
within the validity window (~6 hours).

### 3.1 Find Best Calibrator for Declination

Use the precompute module to find the best calibrator for the observation's declination:

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import sys
sys.path.insert(0, "/data/dsa110-contimg/backend/src")
from dsa110_contimg.pipeline.precompute import get_pointing_tracker

tracker = get_pointing_tracker()
best = tracker.get_best_calibrator(dec_deg=16.2)
print(f"Best calibrator: {best.name}")
print(f"RA: {best.ra_deg:.4f}° ({best.ra_deg/15:.4f}h)")
print(f"Dec: {best.dec_deg:.4f}°")
EOF
```

**Result:**

| Parameter  | Value               |
| ---------- | ------------------- |
| Calibrator | 1911+161            |
| RA         | 287.993° (19.1995h) |
| Dec        | +16.196°            |

---

### 3.2 Calculate Calibrator Transit Time

Find when the calibrator transited the meridian:

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import sys
sys.path.insert(0, "/data/dsa110-contimg/backend/src")
from dsa110_contimg.calibration.transit import predict_calibrator_transit_by_coords
from datetime import datetime

# 1911+161 coordinates
ra_deg = 287.993
dec_deg = 16.196

# Find transit before our science observation
transit = predict_calibrator_transit_by_coords(
    ra_deg=ra_deg,
    dec_deg=dec_deg,
    from_time=datetime(2025, 11, 18, 23, 50, 0)
)
print(f"Transit UTC: {transit}")
EOF
```

**Result:** Transit at **2025-11-18T23:12:06 UTC**

---

### 3.3 Find Matching HDF5 Subband Group

Query the HDF5 file index to find a complete 16-subband group near the transit time:

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import sys
sys.path.insert(0, "/data/dsa110-contimg/backend/src")
from dsa110_contimg.database.hdf5_index import query_subband_groups

groups = query_subband_groups(
    db_path="/data/incoming/hdf5_file_index.sqlite3",
    start_time="2025-11-18T23:00:00",
    end_time="2025-11-18T23:30:00",
    cluster_tolerance_s=60.0,
)

complete = [g for g in groups if len(g) == 16]
print(f"Found {len(complete)} complete groups")
for g in complete:
    print(f"  {g[0].timestamp}")
EOF
```

**Result:** Found group at **2025-11-18T23:09:11** (3 minutes before transit, ideal)

---

### 3.4 Convert Calibrator HDF5 to MS

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import sys
sys.path.insert(0, "/data/dsa110-contimg/backend/src")
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

convert_subband_groups_to_ms(
    input_dir="/data/incoming",
    output_dir="/stage/dsa110-contimg/ms",
    start_time="2025-11-18T23:09:00",
    end_time="2025-11-18T23:10:00",
)
EOF
```

**Result:** Created `/stage/dsa110-contimg/ms/2025-11-18T23:09:11.ms` (2.1 GB)

---

### 3.5 Verify Calibrator is in MS

Confirm that 1911+161 is in one of the fields:

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import sys
sys.path.insert(0, "/data/dsa110-contimg/backend/src")
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog
import numpy as np

ms_path = "/stage/dsa110-contimg/ms/2025-11-18T23:09:11.ms"

result = select_bandpass_from_catalog(ms_path, search_radius_deg=0.5)
sel_str, indices, wflux, cal_info, peak_idx = result
name, ra_deg, dec_deg, flux_jy = cal_info

print(f"Calibrator: {name}")
print(f"Peak field: {peak_idx}")
print(f"Field selection: {sel_str}")
print(f"Peak weighted flux: {np.max(wflux):.4f}")
EOF
```

**Result:**

| Parameter     | Value                   |
| ------------- | ----------------------- |
| Calibrator    | 1911+161                |
| Peak field    | **19**                  |
| Beam response | 0.9996 (nearly on-axis) |
| Separation    | 0.03°                   |

---

### 3.6 Field Position Verification

Confirm the calibrator position matches field 19:

**Command:**

```python
conda activate casa6 && python3 << 'EOF'
import numpy as np
from casacore.tables import table

ms_path = "/stage/dsa110-contimg/ms/2025-11-18T23:09:11.ms"

with table(f"{ms_path}/FIELD", readonly=True) as tf:
    phase_dirs = tf.getcol("PHASE_DIR")
    names = tf.getcol("NAME")

# Field 19 position
ra_h = np.rad2deg(phase_dirs[19, 0, 0]) / 15
dec_deg = np.rad2deg(phase_dirs[19, 0, 1])

print(f"Field 19: RA={ra_h:.4f}h, Dec={dec_deg:+.4f}°")
print(f"1911+161: RA=19.1995h, Dec=+16.196°")
print(f"Separation: {abs(ra_h - 19.1995) * 15 * np.cos(np.deg2rad(16.2)) * 60:.2f} arcmin")
EOF
```

**Result:** Field 19 at RA=19.1999h, Dec=+16.228° (0.03° from calibrator)

---

## Phase 4: Bandpass Calibration

### Session 2: Dec +54° Observations with 0834+555 (2025-12-05)

Switched to a brighter calibrator for better SNR:

| Parameter           | Value                                             |
| ------------------- | ------------------------------------------------- |
| **Calibrator**      | 0834+555                                          |
| **Flux (1.4 GHz)**  | 8.8 Jy                                            |
| **RA**              | 128.729°                                          |
| **Dec**             | 55.573°                                           |
| **MS Path**         | `/stage/dsa110-contimg/ms/2025-10-17T14:40:09.ms` |
| **Observation Dec** | 54.66°                                            |
| **Best Fields**     | 11~13 (RA closest to calibrator transit)          |

### Bug Fixes Applied

#### 1. Silent 2.5 Jy Default Removed

**Problem:** `populate_model_from_catalog()` was silently defaulting to 2.5 Jy
when no flux was provided, instead of using the actual catalog flux (8.8 Jy).

**Fix in `calibration/model.py`:**

- Added `_get_calibrator_flux_from_catalog()` helper to query VLA catalog
- Removed silent 2.5 Jy default - now requires explicit flux OR uses catalog
- Raises `ValueError` if flux cannot be determined

#### 2. MODEL_DATA Validation Added

**Problem:** Bandpass was failing silently when MODEL_DATA was all zeros.

**Fix in `calibration/cli.py`:**

- Added `_validate_model_data_populated()` before bandpass solve
- Validates max amplitude > 0 for selected field
- Provides clear error message if MODEL_DATA is empty

#### 3. Phaseshift Before Bandpass (Critical!)

**Problem:** DATA was phased to each field's meridian (Dec=54.66°) but the
calibrator is at Dec=55.57° - a 54 arcminute offset! This caused:

- ~100° phase scatter across baselines (geometric delay from offset)
- Bandpass solver couldn't find coherent solutions (73% flagged)

**Fix in `calibration/cli.py`:**

- Added `phaseshift_to_calibrator()` function
- Creates a new MS with calibrator field(s) phaseshifted to calibrator position
- Now calibrator is at phase center → MODEL_DATA = constant amplitude, zero phase

```python
# New workflow in run_calibrator():
# Step 1: Phaseshift calibrator field to calibrator position
cal_ms, phasecenter = phaseshift_to_calibrator(ms_path, cal_field, calibrator_name)

# Step 2: Set MODEL_DATA (now simple: constant 8.8 Jy, zero phase)
populate_model_from_catalog(cal_ms, field=field, calibrator_name=calibrator_name)
```

**Verification of phaseshift working:**

```
Before phaseshift:
  Phase center Dec: 54.66° (meridian)
  MODEL_DATA phase std: 10.7° (varying with geometric offset)

After phaseshift:
  Phase center Dec: 55.57° (calibrator position)
  MODEL_DATA phase std: 0.0° ✓ (constant - calibrator at phase center!)
```

#### 4. AOFlagger RFI Flagging Added

**Problem:** `run_calibrator()` only flagged autocorrelations, not RFI.
The streaming path (`streaming.py`) called `preflag_rfi()` but direct calls
to `run_calibrator()` skipped this critical step.

**Fix in `calibration/cli.py`:**

- Added AOFlagger call in Step 0 (pre-calibration flagging)
- Falls back to CASA tfcrop+rflag if AOFlagger fails

```python
# Step 0 now includes:
flagdata(vis=ms_file, autocorr=True)  # Flag autocorrelations
flag_rfi(ms_file, backend="aoflagger")  # Flag RFI with AOFlagger
```

**Result:** Additional 2.48% data flagged by AOFlagger (generic strategy).

### Current Calibration Progress

| Step                | Status | Notes                                             |
| ------------------- | ------ | ------------------------------------------------- |
| Select observation  | ✅     | 2025-10-17T14:40:09, Dec +54.66°                  |
| Identify calibrator | ✅     | 0834+555, 8.8 Jy, Dec +55.57°                     |
| Find best field     | ✅     | Field 12 (RA=128.71°, closest to transit)         |
| Flag RFI            | ✅     | AOFlagger: 2.06% → 4.55% flagged                  |
| Phaseshift          | ✅     | Created `_cal.ms` with calibrator at phase center |
| Set MODEL_DATA      | ✅     | 8.8 Jy, 0° phase (verified)                       |
| Bandpass solve      | 🔄     | In progress - flagging improved from 73% → 53%    |

### Key Lessons Learned

1. **Amplitude doesn't matter for uncalibrated data** - the DATA/MODEL amplitude
   ratio is the bandpass gain we're solving for

2. **Phase coherence is critical** - ~100° phase std means incoherent signal,
   which is expected for uncalibrated data (that's what we're solving for!)

3. **Phaseshift is REQUIRED** - DSA-110 data is phased to meridian, not to
   calibrator. Without phaseshift, there's a huge geometric phase gradient

4. **K calibration is NOT needed** - K (delay) calibration is for VLBI with
   very long baselines. DSA-110's ~km baselines don't need it

5. **AOFlagger before bandpass** - RFI must be flagged before solving or it
   corrupts the bandpass solutions

### Next Steps

1. Run bandpass with correct field selection (`field="12"` not `"0"`)
2. Evaluate solutions quality (target: <30% flagged)
3. If still high flagging, investigate reference antenna selection
4. Apply solutions to full MS and verify improvement

---

_Updated: 2025-12-05_
_Calibrator: 0834+555 (8.8 Jy at Dec +55.6°)_
_Observation: 2025-10-17T14:40:09.ms (Dec +54.7°)_
