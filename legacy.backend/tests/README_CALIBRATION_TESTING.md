# Comprehensive Calibration Testing Guide

## Overview

This document describes the comprehensive testing approach for the DSA-110
continuum imaging calibration pipeline. The tests cover critical issues that
have been identified and fixed in production:

1. **Subband ordering** - Files must be sorted by subband number (0-15) for
   correct spectral ordering
2. **MS phasing** - REFERENCE_DIR must be correctly set for calibration
3. **MODEL_DATA population** - Required for calibration, must be validated
4. **Pre-bandpass phase solve** - Parameters (solint, minsnr) must be correct
5. **Bandpass calibration** - Solution quality must be validated
6. **Field and SPW combination** - Parameters must work correctly

## Test Structure

### Unit Tests (`tests/unit/`)

#### `test_calibration_comprehensive.py`

Comprehensive unit tests covering:

- Subband ordering logic
- MS phasing verification
- MODEL_DATA validation
- Pre-bandpass phase parameters
- Bandpass quality metrics
- Calibration parameter validation

#### `test_subband_ordering.py`

Focused tests for subband ordering:

- Subband code extraction
- File sorting by subband number
- Handling of mixed timestamps
- Complete 16-subband group validation

#### `test_cli_calibration_args.py`

CLI parameter validation:

- Parameter existence checks
- Signature validation

### Integration Tests (`tests/integration/`)

#### `test_calibration_workflow.py`

Full workflow integration tests:

- Subband file discovery and ordering
- UVH5 to MS conversion
- MS phasing verification
- Full calibration workflow
- Parameter validation

#### `test_pipeline_end_to_end.sh`

End-to-end pipeline test (existing):

- Full pipeline from UVH5 to calibrated image
- Includes calibration as one stage

## Running Tests

### Unit Tests

```bash
# Run all unit tests
pytest tests/unit/test_calibration_comprehensive.py -v
pytest tests/unit/test_subband_ordering.py -v

# Run specific test class
pytest tests/unit/test_subband_ordering.py::TestSubbandSorting -v

# Run specific test
pytest tests/unit/test_subband_ordering.py::TestSubbandSorting::test_sort_by_subband_number -v
```

### Integration Tests

```bash
# Run integration tests (requires TEST_WITH_SYNTHETIC_DATA=1)
export TEST_WITH_SYNTHETIC_DATA=1
pytest tests/integration/test_calibration_workflow.py -v

# Run specific integration test
pytest tests/integration/test_calibration_workflow.py::TestCalibrationWorkflowIntegration::test_full_calibration_with_prebp_phase -v
```

### Full Test Suite

```bash
# Run all calibration-related tests
pytest tests/unit/test_calibration*.py tests/integration/test_calibration*.py -v

# Run with coverage
pytest tests/unit/test_calibration*.py --cov=src/dsa110_contimg/calibration --cov=src/dsa110_contimg/conversion -v
```

## Test Coverage

### Critical Components Tested

1. **Subband Ordering**
   (`src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`)
   - :check_mark: File sorting by subband number
   - :check_mark: Handling of mixed timestamps
   - :check_mark: Complete group validation

2. **MS Phasing** (`src/dsa110_contimg/calibration/cli.py`)
   - :check_mark: REFERENCE_DIR verification
   - :check_mark: Phase center alignment calculation
   - :check_mark: Rephasing logic

3. **MODEL_DATA** (`src/dsa110_contimg/calibration/model.py`)
   - :check_mark: Population validation
   - :check_mark: Flux validation

4. **Pre-Bandpass Phase** (`src/dsa110_contimg/calibration/calibration.py`)
   - :check_mark: Parameter validation (solint, minsnr)
   - :check_mark: Solution quality metrics

5. **Bandpass Calibration** (`src/dsa110_contimg/calibration/calibration.py`)
   - :check_mark: Combine parameters (SPW, field)
   - :check_mark: Solution quality validation
   - :check_mark: SNR threshold logic

## Known Issues and Tests

### Issue: Subband Ordering

**Problem:** Files sorted alphabetically by filename, causing incorrect spectral
order.

**Test:**
`test_subband_ordering.py::TestSubbandSorting::test_sort_by_subband_number`

- Verifies files sort by subband number (0-15), not filename

**Fix:** Custom sort key that extracts subband number from filename.

### Issue: MS Phasing

**Problem:** REFERENCE_DIR not updated by phaseshift, causing 54.7 arcmin
offset.

**Test:**
`test_calibration_comprehensive.py::TestMSPhasing::test_phase_center_alignment`

- Verifies phase center alignment calculation
- Tests separation threshold (< 1 arcmin)

**Fix:** Manual REFERENCE_DIR update after phaseshift.

### Issue: Pre-Bandpass Phase Parameters

**Problem:** Default solint='inf' and minsnr=5.0 cause high flagging (80-90%).

**Test:**
`test_calibration_comprehensive.py::TestPreBandpassPhase::test_solint_parameter_default`

- Verifies default parameters
- Tests recommended values (solint='30s', minsnr=3.0)

**Fix:** CLI parameters `--prebp-solint 30s --prebp-minsnr 3.0`.

### Issue: Bandpass Solution Quality

**Problem:** >50% of solutions flagged due to low SNR.

**Test:**
`test_calibration_comprehensive.py::TestBandpassCalibration::test_bandpass_flagged_fraction_threshold`

- Verifies acceptable threshold (< 50%)
- Tests solution quality metrics

**Fix:** Pre-bandpass phase correction + correct parameters.

## Adding New Tests

### Unit Test Template

```python
class TestNewFeature:
    """Test description."""

    def test_feature_basic(self):
        """Test basic functionality."""
        # Arrange
        # Act
        # Assert
        assert True
```

### Integration Test Template

```python
@pytest.mark.skipif(
    not os.environ.get("TEST_WITH_SYNTHETIC_DATA"),
    reason="Requires TEST_WITH_SYNTHETIC_DATA=1",
)
def test_feature_integration(self, temp_dir):
    """Test feature in full workflow."""
    # Full workflow test
    assert True
```

## Continuous Integration

These tests should be run in CI/CD pipelines:

1. **Pre-commit:** Run unit tests (fast)
2. **Pull Request:** Run unit + integration tests (if synthetic data available)
3. **Release:** Full test suite including end-to-end tests

## Test Data Requirements

### Synthetic Data

- Generated using `tests/utils/generate_uvh5_calibrator.py`
- 16 subband files with proper frequency structure
- Point source calibrator at known position

### Real Data (Optional)

- For integration tests with real data
- Requires access to actual UVH5 files
- Should be minimal subset for fast testing

## Troubleshooting

### Test Failures

1. **Import Errors:** Ensure `PYTHONPATH` includes `src/`
2. **Missing Dependencies:** Install test requirements
3. **Synthetic Data:** Set `TEST_WITH_SYNTHETIC_DATA=1` for integration tests

### Test Performance

- Unit tests should run in < 1 second each
- Integration tests may take 10-60 seconds
- Use `pytest -x` to stop on first failure

## Future Improvements

1. **Mock MS Files:** Create lightweight MS mocks for faster testing
2. **Parameterized Tests:** Test multiple parameter combinations
3. **Performance Tests:** Measure calibration performance
4. **Regression Tests:** Test against known good solutions
5. **Visualization Tests:** Verify calibration plots/quality metrics
