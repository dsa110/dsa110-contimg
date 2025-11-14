# CASA-mpi Evaluation for DSA-110 Continuum Imaging Pipeline

**Date:** 2025-11-12  
**Evaluator:** AI Assistant  
**Context:** Evaluation of CASA-mpi for MPI parallelization on remote HPC server

---

## Executive Summary

**Recommendation: LOW PRIORITY / NOT RECOMMENDED for current pipeline**

CASA-mpi provides MPI parallelization for CASA tasks (primarily `tclean`), but has limited applicability to the DSA-110 pipeline due to:

1. **Backend mismatch**: Pipeline uses **WSClean as default** (2-5x faster than tclean), not CASA tclean
2. **MPI version incompatibility**: HPC has OpenMPI 2.1.1, but CASA-mpi requires **OpenMPI >= 5.0**
3. **Limited benefit**: Current parallel processing already handles independent MS operations efficiently
4. **Complexity cost**: Would require MPI infrastructure upgrade and code changes for marginal gains

**Verdict**: Only consider if:
- Switching back to tclean as primary imaging backend
- Processing very large continuum images or cubes that benefit from intra-task parallelization
- HPC infrastructure can be upgraded to OpenMPI >= 5.0

---

## CASA-mpi Capabilities

### What It Provides

1. **Automatic parallelization** (Scenario 1: Plugin for casatasks):
   - Parallel imaging for cubes and continuum (tclean)
   - Multi-MS parallelization for flagdata, setjy, applycal, etc.
   - Transparent to user - just install casampi alongside casatasks

2. **Advanced MPI infrastructure** (Scenario 2: Direct usage):
   - MPI command client/server architecture
   - Custom parallelization schemes (e.g., ALMA/VLA Tier0 pipeline)
   - Fine-grained control over MPI processes

### Requirements

- **mpi4py >= 4.0** (CASA 6.7.2+)
- **OpenMPI >= 5.0** (CASA-mpi verified/tested with 5.0.1)
- **Thread-safe MPI** (compiled with `--enable-mpi-thread-multiple`)
- **casatools** (required dependency)
- **casatasks** (for automatic parallelization scenario)

### Current HPC Environment

```
✓ OpenMPI: 2.1.1 (INSTALLED, but TOO OLD - need >= 5.0)
✓ Python: 3.11.13 (casa6 environment)
✓ CASA: Available (casatools, casatasks)
✓ MPI infrastructure: Present (mpirun, mpicc)
✗ OpenMPI version: Incompatible (2.1.1 < 5.0 required)
```

**Blocking Issue**: OpenMPI 2.1.1 is incompatible. CASA-mpi requires OpenMPI >= 5.0 due to:
- Bug fixes in MPI communication (OpenMPI 4.x has obscure failures)
- Thread-safety requirements (MPI_THREAD_MULTIPLE support)
- API compatibility with mpi4py 4.0+

---

## Current Pipeline Architecture

### Imaging Backend

**Primary**: WSClean (default, 2-5x faster than tclean)
- Native parallelization via OpenMP threads
- No MPI required
- Faster deconvolution algorithms

**Secondary**: CASA tclean (optional, via `--backend tclean`)
- Used for compatibility/testing
- Single-threaded per MS
- Would benefit from CASA-mpi if used as primary

### Current Parallelization Strategy

The pipeline already implements efficient parallelization:

1. **Conversion**: Parallel per-subband writes (16 workers) → CASA concat
2. **Independent MS processing**: ProcessPoolExecutor for multiple MS files
3. **Batch operations**: Parallel flagging, calibration across MS files

**Performance characteristics:**
- MS metadata reads: < 1ms (cached)
- Subband loading: < 5 minutes for 16 subbands (batched)
- Calibration: < 30 minutes for standard preset
- Imaging: < 60 minutes for standard field (WSClean)

### Bottlenecks Identified

From profiling guide (`docs/reference/optimizations/PROFILING_GUIDE.md`):

1. **MS table reads** (`getcol`, `getcell`) - Already optimized with caching
2. **MODEL_DATA calculation** - Single-threaded CASA operation
3. **File I/O** (reading/writing MS files) - Already parallelized
4. **tclean deconvolution** - Only relevant if using tclean backend

**Key Insight**: Current bottlenecks are either:
- Already optimized (caching, batching)
- I/O-bound (already parallelized)
- Only relevant for tclean (not primary backend)

---

## Use Case Analysis

### Scenario 1: Parallel tclean for Large Images

**When beneficial:**
- Very large continuum images (>4096 pixels)
- Spectral cubes (multiple channels)
- Single large MS that doesn't fit in memory

**Current pipeline:**
- Uses WSClean (faster, no MPI needed)
- Standard images: 1024-2048 pixels (manageable)
- No spectral cubes (MFS mode)

**Verdict**: Not applicable - WSClean handles this better

### Scenario 2: Multi-MS Parallelization

**When beneficial:**
- Processing many MS files in parallel
- flagdata, setjy, applycal across multiple MS

**Current pipeline:**
- Already uses ProcessPoolExecutor for independent MS
- Achieves 2-4x speedup on multi-core systems
- No MPI overhead

**Verdict**: Current approach is sufficient and simpler

### Scenario 3: Intra-task Parallelization (Cube Imaging)

**When beneficial:**
- Large spectral cubes
- Continuum imaging with many channels
- Memory-intensive operations within single tclean call

**Current pipeline:**
- MFS mode (no cubes)
- Standard continuum imaging
- WSClean handles this efficiently

**Verdict**: Not applicable to current workflow

---

## Cost-Benefit Analysis

### Costs

1. **Infrastructure upgrade**:
   - Upgrade OpenMPI from 2.1.1 to >= 5.0
   - May require HPC admin privileges
   - Potential compatibility issues with other software

2. **Code changes**:
   - Switch from WSClean to tclean as primary backend
   - Modify imaging CLI to support MPI mode
   - Update job runner to use mpirun
   - Testing and validation

3. **Maintenance overhead**:
   - Additional dependency (casampi)
   - MPI debugging complexity
   - Performance tuning for MPI processes

4. **Performance trade-offs**:
   - WSClean is 2-5x faster than tclean
   - MPI overhead for small jobs
   - Resource allocation complexity

### Benefits

1. **Parallel tclean** (if using tclean):
   - Speedup for large images/cubes
   - Better memory distribution
   - Multi-node capability

2. **Multi-MS parallelization**:
   - Already achieved with ProcessPoolExecutor
   - Minimal additional benefit

3. **Future-proofing**:
   - If switching to tclean for specific features
   - If processing large cubes in future

### Net Assessment

**Costs >> Benefits** for current pipeline:
- Lose WSClean performance advantage
- Require infrastructure upgrade
- Add complexity for marginal gains
- Current parallelization already efficient

---

## Recommendations

### Short-term (Current Pipeline)

**DO NOT implement CASA-mpi** because:
1. WSClean is faster and doesn't need MPI
2. Current parallelization is sufficient
3. OpenMPI version is incompatible
4. Complexity cost outweighs benefits

**Continue with:**
- WSClean as primary imaging backend
- ProcessPoolExecutor for independent MS processing
- Existing optimization strategies (caching, batching)

### Medium-term (If Requirements Change)

**Consider CASA-mpi if:**
1. **Switching to tclean** for specific features**:
   - Advanced deconvolution algorithms
   - Specific CASA features not in WSClean
   - Compatibility requirements

2. **Processing large cubes**:
   - Spectral line imaging
   - Multi-frequency synthesis with many channels
   - Memory-intensive operations

3. **HPC infrastructure upgraded**:
   - OpenMPI >= 5.0 available
   - Multi-node MPI support needed
   - Resource allocation supports MPI jobs

### Implementation Path (If Proceeding)

1. **Upgrade OpenMPI**:
   ```bash
   # Requires HPC admin or module system
   module load openmpi/5.0.1  # or equivalent
   ```

2. **Install casampi**:
   ```bash
   MPICC=/path/to/mpicc pip install --target=$CASA6_PYTHON casampi
   ```

3. **Verify installation**:
   ```python
   from casampi.MPIEnvironment import MPIEnvironment
   assert MPIEnvironment.is_mpi_enabled
   ```

4. **Modify imaging code**:
   - Add MPI mode detection
   - Use mpirun for tclean calls
   - Update job runner for MPI execution

5. **Testing**:
   - Benchmark vs WSClean
   - Validate MPI communication
   - Test on representative datasets

---

## Alternative Approaches

### If Parallelization Needed

1. **WSClean multi-threading**:
   - Already uses OpenMP
   - No MPI required
   - Better performance than tclean

2. **ProcessPoolExecutor** (current):
   - Independent MS processing
   - Simple, effective
   - No infrastructure changes

3. **Job-level parallelization**:
   - Submit multiple imaging jobs to HPC scheduler
   - Let scheduler handle resource allocation
   - Simpler than MPI coordination

### If tclean Required

1. **Single-threaded tclean**:
   - Acceptable for current image sizes
   - No infrastructure changes
   - Simpler debugging

2. **Hybrid approach**:
   - WSClean for production
   - tclean for specific validation/comparison
   - No MPI needed for occasional use

---

## Conclusion

CASA-mpi is a well-designed MPI parallelization framework for CASA, but it has **limited applicability** to the current DSA-110 pipeline:

1. **Backend mismatch**: Pipeline uses WSClean (faster, no MPI needed)
2. **Infrastructure incompatibility**: OpenMPI 2.1.1 < 5.0 required
3. **Diminishing returns**: Current parallelization already efficient
4. **Complexity cost**: Infrastructure upgrade + code changes for marginal gains

**Recommendation**: **Do not implement CASA-mpi** unless:
- Switching to tclean as primary backend (unlikely given WSClean performance)
- Processing large spectral cubes (not current use case)
- HPC infrastructure upgraded and multi-node MPI needed

**Priority**: Low - focus optimization efforts on:
- WSClean tuning
- I/O optimization
- Caching strategies
- Job scheduling efficiency

---

## References

- CASA-mpi README: `~/proj/casampi/README.md`
- CASA Parallel Processing Docs: https://casadocs.readthedocs.io/en/stable/notebooks/parallel-processing.html
- Pipeline Profiling Guide: `docs/reference/optimizations/PROFILING_GUIDE.md`
- Pipeline Optimization API: `docs/reference/optimizations/OPTIMIZATION_API.md`
- Current Parallel Processing: `src/dsa110_contimg/utils/parallel.py`

