# QA Validation Performance Strategy: Sub-60-Second Goal

**Date:** November 11, 2025  
**Goal:** Enable robust validation of entire pipeline (streaming, manual, offline) in under 60 seconds

## Feasibility Analysis

### Current State

**Estimated Current Validation Times:**
- MS quality check: ~5-30s (depends on MS size, sampling)
- Calibration quality: ~2-10s
- Image quality: ~1-5s
- Catalog validation (astrometry): ~10-60s (catalog queries, cross-matching)
- Catalog validation (flux scale): ~15-90s (forced photometry)
- Catalog validation (source counts): ~10-60s
- Photometry validation: ~5-30s
- Variability validation: ~2-10s
- Mosaic validation: ~10-30s
- Streaming validation: ~1-5s (mostly metadata checks)
- Database validation: ~2-10s

**Total Sequential Time:** ~63-340 seconds (1-5.7 minutes)

**Verdict:** Currently **NOT feasible** for sequential execution, but **FEASIBLE** with optimization.

## Optimization Strategies

### 1. Tiered Validation Architecture

**Concept:** Multi-tier validation with fast checks first, detailed checks deferred.

```python
# Tier 1: Critical Fast Checks (<10s total)
- File existence and basic integrity
- MS structure (quick_ms_check)
- Image structure (quick_image_check)
- Database connectivity
- Streaming continuity (metadata only)

# Tier 2: Standard Checks (<30s total, parallel)
- MS quality (sampled)
- Calibration quality
- Image quality (basic metrics)
- Database consistency

# Tier 3: Detailed Checks (<60s total, parallel, optional)
- Catalog validation (astrometry, flux scale)
- Photometry validation
- Variability validation
- Mosaic validation
```

**Implementation:**
```python
from dsa110_contimg.qa.pipeline_quality import (
    check_ms_after_conversion,
    check_calibration_quality,
    check_image_quality,
)
from dsa110_contimg.qa.config import get_default_config
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def validate_pipeline_fast(
    ms_path: str,
    caltables: List[str],
    image_paths: List[str],
    timeout_seconds: int = 60,
) -> Dict:
    """Fast pipeline validation with timeout."""
    start_time = time.time()
    config = get_default_config()
    results = {}
    
    # Tier 1: Critical fast checks (<10s)
    tier1_start = time.time()
    results['tier1'] = {
        'ms_quick': quick_ms_check(ms_path),
        'images_quick': [quick_image_check(img) for img in image_paths],
        'caltables_exist': [os.path.exists(ct) for ct in caltables],
    }
    tier1_time = time.time() - tier1_start
    
    # Tier 2: Standard checks in parallel (<30s)
    tier2_start = time.time()
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(check_ms_after_conversion, ms_path, config=config, quick_check_only=False): 'ms',
            executor.submit(check_calibration_quality, caltables, config=config): 'cal',
            executor.submit(check_image_quality, image_paths[0], config=config, quick_check_only=False): 'img',
        }
        
        for future in as_completed(futures, timeout=30):
            key = futures[future]
            try:
                results[f'tier2_{key}'] = future.result(timeout=30)
            except TimeoutError:
                results[f'tier2_{key}'] = {'timeout': True}
    
    tier2_time = time.time() - tier2_start
    
    total_time = time.time() - start_time
    results['timing'] = {
        'tier1_seconds': tier1_time,
        'tier2_seconds': tier2_time,
        'total_seconds': total_time,
    }
    
    return results
```

### 2. Aggressive Sampling

**Current:** Some validations already use sampling (e.g., `sample_fraction=0.1`)

**Enhancement:** Make sampling configurable and more aggressive for fast mode:

```python
@dataclass
class FastValidationConfig:
    """Configuration for fast validation mode."""
    ms_sample_fraction: float = 0.01  # 1% instead of 10%
    image_sample_pixels: int = 10000  # Fixed pixel count
    catalog_max_sources: int = 50  # Limit catalog matches
    skip_expensive_checks: bool = True  # Skip forced photometry, etc.
    parallel_workers: int = 4
    timeout_seconds: int = 60
```

**Implementation:**
```python
def validate_ms_quality_fast(
    ms_path: str,
    sample_fraction: float = 0.01,  # 1% sampling
    config: Optional[MSQualityConfig] = None,
) -> MSQualityMetrics:
    """Fast MS validation with aggressive sampling."""
    return validate_ms_quality(
        ms_path,
        sample_fraction=sample_fraction,
        config=config,
    )
```

### 3. Caching and Incremental Validation

**Concept:** Cache validation results and only re-validate what changed.

```python
from functools import lru_cache
import hashlib
import json

def get_file_hash(file_path: str) -> str:
    """Get file hash for cache key."""
    stat = os.stat(file_path)
    return hashlib.md5(f"{file_path}:{stat.st_mtime}:{stat.st_size}".encode()).hexdigest()

@lru_cache(maxsize=100)
def validate_with_cache(
    file_path: str,
    file_hash: str,
    validation_type: str,
) -> Dict:
    """Validate with caching."""
    cache_file = f"/tmp/qa_cache/{file_hash}_{validation_type}.json"
    
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    
    # Run validation
    result = run_validation(file_path, validation_type)
    
    # Cache result
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result.to_dict(), f)
    
    return result.to_dict()
```

### 4. Parallel Execution

**Current:** Some validations can run in parallel, but not all.

**Enhancement:** Parallelize all independent validations:

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import asyncio

async def validate_pipeline_parallel(
    ms_path: str,
    caltables: List[str],
    image_paths: List[str],
    config: QAConfig,
) -> Dict:
    """Parallel pipeline validation."""
    tasks = [
        validate_ms_async(ms_path, config),
        validate_calibration_async(caltables, config),
        *[validate_image_async(img, config) for img in image_paths],
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return dict(zip(['ms', 'cal', *[f'img_{i}' for i in range(len(image_paths))]], results))
```

### 5. Lazy/Deferred Validation

**Concept:** Return immediately with quick checks, defer expensive validations.

```python
@dataclass
class ValidationResult:
    """Validation result with deferred checks."""
    passed: bool
    message: str
    quick_checks: Dict
    deferred_checks: Optional[Callable] = None  # Function to run later
    
    def run_deferred(self) -> Dict:
        """Run deferred checks."""
        if self.deferred_checks:
            return self.deferred_checks()
        return {}
```

### 6. Pre-computation and Background Jobs

**Concept:** Pre-compute expensive validations in background.

```python
from celery import Celery

app = Celery('qa_validation')

@app.task
def precompute_catalog_validation(image_path: str):
    """Pre-compute catalog validation in background."""
    result = validate_astrometry(image_path)
    cache_result(image_path, 'astrometry', result)

def validate_pipeline_with_precomputed(
    image_path: str,
    use_precomputed: bool = True,
) -> Dict:
    """Use pre-computed results if available."""
    if use_precomputed:
        cached = get_cached_result(image_path, 'astrometry')
        if cached:
            return cached
    
    # Fallback to quick check
    return quick_astrometry_check(image_path)
```

### 7. Streaming Validation (Real-time)

**Concept:** Validate as data flows, not post-processing.

```python
class StreamingValidator:
    """Validate data as it streams."""
    
    def __init__(self, config: StreamingConfig):
        self.config = config
        self.metrics = {}
    
    def validate_chunk(self, chunk: bytes) -> bool:
        """Validate a data chunk."""
        # Fast checks: size, checksum, basic structure
        if len(chunk) < self.config.min_chunk_size:
            return False
        
        # Update metrics
        self.metrics['bytes_processed'] += len(chunk)
        self.metrics['chunks_processed'] += 1
        
        return True
    
    def get_results(self) -> StreamingValidationResult:
        """Get cumulative results."""
        return StreamingValidationResult(
            passed=self.metrics['chunks_processed'] > 0,
            message=f"Processed {self.metrics['chunks_processed']} chunks",
            details=self.metrics,
        )
```

## Recommended Implementation Plan

### Phase 1: Fast Mode (<30s) - Immediate

1. **Implement tiered validation**
   - Quick checks first (<5s)
   - Standard checks in parallel (<25s)
   - Skip expensive catalog validations

2. **Aggressive sampling**
   - MS: 1% sampling
   - Images: Fixed pixel count (10k pixels)
   - Catalog: Limit to 50 sources

3. **Parallel execution**
   - Use ThreadPoolExecutor for I/O-bound tasks
   - Use ProcessPoolExecutor for CPU-bound tasks

### Phase 2: Caching (<15s for cached) - Short-term

1. **File hash-based caching**
   - Cache validation results by file hash
   - Invalidate on file modification

2. **Incremental validation**
   - Only validate changed files
   - Track validation state in database

### Phase 3: Streaming Validation (<1s per chunk) - Medium-term

1. **Real-time validation**
   - Validate as data streams
   - Cumulative metrics

2. **Background pre-computation**
   - Pre-compute expensive validations
   - Use cached results for fast mode

## Performance Targets

| Mode | Target Time | Strategy |
|------|-------------|----------|
| **Fast Mode** | <30s | Tiered + Sampling + Parallel |
| **Standard Mode** | <60s | Parallel + Caching |
| **Comprehensive Mode** | <5min | Full validation, can be deferred |
| **Streaming Mode** | <1s/chunk | Real-time validation |

## Code Structure

```python
# src/dsa110_contimg/qa/fast_validation.py

from enum import Enum

class ValidationMode(Enum):
    FAST = "fast"  # <30s, sampling, parallel
    STANDARD = "standard"  # <60s, parallel, caching
    COMPREHENSIVE = "comprehensive"  # Full validation

def validate_pipeline(
    ms_path: str,
    caltables: List[str],
    image_paths: List[str],
    mode: ValidationMode = ValidationMode.STANDARD,
    config: Optional[QAConfig] = None,
    timeout_seconds: int = 60,
) -> Dict:
    """Unified pipeline validation with mode selection."""
    
    if mode == ValidationMode.FAST:
        return validate_pipeline_fast(ms_path, caltables, image_paths, timeout_seconds)
    elif mode == ValidationMode.STANDARD:
        return validate_pipeline_standard(ms_path, caltables, image_paths, timeout_seconds)
    else:
        return validate_pipeline_comprehensive(ms_path, caltables, image_paths)
```

## Feasibility Conclusion

**YES, it's possible** with the following approach:

1. **Fast Mode (<30s)**: Tiered validation + aggressive sampling + parallel execution
2. **Standard Mode (<60s)**: Add caching + incremental validation
3. **Streaming Mode**: Real-time validation as data flows
4. **Comprehensive Mode**: Deferred/background for full validation

**Key Enablers:**
- Parallel execution (4-8 workers)
- Aggressive sampling (1% instead of 10%)
- Caching (file hash-based)
- Tiered architecture (quick checks first)
- Skip expensive operations in fast mode

**Trade-offs:**
- Fast mode: Less detailed, but catches critical issues
- Standard mode: Balanced detail/speed
- Comprehensive mode: Full validation, can be deferred

## Next Steps

1. Implement `FastValidationConfig`
2. Create `validate_pipeline_fast()` function
3. Add parallel execution wrapper
4. Implement caching layer
5. Add validation mode selection
6. Benchmark and optimize

