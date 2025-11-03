# K-Calibration Performance Investigation

**Date:** 2025-11-03  
**MS:** `/scratch/dsa110-contimg/ms/0834_transit/2025-10-29T09:03:19.ms`  
**Command:** `--combine-spw --fast --uvrange '>1klambda'`  
**Status:** Running >8 minutes (expected 3-5 minutes)

## Investigation

### Key Finding: `combine='spw'` Behavior

**Important Discovery:**
- `combine='spw'` in CASA gaincal combines the **SOLUTION**, not the processing
- CASA still processes all data from all 16 SPWs
- MODEL_DATA is evaluated across all SPW channels
- This means computational load is still high even with `combine='spw'`

### Data Volume Analysis

For a 5-minute MS with:
- ~1.7M rows
- 16 SPWs
- ~110 antennas
- uvrange filter `>1klambda`

Even with uvrange filtering (which reduces data by ~30-50%), the remaining volume is:
- Still millions of data points
- Across 16 SPWs (even if solution is combined)
- Requires MODEL_DATA evaluation for each SPW channel

### Performance Bottlenecks Identified

1. **MODEL_DATA Evaluation:**
   - Must be computed for each SPW channel
   - Even with `combine='spw'`, CASA processes all channels
   - This is computationally expensive

2. **SPW Processing:**
   - `combine='spw'` doesn't reduce processing time as much as expected
   - Still processes all 16 SPWs internally
   - Only difference: one solution instead of 16 separate solutions

3. **Large Dataset:**
   - ~1.7M rows is a significant amount of data
   - Even with filtering, remains computationally intensive

### Expected vs Actual Performance

**Original Expectation:**
- `combine='spw'` would process all SPWs together = 16x speedup
- uvrange filtering = 30-50% reduction
- Expected: 3-5 minutes

**Reality:**
- `combine='spw'` only speeds up by avoiding separate solution iterations
- Still processes all SPW data
- Actual: 8+ minutes (and still running)

### Recommendations

1. **Accept Current Performance:**
   - 8-10 minutes for a 1.7M row, 16-SPW MS may be reasonable
   - Still better than sequential processing (would be >20 minutes)

2. **Further Optimization Options:**
   - Use time/channel averaging (creates subset MS)
   - Process only a subset of SPWs (scientifically less sound)
   - Accept current performance as baseline

3. **Set Realistic Expectations:**
   - For multi-SPW MS files, 5-10 minutes may be normal
   - Optimizations help but don't eliminate the computational load
   - Still faster than sequential SPW processing

## Conclusion

The slower-than-expected performance is likely due to:
- `combine='spw'` not providing as much speedup as anticipated
- Large data volume even after filtering
- MODEL_DATA evaluation across all SPWs

**Action:** Wait for current calibration to complete, then reassess expectations based on actual runtime.

