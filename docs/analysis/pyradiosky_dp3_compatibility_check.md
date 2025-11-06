# Compatibility Check: pyradiosky + DP3 Integration

## Current Status

### DP3 Availability
- **Status**: Available via Docker
- **Image**: `dp3-everybeam-0.7.4` (latest, 8 days old)
- **Location**: Docker image, not in system PATH
- **Wrapper**: `src/dsa110_contimg/calibration/dp3_wrapper.py` exists
- **Usage**: **NOT currently used in pipeline** (only wrapper exists, no actual calls found)

### pyradiosky Availability
- **Status**: NOT INSTALLED in casa6 environment
- **Python**: 3.11.13 (compatible - pyradiosky requires 3.11+)
- **Dependencies Check**:
  - ✓ astropy: 7.1.0 (required)
  - ✓ numpy: 2.0.2 (required)
  - ✓ pandas: 2.3.3 (required)
  - ✓ h5py: 3.14.0 (required)
  - ✓ scipy: 1.16.2 (required)
  - ✓ pyuvdata: 3.2.4 (required by pyradiosky, already installed and used extensively)

### Current Dependencies in casa6
```
Python: 3.11.13
astropy: 7.1.0
numpy: 2.0.2
pandas: 2.3.3
h5py: 3.14.0
scipy: 1.16.2
```

## Compatibility Assessment

### pyradiosky Requirements
According to PyPI, pyradiosky requires:
- Python >= 3.11 ✓ (we have 3.11.13)
- astropy ✓ (we have 7.1.0)
- numpy ✓ (we have 2.0.2)
- scipy ✓ (we have 1.16.2)
- h5py ✓ (we have 3.14.0)
- pyuvdata (NEEDS CHECK)
- setuptools_scm (usually auto-installed)

### Potential Issues

1. **pyuvdata Dependency** ✓ RESOLVED
   - pyradiosky requires pyuvdata
   - ✓ pyuvdata 3.2.4 is already installed and working
   - ✓ pyuvdata is used extensively in the codebase (conversion, simulation, etc.)

2. **DP3 Not Currently Used** ⚠️ NEEDS TESTING
   - DP3 wrapper exists but is not called anywhere in the pipeline
   - DP3 Docker image exists (`dp3-everybeam-0.7.4`)
   - Need to verify DP3 Docker image works correctly
   - Need to test DP3 predict functionality
   - **Note**: There's a legacy document `archive/legacy/docs/reports/dp3_integration_plan.md` that may have integration details

3. **Dependency Conflicts** ⚠️ NEEDS VERIFICATION
   - Need to check if pyradiosky conflicts with CASA dependencies
   - CASA has specific version requirements that may conflict
   - pyuvdata 3.2.4 is already working with CASA, so likely compatible

## Recommendations

### Before Proceeding

1. **✓ pyuvdata availability**: VERIFIED (3.2.4 installed and working)

2. **Test DP3 functionality** (HIGH PRIORITY):
   - Verify DP3 Docker image works: `docker run --rm dp3-everybeam-0.7.4 DP3 --version`
   - Test `predict_from_skymodel_dp3()` with a small test case
   - Verify DP3 can write to MODEL_DATA correctly
   - Compare DP3 predict output with CASA ft() output for validation

3. **Test pyradiosky installation** (MEDIUM PRIORITY):
   ```bash
   /opt/miniforge/envs/casa6/bin/pip install pyradiosky
   /opt/miniforge/envs/casa6/bin/python -c "import pyradiosky; print(pyradiosky.__version__)"
   ```

4. **Verify no CASA conflicts** (MEDIUM PRIORITY):
   - Test that CASA tools still work after pyradiosky installation
   - Check for version conflicts with casacore, casatools, etc.
   - Test critical CASA operations (ft(), tclean, etc.) after installation

### Risk Assessment

**Low Risk**:
- ✓ Python 3.11.13 is compatible
- ✓ All pyradiosky dependencies are already installed (astropy, numpy, pandas, h5py, scipy, pyuvdata)
- ✓ pyuvdata 3.2.4 is already working with CASA in the pipeline
- ✓ DP3 Docker image exists and is recent

**Medium Risk**:
- ⚠️ DP3 has not been tested in actual pipeline usage (wrapper exists but not called)
- ⚠️ Need to verify DP3 Docker integration works correctly
- ⚠️ Need to test DP3 predict writes MODEL_DATA correctly
- ⚠️ pyradiosky installation may conflict with CASA (needs testing)

**High Risk**:
- ⚠️ DP3 predict may have different behavior than CASA ft() (needs validation)
- ⚠️ Integration testing required before production use

## Next Steps

1. **Immediate**: Check pyuvdata availability
2. **Short-term**: Test DP3 predict with existing NVSS conversion
3. **Short-term**: Install and test pyradiosky in casa6 environment
4. **Medium-term**: Create integration tests for pyradiosky + DP3 workflow
5. **Long-term**: Full pipeline integration if tests pass

## Conclusion

**Compatibility is LIKELY but NOT VERIFIED**. The codebase has good infrastructure:

**✓ Positive indicators**:
- All pyradiosky dependencies are already installed and working
- pyuvdata 3.2.4 is installed and used extensively in the pipeline
- DP3 Docker image exists and is recent
- DP3 wrapper code exists (though not currently used)

**⚠️ Unknowns**:
- DP3 is not currently used in production (needs testing)
- pyradiosky is not installed (needs installation and testing)
- No integration tests exist for pyradiosky + DP3 workflow
- Need to verify DP3 predict behavior matches CASA ft()

**Recommendation**: 
1. **Start with DP3 testing** (higher priority - already integrated, just needs validation)
2. **Then test pyradiosky installation** (lower risk - dependencies already present)
3. **Finally integrate** pyradiosky + DP3 workflow with comprehensive testing

**Overall assessment**: **LOW-MEDIUM RISK** - Good foundation exists, but needs validation testing before production use.

