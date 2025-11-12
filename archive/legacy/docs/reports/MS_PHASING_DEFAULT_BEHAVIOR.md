# MS Phasing Default Behavior

**Date:** 2025-11-05  
**Context:** Understanding whether all MS data is phased to meridian by default

---

## Summary

**Answer: It depends on the conversion path:**

1. **Single file conversion** (`convert single`): Phasing is **OPTIONAL** (can be disabled)
   - Default: **DISABLED** (unless `--enable-phasing` flag is used)
   - Function default: `True` (but CLI overrides this)

2. **Subband groups conversion** (`convert groups`): Phasing is **ALWAYS** performed
   - No option to disable - always phases to meridian

---

## Code Paths

### Path 1: Single File Conversion

**CLI Command:** `convert single`  
**File:** `src/dsa110_contimg/conversion/uvh5_to_ms.py`

**Function:** `convert_single_file()`  
**Default:** `enable_phasing: bool = True` (line 909)

**CLI Argument:** `--enable-phasing` (line 1214-1216)
- `action="store_true"` means:
  - **Without flag**: `args.enable_phasing = False`
  - **With flag**: `args.enable_phasing = True`

**CLI Usage** (line 1252):
```python
enable_phasing=args.enable_phasing,
```

**Result:**
- **Without `--enable-phasing` flag**: Phasing is **DISABLED** (CLI passes `False`)
- **With `--enable-phasing` flag**: Phasing is **ENABLED**

**Code Location:**
```python
# Line 985-989
if enable_phasing:
    logger.info("Phasing to meridian at midpoint of observation")
    phase_to_meridian(uvd, phase_reference_time)
else:
    logger.info("Skipping explicit phasing (using original phasing)")
```

---

### Path 2: Subband Groups Conversion

**CLI Command:** `convert groups`  
**File:** `src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`

**Function:** `convert_subband_groups_to_ms()`  
**Phasing:** Always performed (no option to disable)

**Code Location:**
```python
# Line 340-342
def _set_phase_and_uvw(uv: UVData) -> tuple[u.Quantity, u.Quantity, u.Quantity]:
    phase_to_meridian(uv)  # Always called, no option to skip
    return (...)
```

**Usage** (line 628):
```python
pt_dec, phase_ra, phase_dec = _set_phase_and_uvw(uv)
```

**Result:**
- **ALWAYS phases to meridian** - no way to disable this path

---

## Issue Identified

There's a **mismatch** between function default and CLI behavior:

1. **Function default**: `enable_phasing: bool = True`
2. **CLI default** (without flag): `args.enable_phasing = False`

This means:
- **Function-level**: Phasing defaults to enabled
- **CLI-level**: Phasing defaults to disabled (unless flag used)

**Current behavior**: CLI takes precedence, so phasing is **disabled by default** for single file conversion.

---

## Recommendation

For consistency, the CLI should match the function default:

**Option 1: Make CLI default match function default (True)**
```python
parser.add_argument(
    "--disable-phasing",  # Changed to --disable-phasing
    action="store_true",
    help="Disable phasing of the data (use original phasing).",
)
# Then in code:
enable_phasing = not args.disable_phasing
```

**Option 2: Make function default match CLI default (False)**
```python
def convert_single_file(..., enable_phasing: bool = False, ...):
```

**Option 3: Make CLI explicit (no default)**
Require user to explicitly specify `--enable-phasing` or `--disable-phasing`

---

## Current Behavior Summary

| Conversion Path | Phasing Default | Can Disable? |
|----------------|-----------------|--------------|
| **Single file** (`convert single`) | **DISABLED** (no flag) | ✅ Yes (via CLI) |
| **Subband groups** (`convert groups`) | **ALWAYS ENABLED** | ❌ No |

---

## Verification

To check if an MS is phased to meridian:

```python
from casacore.tables import table
import numpy as np

ms_path = "/data/ms/2025-10-29T13:54:17.ms"

with table(f"{ms_path}::FIELD", readonly=True, ack=False) as field_tb:
    if "PHASE_DIR" in field_tb.colnames():
        phase_dir = field_tb.getcol("PHASE_DIR")[0][0]
        ra_rad = phase_dir[0]
        dec_rad = phase_dir[1]
        ra_deg = np.rad2deg(ra_rad)
        dec_deg = np.rad2deg(dec_rad)
        
        # Check if RA matches LST at midpoint
        # (LST calculation depends on observation time)
        print(f"Phase center: RA={ra_deg:.6f}°, Dec={dec_deg:.6f}°")
```

---

## Conclusion

**Answer to question**: **No, not all data is phased to meridian by default.**

- **Single file conversion**: Phasing is **disabled by default** (requires `--enable-phasing` flag)
- **Subband groups conversion**: Phasing is **always enabled** (no option to disable)

For production use, the subband groups path (which is the main production path) **always phases to meridian**, so in practice, most MS files will be phased to meridian.

