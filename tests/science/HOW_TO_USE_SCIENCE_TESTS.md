# How to Use Science-First Tests

## Quick Start

### Run Structural Tests (No Data Required)

```bash
source activate casa6  # or conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH

# Run all science-first structural tests
pytest tests/science/test_calibration_scientific_validation.py tests/science/test_casa_compliance.py -v
```

These tests validate:
- Test structure and logic
- Scientific principles
- CASA standards knowledge
- Test framework correctness

### Run Integration Tests (Requires Actual Calibration Products)

```bash
# Set environment variables pointing to your calibration products
export TEST_MS_PATH="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.ms"
export TEST_BP_TABLE="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17_0_bpcal"
export TEST_PREBP_TABLE="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17_0_prebp_phase"
export TEST_G_TABLE="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17_0_gcal"

# Run integration tests
pytest tests/science/test_calibration_integration_validation.py -v
```

## Test Categories

### 1. Structural Tests (No Data Required)

**Purpose**: Validate scientific principles and test framework

**Files**:
- `test_calibration_scientific_validation.py` - 26 tests
- `test_casa_compliance.py` - 15 tests

**What They Test**:
- Flux scale principles
- Phase solution physics
- Bandpass shape requirements
- CASA standards knowledge
- Solution quality thresholds
- Calibrator selection criteria

**Run**:
```bash
pytest tests/science/test_calibration_scientific_validation.py tests/science/test_casa_compliance.py -v
```

### 2. Integration Tests (Requires Actual Data)

**Purpose**: Validate actual calibration products for scientific correctness

**File**: `test_calibration_integration_validation.py`

**What They Test**:
- Actual bandpass normalization from table
- Actual MODEL_DATA flux from MS
- Actual phase scatter from tables
- Actual MS phase center alignment
- Actual CASA table structure

**Run**:
```bash
# Set environment variables first
export TEST_MS_PATH="/path/to/your.ms"
export TEST_BP_TABLE="/path/to/your_bpcal"
export TEST_PREBP_TABLE="/path/to/your_prebp_phase"
export TEST_G_TABLE="/path/to/your_gcal"

pytest tests/science/test_calibration_integration_validation.py -v
```

## Example: Validating a Calibration Run

After running calibration:

```bash
# 1. Set paths to your calibration products
export TEST_MS_PATH="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17.ms"
export TEST_BP_TABLE="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17_0_bpcal"
export TEST_PREBP_TABLE="/stage/dsa110-contimg/ms/0834_20251029/2025-10-29T13:54:17_0_prebp_phase"

# 2. Run integration tests
pytest tests/science/test_calibration_integration_validation.py -v

# Expected output:
# - Bandpass normalization check
# - MODEL_DATA flux validation
# - Phase scatter validation
# - MS phase center alignment
# - CASA table structure validation
```

## What Each Test Validates

### Flux Scale Tests

- **Bandpass normalization**: Median amplitude should be ~1.0 (solnorm=True)
- **MODEL_DATA flux**: Should match catalog flux (2.5 Jy for 0834+555)
- **CORRECTED_DATA flux scale**: Should preserve flux scale

### Phase Quality Tests

- **Pre-bandpass phase scatter**: Should be < 20 degrees
- **Phase continuity**: No jumps > 180 degrees
- **Reference antenna stability**: Phase should be ~0 degrees

### MS Structure Tests

- **Phase center alignment**: REFERENCE_DIR must match calibrator within 1 arcmin
- **MODEL_DATA phase scatter**: Should be < 10 degrees
- **Field structure**: Field should contain calibrator

### CASA Compliance Tests

- **Table structure**: Required columns present
- **CPARAM shape**: Correct dimensions
- **Phase center format**: CASA-compliant
- **Task parameters**: Correct bandtype, solnorm, calmode

### Solution Quality Tests

- **Bandpass flagged fraction**: Should be < 50% (target: < 30%)
- **Pre-bandpass flagged fraction**: Should be < 30%
- **SNR threshold**: Solutions should have SNR >= 3.0

## Troubleshooting

### Test Fails: "Bandpass normalization error"

**Problem**: Bandpass median amplitude ≠ 1.0

**Possible causes**:
- `solnorm=True` not working correctly
- Bandpass calibration error
- Data quality issues

**Action**: Check bandpass calibration parameters and data quality

### Test Fails: "MODEL_DATA flux error"

**Problem**: MODEL_DATA flux doesn't match catalog

**Possible causes**:
- MODEL_DATA population error
- Catalog flux error
- Primary beam weighting error

**Action**: Verify MODEL_DATA population and catalog flux

### Test Fails: "MS phase center offset"

**Problem**: REFERENCE_DIR offset > 1 arcmin

**Possible causes**:
- MS phasing error (REFERENCE_DIR not updated)
- `phaseshift` didn't update REFERENCE_DIR
- Manual REFERENCE_DIR update failed

**Action**: Check MS phasing logic and verify REFERENCE_DIR

### Test Fails: "Phase scatter too high"

**Problem**: Phase scatter exceeds threshold

**Possible causes**:
- Phase decorrelation
- Poor data quality
- Calibration parameter issues
- Solution interval too long

**Action**: Check pre-bandpass phase parameters (solint, minsnr)

### Test Fails: "Flagged fraction too high"

**Problem**: >50% of solutions flagged

**Possible causes**:
- Low SNR
- Poor data quality
- Calibration parameter issues
- Missing pre-bandpass phase correction

**Action**: Check calibration parameters, data quality, and add pre-bandpass phase

## Integration with CI/CD

Add to CI/CD pipeline:

```bash
# Run structural tests (always)
pytest tests/science/test_calibration_scientific_validation.py tests/science/test_casa_compliance.py -v

# Run integration tests if calibration products exist
if [ -f "$TEST_MS_PATH" ]; then
    pytest tests/science/test_calibration_integration_validation.py -v
fi
```

## Best Practices

1. **Always run structural tests** before calibration
2. **Run integration tests** after calibration
3. **Fix issues immediately** - don't proceed with bad calibration
4. **Document failures** - they indicate scientific problems
5. **Use as regression tests** - ensure fixes don't break science

## Next Steps

1. **Run tests on your calibration products**
2. **Fix any failures** before proceeding
3. **Document results** for future reference
4. **Add to CI/CD** for continuous validation

