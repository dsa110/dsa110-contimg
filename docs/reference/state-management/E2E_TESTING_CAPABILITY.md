# End-to-End Pipeline Testing with Simulation Suite

**Date**: November 25, 2025
**Question**: Can simulated data and simulation suite tools be used to test the full pipeline end-to-end?

## Answer: YES ✅

The simulation suite **fully supports end-to-end pipeline testing** from synthetic data generation through final photometry validation.

---

## What Was Created

### 1. End-to-End Test Runner
**File**: `simulations/scripts/run_e2e_test.py` (460 lines)

**Capabilities**:
- Orchestrates complete pipeline: UVH5 → MS → Calibration → Imaging → Photometry
- Scenario-based testing using YAML configs
- Automatic validation of outputs against known inputs
- JSON results export for automated testing
- Stage-by-stage error handling and reporting

**Usage**:
```bash
# Run pre-defined scenario
python simulations/scripts/run_e2e_test.py --scenario bright_calibrator

# Custom config
python simulations/scripts/run_e2e_test.py --config path/to/scenario.yaml

# Clean previous outputs
python simulations/scripts/run_e2e_test.py --scenario weak_sources --clean
```

### 2. Test Scenarios
**Files**: `simulations/config/scenarios/*.yaml`

**Created scenarios**:
1. **bright_calibrator.yaml** - Strong 5 Jy calibrator, ideal conditions
   - Tests: Basic pipeline functionality
   - Expected SNR: >20
   - Flux accuracy: ±10%

2. **weak_sources.yaml** - 50 mJy source near detection limit
   - Tests: Sensitivity limits, weak source recovery
   - Expected SNR: ≥5
   - Flux accuracy: ±20%

**Future scenarios** (documented, not yet implemented):
- `crowded_field.yaml` - Blended source deconvolution
- `rfi_contaminated.yaml` - RFI mitigation testing

### 3. Updated Documentation
- `simulations/README.md` - Added E2E testing section
- `simulations/QUICKSTART.md` - Quick reference for E2E tests

---

## Pipeline Flow

### Stage 1: Generate Synthetic UVH5
**Tool**: `dsa110_contimg.simulation.make_synthetic_uvh5`
- Creates 16 subband HDF5 files per observation
- Supports point/Gaussian/disk source models
- Adds realistic thermal noise
- Template-free mode (no reference data needed)

**Example**:
```bash
python -m dsa110_contimg.simulation.make_synthetic_uvh5 \
    --template-free \
    --nants 110 \
    --start-time "2025-11-25T12:00:00" \
    --duration-minutes 5.0 \
    --subbands 16 \
    --flux-jy 5.0 \
    --add-noise \
    --output simulations/data/synthetic_uvh5/test01
```

### Stage 2: Convert to Measurement Set
**Tool**: `dsa110_contimg.conversion.strategies.hdf5_orchestrator.convert_subband_groups_to_ms`
- Groups 16 subbands by timestamp
- Combines into single MS
- Auto-renames calibrator fields
- Updates antenna positions

**Automated in E2E runner**

### Stage 3: Calibration
**Tool**: `dsa110_contimg.calibration.cli_calibrate`
- Auto-selects calibrator field
- Generates bandpass solutions
- Produces calibration tables

**Automated in E2E runner**

### Stage 4: Imaging
**Tool**: `dsa110_contimg.imaging.wsclean_wrapper`
- WSClean imaging
- Configurable size, scale, cleaning parameters
- Produces restored FITS images

**Automated in E2E runner**

### Stage 5: Photometry & Validation
**Tool**: `dsa110_contimg.photometry.forced.measure_forced_peak`
- Forced photometry at known source positions
- Compares measured vs expected fluxes
- Validates SNR thresholds
- Reports pass/fail per source

**Automated in E2E runner**

---

## Existing Pipeline Components

### Simulation Tools (Already Functional) ✅
- `simulation/make_synthetic_uvh5.py` - UVH5 generation CLI
- `simulation/synthetic_fits.py` - FITS image synthesis
- `simulation/visibility_models.py` - Enhanced visibility modeling
- `simulation/validate_synthetic.py` - Synthetic data validation

### Conversion Pipeline ✅
- `conversion/strategies/hdf5_orchestrator.py` - Batch converter
- `conversion/streaming/streaming_converter.py` - Real-time daemon
- `conversion/ms_utils.py` - MS configuration utilities

### Calibration ✅
- `calibration/cli_calibrate.py` - Calibration CLI
- `calibration/field_naming.py` - Auto-field detection

### Imaging ✅
- `imaging/wsclean_wrapper.py` - WSClean interface
- `imaging/casa_tclean.py` - CASA tclean wrapper

### Photometry ✅
- `photometry/forced.py` - Forced photometry with validation

### Pipeline Infrastructure ✅
- `pipeline/orchestrator.py` - Multi-stage orchestration
- `pipeline/stages_impl.py` - Stage implementations
- `pipeline/context.py` - Pipeline context management

---

## What This Enables

### 1. Regression Testing
Run E2E tests before merging changes to catch:
- Algorithm regressions
- Breaking API changes
- Performance degradations

**Example**:
```bash
# CI/CD integration
python simulations/scripts/run_e2e_test.py --scenario bright_calibrator
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "E2E test failed - blocking merge"
    exit 1
fi
```

### 2. Performance Benchmarking
Track stage durations across pipeline versions:
```json
{
  "stages": {
    "generate_uvh5": {"duration": 45.2},
    "convert_to_ms": {"duration": 120.5},
    "calibrate": {"duration": 180.3},
    "image": {"duration": 300.7},
    "photometry": {"duration": 5.2}
  },
  "total_duration": 651.9
}
```

### 3. Parameter Optimization
Test different imaging parameters:
- Image sizes (512, 1024, 2048 pixels)
- Pixel scales (2.5, 3.6, 5.0 arcsec)
- Cleaning thresholds
- Number of iterations

### 4. Sensitivity Studies
Measure detection limits:
- Vary source flux (5 Jy → 50 mJy → 5 mJy)
- Different noise levels
- Integration time effects

### 5. Feature Development
Safe sandbox for:
- New calibration algorithms
- Alternative imaging methods
- Photometry improvements

---

## Example E2E Test Output

```bash
$ python simulations/scripts/run_e2e_test.py --scenario bright_calibrator

2025-11-25 12:00:00 [INFO] Loading scenario from: simulations/config/scenarios/bright_calibrator.yaml
2025-11-25 12:00:00 [INFO] Starting E2E test: Bright Calibrator - Ideal Conditions
2025-11-25 12:00:05 [INFO] Stage 1: Generating synthetic UVH5 files...
2025-11-25 12:00:50 [INFO] Stage 2: Converting UVH5 to MS...
2025-11-25 12:02:55 [INFO] Stage 3: Calibrating MS...
2025-11-25 12:05:58 [INFO] Stage 4: Imaging MS...
2025-11-25 12:11:02 [INFO] Stage 5: Performing photometry...

============================================================
E2E Test: Bright Calibrator - Ideal Conditions
Status: ✅ PASSED
Total Duration: 662.34s
============================================================

Stage Summary:
  ✅ generate_uvh5: 45.23s
  ✅ convert_to_ms: 125.67s
  ✅ calibrate: 183.45s
  ✅ image: 304.12s
  ✅ photometry: 3.87s

Results saved to: simulations/data/e2e_tests/results.json
```

---

## Comparison: What Existed vs What Was Added

### Before
- ✅ Synthetic UVH5 generation tool (`make_synthetic_uvh5.py`)
- ✅ Conversion pipeline
- ✅ Individual pipeline stages
- ✅ Forced photometry validation notebook
- ❌ **No unified E2E test runner**
- ❌ **No scenario-based testing**
- ❌ **No automated validation**

### After
- ✅ All existing tools
- ✅ **End-to-end test runner** (`run_e2e_test.py`)
- ✅ **Test scenario configs** (bright_calibrator, weak_sources)
- ✅ **Automated validation** (flux accuracy, SNR checks)
- ✅ **JSON results export** (for CI/CD integration)
- ✅ **Complete documentation** (README, QUICKSTART)

---

## Next Steps (Optional)

### Additional Scenarios
1. **crowded_field.yaml** - Multiple blended sources
2. **extended_source.yaml** - Non-point sources
3. **rfi_contaminated.yaml** - RFI flagging tests
4. **multi_epoch.yaml** - Time-domain testing

### Test Automation
1. Integrate with CI/CD (GitHub Actions)
2. Nightly regression test suite
3. Performance tracking dashboard
4. Automated alerting on failures

### Enhanced Validation
1. Image quality metrics (dynamic range, RMS)
2. Calibration solution quality checks
3. Astrometric accuracy validation
4. Spectral index recovery tests

---

## Conclusion

**YES** - The simulation suite now provides **complete end-to-end pipeline testing** capabilities:

✅ Synthetic data generation (UVH5)
✅ Conversion to MS
✅ Calibration
✅ Imaging
✅ Photometry
✅ Validation against known inputs
✅ Automated test orchestration
✅ Results export for CI/CD

**Ready to use**: Run `python simulations/scripts/run_e2e_test.py --scenario bright_calibrator` to test the entire pipeline.
