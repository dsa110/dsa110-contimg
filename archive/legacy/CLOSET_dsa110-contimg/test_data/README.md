# Test Data Directory

This directory contains organized test measurement set files used during development and debugging of the DSA-110 pipeline.

## Directory Structure

```
test_data/
├── README.md                    # This file
├── test_files_summary.md       # Detailed organization summary
├── uvw_testing/                # UVW coordinate testing files (12 files, ~1.6 GB)
├── output_testing/             # Output format testing files (3 files, ~393 MB)
├── debugging/                  # Debug and development files (4 files, ~393 MB)
└── archived/                   # Future archival location for old test data
```

## File Categories

### UVW Testing (`uvw_testing/`)
Contains measurement sets used for testing UVW coordinate calculations, preservation, and restoration:
- `test_ms_uvw_preservation.ms` - UVW preservation testing
- `test_ms_uvw_restoration.ms` - UVW restoration testing
- `test_ms_uvw_restoration_fixed.ms` - Fixed restoration version
- `test_ms_uvw_immediate.ms` - Immediate UVW processing
- `test_ms_uvw_recalc.ms` - UVW recalculation testing
- `test_ms_uvw_recalc_corrected.ms` - Corrected recalculation
- `test_ms_uvw_recalc_final.ms` - Final recalculation version
- `test_ms_uvw_recalc_final_corrected.ms` - Final corrected version
- `test_ms_uvw_recalc_fixed.ms` - Fixed recalculation
- `test_ms_uvw_recalc_time_fixed.ms` - Time-fixed recalculation
- `test_ms_uvw_recalc_time_fixed2.ms` - Second time-fixed version
- `test_ms_simple_uvw_fix.ms` - Simple UVW fix testing

### Output Testing (`output_testing/`)
Contains measurement sets used for testing different output formats:
- `test_output.ms` - Basic output testing
- `test_original_output.ms` - Original output format
- `test_improved_output.ms` - Improved output format

### Debugging (`debugging/`)
Contains measurement sets used for debugging and development:
- `test_ms_uvw_debug.ms` - UVW debugging
- `test_ms_uvw_restoration_debug.ms` - UVW restoration debugging
- `test_ms_uvw_shape_debug.ms` - UVW shape debugging
- `test_direct_mod.ms` - Direct modification testing

## Usage

These test files are organized for easy access during development and debugging. When working on UVW coordinate issues, check the `uvw_testing/` directory. For output format issues, check `output_testing/`. For general debugging, check `debugging/`.

## Maintenance

- **Archiving**: Move old test files to `archived/` when they're no longer needed
- **Cleanup**: Periodically review and remove test files that are no longer relevant
- **Documentation**: Update this README when adding new test file categories

## Total Storage

- **Total files**: 19 measurement sets
- **Total size**: ~2.4 GB
- **Organization date**: 2025-09-06
