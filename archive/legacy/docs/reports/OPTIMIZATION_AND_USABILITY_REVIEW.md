# Optimization and User-Friendliness Review

**Date:** 2025-01-27  
**Scope:** Performance optimization and user experience improvements  
**Priority Focus:** Optimization and user-friendliness

---

## Executive Summary

This review identifies opportunities to improve **performance** (speed, memory usage, resource efficiency) and **user experience** (CLI usability, error messages, progress feedback, defaults). Findings are prioritized by impact and implementation effort.

**Key Findings:**
- ✅ **Good:** Error handling with suggestions, progress bars in conversion, validation framework
- ⚠️ **Needs Improvement:** CLI help text completeness, progress indicators in calibration/imaging, memory-efficient data access patterns
- 🔴 **Critical:** Missing progress feedback during long operations, suboptimal CASA table access patterns, inconsistent defaults

---

## 1. Optimization Opportunities

### 1.1 CASA Table Access Patterns (HIGH PRIORITY)

**Problem:** Many operations read entire MS columns into memory using `getcol()` without chunking.

**Impact:** 
- High memory usage for large MS files
- Slow startup for validation operations
- Risk of OOM errors on limited-memory systems

**Current Pattern:**
```python
# Found in multiple files (calibration/cli_flag.py, calibration/cli_calibrate.py, etc.)
with table(ms, readonly=True) as tb:
    flags = tb.getcol("FLAG", startrow=0, nrow=sample_size)  # Good: sampling
    # But elsewhere:
    flags = tb.getcol("FLAG")  # Bad: reads entire column
```

**Recommendations:**

1. **Always sample for validation operations:**
```python
def validate_ms_unflagged_fraction(ms_path: str, sample_size: int = 10000) -> float:
    """Validate unflagged data fraction using sampling (memory-efficient)."""
    with table(ms_path, readonly=True) as tb:
        n_rows = tb.nrows()
        if n_rows == 0:
            return 0.0
        
        sample_size = min(sample_size, n_rows)
        # Sample evenly across MS
        step = max(1, n_rows // sample_size)
        flags_sample = tb.getcol("FLAG", startrow=0, nrow=sample_size, step=step)
        unflagged_fraction = np.mean(~flags_sample)
        return float(unflagged_fraction)
```

2. **Use `getcolslice()` for large arrays:**
```python
# Instead of reading entire DATA column:
data_full = tb.getcol("DATA")  # Bad: may be GB

# Use slicing:
for chunk_start in range(0, n_rows, chunk_size):
    data_chunk = tb.getcolslice("DATA", [0, 0, chunk_start], [n_pols-1, n_chan-1, chunk_start+chunk_size])
    process_chunk(data_chunk)
```

3. **Create utility function for safe sampling:**
```python
# utils/ms_helpers.py
def sample_ms_column(ms_path: str, column: str, sample_size: int = 10000, 
                     seed: Optional[int] = None) -> np.ndarray:
    """Sample a column from MS without loading entire column."""
    with table(ms_path, readonly=True) as tb:
        n_rows = tb.nrows()
        if n_rows == 0:
            return np.array([])
        
        sample_size = min(sample_size, n_rows)
        if seed is not None:
            np.random.seed(seed)
        
        # Random sampling (more representative than sequential)
        indices = np.random.choice(n_rows, size=sample_size, replace=False)
        indices.sort()
        
        # Read in chunks to avoid memory spikes
        chunk_size = 1000
        samples = []
        for i in range(0, len(indices), chunk_size):
            chunk_indices = indices[i:i+chunk_size]
            chunk_data = tb.getcol(column, startrow=chunk_indices[0], 
                                   nrow=chunk_indices[-1]-chunk_indices[0]+1)
            # Extract samples from chunk
            chunk_samples = chunk_data[chunk_indices - chunk_indices[0]]
            samples.append(chunk_samples)
        
        return np.concatenate(samples)
```

**Files to Update:**
- `calibration/cli_flag.py` (line ~300+): flagging statistics calculation
- `calibration/cli_calibrate.py` (line ~830+): unflagged data validation
- `utils/validation.py`: MS validation functions
- `qa/calibration_quality.py`: QA operations

**Estimated Impact:** 30-50% reduction in memory usage for validation operations, faster startup times

---

### 1.2 Progress Indicators for Long Operations (HIGH PRIORITY)

**Problem:** Calibration and imaging operations can take 15-60 minutes with minimal progress feedback.

**Current State:**
- ✅ Progress bars exist in `conversion/strategies/hdf5_orchestrator.py` (subband reading)
- ❌ No progress indicators in calibration solves (K, BP, G)
- ❌ No progress indicators in imaging (tclean/WSClean)
- ❌ Limited progress feedback during MODEL_DATA population

**Impact:** Users don't know if process is stuck or working, leading to:
- Premature termination
- Unnecessary restarts
- Difficulty estimating completion time

**Recommendations:**

1. **Add progress context for calibration solves:**
```python
# calibration/calibration.py
from dsa110_contimg.utils.progress import progress_context

def solve_bandpass(ms: str, field: str, refant: str, 
                  ktable: Optional[str] = None, ...) -> List[str]:
    """Solve bandpass with progress feedback."""
    logger.info("Starting bandpass solve...")
    
    # Estimate time based on MS size
    with table(ms, readonly=True) as tb:
        n_rows = tb.nrows()
        n_antennas = len(get_antennas(ms))
    
    # Rough estimate: ~1-2 seconds per antenna per 10k rows
    estimated_time = (n_antennas * n_rows / 10000) * 1.5
    logger.info(f"Estimated time: {estimated_time:.1f} seconds")
    
    # Use CASA logging to track progress (CASA writes to log file)
    # Monitor log file for progress updates
    with progress_context(total=100, desc="Bandpass solve") as pbar:
        # Start solve in background, monitor log
        result = _solve_bandpass_internal(ms, field, refant, ktable, ...)
        pbar.update(100)
    
    return result
```

2. **Add progress feedback for MODEL_DATA population:**
```python
# calibration/model.py
def write_point_model_with_ft(ms: str, ra_deg: float, dec_deg: float, 
                              flux_jy: float, field: str = "0", 
                              use_manual: bool = True) -> None:
    """Populate MODEL_DATA with progress feedback."""
    if use_manual:
        logger.info("Calculating MODEL_DATA manually (bypassing ft() phase center bugs)...")
        
        with table(ms, readonly=False) as tb:
            n_rows = tb.nrows()
            chunk_size = 10000
            
            with progress_context(total=n_rows, desc="Writing MODEL_DATA") as pbar:
                for start_row in range(0, n_rows, chunk_size):
                    end_row = min(start_row + chunk_size, n_rows)
                    # Calculate MODEL_DATA for this chunk
                    model_chunk = _calculate_model_data_chunk(
                        ms, ra_deg, dec_deg, flux_jy, field, start_row, end_row
                    )
                    tb.putcol("MODEL_DATA", model_chunk, startrow=start_row, nrow=end_row-start_row)
                    pbar.update(end_row - start_row)
```

3. **Add time estimates and checkpoints:**
```python
# calibration/cli_calibrate.py
def handle_calibrate(args):
    # ... existing code ...
    
    logger.info("=" * 70)
    logger.info("CALIBRATION WORKFLOW")
    logger.info("=" * 70)
    logger.info(f"1. Flagging (estimated: 30-60s)")
    logger.info(f"2. MODEL_DATA population (estimated: 2-5 min)")
    logger.info(f"3. Bandpass solve (estimated: 5-15 min)")
    logger.info(f"4. Gain solve (estimated: 5-10 min)")
    logger.info(f"Total estimated time: 15-30 min")
    logger.info("=" * 70)
    
    # At each step:
    logger.info("[1/4] Starting flagging...")
    # ... flagging ...
    logger.info("✓ [1/4] Flagging complete")
    
    logger.info("[2/4] Starting MODEL_DATA population...")
    # ... MODEL_DATA ...
    logger.info("✓ [2/4] MODEL_DATA population complete")
    # etc.
```

**Files to Update:**
- `calibration/calibration.py`: Add progress context to solves
- `calibration/model.py`: Add progress for MODEL_DATA calculation
- `calibration/cli_calibrate.py`: Add workflow checkpoints
- `imaging/cli_imaging.py`: Add progress for imaging operations

**Estimated Impact:** Significant UX improvement, reduced user confusion and support requests

---

### 1.3 Memory-Efficient Data Processing (MEDIUM PRIORITY)

**Problem:** Some operations load entire datasets into memory when chunking would be more efficient.

**Current Pattern:**
```python
# conversion/strategies/hdf5_orchestrator.py
# Loads all subbands into memory before merging
acc = []
for path in file_list:
    tmp = UVData()
    tmp.read(path, ...)  # Loads entire file
    acc.append(tmp)
merged = acc[0]
for uv in acc[1:]:
    merged += uv  # In-memory merge
```

**Recommendation:** Use streaming/chunked processing for large datasets:
```python
def merge_subbands_streaming(file_list: List[str], output_ms: str) -> None:
    """Merge subbands using streaming to reduce memory usage."""
    # Process in batches to limit memory
    batch_size = 4  # Process 4 subbands at a time
    temp_merged = None
    
    for i in range(0, len(file_list), batch_size):
        batch = file_list[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(file_list)+batch_size-1)//batch_size}")
        
        # Load batch
        batch_data = []
        for path in batch:
            uv = UVData()
            uv.read(path, ...)
            batch_data.append(uv)
        
        # Merge batch
        batch_merged = batch_data[0]
        for uv in batch_data[1:]:
            batch_merged += uv
        
        # Merge with accumulated result
        if temp_merged is None:
            temp_merged = batch_merged
        else:
            temp_merged += batch_merged
        
        # Clear batch from memory
        del batch_data, batch_merged
    
    # Write final result
    temp_merged.write_ms(output_ms)
```

**Files to Update:**
- `conversion/strategies/hdf5_orchestrator.py`: `_load_and_merge_subbands()`
- `conversion/merge_spws.py`: Consider chunked merging for large concatenations

**Estimated Impact:** 40-60% reduction in peak memory usage for large conversions

---

### 1.4 Caching Expensive Operations (MEDIUM PRIORITY)

**Problem:** Some expensive operations are repeated unnecessarily:
- MS metadata queries (antenna list, field info)
- Catalog lookups
- Phase center calculations

**Recommendation:** Add caching layer for expensive metadata queries:
```python
# utils/ms_cache.py
from functools import lru_cache
from typing import Dict, List, Tuple
import hashlib

# Cache key: MS path + modification time
def _ms_cache_key(ms_path: str) -> str:
    """Generate cache key from MS path and mtime."""
    stat = os.stat(ms_path)
    key = f"{ms_path}:{stat.st_mtime}"
    return hashlib.md5(key.encode()).hexdigest()

# Cache MS metadata queries
@lru_cache(maxsize=32)
def get_antennas_cached(ms_path: str) -> List[str]:
    """Get antenna list with caching."""
    with table(f"{ms_path}::ANTENNA", readonly=True) as tb:
        return tb.getcol("NAME").tolist()

@lru_cache(maxsize=32)
def get_fields_cached(ms_path: str) -> List[Tuple[str, float, float]]:
    """Get field info with caching (name, RA, Dec)."""
    with table(f"{ms_path}::FIELD", readonly=True) as tb:
        names = tb.getcol("NAME")
        phase_dir = tb.getcol("PHASE_DIR")
        # Convert to degrees
        fields = []
        for i, name in enumerate(names):
            ra_rad, dec_rad = phase_dir[i][0]
            fields.append((name, np.rad2deg(ra_rad), np.rad2deg(dec_rad)))
        return fields

# Clear cache when MS is modified
def clear_ms_cache(ms_path: str) -> None:
    """Clear cache for a specific MS."""
    get_antennas_cached.cache_clear()
    get_fields_cached.cache_clear()
```

**Files to Update:**
- `utils/ms_helpers.py` (new file): Create cached MS metadata functions
- `calibration/selection.py`: Use cached antenna/field queries
- `calibration/refant_selection.py`: Use cached antenna queries

**Estimated Impact:** 20-40% speedup for operations that query MS metadata multiple times

---

### 1.5 Parallel Processing Opportunities (LOW PRIORITY)

**Problem:** Some operations are inherently sequential but could benefit from parallelization:
- Flagging multiple MS files
- QA operations on multiple calibration tables
- Image quality checks on multiple images

**Recommendation:** Add parallel processing utilities:
```python
# utils/parallel.py
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Callable, Any

def process_parallel(items: List[Any], func: Callable, 
                    max_workers: int = 4, 
                    show_progress: bool = True) -> List[Any]:
    """Process items in parallel with progress feedback."""
    results = []
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): item for item in items}
        
        if show_progress:
            from dsa110_contimg.utils.progress import progress_context
            with progress_context(total=len(items), desc="Processing") as pbar:
                for future in as_completed(futures):
                    results.append(future.result())
                    pbar.update(1)
        else:
            for future in as_completed(futures):
                results.append(future.result())
    
    return results

# Usage:
# calibration/cli_flag.py
def flag_multiple_ms(ms_list: List[str], mode: str, **kwargs) -> None:
    """Flag multiple MS files in parallel."""
    def flag_one(ms_path: str):
        handle_flag_args(argparse.Namespace(ms=ms_path, mode=mode, **kwargs))
    
    process_parallel(ms_list, flag_one, max_workers=4)
```

**Files to Update:**
- `utils/parallel.py` (new file): Create parallel processing utilities
- `calibration/cli_flag.py`: Add batch flagging mode
- `qa/pipeline_quality.py`: Parallel QA operations

**Estimated Impact:** 2-4x speedup for batch operations on multi-core systems

---

## 2. User-Friendliness Improvements

### 2.1 CLI Help Text Completeness (HIGH PRIORITY)

**Problem:** Some CLI arguments have minimal or missing help text, making it unclear:
- What the parameter does
- What values are valid
- What the default is
- When to use it

**Examples of Incomplete Help:**

```python
# calibration/cli_calibrate.py
parser.add_argument("--refant", required=False, default=None)  # No help text!
parser.add_argument("--field", required=False, default=None,
                   help="Calibrator field name/index or range (e.g. 10~12)")  # OK but could be better
```

**Recommendations:**

1. **Always provide help text with context:**
```python
parser.add_argument(
    "--refant",
    required=False,
    default=None,
    help=(
        "Reference antenna ID (e.g., '103'). "
        "If not provided, auto-selects using outrigger-priority chain. "
        "Reference antenna must have unflagged data for all calibration steps."
    )
)

parser.add_argument(
    "--field",
    required=False,
    default=None,
    help=(
        "Calibrator field name/index or range (e.g., '0', '10~12', 'calibrator'). "
        "Required unless --auto-fields is used. "
        "Use --auto-fields to automatically select fields from VLA catalog."
    )
)
```

2. **Add examples to complex arguments:**
```python
parser.add_argument(
    "--gain-solint",
    default="inf",
    help=(
        "Gain solution interval. "
        "Options: 'inf' (entire scan, default), 'int' (per integration), "
        "'60s' (60 seconds), '10min' (10 minutes). "
        "Shorter intervals capture time-variable gains but require higher SNR. "
        "Examples: 'inf' for stable calibrators, '30s' for variable conditions."
    )
)
```

3. **Document parameter relationships:**
```python
parser.add_argument(
    "--bp-combine-field",
    action="store_true",
    help=(
        "Combine across selected fields when solving bandpass/gains. "
        "Increases SNR by using data from multiple fields. "
        "Recommended for weak calibrators (<5 Jy). "
        "Requires --auto-fields or multiple fields in --field (e.g., '0~5')."
    )
)
```

**Files to Update:**
- `calibration/cli_calibrate.py`: All arguments (80+ arguments)
- `calibration/cli_flag.py`: All mode-specific arguments
- `imaging/cli.py`: All imaging parameters
- `conversion/cli.py`: All conversion parameters

**Estimated Impact:** Significant reduction in user confusion, fewer support questions

---

### 2.2 Default Value Consistency (MEDIUM PRIORITY)

**Problem:** Default values are inconsistent or not well-documented:
- Some defaults come from environment variables
- Some defaults are hardcoded
- Some defaults are `None` (optional) but behavior unclear

**Current Examples:**
```python
# calibration/cli_calibrate.py
default=float(os.getenv("CONTIMG_CAL_BP_MINSNR", "3.0"))  # Environment variable default
default="inf"  # Hardcoded default
default=None  # Unclear behavior
```

**Recommendations:**

1. **Document all defaults clearly:**
```python
parser.add_argument(
    "--bp-minsnr",
    type=float,
    default=float(os.getenv("CONTIMG_CAL_BP_MINSNR", "3.0")),
    help=(
        "Minimum SNR threshold for bandpass solutions. "
        "Default: 3.0 (or CONTIMG_CAL_BP_MINSNR environment variable). "
        "Lower values (2.0-3.0) use more data but may include noise. "
        "Higher values (5.0+) require stronger signal but more reliable solutions."
    )
)
```

2. **Create default constants module:**
```python
# utils/defaults.py
"""Default values for CLI arguments and configuration."""

# Calibration defaults
CAL_BP_MINSNR = 3.0
CAL_GAIN_MINSNR = 3.0
CAL_GAIN_SOLINT = "inf"
CAL_GAIN_CALMODE = "ap"  # amplitude+phase

# Imaging defaults
IMG_IMSIZE = 1024
IMG_CELL_ARCSEC = None  # Auto-calculated
IMG_ROBUST = 0.0
IMG_NITER = 1000

# Get from environment or use constant
def get_cal_bp_minsnr() -> float:
    """Get BP minimum SNR from env or default."""
    return float(os.getenv("CONTIMG_CAL_BP_MINSNR", str(CAL_BP_MINSNR)))
```

3. **Validate defaults are reasonable:**
```python
# Add validation for default values
def validate_defaults() -> List[str]:
    """Validate default values are reasonable, return warnings."""
    warnings = []
    if CAL_BP_MINSNR < 2.0:
        warnings.append("CAL_BP_MINSNR < 2.0 may produce unreliable solutions")
    if IMG_IMSIZE < 256:
        warnings.append("IMG_IMSIZE < 256 may have poor resolution")
    return warnings
```

**Files to Update:**
- `utils/defaults.py` (new file): Centralize default values
- All CLI modules: Use centralized defaults
- `docs/reference/defaults.md` (new file): Document all defaults

**Estimated Impact:** Improved consistency, easier configuration management

---

### 2.3 Error Message Actionability (HIGH PRIORITY)

**Problem:** Some error messages are technical but don't suggest fixes:
- "MODEL_DATA is all zeros" → What should user do?
- "Validation failed" → Which validation? How to fix?
- Generic exceptions from CASA tools → No context

**Current State:**
- ✅ Good: `ValidationError.format_with_suggestions()` provides suggestions
- ✅ Good: `utils/error_messages.py` has suggestion framework
- ⚠️ Needs improvement: Some errors still lack actionable guidance

**Recommendations:**

1. **Add actionable error messages for common failures:**
```python
# calibration/cli_calibrate.py
if model_data_is_all_zeros(ms_path):
    raise ValidationError(
        errors=[
            "MODEL_DATA column exists but is all zeros. "
            "Calibration requires populated MODEL_DATA to know what signal to calibrate against."
        ],
        error_types=['model_data_unpopulated'],
        error_details=[{'ms_path': ms_path}],
        suggestions=[
            "Populate MODEL_DATA using one of these methods:\n"
            "  1. Use --model-source=catalog (recommended, default)\n"
            "  2. Use --model-source=setjy (only if calibrator at phase center)\n"
            "  3. Use --model-source=component with --model-component=<path>\n"
            "  4. Use --model-source=image with --model-image=<path>\n"
            "\n"
            "Example:\n"
            f"  python -m dsa110_contimg.calibration.cli calibrate \\\n"
            f"    --ms {ms_path} --field 0 --refant 103 --model-source=catalog --auto-fields"
        ]
    )
```

2. **Enhance CASA error handling:**
```python
# utils/casa_error_handling.py
def handle_casa_error(tool_name: str, error: Exception, context: str = "") -> None:
    """Handle CASA tool errors with user-friendly messages."""
    error_msg = str(error)
    
    # Common CASA error patterns
    if "MODEL_DATA" in error_msg and "zero" in error_msg.lower():
        raise ValidationError(
            errors=[f"{tool_name} failed: {error_msg}"],
            suggestions=[
                "MODEL_DATA column is required but appears unpopulated. "
                "Populate it using --model-source before calibration."
            ]
        )
    elif "field" in error_msg.lower() and "not found" in error_msg.lower():
        raise ValidationError(
            errors=[f"{tool_name} failed: {error_msg}"],
            suggestions=[
                "Field selection may be invalid. "
                "Check available fields with: python -m dsa110_contimg.calibration.cli validate --ms <ms>"
            ]
        )
    else:
        # Generic CASA error
        raise RuntimeError(
            f"{tool_name} failed: {error_msg}\n"
            f"Context: {context}\n"
            f"For help, see: docs/troubleshooting/CASA_ERRORS.md"
        ) from error
```

3. **Add error codes for better documentation linking:**
```python
# utils/error_messages.py
ERROR_CODES = {
    'MODEL_DATA_UNPOPULATED': {
        'message': 'MODEL_DATA column exists but is unpopulated',
        'help_url': 'docs/troubleshooting/model_data.md',
        'suggestions': [
            'Use --model-source=catalog (recommended)',
            'Use --model-source=setjy if calibrator at phase center',
        ]
    },
    'FIELD_NOT_FOUND': {
        'message': 'Specified field not found in MS',
        'help_url': 'docs/troubleshooting/field_selection.md',
        'suggestions': [
            'List available fields: python -m dsa110_contimg.calibration.cli validate --ms <ms>',
            'Use --auto-fields to auto-select fields',
        ]
    },
    # ... more error codes
}
```

**Files to Update:**
- `utils/error_messages.py`: Add error codes and suggestions
- `calibration/cli_calibrate.py`: Use error codes for common failures
- `calibration/model.py`: Use error codes for MODEL_DATA errors
- `docs/troubleshooting/` (new directory): Create troubleshooting guides

**Estimated Impact:** Significant reduction in user confusion, faster problem resolution

---

### 2.4 Preset System Enhancement (MEDIUM PRIORITY)

**Problem:** Presets exist but could be more comprehensive and better documented.

**Current State:**
- ✅ Presets exist: `fast`, `standard`, `production`, `test`
- ⚠️ Presets don't cover all common workflows
- ⚠️ Preset behavior not always clear from help text

**Recommendations:**

1. **Expand preset system:**
```python
# calibration/presets.py
PRESETS = {
    'fast': {
        'description': 'Fast calibration for testing (<5 min)',
        'timebin': '30s',
        'chanbin': 4,
        'uvrange': '>1klambda',
        'gain_calmode': 'p',  # phase-only
        'gain_solint': '60s',
        'bp_minsnr': 2.0,  # Lower threshold for speed
    },
    'standard': {
        'description': 'Standard production calibration (15-30 min)',
        'timebin': None,
        'chanbin': None,
        'uvrange': '',
        'gain_calmode': 'ap',  # amplitude+phase
        'gain_solint': 'inf',
        'bp_minsnr': 3.0,
    },
    'production': {
        'description': 'High-quality calibration for science (30-60 min)',
        'timebin': None,
        'chanbin': None,
        'uvrange': '',
        'gain_calmode': 'ap',
        'gain_solint': 'int',  # Per-integration
        'bp_minsnr': 5.0,  # Higher threshold
        'prebp_phase': True,  # Pre-bandpass phase solve
    },
    'test': {
        'description': 'Minimal calibration for quick tests (<30s)',
        'minimal': True,  # Enable minimal mode
        'timebin': 'inf',
        'chanbin': 16,
    },
    'weak_calibrator': {
        'description': 'Optimized for weak calibrators (<2 Jy)',
        'bp_combine_field': True,
        'gain_solint': 'inf',  # Combine across time
        'bp_minsnr': 2.0,
        'gain_minsnr': 2.0,
    },
    'variable_conditions': {
        'description': 'For time-variable atmospheric conditions',
        'gain_solint': '30s',  # Short interval
        'prebp_phase': True,
        'gain_calmode': 'ap',
    },
}
```

2. **Add preset documentation:**
```python
parser.add_argument(
    "--preset",
    choices=list(PRESETS.keys()),
    help=(
        "Use preset calibration configuration. "
        "Presets can be overridden with individual flags.\n\n"
        "Available presets:\n"
        "  fast: Fast calibration for testing (<5 min)\n"
        "  standard: Standard production calibration (15-30 min, default)\n"
        "  production: High-quality calibration for science (30-60 min)\n"
        "  test: Minimal calibration for quick tests (<30s)\n"
        "  weak_calibrator: Optimized for weak calibrators (<2 Jy)\n"
        "  variable_conditions: For time-variable atmospheric conditions\n\n"
        "Example:\n"
        "  python -m dsa110_contimg.calibration.cli calibrate \\\n"
        "    --ms <ms> --field 0 --refant 103 --preset fast"
    )
)
```

**Files to Update:**
- `calibration/presets.py` (new file): Centralize preset definitions
- `calibration/cli_calibrate.py`: Use centralized presets
- `docs/reference/presets.md` (new file): Document all presets

**Estimated Impact:** Easier workflow selection for users, fewer configuration errors

---

### 2.5 Interactive Mode / Guided Workflow (LOW PRIORITY)

**Problem:** First-time users may not know which parameters to use.

**Recommendation:** Add interactive mode for guided setup:
```python
# calibration/cli_calibrate.py
def interactive_calibrate_setup(ms_path: str) -> argparse.Namespace:
    """Interactive guided setup for calibration."""
    print("=" * 70)
    print("CALIBRATION INTERACTIVE SETUP")
    print("=" * 70)
    print()
    
    # Query MS for information
    with table(ms_path, readonly=True) as tb:
        fields = get_fields_cached(ms_path)
        antennas = get_antennas_cached(ms_path)
    
    print(f"MS: {ms_path}")
    print(f"Fields: {len(fields)}")
    print(f"Antennas: {len(antennas)}")
    print()
    
    # Ask user questions
    print("1. Calibrator type:")
    print("   [1] Bright calibrator (>5 Jy) - Standard preset")
    print("   [2] Weak calibrator (<2 Jy) - Weak calibrator preset")
    print("   [3] Variable conditions - Variable conditions preset")
    choice = input("Choice [1]: ").strip() or "1"
    
    if choice == "1":
        preset = "standard"
    elif choice == "2":
        preset = "weak_calibrator"
    else:
        preset = "variable_conditions"
    
    # Auto-select field if possible
    if len(fields) == 1:
        field = "0"
        print(f"Auto-selected field: {field}")
    else:
        print(f"\n2. Available fields:")
        for i, (name, ra, dec) in enumerate(fields):
            print(f"   [{i}] {name} (RA={ra:.4f}°, Dec={dec:.4f}°)")
        field_choice = input("Field [0]: ").strip() or "0"
        field = str(field_choice)
    
    # Auto-select refant
    refant = recommend_refants_from_ms(ms_path)
    print(f"Auto-selected reference antenna: {refant}")
    
    # Build args
    args = argparse.Namespace(
        ms=ms_path,
        field=field,
        refant=refant,
        preset=preset,
        auto_fields=True,  # Use auto-fields by default
    )
    
    print()
    print("Configuration:")
    print(f"  Preset: {preset}")
    print(f"  Field: {field}")
    print(f"  Refant: {refant}")
    print()
    confirm = input("Proceed with calibration? [Y/n]: ").strip().lower()
    if confirm == 'n':
        sys.exit(0)
    
    return args
```

**Files to Update:**
- `calibration/cli_calibrate.py`: Add `--interactive` flag
- `imaging/cli.py`: Add interactive mode for imaging

**Estimated Impact:** Easier onboarding for new users, reduced configuration errors

---

## 3. Priority Summary

### High Priority (Implement First)
1. **CASA Table Access Patterns** - Memory efficiency, performance
2. **Progress Indicators** - User experience, reduces confusion
3. **CLI Help Text Completeness** - Reduces support burden
4. **Error Message Actionability** - Faster problem resolution

### Medium Priority (Implement Next)
1. **Memory-Efficient Data Processing** - Scalability
2. **Default Value Consistency** - Configuration management
3. **Preset System Enhancement** - Workflow simplification
4. **Caching Expensive Operations** - Performance improvement

### Low Priority (Nice to Have)
1. **Parallel Processing Opportunities** - Batch operations
2. **Interactive Mode** - New user onboarding

---

## 4. Implementation Recommendations

### Phase 1: Quick Wins (1-2 weeks)
- Add progress indicators to calibration/imaging
- Enhance CLI help text
- Improve error messages with suggestions

### Phase 2: Performance (2-3 weeks)
- Optimize CASA table access patterns
- Add memory-efficient data processing
- Implement caching for metadata queries

### Phase 3: Polish (1-2 weeks)
- Expand preset system
- Centralize defaults
- Add interactive mode (optional)

---

## 5. Metrics for Success

**Optimization Metrics:**
- Memory usage reduction: Target 30-50% for validation operations
- Startup time improvement: Target 20-30% faster
- Progress feedback: 100% of long operations (>1 min) show progress

**Usability Metrics:**
- Help text completeness: 100% of arguments have comprehensive help
- Error message actionability: 100% of common errors include suggestions
- User satisfaction: Reduced support questions, faster problem resolution

---

## 6. Related Documentation

- `docs/USABILITY_REVIEW.md` - Previous usability analysis
- `docs/architecture/CLI_IMPROVEMENTS.md` - CLI improvement plans
- `docs/reports/USER_SAFEGUARDS_PROPOSAL.md` - User safeguards
- `docs/reports/CODE_ORGANIZATION_AUDIT.md` - Code organization review

---

**Review Completed:** 2025-01-27

