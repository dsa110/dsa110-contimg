# Usability Review: DSA-110 Continuum Imaging Pipeline

**Date:** 2025-01-XX  
**Purpose:** Identify sources of confusion and suggest improvements for clarity, workflow, choices, and tunable parameters

---

## Executive Summary

This review identifies potential sources of confusion for agents or developers using the pipeline for the first time, focusing on:

1. **Workflow clarity** - Understanding the end-to-end process
2. **Decision points** - Choices that must be made vs. can be made
3. **Tunable parameters** - Controllable factors and their impacts
4. **Usability** - Overall ease of use and discoverability

---

## 1. Entry Point Confusion

### 1.1 Multiple Conversion Entry Points

**Problem:** Multiple entry points exist for conversion, creating confusion about which to use:

- `python -m dsa110_contimg.conversion.cli` (unified CLI with subcommands)
- `python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator` (orchestrator CLI)
- `python -m dsa110_contimg.conversion.uvh5_to_ms` (standalone converter)
- `python -m dsa110_contimg.conversion.streaming.streaming_converter` (streaming daemon)
- `scripts/run_conversion.sh` (wrapper script)

**Why This Is Confusing:**
- Documentation mentions different entry points in different contexts
- No clear hierarchy showing which is preferred for which use case
- The unified CLI (`conversion.cli`) exists but orchestrator is often referenced directly

**Recommendations:**
1. **Document entry point hierarchy** clearly:
   ```
   Primary Entry Points:
   - Streaming: streaming_converter (daemon mode)
   - One-off groups: conversion.cli groups (uses orchestrator)
   - Single file: conversion.cli single (uses uvh5_to_ms)
   - Direct orchestrator: hdf5_orchestrator (advanced use)
   ```

2. **Deprecate direct orchestrator usage** in documentation in favor of `conversion.cli groups`
3. **Update README** to show unified CLI as primary entry point
4. **Add decision tree** to quickstart: "Which conversion tool should I use?"

### 1.2 Writer Selection Complexity

**Problem:** Writer selection involves multiple factors:
- `--writer auto` vs. `--writer parallel-subband` vs. `--writer pyuvdata-monolithic`
- Auto-selection logic based on subband count (≤2 vs. >2)
- Production vs. testing implications

**Confusion Sources:**
- When to use `auto` vs. explicit selection?
- Why is `pyuvdata-monolithic` "TESTING ONLY"?
- What happens if you use wrong writer for 16 subbands?

**Recommendations:**
1. **Add explicit warnings** when wrong writer is selected:
   ```python
   if n_subbands > 2 and writer == 'pyuvdata-monolithic':
       logger.warning("pyuvdata-monolithic writer limited to ≤2 subbands. "
                     "Automatically switching to parallel-subband writer.")
   ```

2. **Document writer selection rules** in a prominent table:
   | Subbands | Auto Selects | Production OK? | Testing OK? |
   |----------|--------------|----------------|-------------|
   | ≤2       | pyuvdata     | No             | Yes         |
   | >2       | parallel-subband | Yes        | Yes         |

3. **Make `auto` the default** and document it clearly in CLI help

---

## 2. Workflow Clarity Issues

### 2.1 Pipeline Stage Ordering

**Problem:** The pipeline has multiple stages with dependencies, but the order isn't always clear:

1. Conversion (UVH5 → MS)
2. MODEL_DATA population (sky model seeding)
3. Calibration (K/BP/G)
4. Apply calibration
5. Imaging
6. Photometry (optional, not integrated)

**Confusion Sources:**
- MODEL_DATA population happens where? Before calibration? During imaging?
- When should sky model seeding occur?
- What's the difference between calibration and applycal?

**Recommendations:**
1. **Create explicit workflow diagram** showing:
   - Required stages (solid lines)
   - Optional stages (dashed lines)
   - Decision points (diamonds)
   - Data products (rectangles)

2. **Document stage dependencies** clearly:
   ```
   Stage N requires Stage N-1 products:
   - Calibration requires MODEL_DATA (populated before calibration)
   - ApplyCal requires calibration tables (created by calibration)
   - Imaging can use CORRECTED_DATA or DATA (depending on calibration)
   ```

3. **Add stage validation** that checks prerequisites:
   ```python
   def validate_stage_prerequisites(stage: str, ms_path: Path) -> bool:
       """Check if prerequisites for stage are met."""
       if stage == "calibration":
           return has_model_data(ms_path)
       elif stage == "imaging":
           return has_corrected_data(ms_path) or has_data(ms_path)
   ```

### 2.2 K-Calibration Default Behavior

**Problem:** K-calibration is skipped by default, but this isn't obvious:
- Default: `--do-k=False` (K-cal skipped)
- Rationale: Short baselines (2.6 km) mean delays <0.5 ns
- Impact: Calibration produces BP/G tables only

**Confusion Sources:**
- Why is K-cal skipped?
- When should I enable it?
- Does skipping affect calibration quality?

**Recommendations:**
1. **Add prominent warning** when K-cal is skipped:
   ```python
   if not do_k:
       logger.info("K-calibration skipped by default for DSA-110 "
                  "(short baselines <2.6 km, delays <0.5 ns absorbed into gains). "
                  "Use --do-k to enable if needed.")
   ```

2. **Document rationale** in calibration CLI help:
   ```python
   parser.add_argument('--do-k', action='store_true',
                      help='Enable K-calibration (delay). '
                           'Default: disabled for DSA-110 short baselines. '
                           'Delays <0.5 ns are absorbed into gain calibration.')
   ```

3. **Add validation** that checks if K-cal might be needed:
   ```python
   def recommend_k_calibration(ms_path: Path) -> bool:
       """Check if K-calibration might be beneficial."""
       # Check baseline lengths, residual delays, etc.
   ```

### 2.3 Calibration Table Registry Complexity

**Problem:** Calibration table registry tracks validity windows, but:
- When should tables be registered?
- How does applycal select tables?
- What happens if multiple valid tables exist?

**Confusion Sources:**
- Registry is automatic in streaming, manual in CLI
- Validity windows (MJD ranges) aren't intuitive
- Apply order matters (K → BP → G) but isn't enforced

**Recommendations:**
1. **Document registry workflow** clearly:
   ```
   Calibration Table Registry:
   1. Calibration creates tables (K.bpcal, BP.bpcal, G.gpcal)
   2. Tables are registered with validity window (MJD range)
   3. ApplyCal queries registry for active tables at MS mid-MJD
   4. Tables applied in order: K → BP → G
   ```

2. **Add registry inspection CLI**:
   ```bash
   python -m dsa110_contimg.database.registry_cli list --mjd 60000
   # Shows active tables for given MJD
   ```

3. **Validate apply order** when registering:
   ```python
   def register_table(table_path: Path, apply_order: int):
       """Register table with apply order validation."""
       if apply_order == 1 and not table_path.name.startswith('K'):
           raise ValueError("Apply order 1 must be K-calibration table")
   ```

---

## 3. Tunable Parameters and Choices

### 3.1 Calibration Parameter Overload

**Problem:** Calibration has many tunable parameters with unclear defaults:

**K-Calibration:**
- `--delay-solint`: `'inf'` (default) vs. `'30s'` vs. `'int'`
- `--delay-minsnr`: Default not documented
- `--delay-combine`: Default not documented

**BP-Calibration:**
- `--bp-solint`: `'inf'` (default)
- `--bp-combine-field`: Default behavior unclear
- `--bp-minsnr`: Default not documented
- `--uvrange`: `'>1klambda'` (default) - when to change?

**G-Calibration:**
- `--gain-solint`: `'inf'` vs. `'30s'` vs. `'int'`
- `--gain-calmode`: `'ap'` vs. `'p'` vs. `'a'`
- `--fast`: Enables phase-only gains, timebin, chanbin

**Confusion Sources:**
- Which parameters matter most?
- What are good defaults for DSA-110?
- When should I deviate from defaults?

**Recommendations:**
1. **Create calibration presets**:
   ```python
   CALIBRATION_PRESETS = {
       'fast': {
           'do_k': False,
           'bp_solint': 'inf',
           'bp_combine_field': True,
           'gain_solint': '30s',
           'gain_calmode': 'p',  # phase-only
           'timebin': '30s',
           'chanbin': 4,
           'uvrange': '>1klambda',
       },
       'standard': {
           'do_k': False,
           'bp_solint': 'inf',
           'bp_combine_field': True,
           'gain_solint': 'inf',
           'gain_calmode': 'ap',  # amplitude+phase
           'timebin': None,
           'chanbin': None,
           'uvrange': '',
       },
       'high_snr': {
           # For bright calibrators
           'do_k': False,
           'bp_solint': 'inf',
           'bp_combine_field': True,
           'gain_solint': 'int',
           'gain_calmode': 'ap',
           'bp_minsnr': 5.0,
           'gain_minsnr': 5.0,
       }
   }
   ```

2. **Add parameter recommendations** based on data quality:
   ```python
   def recommend_calibration_params(ms_path: Path, snr_estimate: float) -> dict:
       """Recommend calibration parameters based on data quality."""
       if snr_estimate < 10:
           return CALIBRATION_PRESETS['fast']
       elif snr_estimate > 50:
           return CALIBRATION_PRESETS['high_snr']
       else:
           return CALIBRATION_PRESETS['standard']
   ```

3. **Document parameter impacts** in table format:
   | Parameter | Impact | When to Change |
   |-----------|--------|----------------|
   | `--bp-combine-field` | SNR | Enable for weak calibrators |
   | `--uvrange` | Solution count | Relax (`>0.3klambda`) for low SNR |
   | `--gain-solint` | Time variability | Use `'int'` for fast variations |
   | `--gain-calmode` | Speed vs. accuracy | `'p'` for speed, `'ap'` for accuracy |

### 3.2 Imaging Parameter Choices

**Problem:** Imaging has many parameters with unclear relationships:

**Image Size:**
- `--imsize`: Default 1024, but depends on FoV and cell size
- `--cell`: Auto-calculated, but can override

**Weighting:**
- `--weighting`: `'briggs'` (default)
- `--robust`: 0.0 (default), but optimal depends on science goal

**Deconvolution:**
- `--deconvolver`: `'hogbom'` vs. `'multiscale'` vs. `'mtmfs'`
- `--niter`: Default varies by mode
- `--threshold`: Default not documented

**Confusion Sources:**
- How do imsize, cell, and FoV relate?
- When to use which deconvolver?
- What's a good threshold?

**Recommendations:**
1. **Add imaging presets**:
   ```python
   IMAGING_PRESETS = {
       'quick': {
           'imsize': 512,
           'niter': 300,
           'threshold': '0.1mJy',
           'robust': 0.0,
           'skip_fits': True,
       },
       'standard': {
           'imsize': 1024,
           'niter': 1000,
           'threshold': '0.05mJy',
           'robust': 0.5,
           'skip_fits': False,
       },
       'deep': {
           'imsize': 2048,
           'niter': 5000,
           'threshold': '0.01mJy',
           'robust': 0.0,
           'skip_fits': False,
       }
   }
   ```

2. **Add auto-calculation** for cell size:
   ```python
   def calculate_cell_size(ms_path: Path, imsize: int = None) -> float:
       """Calculate optimal cell size based on uv coverage."""
       # Query MS for max baseline, calculate beam size
       # Recommend 3-5 pixels per beam
   ```

3. **Document deconvolver selection**:
   ```
   Deconvolver Selection:
   - hogbom: Point sources (default for calibrators)
   - multiscale: Extended sources
   - mtmfs: Wide-field, multi-frequency synthesis
   ```

### 3.3 Environment Variable Overload

**Problem:** Many environment variables control behavior:

**Core:**
- `PIPELINE_QUEUE_DB`, `PIPELINE_REGISTRY_DB`, `PIPELINE_PRODUCTS_DB`
- `PIPELINE_STATE_DIR`
- `PIPELINE_TELESCOPE_NAME`

**Performance:**
- `HDF5_USE_FILE_LOCKING` (should be `FALSE`)
- `OMP_NUM_THREADS`, `MKL_NUM_THREADS`

**Streaming:**
- `PIPELINE_POINTING_DEC_DEG`
- `VLA_CALIBRATOR_CSV`
- `CAL_MATCH_RADIUS_DEG`, `CAL_MATCH_TOPN`

**Imaging:**
- `IMG_IMSIZE`, `IMG_ROBUST`, `IMG_NITER`, `IMG_THRESHOLD`

**Confusion Sources:**
- Which variables are required vs. optional?
- What are good defaults?
- Where should they be set? (systemd env, Docker env, shell?)

**Recommendations:**
1. **Create configuration template** with all variables documented:
   ```bash
   # ops/docker/.env.example (expand current)
   # Core Database Paths (required)
   PIPELINE_QUEUE_DB=state/ingest.sqlite3
   PIPELINE_REGISTRY_DB=state/cal_registry.sqlite3
   PIPELINE_PRODUCTS_DB=state/products.sqlite3
   PIPELINE_STATE_DIR=state
   
   # Telescope Configuration (required)
   PIPELINE_TELESCOPE_NAME=DSA_110
   
   # Performance Tuning (recommended)
   HDF5_USE_FILE_LOCKING=FALSE  # CRITICAL: Prevents file locking issues
   OMP_NUM_THREADS=4  # Adjust based on CPU cores
   MKL_NUM_THREADS=4  # Adjust based on CPU cores
   
   # Streaming Configuration (optional)
   PIPELINE_POINTING_DEC_DEG=  # Auto-detect if not set
   VLA_CALIBRATOR_CSV=state/catalogs/vla_calibrators.sqlite3
   CAL_MATCH_RADIUS_DEG=1.0
   CAL_MATCH_TOPN=3
   
   # Imaging Defaults (optional, can override via CLI)
   IMG_IMSIZE=1024
   IMG_ROBUST=0.5
   IMG_NITER=1000
   IMG_THRESHOLD=0.05mJy
   ```

2. **Add configuration validation**:
   ```python
   def validate_pipeline_config() -> list[str]:
       """Validate environment configuration, return list of issues."""
       issues = []
       if not os.getenv('PIPELINE_PRODUCTS_DB'):
           issues.append("PIPELINE_PRODUCTS_DB not set")
       if os.getenv('HDF5_USE_FILE_LOCKING') != 'FALSE':
           issues.append("HDF5_USE_FILE_LOCKING should be FALSE")
       return issues
   ```

3. **Document variable precedence**:
   ```
   Configuration Precedence:
   1. CLI arguments (highest priority)
   2. Environment variables
   3. Default values (lowest priority)
   ```

---

## 4. Documentation and Discoverability

### 4.1 Scattered Documentation

**Problem:** Documentation exists but is scattered:
- `README.md` - Overview
- `docs/quickstart.md` - Quick start
- `docs/pipeline.md` - Pipeline flow
- `docs/reference/` - CLI, API, env vars
- `MEMORY.md` - Codebase understanding
- `PROJECT_REVIEW.md` - Code review

**Confusion Sources:**
- Where do I start?
- Which doc answers my question?
- What's the difference between quickstart and pipeline docs?

**Recommendations:**
1. **Create documentation map**:
   ```
   Documentation Hierarchy:
   ├── README.md (start here)
   ├── docs/quickstart.md (get running in 5 minutes)
   ├── docs/pipeline.md (understand workflow)
   ├── docs/tutorials/ (step-by-step guides)
   ├── docs/reference/ (complete API/CLI reference)
   └── docs/guides/ (advanced topics)
   ```

2. **Add "Getting Started" section** to README:
   ```markdown
   ## Getting Started
   
   **First time?** Start here:
   1. Read [Quick Start](docs/quickstart.md) (5 min)
   2. Try [End-to-End Tutorial](docs/tutorials/streaming.md) (30 min)
   3. Explore [Pipeline Flow](docs/pipeline.md) (10 min)
   
   **Common tasks:**
   - [Convert UVH5 → MS](docs/tutorials/convert-standalone.md)
   - [Calibrate Data](docs/tutorials/calibrate-apply.md)
   - [Image Data](docs/reference/cli.md#imaging)
   ```

3. **Add cross-references** between docs:
   - Each doc should link to related docs
   - Use consistent terminology

### 4.2 Missing Decision Guides

**Problem:** No guides for making choices:
- Which calibrator to use?
- Which calibration parameters?
- Which imaging parameters?
- When to use streaming vs. one-off?

**Recommendations:**
1. **Create decision guides**:
   - `docs/guides/calibrator_selection.md`
   - `docs/guides/calibration_parameters.md`
   - `docs/guides/imaging_parameters.md`
   - `docs/guides/streaming_vs_manual.md`

2. **Add decision trees**:
   ```
   Should I use streaming or manual processing?
   
   ┌─────────────────┐
   │ Continuous data? │──Yes──→ Streaming
   └─────────────────┘
          │ No
          ↓
   ┌─────────────────┐
   │ Single group?    │──Yes──→ Manual (orchestrator)
   └─────────────────┘
          │ No
          ↓
   ┌─────────────────┐
   │ Batch process?   │──Yes──→ Script with orchestrator
   └─────────────────┘
   ```

### 4.3 Error Message Clarity

**Problem:** Some error messages are technical but don't guide next steps:
- "MODEL_DATA is all zeros" - What should I do?
- "No valid calibration tables found" - How do I create them?
- "Writer selection failed" - Why?

**Recommendations:**
1. **Add actionable error messages**:
   ```python
   if model_data_is_all_zeros(ms_path):
       raise ValueError(
           "MODEL_DATA is all zeros. This is required for calibration.\n"
           "Action: Populate MODEL_DATA using one of:\n"
           "  1. Setjy for calibrator: python -m dsa110_contimg.calibration.cli setjy ...\n"
           "  2. NVSS catalog: python -m dsa110_contimg.calibration.cli model catalog ...\n"
           "See: docs/tutorials/calibrate-apply.md#sky-model-seeding"
       )
   ```

2. **Add error code system**:
   ```python
   class PipelineError(Exception):
       """Base exception with error code."""
       def __init__(self, code: str, message: str, help_url: str = None):
           self.code = code
           self.help_url = help_url
           super().__init__(f"[{code}] {message}")
   ```

3. **Link errors to documentation**:
   - Each error code links to troubleshooting guide
   - Help URLs point to specific docs

---

## 5. Usability Improvements

### 5.1 CLI Consistency

**Problem:** CLI interfaces vary across modules:
- Some use subcommands (`calibration.cli calibrate`)
- Some use flags (`imaging.cli --ms ...`)
- Some use positional args (`orchestrator input output start end`)

**Recommendations:**
1. **Standardize CLI patterns**:
   ```python
   # Consistent subcommand structure:
   python -m dsa110_contimg.<module>.cli <command> [options]
   
   # Examples:
   python -m dsa110_contimg.calibration.cli calibrate --ms ...
   python -m dsa110_contimg.imaging.cli image --ms ...
   python -m dsa110_contimg.conversion.cli groups --input-dir ...
   ```

2. **Use common argument names**:
   - `--ms` (not `--ms-path`, `--measurement-set`)
   - `--output-dir` (not `--out`, `--output`)
   - `--log-level` (not `--verbose`, `--log`)

3. **Add consistent help output**:
   ```python
   parser.add_argument('--ms', required=True,
                      help='Path to Measurement Set (required)')
   ```

### 5.2 Validation and Pre-flight Checks

**Problem:** Some stages fail late with unclear errors:
- Calibration fails because MODEL_DATA missing
- Imaging fails because calibration not applied
- Conversion fails because file format wrong

**Recommendations:**
1. **Add pre-flight validation**:
   ```python
   def validate_before_calibration(ms_path: Path) -> ValidationResult:
       """Check if MS is ready for calibration."""
       result = ValidationResult()
       if not has_model_data(ms_path):
           result.add_error("MODEL_DATA column missing or all zeros")
       if not has_valid_fields(ms_path):
           result.add_error("No valid fields found")
       return result
   ```

2. **Add dry-run mode**:
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate --ms ... --dry-run
   # Validates prerequisites without running calibration
   ```

3. **Show validation results**:
   ```bash
   python -m dsa110_contimg.calibration.cli validate --ms ...
   # Checks MS and reports issues
   ```

### 5.3 Progress Reporting

**Problem:** Long-running operations don't always show progress:
- Conversion can take minutes with no feedback
- Calibration progress unclear
- Imaging progress limited

**Recommendations:**
1. **Add progress bars** for long operations:
   ```python
   with progress_bar(total=len(subbands), desc="Converting subbands"):
       for sb in subbands:
           convert_subband(sb)
           progress_bar.update(1)
   ```

2. **Add time estimates**:
   ```python
   logger.info(f"Calibration started. Estimated time: {estimate_time()} minutes")
   ```

3. **Add checkpoint reporting**:
   ```python
   logger.info("Calibration progress: K-cal complete, BP-cal in progress...")
   ```

---

## 6. Configuration Management

### 6.1 Configuration File Support

**Problem:** All configuration via environment variables or CLI args:
- No configuration file support
- Hard to version control settings
- Repetitive CLI invocations

**Recommendations:**
1. **Add YAML/TOML config file support**:
   ```yaml
   # pipeline_config.yaml
   pipeline:
     telescope_name: DSA_110
     state_dir: state
     databases:
       queue: state/ingest.sqlite3
       registry: state/cal_registry.sqlite3
       products: state/products.sqlite3
   
   calibration:
     default_preset: fast
     do_k: false
     fast:
       timebin: 30s
       chanbin: 4
       uvrange: ">1klambda"
   
   imaging:
     default_preset: standard
     standard:
       imsize: 1024
       robust: 0.5
       niter: 1000
   ```

2. **Support config file + CLI override**:
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate \
     --config pipeline_config.yaml \
     --ms ... \
     --gain-solint 60s  # Override config file
   ```

3. **Validate config file**:
   ```python
   def validate_config(config_path: Path) -> list[str]:
       """Validate configuration file, return list of issues."""
       # Check required fields, valid values, etc.
   ```

### 6.2 Preset System

**Problem:** No easy way to use common parameter combinations:
- "Fast calibration" requires many flags
- "Quick imaging" requires many flags
- "Production imaging" requires many flags

**Recommendations:**
1. **Add preset system**:
   ```python
   # Built-in presets
   PRESETS = {
       'calibration': {
           'fast': {...},
           'standard': {...},
           'high_snr': {...},
       },
       'imaging': {
           'quick': {...},
           'standard': {...},
           'deep': {...},
       }
   }
   ```

2. **Allow preset + overrides**:
   ```bash
   python -m dsa110_contimg.calibration.cli calibrate \
     --preset fast \
     --ms ... \
     --gain-solint 60s  # Override preset
   ```

3. **Allow custom presets**:
   ```yaml
   # Custom presets in config file
   presets:
     my_custom_cal:
       do_k: false
       gain_solint: 60s
       # ...
   ```

---

## 7. Testing and Validation

### 7.1 Synthetic Data Generation

**Problem:** Testing requires real data or complex synthetic generation:
- Synthetic data tools exist but not well-documented
- No simple "test pipeline" command
- Hard to reproduce test scenarios

**Recommendations:**
1. **Add test pipeline command**:
   ```bash
   python -m dsa110_contimg.test generate_synthetic \
     --n-subbands 16 \
     --duration 5min \
     --output /tmp/test_data
   
   python -m dsa110_contimg.test run_pipeline \
     --input /tmp/test_data \
     --output /tmp/test_output
   ```

2. **Document synthetic data workflows**:
   - `docs/testing/synthetic_data.md`
   - `docs/testing/pipeline_testing.md`

3. **Add test presets**:
   ```python
   TEST_PRESETS = {
       'minimal': {'n_subbands': 4, 'duration': '1min'},
       'standard': {'n_subbands': 16, 'duration': '5min'},
       'full': {'n_subbands': 16, 'duration': '30min'},
   }
   ```

---

## 8. Summary of Recommendations

### High Priority (Immediate Impact)

1. **Entry Point Clarity**
   - Document entry point hierarchy
   - Make unified CLI primary entry point
   - Add decision tree for tool selection

2. **Workflow Documentation**
   - Create explicit workflow diagram
   - Document stage dependencies
   - Add stage validation

3. **Parameter Documentation**
   - Document all tunable parameters
   - Create parameter impact tables
   - Add calibration/imaging presets

### Medium Priority (Improves Usability)

4. **Configuration Management**
   - Add config file support (YAML/TOML)
   - Create configuration templates
   - Add configuration validation

5. **Error Messages**
   - Add actionable error messages
   - Link errors to documentation
   - Add error code system

6. **Progress Reporting**
   - Add progress bars for long operations
   - Add time estimates
   - Add checkpoint reporting

### Low Priority (Nice to Have)

7. **Preset System**
   - Add built-in presets
   - Allow custom presets
   - Document preset usage

8. **Testing Tools**
   - Add test pipeline command
   - Document synthetic data workflows
   - Add test presets

---

## 9. Implementation Priority

**Phase 1 (Week 1):**
- Document entry point hierarchy
- Add workflow diagram
- Create parameter impact tables

**Phase 2 (Week 2):**
- Add configuration file support
- Create presets system
- Improve error messages

**Phase 3 (Week 3):**
- Add progress reporting
- Add pre-flight validation
- Create test pipeline command

---

## 10. Metrics for Success

**Usability Metrics:**
- Time to first successful pipeline run (target: <30 minutes)
- Number of documentation lookups needed (target: <5)
- Error rate for common operations (target: <10%)

**Clarity Metrics:**
- Documentation completeness score (target: >90%)
- Parameter documentation coverage (target: 100%)
- Error message actionability (target: >80%)

---

**Next Steps:**
1. Review this document with team
2. Prioritize recommendations
3. Create implementation tickets
4. Track usability improvements

