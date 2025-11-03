# Pipeline Testing Guide

**Purpose:** Verify each pipeline stage is functional and ready for streaming/debugging

**Related Guides:**
- Finding calibrator transit data: [`FIND_CALIBRATOR_TRANSIT_DATA.md`](FIND_CALIBRATOR_TRANSIT_DATA.md)

---

## Quick Answer: Simplest Test

The **simplest end-to-end test** covers all pipeline stages in ~2-5 minutes:

```bash
conda activate casa6
bash scripts/test_pipeline_end_to_end.sh
```

This test:
1. ✅ Generates minimal synthetic UVH5 data (4 subbands, 1 minute, 64 channels)
2. ✅ Converts UVH5 → MS (orchestrator with direct-subband writer)
3. ✅ RFI flagging (reset flags, flag zeros)
4. ✅ Calibration (BP/G in fast mode, K skipped by default)
5. ✅ Apply calibration (if caltables created)
6. ✅ Imaging (quick-look tclean)
7. ✅ Basic QA checks

**Time:** 2-5 minutes depending on hardware  
**Requirements:** casa6 conda environment, ~500 MB disk space

---

## Alternative Test Options

### Option 1: Use Existing Real Data

If you have real UVH5 files or an existing MS:

```bash
# Using existing UVH5 files (skip synthetic generation)
bash scripts/test_pipeline_end_to_end.sh --skip-synthetic

# Using existing MS (skip conversion and synthetic)
bash scripts/test_pipeline_end_to_end.sh --use-existing-ms /path/to/existing.ms
```

**Best for:** Testing calibration/imaging stages with production data

---

### Option 2: Manual 3-Stage Quick-Look (from docs/quicklook.md)

For fastest iteration on specific stages:

```bash
# 1. Conversion (if you have UVH5 files)
scripts/run_conversion.sh /path/to/uvh5_dir /scratch/ms \
  2025-10-13T13:25:00 2025-10-13T13:30:00

# 2. Calibration (fast mode)
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/ms/<obs>.ms \
  --field 0 --refant 1 --fast --timebin 30s --chanbin 4 --uvrange '>1klambda'

# 3. Imaging (quick-look)
scripts/image_ms.sh /scratch/ms/<obs>.ms /scratch/out/<obs> \
  --quick --skip-fits --uvrange '>1klambda'
```

**Time:** <1 minute (with existing MS)  
**Best for:** Quick iteration on calibration/imaging parameters

---

### Option 3: Individual Component Tests

For debugging specific stages:

```bash
# Test individual components
conda activate casa6
python scripts/comprehensive_test_suite.py

# Test QA modules specifically
python scripts/test_qa_modules.py

# Test photometry normalization
python scripts/test_photometry_without_db.py

# Test data accessibility
python scripts/test_data_accessibility.py
```

**Best for:** Isolating problems in specific modules

---

### Option 4: Create Test MS from Real MS

For faster calibration testing:

```bash
# Create smaller test MS (reduces size by 6-7x)
python scripts/create_test_ms.py \
  /scratch/ms/full.ms \
  /scratch/ms/full_test.ms \
  --max-baselines 15 \
  --max-times 50

# Then test calibration on smaller MS
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/ms/full_test.ms \
  --field 0 --refant 1 --fast
```

**Best for:** Faster calibration iteration (preserves full bandwidth, reduces baselines/times)

---

### Option 5: Check Upstream Delay Correction

Verify if delays are already corrected before calibration:

```bash
conda run -n casa6 python scripts/check_upstream_delays.py \
  <ms_path> \
  --n-baselines 50
```

**Output interpretation:**
- <1 ns: Likely corrected upstream ✓
- 1-5 ns: Partial correction (may need K-calibration)
- >5 ns: Needs K-calibration (use `--do-k` flag)

**Best for:** Determining if K-calibration is needed

---

## Stage-by-Stage Verification

### Stage 1: Conversion (UVH5 → MS)

**Test:**
```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
  /path/to/uvh5_dir \
  /scratch/ms \
  "2025-01-15T12:00:00" \
  "2025-01-15T12:01:00" \
  --writer auto \
  --max-workers 4
```

**Verify:**
- MS created in output directory
- MS has correct columns: `DATA`, `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`
- No errors in logs
- MS can be opened with `casatasks`: `python -c "from casacore.tables import table; t = table('${MS_PATH}'); print(t.nrows())"`

**Common issues:**
- Missing subbands → Check file pattern matches `*_sb??.hdf5`
- Writer errors → Try `--writer direct-subband` explicitly
- Memory issues → Reduce `--max-workers` or disable tmpfs staging

---

### Stage 2: RFI Flagging

**Test:**
```bash
python -m dsa110_contimg.calibration.cli flag \
  --ms /scratch/ms/test.ms \
  --reset \
  --flag-zeros
```

**Verify:**
- Flags reset to False
- Zero visibilities flagged
- MS still readable

**Common issues:**
- MS locked → Check no other processes accessing MS
- No flags column → Should be created automatically

---

### Stage 3: Calibration (K/BP/G)

**Test:**
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /scratch/ms/test.ms \
  --field 0 \
  --refant 1 \
  --fast \
  --timebin 30s \
  --chanbin 4 \
  --uvrange '>1klambda'
```

**Note:** K-calibration is **skipped by default** for DSA-110. Use `--do-k` to enable.

**Verify:**
- Caltables created: `test.ms.bpcal`, `test.ms.gcal` (and `test.ms.kcal` if `--do-k`)
- No errors in logs
- Caltables readable: `python -c "from casacore.tables import table; t = table('test.ms.bpcal'); print(t.nrows())"`

**Common issues:**
- No calibrator field → Ensure field 0 (or specified field) has bright source
- Low SNR → Increase `--timebin` or remove `--uvrange` cut
- K-calibration fails → Check if delays corrected upstream (see Option 5)

---

### Stage 4: Apply Calibration

**Test:**
```bash
python -m dsa110_contimg.calibration.cli apply \
  --ms /scratch/ms/test.ms
```

**Verify:**
- `CORRECTED_DATA` column has non-zero values
- No errors in logs
- Check values: `python -c "from casacore.tables import table; t = table('test.ms'); cd = t.getcol('CORRECTED_DATA'); print('Non-zero:', (cd != 0).sum())"`

**Common issues:**
- No caltables found → Check caltable registry: `python -m dsa110_contimg.database.registry_cli list`
- CORRECTED_DATA all zeros → Verify caltables are valid and applied in correct order

---

### Stage 5: Imaging

**Test:**
```bash
scripts/image_ms.sh /scratch/ms/test.ms /scratch/out/test \
  --quick \
  --skip-fits \
  --uvrange '>1klambda'
```

**Verify:**
- Image created: `test.image` directory
- No errors in logs
- Image readable: `python -c "from casacore.tables import table; t = table('test.image'); print('Shape:', t.getcol('map').shape)"`

**Common issues:**
- tclean fails → Check if `CORRECTED_DATA` exists and is non-zero (or falls back to `DATA`)
- Out of memory → Reduce `imsize` or use `--quick` mode
- No convergence → Increase `--niter` or adjust threshold

---

### Stage 6: QA Checks

**Test:**
```bash
python <<PY
from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_image_quality
)

# MS QA
passed, metrics = check_ms_after_conversion("/scratch/ms/test.ms", 
                                             quick_check_only=True)
print(f"MS QA: {'PASS' if passed else 'FAIL'}")
print(f"Metrics: {metrics}")

# Image QA
passed, metrics = check_image_quality("/scratch/out/test.image",
                                      quick_check_only=True)
print(f"Image QA: {'PASS' if passed else 'FAIL'}")
print(f"Metrics: {metrics}")
PY
```

**Verify:**
- QA checks return `passed=True` (or identify specific issues)
- Metrics are reasonable (no NaN/Inf values)
- QA plots generated (if enabled)

---

## Debugging Tips

### 1. Check Logs

All pipeline stages output detailed logs:
- Conversion: Check orchestrator output for writer type, timing, errors
- Calibration: Check for solve statistics, reference antenna warnings
- Imaging: Check tclean convergence, deconvolution progress

### 2. Validate MS Structure

```bash
python <<PY
from casacore.tables import table
ms = "/scratch/ms/test.ms"

# Check columns
with table(ms) as tb:
    print("Columns:", tb.colnames())
    print("Rows:", tb.nrows())
    
# Check fields
with table(ms + "::FIELD") as tf:
    print("Fields:", tf.getcol("NAME"))

# Check SPWs
with table(ms + "::SPECTRAL_WINDOW") as spw:
    print("SPWs:", spw.nrows())
PY
```

### 3. Verify Data Accessibility

```bash
python scripts/test_data_accessibility.py
```

This checks:
- MS files readable
- Image directories accessible
- Database connectivity
- Temp directories writable

### 4. Check Calibration Tables

```bash
python -m dsa110_contimg.database.registry_cli list
```

This shows:
- Registered caltables
- Validity windows
- Apply order

### 5. Test with Minimal Data

If full pipeline fails, test stages individually:
1. Create minimal synthetic data (4 subbands, 1 minute)
2. Test conversion only
3. Test calibration on converted MS
4. Test imaging on calibrated MS

---

## Expected Outputs

### Successful Conversion
- MS directory created with `.ms` extension
- MS contains all required columns
- Logs show "WRITER_TYPE: direct-subband" (or "pyuvdata" for ≤2 subbands)
- No errors, only warnings (if any)

### Successful Calibration
- Caltables created (`.bpcal`, `.gcal`, optionally `.kcal`)
- Caltables registered in `cal_registry.sqlite3`
- Logs show solve statistics (SNR, residuals)
- No critical errors

### Successful Imaging
- Image directory created (`.image` extension)
- Image contains reasonable flux values
- tclean converged (niter < max iterations)
- No deconvolution warnings

### Successful QA
- All checks return `passed=True`
- Metrics within expected ranges
- No NaN/Inf values
- QA plots generated (if enabled)

---

## Troubleshooting

### Problem: Conversion fails

**Check:**
- UVH5 file pattern matches `*_sb??.hdf5`
- All 16 subbands present (or reduced set if using minimal config)
- Timestamps match search window
- Sufficient disk space in scratch directory

### Problem: Calibration fails

**Check:**
- Calibrator field exists and has bright source
- Reference antenna is present in MS
- Sufficient baselines for solving
- Delays already corrected (may not need K-calibration)

### Problem: Imaging fails

**Check:**
- `CORRECTED_DATA` exists and non-zero (or `DATA` if no calibration)
- Sufficient memory for imsize
- UV range has data (`--uvrange` may be too restrictive)
- Convergence criteria met (increase `--niter` if needed)

### Problem: QA checks fail

**Check:**
- MS structure is valid (all required columns present)
- Image dimensions match expected
- No corrupted data (NaN/Inf)
- Metrics thresholds are appropriate for test data

---

## Next Steps

After verifying all stages work:

1. **Test with real data:** Run full pipeline on production UVH5 files
2. **Check streaming:** Verify streaming converter processes groups correctly
3. **Monitor performance:** Check timing and resource usage
4. **Validate outputs:** Compare with known-good results
5. **Integration testing:** Test API endpoints, database interactions

---

## References

- **Quick-look guide:** `docs/quicklook.md`
- **Quick-start guide:** `docs/quickstart.md`
- **Pipeline overview:** `docs/pipeline.md`
- **Simulation docs:** `docs/simulation/README.md` (if exists)
- **Test results:** `docs/reports/TESTING_COMPLETE_SUMMARY.md`

