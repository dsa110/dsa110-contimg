# DP3 Multi-Field MS: Recommendation

## Problem Summary

DP3 predict fails with multi-field MS files (24 fields = 12.5 second integrations each) with error: "Multiple entries in FIELD table".

**Key Constraint**: Processing 12.5-second integrations separately would have extremely poor S/N and is not viable.

## Analysis

### Current Situation
- MS has 24 fields (likely 12.5 second integrations)
- Each field has ~74k rows
- DP3 fails even when selecting a single field
- Error suggests DP3 has fundamental issue with multi-field MS structure

### Why Field-by-Field Processing Won't Work
- 12.5 second integrations have very low S/N individually
- Would need to combine results anyway
- Defeats purpose of using DP3 for speed

### Why Phaseshift+Concatenate is Problematic
- Significant data transformation
- Loss of original field structure
- May introduce artifacts
- Requires phaseshifting infrastructure
- Not easily reversible

## Recommendation: Hybrid Approach

**Use DP3 for single-field MS, fall back to CASA ft() for multi-field MS:**

```python
def predict_from_skymodel_smart(
    ms_path: str,
    sky_model_path: str,
    *,
    prefer_dp3: bool = True,
) -> None:
    """Smart prediction: DP3 for single-field, CASA ft() for multi-field.
    
    Args:
        ms_path: Path to Measurement Set
        sky_model_path: Path to sky model (DP3 format or componentlist)
        prefer_dp3: Prefer DP3 when possible (single-field MS)
    """
    # Check field count
    from casacore.tables import table
    field_table = table(ms_path + "/FIELD", readonly=True)
    nfields = field_table.nrows()
    field_table.close()
    
    if nfields == 1 and prefer_dp3:
        # Single field - use DP3 (fast)
        if sky_model_path.endswith('.skymodel'):
            predict_from_skymodel_dp3(ms_path, sky_model_path)
        else:
            # Convert to DP3 format first
            dp3_path = convert_to_dp3_format(sky_model_path)
            predict_from_skymodel_dp3(ms_path, dp3_path)
    else:
        # Multi-field - use CASA ft() (proven, works)
        if sky_model_path.endswith('.cl'):
            ft_from_cl(ms_path, sky_model_path)
        else:
            # Convert to componentlist
            cl_path = convert_to_componentlist(sky_model_path)
            ft_from_cl(ms_path, cl_path)
```

## Benefits

1. **Speed when possible**: DP3 for single-field MS (faster than CASA ft())
2. **Reliability**: CASA ft() for multi-field MS (proven, works)
3. **No data transformation**: Preserves original MS structure
4. **Graceful degradation**: Falls back automatically
5. **Best of both worlds**: Speed + compatibility

## Implementation

1. **Detect field count** in MS
2. **Route to appropriate method**:
   - Single field → DP3 predict
   - Multi-field → CASA ft() (or convert to componentlist first)
3. **Use pyradiosky** for sky model construction in both cases
4. **Convert format** as needed (SkyModel → DP3 or SkyModel → componentlist)

## Conclusion

**Don't force DP3 on multi-field MS files.** Instead:
- Use DP3 for single-field MS (where it works and is fast)
- Use CASA ft() for multi-field MS (where it's proven and reliable)
- Use pyradiosky for better sky model management in both cases

This gives us:
- ✓ Speed improvement for single-field MS
- ✓ Better tooling (pyradiosky)
- ✓ Reliability for multi-field MS
- ✓ No risky data transformations

