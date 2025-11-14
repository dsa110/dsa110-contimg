# DP3 Multi-Field MS Issue

## Problem

DP3 predict fails with error: "Multiple entries in FIELD table" when processing MS files with multiple fields.

## Test Case

- MS: `/tmp/dp3_pyradiosky_test/test_ms.ms`
- Fields: 24 fields in FIELD table
- Error occurs even with:
  - `msin.field=0` (selecting first field)
  - `predict.fieldids=0` (predicting for first field)
  - Empty steps (just reading MS)

## Possible Solutions

1. **Process fields separately**: Split MS by field, process each separately
2. **DP3 version issue**: May need different DP3 version or configuration
3. **MS format issue**: May need to preprocess MS to single-field format
4. **DP3 limitation**: May be a known limitation with multi-field MS files

## Workaround Options

1. Use CASA `ft()` for multi-field MS files (current approach)
2. Process each field separately with DP3
3. Create single-field MS copies for DP3 processing

## Status

**BLOCKED**: Cannot proceed with DP3 predict on multi-field MS files until this issue is resolved.

## Next Steps

1. Check DP3 documentation for multi-field support
2. Test with single-field MS file
3. Consider field-by-field processing approach
4. Investigate DP3 version compatibility

