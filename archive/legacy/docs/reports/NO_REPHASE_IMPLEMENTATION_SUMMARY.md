# No-Rephase Calibration Implementation Summary

**Date:** 2025-11-05  
**Status:** Implementation Complete  
**Purpose:** Skip rephasing to allow ft() to work correctly

---

## Implementation Summary

### New CLI Arguments

1. **`--skip-rephase`**: Skip rephasing MS to calibrator position
2. **`--prebp-minblperant <int>`**: Minimum baselines per antenna for pre-bandpass phase solve
3. **`--prebp-spw <string>`**: SPW selection (e.g., `4~11` for central 8 SPWs)
4. **`--prebp-table-name <string>`**: Custom table name (e.g., `.bpphase.gcal`)
5. **`--bp-combine <string>`**: Custom combine string for bandpass (e.g., `scan,obs,field`)

### Code Changes

#### `solve_prebandpass_phase()` - Added Parameters:
- `minblperant`: Minimum baselines per antenna
- `spw`: SPW selection string
- `table_name`: Custom table name

#### `solve_bandpass()` - Added Parameter:
- `combine`: Custom combine string (overrides auto-generated combine)

#### CLI `calibrate` command:
- Added `--skip-rephase` flag to skip rephasing
- Added new arguments for pre-bandpass phase solve
- Added `--bp-combine` argument for custom combine string

---

## Usage Example

### Complete Command

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 106 \
    --skip-rephase \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 2.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal \
    --bp-combine "scan,obs,field"
```

### Parameters Breakdown

**Gaincal Phase-Only (Pre-Bandpass):**
- `calmode='p'` (phase-only) - automatic
- `solint='30s'` - `--prebp-solint 30s`
- `minsnr=2.0` - `--prebp-minsnr 2.0`
- `minblperant=4` - `--prebp-minblperant 4`
- `refant=106` - `--refant 106`
- `spw='4~11'` - `--prebp-spw 4~11` (central 8 SPWs)
- Output: `.bpphase.gcal` - `--prebp-table-name .bpphase.gcal`

**Bandpass:**
- `solint='inf'` - automatic (per-channel)
- `bandtype='B'` - automatic (per-channel bandpass)
- `combine='scan,obs,field'` - `--bp-combine "scan,obs,field"`
- `gaintable=[.bpphase.gcal]` - automatic (uses pre-bandpass phase table)

---

## Expected Behavior

### With `--skip-rephase`:

1. **Rephasing is skipped** - MS stays at meridian phase center
2. **`ft()` works correctly** - Uses meridian phase center (matches MS)
3. **MODEL_DATA calculated correctly** - Relative to meridian phase center
4. **DATA and MODEL_DATA aligned** - Both relative to meridian (< 20° phase difference)
5. **Calibration should succeed** - Even with ~102° phase scatter (correct for 1° offset)

### Central 8 SPWs:

For 16 SPWs (0-15), central 8 SPWs are SPWs 4-11:
- SPW selection: `--prebp-spw 4~11`
- Avoids edge effects at band edges
- Uses most stable central frequencies

---

## Files Modified

1. `src/dsa110_contimg/calibration/calibration.py`
   - Modified `solve_prebandpass_phase()` - added parameters
   - Modified `solve_bandpass()` - added `combine` parameter

2. `src/dsa110_contimg/calibration/cli.py`
   - Added `--skip-rephase` flag
   - Added `--prebp-minblperant` argument
   - Added `--prebp-spw` argument
   - Added `--prebp-table-name` argument
   - Added `--bp-combine` argument
   - Modified rephasing logic to respect `--skip-rephase`

---

## Next Steps

1. **Test the workflow** with the new parameters
2. **Verify MODEL_DATA phase scatter** (should be ~102°, but correct)
3. **Verify DATA vs MODEL_DATA alignment** (should be < 20°)
4. **Run calibration** and check phase scatter in bandpass solutions

