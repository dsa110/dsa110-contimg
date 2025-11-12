# DP3 Integration Plan: Sky Model Seeding & Calibration Application

## Overview

**Proposed Workflow:**
1. **DP3** for visibility operations:
   - Sky model prediction (seeding MODEL_DATA)
   - Calibration application (applycal equivalent)
2. **WSClean** for imaging/deconvolution

## Benefits of Using DP3

### Sky Model Seeding (DP3 Predict vs CASA ft())

**DP3 Advantages:**
- **Faster**: DP3 is optimized for visibility operations and can be 2-5x faster than CASA ft()
- **Memory efficient**: Processes data in chunks, better for large MS files
- **Native sky model format**: Supports DP3/BBS sky model format directly
- **Better integration**: Can seamlessly work with WSClean (same sky model format)

**Current CASA ft() Limitations:**
- Slower for large component lists
- Memory intensive for many sources
- Requires CASA component list format conversion

### Calibration Application (DP3 ApplyCal vs CASA applycal)

**DP3 Advantages:**
- **Faster**: Optimized calibration application routines
- **Better memory management**: Handles large MS files more efficiently
- **Supports CASA caltables**: Can read CASA calibration tables
- **Flexible**: Can combine with DP3-specific calibration steps if needed

**Current CASA applycal Limitations:**
- Can be slow for large MS files
- Memory intensive operations
- Single-threaded performance

## Implementation Plan

### Phase 1: DP3 Sky Model Seeding ✓ (COMPLETED)

**Created `predict_from_skymodel_dp3()` wrapper:**

Location: `src/dsa110_contimg/calibration/dp3_wrapper.py`

Features:
- Converts NVSS catalogs to DP3 sky model format (`.skymodel`)
- Converts calibrator point sources to DP3 sky model format
- Uses DP3 Predict step to seed MODEL_DATA column
- Supports operations: `replace`, `add`, `subtract`
- Optional primary beam model application

**Sky Model Format:**
DP3 uses a simple text format:
```
Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, ReferenceFrequency='1400000000.0', MajorAxis, MinorAxis, Orientation
s0c0,POINT,07:02:53.6790,+44:31:11.940,2.4,[0.0],false,1400000000.0,,,
```

### Phase 2: DP3 Calibration Application (LIMITED)

**Important Finding:** DP3 ApplyCal requires **ParmDB format**, not CASA calibration tables.

**Current Status:**
- DP3 ApplyCal cannot directly use CASA tables (K, BP, G tables)
- Created `apply_calibration_dp3()` wrapper that falls back to CASA applycal
- Future work needed: Convert CASA tables to ParmDB or use DP3 GainCal directly

**Workaround:**
- Continue using CASA `applycal` for calibration application
- Focus on DP3 Predict for sky model seeding (main speedup)

### Phase 3: Integration with Existing Workflow

**Update `image_ms()` function:**
- Add `use_dp3_seeding` parameter
- Add `use_dp3_applycal` parameter
- Route to DP3 functions when enabled
- Keep WSClean for imaging (already implemented)

## Sky Model Format Conversion

**DP3 Sky Model Format:**
```
Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, ReferenceFrequency='1400000000.0', MajorAxis, MinorAxis, Orientation
s0c0,POINT,07:02:53.6790,+44:31:11.940,2.4,[-0.7],false,1400000000.0,,,
```

**Conversion Function Needed:**
```python
def convert_nvss_to_dp3_skymodel(
    center_ra_deg: float,
    center_dec_deg: float,
    radius_deg: float,
    min_mjy: float = 10.0,
    freq_ghz: float = 1.4,
    out_path: str,
) -> str:
    """Convert NVSS catalog to DP3 sky model format."""
    # Query NVSS catalog
    # Format as DP3 sky model text file
    # Return path to .skymodel file
```

## Performance Comparison

### Expected Speedup

**Sky Model Seeding:**
- CASA ft(): ~30-60 seconds for 100 sources
- DP3 Predict: ~10-20 seconds (estimated 2-3x faster)

**Calibration Application:**
- CASA applycal: ~60-120 seconds for large MS
- DP3 ApplyCal: ~20-40 seconds (estimated 2-3x faster)

**Total Pipeline Speedup:**
- Pre-imaging steps: ~90-180 seconds → ~30-60 seconds
- ~2-3x faster preprocessing while keeping WSClean imaging speed

## DP3 Installation Requirements

**Dependencies:**
- DP3 (Data Processing Pipeline 3)
- Casacore (for MS support)
- EveryBeam (for DSA-110 beam models)
- CMake, C++17 compiler

**Installation Options:**
1. **Build from source** (recommended for Ubuntu 18.04)
2. **Docker container** (similar to WSClean approach)
3. **System package** (if available)

## Implementation Steps

1. **Install DP3** (Docker or build from source)
2. **Create DP3 sky model converter** from NVSS/calibrator catalogs
3. **Implement `ft_from_cl_dp3()`** wrapper
4. **Implement `apply_to_target_dp3()`** wrapper
5. **Add flags to `image_ms()`** for DP3 usage
6. **Benchmark performance** vs CASA baseline
7. **Update pipeline scripts** to use DP3 optionally

## Compatibility Considerations

**DP3 + CASA Caltables:**
- DP3 can read CASA calibration tables (K, BP, G tables)
- Format compatibility confirmed

**DP3 + WSClean:**
- Both support DP3 sky model format
- Seamless integration

**DP3 + EveryBeam:**
- DP3 uses EveryBeam for primary beam models
- DSA-110 support should work (same as WSClean)

## Code Structure (IMPLEMENTED)

```
src/dsa110_contimg/calibration/
├── applycal.py          # Existing (still used for CASA applycal)
├── skymodels.py         # Existing (keep for CASA ft() fallback)
└── dp3_wrapper.py       # NEW: DP3 Predict wrapper + sky model converters
    ├── convert_nvss_to_dp3_skymodel()
    ├── convert_calibrator_to_dp3_skymodel()
    ├── predict_from_skymodel_dp3()
    └── apply_calibration_dp3()  # Falls back to CASA for now
```

## Next Steps

1. **Build/Install DP3** (Docker or from source) ✓ Repository cloned at `/home/ubuntu/proj/DP3` ✓ Docker image built
2. **Test DP3 Predict** on test MS ✗ Failed: DP3 requires 4 polarizations, DSA-110 uses 2-pol
3. **Benchmark DP3 Predict vs CASA ft()** ✗ **BLOCKED**: Cannot test due to polarization mismatch
4. **Integrate into `image_ms()` workflow** ✗ **BLOCKED**: DP3 incompatible with DSA-110 MS format
5. **Investigate CASA→ParmDB conversion** ✗ **BLOCKED**: Polarization requirement blocks DP3 usage

## Critical Finding: DP3 Incompatibility

**DP3 requires 4 polarizations, but DSA-110 uses 2 polarizations.**

See `/data/dsa110-contimg/docs/reports/dp3_test_results.md` for detailed test results and limitations.

**Recommendation:** Continue using CASA tools (`ft()` for seeding, `applycal` for calibration) until DP3 supports 2-pol or MS conversion is implemented.

## Notes

- **Backward compatibility**: Keep CASA functions as fallback
- **Progressive rollout**: Make DP3 optional initially, enable by default if faster
- **Error handling**: Graceful fallback to CASA if DP3 fails
- **Documentation**: Update workflows to mention DP3 option

