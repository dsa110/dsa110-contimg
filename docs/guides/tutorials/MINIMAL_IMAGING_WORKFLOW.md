# Minimal DSA-110 Imaging Workflow

**Last Updated:** November 25, 2025  
**Status:** Validated against production codebase

This document provides the **minimal viable workflow** to take DSA-110 raw
subband data through to a calibrated, cleaned image. This is intended for
testing, development, and understanding the core pipeline flow.

---

## Prerequisites

**Environment Setup:**

```bash
conda activate casa6  # REQUIRED - all CASA tools depend on this
```

**Required Inputs:**

- 16 HDF5 subband files (e.g., `2025-10-05T12:30:00_sb00.hdf5` through
  `_sb15.hdf5`)
- Or: Time range where subband files exist in `/data/incoming/`

**Key Paths:**

- Raw data: `/data/incoming/` (watched by streaming converter)
- Working directory: `/stage/dsa110-contimg/`
- Products: `/data/dsa110-contimg/products/`
- Logs: `/data/dsa110-contimg/state/logs/`

---

## Option A: Ultra-Minimal (No Calibration)

For **quick testing** or **dirty images only**. Produces an uncalibrated image
to verify data flow.

### Step 1: Convert UVH5 → Measurement Set

```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

convert_subband_groups_to_ms(
    input_dir='/data/incoming/2025-10-05',
    output_dir='/stage/dsa110-contimg/ms',
    start_time='2025-10-05T12:30:00',
    end_time='2025-10-05T12:36:00',  # 6-minute window
    writer='parallel-subband',  # Production writer
)
```

**What This Does:**

1. Groups files by timestamp (60s tolerance) → finds 16-subband groups
2. Loads subbands in batches (default: 4 per batch)
3. Combines subbands using `pyuvdata.fast_concat()` (reverse order for ascending
   frequency)
4. Phases visibilities to meridian
5. Writes MS directly (no UVFITS intermediate)
6. Updates antenna positions from `DSA110_Station_Coordinates.csv`
7. Auto-detects and renames calibrator fields (e.g., `meridian_icrs_t17` →
   `3C286_t17`)
8. Validates frequency order, antenna positions, phase center

**Output:** `/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms`

**Field Naming:** After conversion, the MS has 24 fields (one per 12.88s
timestamp). If a known calibrator is detected, the field containing it is
automatically renamed from `meridian_icrs_t{i}` to `{calibrator}_t{i}` (e.g.,
`3C286_t17`). Other fields keep their generic names.

### Step 2: Image with WSClean (No Calibration)

```python
from dsa110_contimg.imaging.cli_imaging import run_wsclean

run_wsclean(
    ms_path='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    imagename='/stage/dsa110-contimg/images/test_dirty',
    datacolumn='DATA',  # Uncalibrated data
    field='0',
    imsize=2048,
    cell_arcsec=2.0,
    weighting='briggs',
    robust=-0.5,
    specmode='mfs',
    deconvolver='hogbom',
    nterms=1,
    niter=10000,
    threshold='0.5mJy',
    pbcor=True,
    uvrange='',
    pblimit=0.1,
    quality_tier='standard',
)
```

**Output:** Dirty image at `/stage/dsa110-contimg/images/test_dirty-image.fits`

**Expected Quality:** Low dynamic range, no calibration corrections applied

---

## Option B: Minimal with Calibration

For **science-quality images**. Includes bandpass and gain calibration.

### Step 1: Convert UVH5 → MS

```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

# Same as Option A
convert_subband_groups_to_ms(
    input_dir='/data/incoming/2025-10-05',
    output_dir='/stage/dsa110-contimg/ms',
    start_time='2025-10-05T12:30:00',
    end_time='2025-10-05T12:36:00',
    writer='parallel-subband',
)
```

### Step 2: Run Calibrator Processing

**Prerequisite:** MS must contain a known calibrator (e.g., 3C286, 3C48).

**Field Naming After Conversion:** The MS has 24 fields named `meridian_icrs_t0`
through `meridian_icrs_t23`. If auto-detection succeeded during conversion, one
field will be renamed to include the calibrator name (e.g., `3C286_t17`).

**Check field names:**

```bash
# List all fields
python -c "
from casacore import tables as tb
with tb.table('/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms/FIELD') as t:
    names = t.getcol('NAME')
    phase_dir = t.getcol('PHASE_DIR')
    import numpy as np
    for i, name in enumerate(names):
        ra_deg = np.rad2deg(phase_dir[i, 0, 0])
        dec_deg = np.rad2deg(phase_dir[i, 0, 1])
        print(f'Field {i}: {name} @ RA={ra_deg:.4f}°, Dec={dec_deg:.4f}°')
"
# Look for field with calibrator name (e.g., "3C286_t17")
# If all fields are still "meridian_icrs_t*", auto-detection didn't find a calibrator
```

**Option 2A: Use auto-renamed field (recommended):**

```python
from dsa110_contimg.calibration.cli import run_calibrator

# If conversion auto-detected calibrator, use that field name
caltables = run_calibrator(
    ms='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    cal_field='3C286_t17',  # Use the auto-renamed field name
    refant='68',
    do_flagging=True,
    do_k=False,
)
```

**Option 2B: Specify calibrator field manually (if auto-detection failed):**

```python
from dsa110_contimg.calibration.cli import run_calibrator

# Specify field by numeric ID (if you know which timestamp has the calibrator)
caltables = run_calibrator(
    ms='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    cal_field='17',  # Field ID containing the calibrator
    refant='68',  # Stable reference antenna (check with QA tools)
    do_flagging=True,  # RFI mitigation before calibration
    do_k=False,  # K-calibration not needed for DSA-110 (connected-element array)
)
```

**Option 2C: Force re-detection (if auto-detection failed during conversion):**

```python
from dsa110_contimg.calibration.field_naming import rename_calibrator_fields_from_catalog
from dsa110_contimg.calibration.cli import run_calibrator

# Manually trigger calibrator detection and renaming
result = rename_calibrator_fields_from_catalog(
    '/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms'
)

if result:
    cal_name, field_idx = result
    print(f"Detected {cal_name} in field {field_idx}, renamed to {cal_name}_t{field_idx}")

    # Now use the renamed field
    caltables = run_calibrator(
        ms='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
        cal_field=f'{cal_name}_t{field_idx}',
        refant='68',
        do_flagging=True,
        do_k=False,
    )
else:
    print("No known calibrator found in any field")
```

**What This Does:**

1. **Flagging** (if `do_flagging=True`):
   - `reset_flags()` - Remove previous flags
   - `flag_zeros()` - Flag zero-valued data
   - `flag_rfi()` - RFI mitigation
2. **Bandpass Calibration** (`solve_bandpass`):
   - Solves for frequency-dependent gain structure
   - Long solution interval (`solint='inf'`)
   - Uses Perley-Butler 2017 flux scale via `setjy`
3. **Gain Calibration** (`solve_gains`):
   - Solves for time-variable atmospheric/instrumental effects
   - Shorter solution intervals for temporal variations

**Output:** List of calibration tables `[bp_table, g_table]`

### Step 3: Apply Calibration

```python
from dsa110_contimg.calibration.cli import apply_calibration

apply_calibration(
    ms='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    caltables=caltables,  # From Step 2
    field='0',  # Apply to all fields
)
```

**What This Does:**

- Writes calibrated visibilities to `CORRECTED_DATA` column
- Original data remains in `DATA` column

### Step 4: Inject Sky Model (Optional but Recommended)

**Guided deconvolution** using NVSS catalog sources:

```python
from dsa110_contimg.calibration.model import write_point_model_with_ft

# For a point source at field center with known flux
write_point_model_with_ft(
    ms_path='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    ra_deg=207.5,  # RA of field center (example)
    dec_deg=40.5,  # Dec of field center (example)
    flux_jy=1.0,
    field='0',
    use_manual=True,  # Use manual calculation (avoids ft() phase bugs)
)
```

**Alternative:** Use catalog-based model from pipeline (see Step 5 alternative)

### Step 5: Image with WSClean

```python
from dsa110_contimg.imaging.cli_imaging import run_wsclean

run_wsclean(
    ms_path='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    imagename='/stage/dsa110-contimg/images/calibrated_image',
    datacolumn='CORRECTED_DATA',  # Use calibrated data
    field='0',
    imsize=2048,
    cell_arcsec=2.0,
    weighting='briggs',
    robust=-0.5,
    specmode='mfs',
    deconvolver='hogbom',  # For point sources
    nterms=1,
    niter=50000,
    threshold='0.2mJy',
    pbcor=True,
    uvrange='',
    pblimit=0.1,
    quality_tier='standard',
)
```

**Output:** Calibrated image at
`/stage/dsa110-contimg/images/calibrated_image-image.fits`

---

## Option C: Full Pipeline with Self-Calibration

For **highest dynamic range**. Adds iterative self-calibration loops.

### Steps 1-5: Same as Option B

### Step 6: Self-Calibration

```python
from dsa110_contimg.calibration.selfcal import selfcal_ms, SelfCalConfig

success, summary = selfcal_ms(
    ms_path='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    output_dir='/stage/dsa110-contimg/selfcal',
    config=SelfCalConfig(
        max_iterations=3,
        initial_solint='10min',
        final_solint='2min',
        phase_only_rounds=2,
        amplitude_selfcal=True,
        min_snr=3.0,
        reset_ms=False,  # Don't regenerate from HDF5
    ),
    initial_caltables=caltables,  # From Step 2
)

if success:
    print(f"Self-cal succeeded: {summary['iterations_completed']} iterations")
else:
    print(f"Self-cal failed: {summary.get('failure_reason', 'Unknown')}")
```

**What This Does:**

1. Iteratively refines calibration using the source itself
2. Phase-only calibration first (preserves flux scale)
3. Optional amplitude calibration in final rounds
4. Monitors improvement via image RMS and dynamic range

**Output:** Refined calibration tables in `/stage/dsa110-contimg/selfcal/`

---

## Critical Patterns & Gotchas

### 1. The 16-Subband Architecture

**CRITICAL:** Every observation = **16 subband files** (sb00-sb15)

- **Frequency order:** DESCENDING (sb00=highest, sb15=lowest)
- **Time tolerance:** ±60 seconds (default clustering)
- **Never process individual subbands** - must group first

**Filesystem grouping:**

```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups

groups = find_subband_groups(
    input_dir='/data/incoming',
    start_time='2025-10-05T00:00:00',
    end_time='2025-10-05T23:59:59',
    tolerance_s=60.0,  # Default 60s
)
print(f"Found {len(groups)} complete groups")
```

### 2. Semi-Complete Groups (12-16 subbands)

**NEW:** Groups with 12-16 subbands are now accepted

- Missing subbands filled with synthetic zero-padded data
- Synthetic data properly flagged as corrupted
- See: `backend/src/dsa110_contimg/conversion/SEMI_COMPLETE_SUBBAND_GROUPS.md`

### 3. Writer Pattern

**CORRECT:**

```python
from dsa110_contimg.conversion.strategies.writers import get_writer

writer_cls = get_writer('parallel-subband')
writer_instance = writer_cls(uvdata, output_path, **kwargs)
writer_type = writer_instance.write()  # No arguments to write()
```

### 4. Antenna Positions

**CORRECT import:**

```python
from dsa110_contimg.utils.antpos_local import get_itrf

df_itrf = get_itrf()
antpos = np.array([df_itrf['x_m'], df_itrf['y_m'], df_itrf['z_m']]).T
```

### 5. Data Flow (No UVFITS)

**Actual flow:**

```
UVH5 → pyuvdata.UVData → combine subbands →
direct MS writing → configure_ms_for_imaging → update antenna positions
```

**NOT:** UVH5 → UVFITS → importuvfits → MS (this is outdated)

---

## Performance Expectations

**Conversion (Step 1):**

- Time: <4.5 minutes per 16-subband group (target)
- Memory: 2-4 GB per group
- Batched loading reduces peak memory by ~40%

**Calibration (Step 2):**

- Time: 5-10 minutes (depends on data quality, RFI)
- Memory: 1-2 GB

**Imaging (Step 5):**

- Time: 10-30 minutes (depends on niter, image size)
- Memory: 4-8 GB

**Self-Calibration (Step 6):**

- Time: 30-90 minutes (3 iterations)
- Memory: 4-8 GB

---

## Validation & QA

**After conversion:**

```python
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion

check_ms_after_conversion('/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms')
```

**After calibration:**

```python
from dsa110_contimg.qa.fast_plots import plot_calibration_qa

plot_calibration_qa(
    ms='/stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms',
    caltables=caltables,
    output_dir='/stage/dsa110-contimg/qa',
)
```

**QA Plots Generated:**

- Amplitude vs Time/Frequency
- Phase vs Time/Frequency
- UV coverage
- Residuals after calibration

---

## Command-Line Equivalents

All functions have CLI equivalents:

**Conversion:**

```bash
# With automatic calibrator field renaming (default)
python -m dsa110_contimg.conversion.cli convert \
    --input-dir /data/incoming/2025-10-05 \
    --output-dir /stage/dsa110-contimg/ms \
    --start-time "2025-10-05T12:30:00" \
    --end-time "2025-10-05T12:36:00"

# Disable automatic field renaming (if needed)
python -m dsa110_contimg.conversion.cli convert \
    --input-dir /data/incoming/2025-10-05 \
    --output-dir /stage/dsa110-contimg/ms \
    --start-time "2025-10-05T12:30:00" \
    --end-time "2025-10-05T12:36:00" \
    --no-rename-calibrator-fields
```

**Calibration:**

```bash
# Use auto-renamed field (if conversion detected calibrator)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms \
    --cal-field 3C286_t17 \
    --refant 68

# Or use numeric field ID
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms \
    --cal-field 17 \
    --refant 68
```

**Imaging:**

```bash
python -m dsa110_contimg.imaging.cli_imaging wsclean \
    --ms /stage/dsa110-contimg/ms/2025-10-05T12:30:00.ms \
    --imagename /stage/dsa110-contimg/images/test \
    --datacolumn CORRECTED_DATA \
    --niter 50000
```

---

## Troubleshooting

**"No complete subband groups found"**

- Check time tolerance (default 60s may be too strict)
- Verify filenames match pattern: `YYYY-MM-DDTHH:MM:SS_sbNN.hdf5`
- Use `find_subband_groups()` to debug grouping logic

**"Nants_data not found" error**

- Using deprecated pyuvdata attribute
- Update to: `uvdata.Nants_telescope` (NOT `Nants_data`)

**"MS frequency order incorrect"**

- Subbands weren't reversed during combination
- Ensure `sort_by_subband(..., reverse=True)` in orchestrator

**Calibration fails with phase scatter**

- Check reference antenna stability with QA plots
- Try different reference antenna
- Increase flagging aggressiveness

**Self-cal diverges (RMS increases)**

- Initial model too poor
- Reduce solution interval (longer solint)
- Add more phase-only rounds before amplitude

---

## Next Steps

**For production workflows:**

- Use full pipeline: `backend/src/dsa110_contimg/pipeline/stages_impl.py`
- Leverage streaming converter for real-time processing
- Integrate with database registries for product tracking

**For advanced imaging:**

- Multi-scale deconvolution for extended sources
- Automated masking with catalog guidance
- Mosaicking multiple pointings

**Documentation:**

- Full pipeline: `docs/SYSTEM_CONTEXT.md`
- Code organization: `.github/copilot-instructions.md`
- Serena memories: `.serena/memories/architecture_and_code_organization.md`
