# Bandpass Calibration Performance Issue

**Date:** 2025-11-02  
**Phase:** 3.2 (Calibration)  
**Status:** IDENTIFIED - Same root cause as K-calibration performance issue

## Problem Statement

Bandpass calibration is taking >8 minutes (and still running) for a 16-SPW MS with ~1.7M rows. This is abnormally slow and indicates a performance bottleneck.

## Root Cause Analysis

**Identified:** `solve_bandpass()` processes 16 SPWs **sequentially** (one at a time), similar to the K-calibration performance issue that was identified earlier.

### Evidence:

1. **CASA log shows 16 solution intervals:**
   ```
   INFO	Calibrater::solve	For solint = inf, found 16 solution intervals.
   ```
   This indicates CASA is solving each SPW separately.

2. **Code analysis:**
   - `solve_bandpass()` does NOT have a `combine_spw` parameter (unlike `solve_delay`)
   - `casa_bandpass()` calls on lines 458 and 485 do NOT include `combine='spw'`
   - Each SPW is processed sequentially, multiplying runtime by 16x

3. **Process status:**
   - Runtime: 8+ minutes (still running)
   - CPU: 101% (actively processing)
   - Status: Stuck in phase solve after amplitude solve completed

## Comparison with K-Calibration Fix

We previously fixed K-calibration performance by:
1. Adding `--combine-spw` CLI argument
2. Adding `combine_spw` parameter to `solve_delay()`
3. Passing `combine='spw'` to `casa_gaincal()`

**The same solution should be applied to `solve_bandpass()`.**

## Proposed Solution

### 1. Add `combine_spw` parameter to `solve_bandpass()`

```python
def solve_bandpass(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    table_prefix: Optional[str] = None,
    set_model: bool = True,
    model_standard: str = "Perley-Butler 2017",
    combine_fields: bool = False,
    combine_spw: bool = False,  # NEW PARAMETER
    minsnr: float = 5.0,
    uvrange: str = "",
) -> List[str]:
```

### 2. Add `combine='spw'` to `casa_bandpass()` calls

```python
# For amplitude solve
comb = "scan,field" if combine_fields else ""
if combine_spw:
    comb = f"{comb},spw" if comb else "spw"
    
kwargs = dict(
    ...
    combine=comb,  # Include 'spw' if combine_spw=True
    ...
)
```

### 3. Add `--combine-spw` CLI argument for bandpass

```python
"--combine-spw",
action="store_true",
help=(
    "Combine spectral windows when solving bandpass calibration. "
    "Recommended for multi-SPW MS files to improve performance. "
    "Default: process SPWs separately"
),
```

### 4. Pass `combine_spw` from CLI to `solve_bandpass()`

```python
bptabs = solve_bandpass(
    ms_in,
    field_sel,
    refant,
    ktabs[0] if ktabs else None,
    combine_fields=bool(args.bp_combine_field),
    combine_spw=args.combine_spw,  # NEW
    uvrange=(...),
)
```

## Expected Impact

- **Current:** 16 SPWs × ~30 seconds per SPW = ~8+ minutes (and counting)
- **With fix:** Single solve across all SPWs = ~30-60 seconds total
- **Speedup:** 8-16x faster

## Scientific Validity

Combining SPWs during bandpass solve is scientifically sound because:
- Bandpass solutions are frequency-dependent, but the **gain structure** across SPWs is often similar
- Combining SPWs uses all available data to derive a single, consistent solution
- This is the same approach used successfully for K-calibration

## Implementation Priority

**HIGH** - This is blocking the testing pipeline and causing excessive runtime.

## Files to Modify

1. `src/dsa110_contimg/calibration/calibration.py` - Add `combine_spw` parameter and pass to `casa_bandpass`
2. `src/dsa110_contimg/calibration/cli.py` - Add CLI argument and pass to `solve_bandpass`
3. `docs/reports/CALIBRATION_PERFORMANCE_ISSUE_2025-11-03.md` - Update with bandpass findings

## Testing

After implementation, verify:
1. Bandpass calibration completes in <2 minutes for 16-SPW MS
2. Bandpass tables are created successfully
3. Calibration solutions are valid (QA checks pass)

