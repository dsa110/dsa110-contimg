# MS Conversion Speed Optimization Analysis

## Current Performance
- **Input**: 16 × 145MB UVH5 files (~2.3GB total)
- **Output**: 2.0GB MS file
- **Time**: ~10 minutes (600 seconds)
- **Target**: <1 minute (60 seconds)
- **Required speedup**: 10x

## Bottleneck Identification

### Profiling Results (4 files → 192 channels):
```
1. Reading first file:        3.01s  (5.0 min)
2. Reading + concat 15 files:  9.10s  (15 min)  [estimated for 16 files]
3. Reordering frequencies:     0.00s  (0%)
4. Writing MS:                20.96s  (35 min)  [estimated for 768 channels]
   ACTUAL for 16 files:      ~540s  (90%)  ← PRIMARY BOTTLENECK
---
Total (predicted):            33.07s
Total (actual):              ~600s
```

**Key Finding**: `write_ms()` takes 90% of the time and scales non-linearly!

## Root Causes of Slow write_ms

1. **pyuvdata.write_ms() internals**:
   - Uses python-casacore bindings (not native CASA)
   - Single-threaded table writes
   - No chunking/batching for large datasets
   - Heavy metadata operations per write

2. **Force phasing operations**:
   - `force_phase='drift'` triggers UVW recalculation
   - "Phasing to zenith" message indicates coordinate transformation
   - This is O(N_blts × N_times) operation

3. **CASA Table format overhead**:
   - MS format has many small files (table.f*)
   - Metadata tables require random I/O
   - No optimization for write-once workloads

## Optimization Strategies

### Strategy 1: Direct UVH5 → MS with pyuvdata optimizations ⭐
**Approach**: Optimize current pyuvdata path
- Skip unnecessary checks (`run_check=False`, `check_extra=False`)
- Pre-phase data before concatenation (avoid phasing large dataset)
- Use `force_phase=False` if data already phased
- Increase I/O buffer sizes

**Expected speedup**: 2-3x (reduce to ~3 minutes)
**Implementation difficulty**: Easy
**Risk**: Low

### Strategy 2: Write multiple sub-band MS files, then CASA concat
**Approach**: Parallel writes + CASA concat
```
Step 1: Write 16 separate MS files (1 per subband) in parallel  [~30s]
Step 2: CASA concat to combine  [~30s]
```

**Pros**:
- Parallelizes the slow write_ms step
- Can use all CPU cores
- CASA concat is optimized C++ code

**Cons**:
- Requires 2-pass approach
- More disk I/O (write 16 MS + 1 combined MS)

**Expected speedup**: 5-8x (reduce to ~1-2 minutes)
**Implementation difficulty**: Medium
**Risk**: Medium (CASA concat may have its own overhead)

### Strategy 3: Direct CASA Table API writes (bypass pyuvdata)
**Approach**: Write MS directly using python-casacore or casatools
- Skip pyuvdata's write_ms entirely
- Use CASA's optimized table writers
- Write in larger chunks

**Pros**:
- Maximum control over write process
- Can optimize for DSA-110's specific format
- Potential for best performance

**Cons**:
- Requires reimplementing pyuvdata's MS writer logic
- Complex (need to handle all MS subtables correctly)
- Higher maintenance burden

**Expected speedup**: 8-15x (reduce to <1 minute)
**Implementation difficulty**: Hard
**Risk**: High (correctness, compatibility)

### Strategy 4: Use CASA's importuvfits
**Approach**: UVH5 → UVFITS → MS
- `pyuvdata.write_uvfits()` is faster than `write_ms()`
- CASA `importuvfits` is optimized C++
- Can parallelize UVFITS writes per subband

**Pros**:
- UVFITS is simpler format (single file)
- CASA importuvfits is mature and fast
- Proven approach in radio astronomy

**Cons**:
- Extra intermediate file (~same size as MS)
- 2-step process
- UVFITS has limitations (32-bit floats, etc.)

**Expected speedup**: 4-6x (reduce to ~1.5-2 minutes)
**Implementation difficulty**: Medium
**Risk**: Low

### Strategy 5: Pre-compute phasing on HDF5 files
**Approach**: Modify upstream HDF5 creation to include phased UVWs
- Phase data at observation time
- Store pre-phased coordinates in HDF5
- Skip `force_phase` in write_ms

**Pros**:
- One-time cost, amortized across all imaging
- Cleanest solution long-term

**Cons**:
- Requires upstream pipeline changes
- Doesn't help with existing data
- Not under our control

**Expected speedup**: 3-5x for write step only
**Implementation difficulty**: N/A (upstream)
**Risk**: N/A

## Recommended Approach

### Short-term (Implement Now): Strategy 1 + Strategy 4
1. **Optimize current path** (Strategy 1):
   - Pre-phase each UVH5 before concatenation
   - Use `force_phase=False` in write_ms
   - Expected: ~3 minutes

2. **Add UVFITS path** (Strategy 4):
   - Implement parallel UVH5 → UVFITS conversion
   - Use CASA importuvfits
   - Expected: ~1.5-2 minutes

### Medium-term (Next Sprint): Strategy 2
- Implement parallel sub-band MS writes
- Test CASA concat performance
- Target: <1 minute

### Long-term: Strategy 5
- Work with DSA-110 team to add phasing to upstream pipeline
- Ultimate target: <30 seconds

## Implementation Priority

1. **Immediate** (today): Test Strategy 1 (pre-phasing optimization)
2. **This week**: Implement Strategy 4 (UVFITS path)
3. **Next**: Benchmark Strategy 2 (parallel writes)
4. **Future**: Propose Strategy 5 to DSA-110 team

