# Calibration CLI Confusion Analysis

**Date:** 2025-11-04  
**File:** `src/dsa110_contimg/calibration/cli.py` (1578 lines)  
**Purpose:** Identify sources of confusion and suggest improvements

---

## Executive Summary

The calibration CLI is a **monolithic 1578-line file** that handles multiple subcommands, complex flag interactions, and conditional logic. This creates several sources of confusion for users:

1. **Import-time side effects** (CWD changes)
2. **Complex flag interdependencies** (many flags interact in non-obvious ways)
3. **Multiple ways to achieve similar goals** (field selection, model population)
4. **Hidden behaviors** (automatic subset creation, conditional logic)
5. **Lack of presets** (no shortcuts for common workflows)
6. **Inconsistent validation** (some checks early, some late)

---

## 1. Import-Time Side Effects

### Problem

```python
# Line 26: setup_casa_environment() called at module import
setup_casa_environment()
```

**Issue:**
- Changes working directory globally at import time
- Affects all code that imports this module
- Not obvious to users or developers
- Can break relative path handling

**Impact:**
- Unexpected behavior when importing the module
- Hard to test (CWD changes affect test isolation)
- Violates principle of least surprise

**Recommendation:**
- Move `setup_casa_environment()` call to `main()` function
- Or use context manager: `with casa_log_environment():`
- Document that CASA requires specific CWD setup

---

## 2. Complex Flag Interdependencies

### 2.1 Field Selection Complexity

**Flags involved:**
- `--field` (explicit field selection)
- `--auto-fields` (automatic selection)
- `--cal-catalog` (catalog for auto-selection)
- `--cal-ra-deg` / `--cal-dec-deg` (coordinates for auto-selection)
- `--cal-flux-jy` (flux for weighting)
- `--pt-dec-deg` (pointing declination)
- `--bp-window` (field window size)
- `--bp-min-pb` (primary beam threshold)

**Confusion:**
- When is `--field` required vs optional?
- What happens if both `--field` and `--auto-fields` are provided?
- How do catalog-based selection and manual coordinates interact?
- What's the difference between `--cal-ra-deg` and `--pt-dec-deg`?

**Current behavior:**
- `--auto-fields` attempts automatic selection, falls back to `--field` if provided
- Multiple selection methods can conflict
- Error messages don't explain interactions

**Recommendation:**
1. **Create field selection presets:**
   ```python
   --field-mode {manual|auto|catalog}
   # manual: requires --field
   # auto: uses --cal-ra-deg/--cal-dec-deg
   # catalog: uses --cal-catalog
   ```

2. **Validate exclusivity:**
   - If `--auto-fields` is used, warn if `--field` is also provided
   - Document which flags are mutually exclusive

3. **Add decision tree to help:**
   ```
   Field Selection:
   - Use --field for explicit field index/range
   - Use --auto-fields for automatic selection (requires catalog or coordinates)
   - Use --cal-catalog for catalog-based selection
   ```

### 2.2 Fast Mode vs Minimal Mode vs Regular Mode

**Flags involved:**
- `--fast` (fast subset mode)
- `--minimal` (ultra-fast test mode)
- `--timebin` / `--chanbin` (subset parameters)
- `--uvrange` (UV range cuts)

**Confusion:**
- When does `--fast` create a subset MS vs use full MS?
- What's the difference between `--fast` and `--minimal`?
- How do `--timebin`/`--chanbin` interact with `--fast`?
- Does `--fast` automatically create a subset file?

**Current behavior:**
- `--fast` + `--timebin`/`--chanbin` → Creates subset MS (`ms.fast.ms`)
- `--minimal` → Creates subset MS (`ms.minimal.ms`) with extreme downsampling
- Subset creation is **hidden** - user may not realize a new MS is created
- No warning about disk space or cleanup

**Recommendation:**
1. **Make subset creation explicit:**
   ```python
   --create-subset PATH  # Explicit output path for subset
   --no-subset           # Disable subset creation even with --fast
   ```

2. **Document subset behavior:**
   ```
   --fast: Creates a subset MS for faster calibration
     - Creates: {ms}.fast.ms (unless --no-subset)
     - Uses time/channel binning (--timebin, --chanbin)
     - Original MS unchanged
   ```

3. **Add cleanup option:**
   ```python
   --cleanup-subset      # Remove subset MS after calibration
   ```

### 2.3 K-Calibration Flag Interactions

**Flags involved:**
- `--do-k` (enable K-calibration)
- `--k-fast-only` (skip slow K-cal)
- `--combine-spw` (combine spectral windows)
- `--skip-bp` / `--skip-g` (skip other solves)

**Confusion:**
- Why is K-cal disabled by default?
- When should `--do-k` be used?
- What's the difference between full K-cal and `--k-fast-only`?
- How does `--combine-spw` affect K-cal?

**Current behavior:**
- K-cal disabled by default (DSA-110 short baselines)
- `--do-k` enables full K-cal (slow, ~15-30 min)
- `--k-fast-only` enables fast K-cal only (~2-3 min)
- Help text explains but buried in long description

**Recommendation:**
1. **Add prominent warning:**
   ```python
   if not args.do_k:
       logger.info("K-calibration skipped by default for DSA-110 "
                  "(short baselines <2.6 km). Use --do-k to enable.")
   ```

2. **Create K-cal presets:**
   ```python
   --k-mode {none|fast|full}
   # none: skip (default for DSA-110)
   # fast: fast-only (--k-fast-only)
   # full: full K-cal (--do-k)
   ```

### 2.4 Model Source Selection

**Flags involved:**
- `--model-source` (catalog|setjy|component|image)
- `--model-component` (component list path)
- `--model-image` (image path)
- `--model-field` (field for setjy)
- `--model-setjy-standard` (flux standard)
- `--cal-catalog` (catalog path, also used for field selection)

**Confusion:**
- When is MODEL_DATA populated?
- What's the difference between `--model-source=catalog` and `--cal-catalog`?
- Which model source should be used when?
- Why are there so many model-related flags?

**Current behavior:**
- MODEL_DATA population happens automatically in some cases
- Different model sources require different flags
- Not clear when MODEL_DATA is needed vs optional

**Recommendation:**
1. **Document model source selection:**
   ```
   MODEL_DATA Population:
   - catalog: Use NVSS catalog (automatic)
   - setjy: Use CASA setjy for standard calibrator
   - component: Use component list (.cl file)
   - image: Use existing CASA image
   ```

2. **Simplify model flags:**
   ```python
   --model-source {catalog|setjy|component|image}
   --model-path PATH  # Path to component/image/catalog (context-dependent)
   ```

---

## 3. Multiple Ways to Achieve Similar Goals

### 3.1 Reference Antenna Selection

**Flags:**
- `--refant` (explicit antenna ID)
- `--refant-ranking` (JSON file with ranking)

**Confusion:**
- Which takes precedence?
- What's the format of refant-ranking JSON?
- When should ranking be used vs explicit?

**Recommendation:**
- Document precedence clearly
- Add validation that refant is provided (either way)
- Show which method was used in output

### 3.2 Calibration Table Output

**Flags:**
- `--output-dir` (not present - uses MS directory)
- `--prefix` (not present - uses MS basename)

**Confusion:**
- Where are caltables written?
- How are they named?
- Can output location be controlled?

**Current behavior:**
- Caltables written to same directory as MS
- Naming based on MS basename + calibration type
- No control over output location

**Recommendation:**
- Add `--output-dir` flag for caltable output
- Add `--prefix` flag for caltable naming
- Document default behavior

---

## 4. Hidden Behaviors

### 4.1 Automatic Subset Creation

**Problem:**
- `--fast` mode creates subset MS automatically
- User may not realize a new file is created
- No cleanup by default (subset files accumulate)

**Recommendation:**
- Warn user when subset is created
- Show subset path clearly
- Add `--cleanup-subset` flag

### 4.2 Conditional Validation

**Problem:**
- Some validation happens early (field/refant)
- Some validation happens late (MODEL_DATA check)
- Some validation is skipped in certain modes

**Recommendation:**
- Standardize validation order
- Add `--validate` flag for pre-flight checks
- Document what's validated when

---

## 5. Lack of Presets

### Problem

Users must specify many flags for common workflows:
- Fast calibration: `--fast --timebin 30s --chanbin 4 --uvrange '>1klambda' --gain-calmode p`
- Standard calibration: Multiple flags with defaults
- Production calibration: Different flag combinations

**Recommendation:**

Add preset system:
```python
--preset {fast|standard|production|test}
```

**Presets:**
- `fast`: Fast subset, phase-only gains, uvrange cuts
- `standard`: Full MS, amp+phase gains, no subset
- `production`: Full MS, optimized for quality
- `test`: Minimal mode for quick tests

Presets can be overridden with individual flags.

---

## 6. Inconsistent Error Messages

### Problem

- Some errors are clear: "Field validation failed"
- Some errors are cryptic: Generic exceptions
- Some errors don't suggest fixes

**Examples:**
- `p.error("--field is required when --auto-fields is not used")` - Clear
- Generic exceptions from CASA tools - Cryptic
- Missing MODEL_DATA errors - No suggestion how to fix

**Recommendation:**
1. **Add actionable error messages:**
   ```python
   if model_data_is_all_zeros(ms_path):
       raise ValueError(
           "MODEL_DATA is all zeros. Required for calibration.\n"
           "Action: Use --model-source=catalog or --model-source=setjy"
       )
   ```

2. **Add error code system:**
   ```python
   class CalibrationError(Exception):
       def __init__(self, code: str, message: str, help_url: str = None):
           self.code = code
           self.help_url = help_url
           super().__init__(f"[{code}] {message}")
   ```

---

## 7. Documentation Gaps

### Problem

- Help text is long but not structured
- Examples are scattered
- No quick reference guide
- Complex flag interactions not documented

**Recommendation:**

1. **Create structured help:**
   ```
   python -m dsa110_contimg.calibration.cli calibrate --help
   
   Usage:
     calibrate [options]
   
   Quick Start:
     # Fast calibration (recommended for quick-look)
     --preset fast --ms MS.ms --field 0 --refant 103
   
     # Standard calibration (recommended for production)
     --preset standard --ms MS.ms --field 0 --refant 103
   
   Field Selection:
     --field INDEX           Explicit field selection
     --auto-fields           Automatic field selection (requires catalog/coordinates)
   
   Calibration Modes:
     --preset {fast|standard|production|test}
     --fast                  Fast subset mode (creates subset MS)
     --minimal               Ultra-fast test mode
   
   ...
   ```

2. **Create quick reference guide:**
   - Common workflows
   - Flag combinations
   - Decision trees

---

## 8. File Size and Organization

### Problem

- 1578 lines in single file
- Multiple subcommands mixed together
- Hard to navigate
- Hard to test individual components

**Recommendation:**

1. **Split into modules:**
   ```
   calibration/
     cli.py              # Main entry point (thin)
     cli_calibrate.py    # Calibrate subcommand
     cli_apply.py        # Apply subcommand
     cli_flag.py          # Flag subcommand
     cli_validate.py     # Validate subcommand
     ...
   ```

2. **Extract shared logic:**
   - Field selection → `field_selection.py`
   - Model population → `model_population.py`
   - Validation → `validation.py` (already exists)

---

## 9. Summary of Recommendations

### High Priority (Immediate Impact)

1. **Move CASA environment setup** from import time to `main()`
2. **Add presets** for common workflows (`--preset fast|standard|production`)
3. **Make subset creation explicit** (`--create-subset`, `--no-subset`)
4. **Add actionable error messages** with next steps

### Medium Priority (Improves Usability)

5. **Simplify field selection** (`--field-mode` instead of multiple flags)
6. **Add output control** (`--output-dir`, `--prefix` for caltables)
7. **Document flag interactions** in structured help
8. **Add validation warnings** for common issues

### Low Priority (Code Quality)

9. **Split large file** into subcommand modules
10. **Extract shared logic** to separate modules
11. **Add error code system** for better debugging

---

## 10. Quick Wins

### Example 1: Add Preset System

```python
# Add to argument parser
pc.add_argument(
    '--preset',
    choices=['fast', 'standard', 'production', 'test'],
    help='Use preset calibration configuration'
)

# In handler:
if args.preset:
    if args.preset == 'fast':
        args.fast = True
        args.timebin = args.timebin or '30s'
        args.chanbin = args.chanbin or 4
        args.uvrange = args.uvrange or '>1klambda'
        args.gain_calmode = 'p'
    elif args.preset == 'standard':
        args.fast = False
        args.gain_calmode = 'ap'
    # ... etc
```

### Example 2: Warn About Subset Creation

```python
if args.fast and (args.timebin or args.chanbin):
    ms_fast = f"{base}.fast.ms"
    logger.warning(
        f"Fast mode will create subset MS: {ms_fast}\n"
        f"Original MS unchanged. Use --cleanup-subset to remove after."
    )
```

### Example 3: Improve Field Selection Help

```python
pc.add_argument(
    '--field-mode',
    choices=['manual', 'auto', 'catalog'],
    help=(
        'Field selection mode:\n'
        '  manual: Use --field (explicit)\n'
        '  auto: Use --cal-ra-deg/--cal-dec-deg\n'
        '  catalog: Use --cal-catalog'
    )
)
```

---

**Next Steps:**
1. Review this analysis
2. Prioritize improvements
3. Implement high-priority items first
4. Create user testing to validate improvements

