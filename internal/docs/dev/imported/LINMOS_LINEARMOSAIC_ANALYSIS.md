# linmos vs linearmosaic Analysis

## Question
Are we making use of CASA's `linmos` function?

## Answer
**No, we are not using `linmos` or `linearmosaic`.**

## Investigation Results

### 1. `linmos` Does Not Exist in CASA
- **Not found in `casatasks`**: Import error confirmed
- **Not found in `casatools`**: Not available
- **`linmos` is from MIRIAD**: Another radio astronomy software package
- **ASKAPsoft has `linmos`**: But we're using CASA, not ASKAPsoft

### 2. CASA Has `linearmosaic` Tool (Not Task)
- **Available in `casatools`**: As a toolkit tool (not a task)
- **Also called `lm`**: Shorthand name
- **Purpose**: Linear mosaicking with weighted combination
- **Not a standard task**: Accessed through tools system, not `casatasks`

### 3. Our Current Approach
**We use `imregrid` + `immath` for mosaicking:**

```python
# From mosaic/cli.py
from casatasks import imregrid, immath

# 1. Regrid tiles to common coordinate system
imregrid(imagename=tile, template=template, output=regridded_tile)

# 2. Combine using immath with PB weighting
immath(imagename=[regridded_tiles], expr='weighted_combination', outfile=mosaic)
```

**Why we don't use `linearmosaic`:**
- `linearmosaic` is a toolkit tool (more complex API)
- `imregrid` + `immath` provides explicit control
- Our approach matches VAST's workflow pattern
- Simpler to understand and debug

## Comparison

| Aspect | `linearmosaic` (CASA) | Our Approach (`imregrid` + `immath`) |
|--------|----------------------|-------------------------------------|
| **Type** | Toolkit tool | Standard tasks |
| **Complexity** | Higher-level API | Lower-level, explicit |
| **Control** | Less explicit | More explicit |
| **Error Handling** | Built-in | Manual (more transparent) |
| **PB Weighting** | Built-in | Manual (Sault weighting) |
| **Coordinate System** | Handles automatically | Explicit via `imregrid` |

## Recommendation

**Our current approach is appropriate:**
- Uses standard CASA tasks (`imregrid`, `immath`)
- Provides explicit control over each step
- Matches VAST's workflow pattern
- Easier to debug and understand
- Handles edge cases explicitly

**Potential Future Consideration:**
- Could explore `linearmosaic` if we need:
  - More automated workflow
  - Built-in PB handling
  - Less code to maintain
- But current approach is working well

## Conclusion

**We are NOT using `linmos` or `linearmosaic`.**

- `linmos` doesn't exist in CASA (it's from MIRIAD/ASKAPsoft)
- `linearmosaic` exists but we use `imregrid` + `immath` instead
- Our approach is appropriate and working well
- No changes needed

