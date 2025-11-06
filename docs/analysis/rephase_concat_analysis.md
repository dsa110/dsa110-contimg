# Rephasing + Concatenation Analysis

## Current Situation

The MS has 24 fields, each representing a 12.5-second integration in a drift scan:
- Fields have different phase centers (tracking source motion)
- RA spans ~0.11 degrees across fields
- Each field has ~74k rows

## Rephasing + Concatenation Approach

### What It Would Do

1. **Rephase all fields** to a common phase center (e.g., calibrator position)
2. **Concatenate fields** into a single field
3. **Result**: Single-field MS that DP3 can process

### Why This Might Be Fine

1. **You already do rephasing**: `rephase_ms_to_calibrator()` exists and is used
2. **Rephasing is standard**: Common operation in radio astronomy
3. **Preserves data**: Rephasing is a phase rotation, doesn't lose information
4. **Better S/N**: Combining all integrations gives full S/N, not 12.5-second chunks

### Potential Concerns

1. **Phase errors**: If rephasing is inaccurate, could introduce errors
   - **Mitigation**: You already have tested rephasing code
   
2. **Data integrity**: Need to ensure concatenation preserves everything
   - **Mitigation**: CASA concat is well-tested
   
3. **Reversibility**: Once concatenated, can't easily separate back
   - **Mitigation**: Work on a copy (which we're already doing)
   
4. **UVW coordinates**: Need to ensure UVW are updated correctly
   - **Mitigation**: Rephasing should handle this

## Implementation

```python
def prepare_ms_for_dp3(ms_path: str, target_phase_center: tuple) -> str:
    """Rephase and concatenate MS for DP3 processing.
    
    Args:
        ms_path: Path to multi-field MS
        target_phase_center: (RA_deg, Dec_deg) for rephasing
        
    Returns:
        Path to single-field MS ready for DP3
    """
    # 1. Rephase all fields to common center
    rephase_ms_to_calibrator(
        ms_path, 
        target_phase_center[0],
        target_phase_center[1],
        "DP3_target",
        logger,
    )
    
    # 2. Concatenate fields into single field
    # (CASA concat or custom implementation)
    
    # 3. Return path to concatenated MS
    return concatenated_ms_path
```

## Recommendation

**Rephasing + concatenation is actually a reasonable approach** because:

1. ✓ You already have rephasing infrastructure
2. ✓ Rephasing is a standard, well-understood operation
3. ✓ Preserves full S/N (all integrations combined)
4. ✓ Makes DP3 work without field-by-field processing
5. ✓ Works on a copy, so original data is safe

**The main requirement**: Ensure rephasing is done correctly and concatenation preserves data integrity.

## Next Steps

1. Test rephasing on the test MS
2. Test concatenation after rephasing
3. Verify DP3 works on the concatenated MS
4. Validate MODEL_DATA is correct

