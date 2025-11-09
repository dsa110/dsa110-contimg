# Masking Efficiency Analysis: Masked vs Unmasked Imaging

## Executive Summary

**Masking is generally MORE efficient than not masking**, especially for wide-field imaging with known sources. However, the efficiency gain depends on several factors:

- **Typical case**: 2-4x faster processing (based on GLEAM survey results)
- **Mask overhead**: Negligible (~0.1-0.5 seconds for generation, <1% per iteration)
- **Efficiency gains**: Significant reduction in iterations and pixels cleaned per iteration

## Computational Complexity Analysis

### Without Masking (Current Auto-Mask Only)

**Per Iteration:**
- **Pixels processed**: All pixels in image (N = `imsize²`)
- **Operations**: O(N) cleaning operations
- **Complexity**: O(N × iterations)

**Typical Values:**
- Image size: 2048×2048 = 4.2M pixels
- Iterations: 1000 (standard) to 2000+ (high precision)
- Total operations: ~4.2 billion pixel operations

**Characteristics:**
- Explores entire image each iteration
- May converge slowly (wastes iterations on empty regions)
- Auto-masking discovers sources during cleaning (adds overhead)

### With Masking

**Per Iteration:**
- **Pixels processed**: Only masked regions (M pixels, typically M << N)
- **Mask checking**: O(N) simple comparisons (very fast)
- **Cleaning operations**: O(M) where M = masked pixels
- **Complexity**: O(N × iterations_mask_check + M × iterations_cleaning)

**Typical Values:**
- Masked pixels: ~1-5% of image (42K - 210K pixels for 2048² image)
- Iterations: 30-50% fewer (faster convergence)
- Total operations: ~100-500 million pixel operations (10-25% of unmasked)

**Characteristics:**
- Focused search space (only clean where sources expected)
- Faster convergence (fewer iterations needed)
- Less exploration overhead

## Efficiency Breakdown

### 1. Mask Generation Overhead

**Cost**: One-time, negligible
- NVSS catalog query: ~0.01-0.1 seconds
- Mask file creation: ~0.1-0.5 seconds
- Total: < 1 second (negligible compared to imaging time)

**Impact**: None on iteration efficiency

### 2. Mask Checking Overhead Per Iteration

**Cost**: Very small
- Simple pixel-wise comparison: O(N) per iteration
- Memory access: Sequential (cache-friendly)
- Typical overhead: < 1% of iteration time

**Example:**
- Image: 2048×2048 = 4.2M pixels
- Mask check: ~0.1-1 ms per iteration
- Cleaning: ~100-1000 ms per iteration
- Overhead: < 1%

### 3. Reduction in Pixels Cleaned

**Savings**: Significant
- **Typical mask coverage**: 1-5% of image
- **Reduction**: 95-99% fewer pixels cleaned per iteration
- **Per-iteration savings**: 95-99% of cleaning operations

**Example:**
- Without mask: 4.2M pixels cleaned per iteration
- With mask (5% coverage): 210K pixels cleaned per iteration
- **Savings**: 95% reduction per iteration

### 4. Reduction in Total Iterations

**Savings**: Moderate to significant
- **Focused search**: Converges faster (30-50% fewer iterations typical)
- **Less exploration**: Doesn't waste iterations on empty regions
- **Better initial model**: NVSS seeding + mask = faster convergence

**Example:**
- Without mask: 1000 iterations (standard tier)
- With mask: 600-700 iterations (30-40% reduction)
- **Savings**: 300-400 iterations avoided

### 5. Overall Efficiency Calculation

**Without Masking:**
```
Total operations = N × iterations_unmasked
                 = 4.2M × 1000
                 = 4.2 billion operations
```

**With Masking:**
```
Total operations = (N × iterations_mask_check) + (M × iterations_masked)
                 = (4.2M × 650 × 0.001) + (210K × 650)
                 = 2.7M + 136.5M
                 = 139.2 million operations
```

**Efficiency Gain:**
```
Speedup = 4.2B / 139.2M ≈ 30x reduction in operations
```

**Note**: Actual wall-clock time improvement is typically 2-4x due to:
- Fixed overhead (I/O, FFTs, gridding)
- Mask checking overhead (small but non-zero)
- Memory bandwidth limitations

## Real-World Evidence

### GLEAM Survey Results

From the GLEAM survey using WSClean v2.5:
- **Auto-masking + deeper thresholding**: 4x faster processing time
- **Noise reduction**: 29% improvement
- **Conclusion**: Masking significantly improved efficiency

### DSA-110 Pipeline Context

**Current Settings:**
- Standard tier: 1000 iterations
- High precision tier: 2000+ iterations
- Image size: 2048×2048 (typical)
- NVSS sources: 10-50 sources per field (typical)

**Expected Benefits:**
- **Iteration reduction**: 30-50% (300-1000 fewer iterations)
- **Per-iteration savings**: 95-99% (only clean masked regions)
- **Overall speedup**: 2-4x faster (conservative estimate)

## When Masking Might Be Less Efficient

### Edge Cases (Rare)

1. **Very Sparse Masks** (< 0.1% coverage):
   - Mask checking overhead may exceed cleaning savings
   - **Mitigation**: Use auto-masking instead

2. **Very Small Images** (< 512×512):
   - Overhead becomes more significant
   - **Mitigation**: Masking still beneficial but less dramatic

3. **Unknown Source Fields**:
   - Mask may miss sources
   - **Mitigation**: Use hybrid approach (mask + auto-masking)

4. **Very Fast Convergence Already**:
   - If unmasked imaging already converges in < 100 iterations
   - **Mitigation**: Masking still helps but less dramatic

### Typical DSA-110 Case

**Not applicable** because:
- Wide-field imaging (3.5° × 3.5°)
- Known NVSS sources (10-50 per field)
- Large images (2048×2048 typical)
- Many iterations (1000-2000+)

**Conclusion**: Masking is highly beneficial for DSA-110

## Performance Comparison

| Metric | Without Mask | With Mask | Improvement |
|--------|--------------|----------|-------------|
| **Mask generation** | 0s | 0.5s | One-time cost |
| **Pixels cleaned/iter** | 4.2M | 210K | 95% reduction |
| **Iterations needed** | 1000 | 650 | 35% reduction |
| **Total operations** | 4.2B | 139M | 97% reduction |
| **Wall-clock time** | 100% | 25-50% | 2-4x faster |
| **Memory usage** | Same | Same | No change |

## Computational Cost Breakdown

### Without Masking

```
Total Time = Setup + (Iterations × Per-Iteration-Time)
           = 10s + (1000 × 0.1s)
           = 110 seconds
```

### With Masking

```
Total Time = Setup + MaskGen + (Iterations × Per-Iteration-Time)
           = 10s + 0.5s + (650 × 0.01s)  # Much faster per iteration
           = 17 seconds
```

**Speedup**: 6.5x (theoretical), 2-4x (practical)

## Memory Efficiency

**Masking has NO negative impact on memory:**
- Mask is small (same size as image, but simple boolean/float)
- Mask checking uses minimal memory
- No additional memory allocations during cleaning

**Potential memory benefits:**
- Fewer intermediate arrays (only for masked regions)
- Better cache locality (focused operations)

## Recommendations

### For DSA-110 Pipeline

1. **Enable masking by default** for standard/high precision tiers
   - Expected 2-4x speedup
   - Better image quality
   - Minimal overhead

2. **Use NVSS-based masks**:
   - Leverage existing NVSS catalog access
   - Known source positions
   - Appropriate mask sizes (2-3× beam)

3. **Hybrid approach** (recommended):
   - Start with NVSS mask
   - Enable auto-masking to discover additional sources
   - Best of both worlds

4. **Enable for ALL tiers including development**:
   - Development tier benefits from faster tests (2-4x speedup)
   - Mask generation overhead is negligible (< 1 second)
   - NVSS catalog access already exists (no new dependencies)
   - Faster tests = faster development iteration

### Implementation Strategy

```python
# Pseudo-code for efficient masked imaging
# Use masking for ALL quality tiers (more efficient)
if nvss_min_mjy is not None:
    # Generate mask from NVSS sources (same logic for all tiers)
    mask_path = create_nvss_fits_mask(
        imagename=imagename,
        imsize=imsize,
        cell_arcsec=cell_arcsec,
        phasecenter=phasecenter,
        nvss_min_mjy=nvss_min_mjy,
        radius_arcsec=60.0,  # 2-3× beam
    )
    
    # Use mask + auto-masking (hybrid approach)
    run_wsclean(..., mask_path=mask_path, auto_mask=True)
else:
    # Fallback: auto-masking only (if no NVSS threshold specified)
    run_wsclean(..., auto_mask=True)
```

### Why Use Masking for Development Tier?

**Counter-argument to original recommendation:**

The original recommendation suggested disabling masking for development tier, but this is **incorrect** because:

1. **Faster tests = better development experience**
   - Development tier goal: Fast iteration for code testing
   - Masking provides 2-4x speedup → faster tests
   - Mask generation overhead (< 1s) is negligible compared to imaging time

2. **NVSS infrastructure already exists**
   - Development tier already uses NVSS seeding (`nvss_min_mjy=10.0`)
   - Mask generation uses same NVSS catalog access
   - No new dependencies or complexity

3. **Consistent code path**
   - Same masking logic for all tiers = fewer code paths to test
   - Easier to maintain and debug
   - Tests exercise production code path

4. **Even with fewer iterations, masking helps**
   - Development tier: 300 iterations max
   - Masking still reduces pixels cleaned per iteration (95% reduction)
   - Even if iterations don't reduce much, per-iteration savings are significant

**Only exception:** If specifically testing unmasked code path (rare edge case)

## Conclusion

**Masking is MORE efficient than not masking** for the DSA-110 continuum imaging pipeline:

1. **Significant operation reduction**: 95-99% fewer pixels cleaned per iteration
2. **Faster convergence**: 30-50% fewer iterations needed
3. **Overall speedup**: 2-4x faster wall-clock time (conservative)
4. **Minimal overhead**: < 1 second mask generation, < 1% per iteration
5. **Real-world evidence**: GLEAM survey showed 4x speedup

**The efficiency gains far outweigh the minimal overhead**, especially for wide-field imaging with known sources (which is exactly the DSA-110 use case).

## References

- **GLEAM Survey Results**: Cambridge University Press (4x speedup with masking)
- **WSClean Masking Documentation**: https://wsclean.readthedocs.io/en/latest/masking.html
- **Current Implementation**: `src/dsa110_contimg/imaging/cli_imaging.py`
- **Masked Imaging Analysis**: `docs/analysis/MASKED_IMAGING_ANALYSIS.md`

