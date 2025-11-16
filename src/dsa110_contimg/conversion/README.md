# Conversion Module: UVH5 → Measurement Set

This module handles conversion of UVH5 subband files to CASA Measurement Set
(MS) format.

## Overview

The conversion process:

1. Reads UVH5 subband files using pyuvdata
2. Applies time-dependent phasing (meridian-tracking, RA=LST)
3. Sets antenna positions and telescope metadata
4. Writes to CASA MS format
5. Concatenates subbands into a single MS
6. Configures MS for imaging

## Expected Behaviors

### Phase Center Incoherence (EXPECTED)

**Important**: After conversion, phase centers may appear "incoherent" across
fields (subbands). **This is expected and correct behavior.**

**Why?**

- Each subband uses **time-dependent phasing** (meridian-tracking)
- Phase centers track LST: `RA = LST(time)` for each time sample
- When subbands are concatenated, each subband becomes a separate FIELD
- Different FIELDs have different phase centers because they were observed at
  different times
- This follows radio interferometry best practices for continuous phase tracking

**What to expect:**

- Phase center separations of **hundreds to thousands of arcseconds** are normal
- Separation roughly matches LST change over the observation time span
- Example: 5-minute observation → ~75 arcsec separation (15°/hour × 0.083 hours)

**Validation:**

- The `validate_phase_center_coherence()` function automatically detects
  time-dependent phasing
- If detected, it skips the strict coherence check
- If not detected but separation > 60 arcsec, assume time-dependent phasing

**Error Messages:** If you see:
`"Phase centers are incoherent... Maximum separation: X arcsec"`

- **If separation > 60 arcsec**: This is likely time-dependent phasing
  (expected)
- **If separation < 60 arcsec**: This may indicate a conversion issue

### MS Structure After Conversion

- **Multiple FIELDs**: One per subband (16 subbands = 16 FIELDs)
- **Time-dependent phase centers**: Each FIELD has phase centers tracking LST
- **Spectral windows**: Each FIELD corresponds to one spectral window (former
  subband)

## Common Issues

### "Phase centers are incoherent" Error

**Symptom**: Validation error about incoherent phase centers

**Solution**:

- Check if separation > 60 arcsec → This is expected for time-dependent phasing
- Check observation time span → Separation should match LST change
- If separation is small (< 60 arcsec) but still incoherent, check conversion
  logs

### MS Validation Failures

**Symptom**: MS fails validation checks

**Common causes:**

- Invalid or corrupted UVH5 files
- Missing antenna positions
- Incorrect time format

**Solution**: Check conversion logs for specific error messages

## Key Functions

- `convert_subband_groups_to_ms()`: Main conversion function for subband groups
- `convert_single_file()`: Convert a single UVH5 file to MS
- `configure_ms_for_imaging()`: Prepare MS for imaging (adds columns,
  initializes weights)
- `validate_phase_center_coherence()`: Validate phase centers (handles
  time-dependent phasing)

## Phasing Details

The conversion uses **meridian-tracking phasing** (`phase_to_meridian()`):

- Phase centers track the meridian (RA = LST) throughout the observation
- Each unique time sample gets its own phase center
- This ensures proper phase coherence as Earth rotates
- Prevents phase errors from accumulating

See `conversion/helpers_coordinates.py` for implementation details.

## Validation

The conversion process includes several validation checks:

1. **Phase center coherence**: Checks for time-dependent phasing (expected) vs
   errors
2. **UVW precision**: Validates UVW coordinate accuracy
3. **Frequency order**: Ensures frequencies are in ascending order
4. **MS structure**: Validates required columns and data integrity

All validations handle expected behaviors (like time-dependent phasing)
gracefully.

## Troubleshooting

### Conversion Fails with Phase Center Error

1. Check separation value:
   - > 60 arcsec → Expected (time-dependent phasing)
   - < 60 arcsec → May indicate issue
2. Check observation time span
3. Review conversion logs for details

### MS Appears Invalid After Conversion

1. Verify UVH5 files are valid
2. Check disk space
3. Review conversion logs for specific errors
4. Try re-converting with validation enabled

## References

- `conversion/helpers_coordinates.py`: Phasing implementation
- `conversion/helpers_validation.py`: Validation functions
- `conversion/ms_utils.py`: MS configuration utilities
- `conversion/strategies/hdf5_orchestrator.py`: Main conversion orchestrator
