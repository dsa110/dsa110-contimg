# Roadmap to 100% Confidence in Synthetic Data Suite

## Goal

Achieve **100% confidence** in both:

1. **Pipeline Testing** (currently 95%)
2. **Science Validation** (currently 70%, excluding real data comparison)

---

## Current State Analysis

### Pipeline Testing: 95% → 100% (5% gap)

**Remaining Gaps:**

1. ⚠️ **Performance testing** - Large datasets, many sources
2. ⚠️ **Memory usage** - Very large arrays
3. ⚠️ **Concurrent generation** - Multiple processes
4. ⚠️ **Long time series** - Many integrations
5. ⚠️ **Edge cases** - Extreme parameter values, antenna configurations

### Science Validation: 70% → 100% (30% gap)

**Remaining Gaps:**

1. ⚠️ **Multi-source fields** - Only single source per UVH5
2. ⚠️ **Spectral index** - Flux constant across frequency
3. ⚠️ **Time variability** - Sources are static
4. ⚠️ **Complex morphologies** - Only point, Gaussian, disk
5. ⚠️ **RFI simulation** - No RFI contamination
6. ⚠️ **Crowded fields** - Sparse source distribution
7. ⚠️ **Catalog completeness** - Few sources vs. real catalogs

---

## Implementation Plan

### Phase 1: Pipeline Testing → 100% (Priority: HIGH)

#### 1.1 Performance Testing Suite ✅ **IMPLEMENT**

**Goal:** Test generation with realistic data volumes

**Tasks:**

- [ ] Create `tests/performance/test_synthetic_data_performance.py`
- [ ] Test generation with:
  - Large datasets (100+ subbands, 1000+ integrations)
  - Many sources (10+ sources per field)
  - Large frequency ranges (full bandwidth)
- [ ] Benchmark generation time vs. data volume
- [ ] Memory profiling for large arrays
- [ ] Document performance characteristics

**Files:**

- `tests/performance/test_synthetic_data_performance.py` (NEW)
- `docs/reference/SYNTHETIC_DATA_PERFORMANCE.md` (NEW)

**Confidence Gain:** +2% (95% → 97%)

---

#### 1.2 Edge Case Testing ✅ **IMPLEMENT**

**Goal:** Comprehensive edge case coverage

**Tasks:**

- [ ] Extreme parameter values:
  - Very large/small flux (1e-6 to 1e6 Jy)
  - Very extended sources (size > field of view)
  - Very high/low system temperature
  - Extreme calibration errors (gain > 1.0, phase > 180°)
- [ ] Antenna configuration edge cases:
  - Minimum antennas (2-3 antennas)
  - Maximum antennas (110+ antennas)
  - Irregular antenna layouts
  - Missing antenna data
- [ ] Time/frequency edge cases:
  - Single integration
  - Very long time series (24+ hours)
  - Single channel
  - Very wide bandwidth
- [ ] Coordinate edge cases:
  - Poles (dec = ±90°)
  - Equator (dec = 0°)
  - Date line (ra = 0°/360°)

**Files:**

- `tests/unit/simulation/test_edge_cases.py` (NEW)
- Update existing test files

**Confidence Gain:** +2% (97% → 99%)

---

#### 1.3 Concurrent Generation Testing ✅ **IMPLEMENT**

**Goal:** Test parallel generation scenarios

**Tasks:**

- [ ] Test concurrent UVH5 generation (multiple processes)
- [ ] Test concurrent catalog generation
- [ ] Test thread safety of random number generators
- [ ] Test file locking and I/O contention
- [ ] Performance comparison: sequential vs. parallel

**Files:**

- `tests/integration/test_concurrent_generation.py` (NEW)

**Confidence Gain:** +1% (99% → 100%)

---

### Phase 2: Science Validation → 100% (Priority: HIGH)

#### 2.1 Multi-Source Fields ✅ **IMPLEMENT**

**Goal:** Generate fields with multiple sources

**Tasks:**

- [ ] Add `--n-sources` parameter to `make_synthetic_uvh5.py`
- [ ] Implement source position distribution:
  - Random uniform distribution
  - Clustered distribution (galaxy groups)
  - Grid distribution (for testing)
- [ ] Implement flux distribution:
  - Power law (realistic source counts)
  - Uniform (for testing)
  - Custom (user-specified)
- [ ] Update visibility generation to sum multiple sources
- [ ] Update catalog generation to include all sources
- [ ] Add unit tests for multi-source visibility

**Files:**

- `src/dsa110_contimg/simulation/make_synthetic_uvh5.py` (UPDATE)
- `src/dsa110_contimg/simulation/visibility_models.py` (UPDATE)
- `tests/unit/simulation/test_multi_source.py` (NEW)

**Confidence Gain:** +5% (70% → 75%)

---

#### 2.2 Spectral Index ✅ **IMPLEMENT**

**Goal:** Frequency-dependent flux (realistic source spectra)

**Tasks:**

- [ ] Add `--spectral-index` parameter (default: -0.7 for synchrotron)
- [ ] Implement frequency-dependent flux:
  - `S(ν) = S(ν₀) * (ν/ν₀)^α`
  - Where α is spectral index
- [ ] Update visibility generation per frequency channel
- [ ] Support multiple spectral indices (per source)
- [ ] Add unit tests for spectral index behavior
- [ ] Update documentation with spectral index examples

**Files:**

- `src/dsa110_contimg/simulation/make_synthetic_uvh5.py` (UPDATE)
- `src/dsa110_contimg/simulation/visibility_models.py` (UPDATE)
- `tests/unit/simulation/test_spectral_index.py` (NEW)

**Confidence Gain:** +5% (75% → 80%)

---

#### 2.3 Time Variability ✅ **IMPLEMENT**

**Goal:** Time-dependent flux (for variability studies)

**Tasks:**

- [ ] Add `--variability` parameter with models:
  - Constant (default)
  - Linear drift (flux = flux₀ + rate \* t)
  - Sinusoidal (flux = flux₀ + amplitude _ sin(2π _ t / period))
  - Exponential decay (flux = flux₀ \* exp(-t / τ))
  - Random walk (stochastic variability)
- [ ] Update visibility generation per time integration
- [ ] Support multiple variability models (per source)
- [ ] Add unit tests for time variability
- [ ] Update documentation with variability examples

**Files:**

- `src/dsa110_contimg/simulation/make_synthetic_uvh5.py` (UPDATE)
- `src/dsa110_contimg/simulation/visibility_models.py` (UPDATE)
- `tests/unit/simulation/test_time_variability.py` (NEW)

**Confidence Gain:** +5% (80% → 85%)

---

#### 2.4 Complex Source Morphologies ✅ **IMPLEMENT**

**Goal:** Support more realistic source shapes

**Tasks:**

- [ ] Add `--source-model` options:
  - `double` - Double source (two point sources)
  - `jet` - Jet model (extended + point core)
  - `ring` - Ring source (annular brightness)
  - `sersic` - Sérsic profile (galaxy-like)
- [ ] Implement visibility models for each:
  - Double: Two point sources with separation
  - Jet: Point + extended component
  - Ring: Bessel function (J₀) for uniform ring
  - Sérsic: Numerical Fourier transform
- [ ] Add unit tests for each morphology
- [ ] Update documentation with morphology examples

**Files:**

- `src/dsa110_contimg/simulation/visibility_models.py` (UPDATE)
- `tests/unit/simulation/test_complex_morphologies.py` (NEW)

**Confidence Gain:** +5% (85% → 90%)

---

#### 2.5 RFI Simulation ✅ **IMPLEMENT**

**Goal:** Realistic RFI contamination

**Tasks:**

- [ ] Add `--add-rfi` parameter with RFI types:
  - Narrowband (single channel)
  - Broadband (multiple channels)
  - Time-dependent (bursts)
  - Frequency-dependent (sweeping)
  - Antenna-specific (local interference)
- [ ] Implement RFI injection:
  - Add strong signals to specific channels/times
  - Optionally flag contaminated data
  - Realistic RFI patterns (narrowband, broadband, bursts)
- [ ] Add unit tests for RFI injection
- [ ] Update documentation with RFI examples

**Files:**

- `src/dsa110_contimg/simulation/visibility_models.py` (UPDATE)
- `src/dsa110_contimg/simulation/make_synthetic_uvh5.py` (UPDATE)
- `tests/unit/simulation/test_rfi_simulation.py` (NEW)

**Confidence Gain:** +5% (90% → 95%)

---

#### 2.6 Enhanced Catalog Generation ✅ **IMPLEMENT**

**Goal:** More realistic catalog completeness and density

**Tasks:**

- [ ] Add `--catalog-density` parameter:
  - `sparse` - Few sources (current default)
  - `normal` - Realistic density (~100 sources/deg²)
  - `crowded` - High density (~1000 sources/deg²)
- [ ] Implement source count distribution:
  - Power law flux distribution (dN/dS ∝ S^α)
  - Realistic source counts (NVSS-like)
- [ ] Add background sources (not in phase center):
  - Random positions in field
  - Realistic flux distribution
  - Optionally include in visibility generation
- [ ] Update catalog generation to include all sources
- [ ] Add unit tests for catalog density

**Files:**

- `src/dsa110_contimg/simulation/synthetic_catalog.py` (UPDATE)
- `src/dsa110_contimg/simulation/make_synthetic_uvh5.py` (UPDATE)
- `tests/unit/simulation/test_catalog_density.py` (NEW)

**Confidence Gain:** +5% (95% → 100%)

---

## Implementation Priority

### High Priority (Complete First)

1. **Multi-Source Fields** - Enables crowded field testing
2. **Spectral Index** - Critical for multi-frequency science
3. **Edge Case Testing** - Ensures robustness
4. **Performance Testing** - Validates scalability

### Medium Priority

5. **Time Variability** - Important for variability studies
6. **Complex Morphologies** - Realistic source shapes
7. **Enhanced Catalog Generation** - Realistic source counts

### Lower Priority

8. **RFI Simulation** - Important but can be added later
9. **Concurrent Generation** - Nice to have for performance

---

## Estimated Effort

| Feature               | Effort   | Priority | Confidence Gain |
| --------------------- | -------- | -------- | --------------- |
| Multi-Source Fields   | 2-3 days | High     | +5%             |
| Spectral Index        | 2-3 days | High     | +5%             |
| Edge Case Testing     | 1-2 days | High     | +2%             |
| Performance Testing   | 1-2 days | High     | +2%             |
| Time Variability      | 2-3 days | Medium   | +5%             |
| Complex Morphologies  | 3-4 days | Medium   | +5%             |
| Enhanced Catalogs     | 2-3 days | Medium   | +5%             |
| RFI Simulation        | 3-4 days | Low      | +5%             |
| Concurrent Generation | 1-2 days | Low      | +1%             |

**Total Effort:** ~20-30 days for complete implementation

**Minimum for 100%:** ~10-15 days (High priority items)

---

## Validation Plan

### After Each Phase

1. **Run full test suite** - Ensure no regressions
2. **Generate validation dataset** - Test with new features
3. **Run pipeline end-to-end** - Verify all stages work
4. **Compare with real data** - Validate realism (when available)

### Final Validation

1. **Comprehensive test suite** - All features covered
2. **Performance benchmarks** - Documented characteristics
3. **Example datasets** - Demonstrating all features
4. **Documentation** - Complete usage guide

---

## Success Criteria

### Pipeline Testing: 100%

- ✅ All edge cases tested
- ✅ Performance validated at scale
- ✅ Memory usage documented
- ✅ Concurrent generation works
- ✅ No known limitations

### Science Validation: 100% (excluding real data)

- ✅ Multi-source fields supported
- ✅ Spectral index implemented
- ✅ Time variability supported
- ✅ Complex morphologies available
- ✅ RFI simulation implemented
- ✅ Realistic catalog density
- ✅ All features tested

---

## Related Documentation

- `docs/analysis/SYNTHETIC_DATA_CONFIDENCE_ASSESSMENT.md` - Current confidence
  levels
- `docs/analysis/SYNTHETIC_DATA_PIPELINE_STAGE_COVERAGE.md` - Pipeline coverage
- `docs/how-to/testing_crossmatch_stage_with_synthetic_data.md` - Usage examples
