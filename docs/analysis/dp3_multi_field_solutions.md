# DP3 Multi-Field MS Solutions

## Problem

DP3 predict fails with error: "Multiple entries in FIELD table" when processing MS files with multiple fields, even when trying to select a single field.

## Possible Solutions

### Option 1: Process Fields Separately (RECOMMENDED)

Process each field individually with DP3, then combine results:

```python
def predict_from_skymodel_dp3_multi_field(ms_path, sky_model_path, fields=None):
    """Process each field separately."""
    # Get field list
    if fields is None:
        # Get all fields from MS
        fields = get_field_list(ms_path)
    
    # Process each field
    for field_id in fields:
        predict_from_skymodel_dp3(
            ms_path, 
            sky_model_path,
            field=str(field_id),
        )
```

**Pros:**
- No data transformation needed
- Preserves original MS structure
- Can parallelize field processing

**Cons:**
- Multiple DP3 calls (slower)
- More complex code

### Option 2: Phaseshift + Concatenate (NOT RECOMMENDED)

Phaseshift all fields to common phase center, concatenate into single field:

**Pros:**
- Single DP3 call
- Simpler processing

**Cons:**
- Significant data transformation
- Loss of original field structure
- May introduce artifacts
- Requires phaseshifting infrastructure
- Not reversible

### Option 3: Use CASA ft() as Fallback (CURRENT APPROACH)

For multi-field MS files, fall back to CASA ft():

```python
def predict_from_skymodel(ms_path, sky_model_path, use_dp3=True):
    """Use DP3 if possible, otherwise CASA ft()."""
    if use_dp3 and is_single_field_ms(ms_path):
        predict_from_skymodel_dp3(ms_path, sky_model_path)
    else:
        # Convert to componentlist and use CASA ft()
        convert_skymodel_to_componentlist(sky_model_path)
        ft_from_cl(ms_path, componentlist_path)
```

**Pros:**
- Works with all MS types
- No data transformation
- Proven approach

**Cons:**
- CASA ft() is slower
- Still have CASA ft() phase center bugs

### Option 4: Investigate DP3 Configuration

Check if DP3 has configuration options for multi-field MS:
- Different DP3 version
- Different parset parameters
- DP3 documentation/community support

## Recommendation

**Use Option 1 (Process Fields Separately)** for DP3, with **Option 3 (CASA ft() fallback)** as backup:

1. Check if MS is single-field → use DP3 directly
2. If multi-field → process each field separately with DP3
3. If DP3 fails → fall back to CASA ft()

This gives:
- Speed benefit of DP3 when possible
- Compatibility with all MS types
- No data transformation
- Graceful degradation

