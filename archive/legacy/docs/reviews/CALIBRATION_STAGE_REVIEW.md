# Calibration Stage Review

## Current Architecture

### Primary Entry Points (Production)

1. **Unified CLI** (`src/dsa110_contimg/calibration/cli.py`)
   - Subcommand: `calibrate` → orchestrates K/BP/G calibration solves
   - Subcommand: `apply` → applies calibration tables to target MS
   - Subcommand: `check-delays` → checks if delays are corrected upstream
   - Subcommand: `verify-delays` → verifies K-calibration delay solutions
   - Subcommand: `inspect-delays` → inspects K-calibration delay values
   - Subcommand: `list-transits` → lists available calibrator transits with data
   - **Status**: ✓ Modern, clean, uses shared utilities

2. **Core Calibration Modules** (`src/dsa110_contimg/calibration/`)
   - `calibration.py` → `solve_delay()`, `solve_bandpass()`, `solve_gains()`
   - `flagging.py` → `reset_flags()`, `flag_zeros()`, `flag_rfi()`, etc.
   - `applycal.py` → `apply_to_target()` with verification
   - `qa.py` → QA/diagnostic functions (check delays, verify solutions)
   - `selection.py` → Field selection utilities for bandpass calibration
   - `validate.py` → Calibration table validation
   - **Status**: ✓ Well-organized, good separation of concerns

3. **Service Layer** (`src/dsa110_contimg/calibration/apply_service.py`)
   - High-level calibration application with registry lookup
   - Verification and database integration
   - **Status**: ✓ Production-ready service layer

### Test Utilities (Questionable)

4. **Demo Script** (`tests/utils/cal_ms_demo.py`)
   - 66 lines
   - Uses **outdated imports**: `from casa_cal.*` instead of `dsa110_contimg.calibration.*`
   - Demonstrates full calibration workflow (K+B+G, apply, image)
   - **Status**: ⚠️ **Uses wrong import paths** - should be updated or removed

### Integration Tests (Good)

5. **End-to-End Test** (`tests/integration/test_pipeline_end_to_end.sh`)
   - Uses production modules correctly: `from dsa110_contimg.calibration.flagging import reset_flags, flag_zeros`
   - Uses production modules correctly: `from dsa110_contimg.calibration.applycal import apply_to_target`
   - Calls production CLI: `dsa110_contimg.calibration.cli calibrate`
   - **Status**: ✅ **Good example** - uses production code

---

## Question 1: Multiple Scripts Analysis

### Why Multiple Scripts Exist

**Problem Identified**: There is **1 demo script** with outdated imports that should be updated or removed.

#### `tests/utils/cal_ms_demo.py` issues:
- Uses `from casa_cal.*` instead of `dsa110_contimg.calibration.*`
- This appears to be legacy code from before the module was renamed/reorganized
- The README mentions "casa_cal: CASA 6.7 calibration helpers (no dsacalib)" but the actual package is `dsa110_contimg.calibration`
- **Impact**: Script will fail to run due to import errors

**Why this happened:**
- Likely created during early development when package structure was different
- Not updated during module reorganization
- May have been a quick demo/test script that wasn't maintained

**Recommendation**: 
- ✅ **Update imports** to use `dsa110_contimg.calibration.*`
- ✅ Or **archive** the script if it's no longer needed (since we have CLI and integration tests)
- ✅ If keeping, ensure it uses production modules (not duplicate code)

### No Duplicate Production Code Found ✓

Unlike the MS generation stage, **calibration does not have duplicate production code**:
- All test scripts use production modules correctly (except `cal_ms_demo.py` which has wrong imports)
- Integration tests import from `dsa110_contimg.calibration.*` directly
- CLI is the single source of truth for calibration workflows

**Status**: ✅ Good - single source of truth maintained

---

## Question 2: Testing Improvements

### Current Testing Capabilities

**Available:**
- Production CLI with comprehensive flags (`--fast`, `--do-k`, `--skip-bp`, etc.)
- QA subcommands for diagnostic checks (`check-delays`, `verify-delays`, `inspect-delays`)
- `apply` subcommand with verification
- Integration test using production code correctly

### What Users Might Want for Easier Testing

#### 1. **Calibration Validation Mode** (Partially exists)
**What**: Validate MS is ready for calibration without solving
**Current**: MS validation exists (`validate_ms_for_calibration`) but no standalone command
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.calibration.cli validate \
    --ms /path/to/ms \
    --field 0 \
    --refant 103
```
**Benefit**: Quick check before committing to long calibration solve

#### 2. **Dry-Run Mode**
**What**: Simulate calibration workflow without writing caltables
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --dry-run  # Validates inputs, checks data quality, estimates time/cost
```
**Benefit**: Fast feedback on whether calibration will succeed

#### 3. **Calibration Solve Progress**
**What**: Better visibility into long-running solves
**Current**: Some progress via CASA, but could be enhanced
**Implementation**:
```python
# Add progress callbacks or intermediate output:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --verbose-progress  # Show intermediate solve statistics
```
**Benefit**: Debug slow calibrations, understand what's happening

#### 4. **Minimal Test Calibration**
**What**: Quick calibration test on tiny subset
**Current**: `--fast` mode exists but could be more minimal
**Implementation**:
```python
# Enhance --fast mode or add --minimal:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --minimal  # Even more aggressive subsetting: 1 baseline, 4 channels, 1 time
```
**Benefit**: Very fast calibration test (< 30 seconds) for quick iteration

#### 5. **Calibration Comparison Tool**
**What**: Compare two calibration solutions to verify consistency
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.calibration.cli compare \
    --caltable1 /path/to/cal1.gcal \
    --caltable2 /path/to/cal2.gcal \
    --tolerance 1e-6
```
**Benefit**: Regression testing, verify fixes don't break existing solutions

#### 6. **Calibration Diagnostics Mode**
**What**: Comprehensive diagnostic report after calibration
**Current**: Some QA exists but could be more integrated
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --diagnostics  # Generate detailed report: solution quality, SNR, flags, etc.
```
**Benefit**: Understand calibration quality and identify issues

#### 7. **Incremental Calibration Testing**
**What**: Test individual calibration stages separately
**Implementation**:
```python
# Add stop-after flags:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --stop-after flagging    # Stop after flagging, show statistics
    --stop-after k           # Stop after K-cal, inspect K table
    --stop-after bp          # Stop after BP, inspect BP table
```
**Benefit**: Debug specific calibration stages

#### 8. **Calibration Table Verification Tool**
**What**: Verify caltables are valid before applying
**Current**: Some validation exists in `validate.py`
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.calibration.cli verify-tables \
    --ms /path/to/ms \
    --tables cal.kcal cal.bpcal cal.gcal \
    --check-compatibility \
    --check-solutions
```
**Benefit**: Catch errors before applying calibration

#### 9. **Quick Calibration Smoke Test**
**What**: Very fast end-to-end calibration test
**Implementation**:
```python
# Add test command:
dsa110_contimg.calibration.cli smoke-test \
    --ms /path/to/minimal-test.ms \
    --field 0 --refant 1
# Runs minimal calibration (fast mode, minimal subset) in < 1 minute
```
**Benefit**: Quick sanity check after environment changes

#### 10. **Calibration Recipe Presets**
**What**: Common calibration workflows as presets
**Implementation**:
```python
# Add preset flags:
dsa110_contimg.calibration.cli calibrate \
    --ms /path/to/ms \
    --preset quick-look     # Fast mode, minimal subset
    --preset production     # Full calibration, no shortcuts
    --preset debugging      # Extra diagnostics, intermediate outputs
```
**Benefit**: Easier for users to choose appropriate calibration strategy

#### 11. **Calibration Stage Isolation**
**What**: Test individual stages (flagging, K, BP, G) in isolation
**Current**: Can be done manually but no convenient wrapper
**Implementation**:
```python
# Add stage-specific commands:
dsa110_contimg.calibration.cli flag \
    --ms /path/to/ms \
    --mode rfi

dsa110_contimg.calibration.cli solve-k \
    --ms /path/to/ms \
    --field 0 --refant 103

dsa110_contimg.calibration.cli solve-bp \
    --ms /path/to/ms \
    --field 0 --refant 103 \
    --k-table cal.kcal
```
**Benefit**: Test/debug individual stages without full workflow

#### 12. **Calibration Metadata Export**
**What**: Export calibration solution statistics and metadata
**Implementation**:
```python
# Add export command:
dsa110_contimg.calibration.cli export-metadata \
    --caltables cal.kcal cal.bpcal cal.gcal \
    --output cal_metadata.json
```
**Benefit**: Documentation, quality tracking, debugging

---

## Recommendations Summary

### Immediate Actions

1. **Fix Demo Script Imports** ⚠️
   - Update `tests/utils/cal_ms_demo.py` to use `dsa110_contimg.calibration.*`
   - Or archive if no longer needed
   - **Priority**: Low (demo script, not used in production)

2. **Add Validation Subcommand** ✅
   - Add `validate` subcommand for MS pre-calibration validation
   - Leverage existing `validate_ms_for_calibration()` function
   - **Priority**: Medium (useful for users)

3. **Add Dry-Run Mode** ✅
   - Add `--dry-run` flag to `calibrate` subcommand
   - Validates inputs, estimates time/cost, checks data quality
   - **Priority**: Medium (improves user experience)

4. **Enhance Progress Reporting** ✅
   - Better visibility into long-running solves
   - Intermediate statistics/output during solves
   - **Priority**: Low (nice to have)

### Long-term Improvements

5. **Calibration Comparison Tool**
   - Compare calibration solutions for regression testing
   - Useful for verifying fixes don't break existing solutions

6. **Comprehensive Diagnostics**
   - Integrated diagnostic report generation
   - Solution quality metrics, SNR analysis, flag statistics

7. **Calibration Recipe Presets**
   - Common workflows as easy-to-use presets
   - Reduces user configuration burden

---

## Code Quality Assessment

**Strengths:**
- ✅ Clean separation: solve vs. apply vs. validation
- ✅ Good use of shared utilities (validation, CLI helpers)
- ✅ Modern CLI architecture with subcommands
- ✅ Comprehensive error handling and validation
- ✅ No duplicate production code (unlike MS generation stage)
- ✅ Integration tests use production modules correctly

**Weaknesses:**
- ⚠️ One demo script with outdated imports (minor)
- ⚠️ No validation-only mode (would be useful)
- ⚠️ No dry-run mode (would improve testing experience)
- ⚠️ Limited progress visibility for long-running solves

**Overall Assessment**: ✅ **Well-architected** - Calibration stage is in good shape compared to MS generation. Main issues are minor (outdated demo script) and missing convenience features (validation mode, dry-run) rather than architectural problems.

---

## Comparison to MS Generation Stage

| Aspect | MS Generation | Calibration |
|--------|---------------|-------------|
| **Duplicate Code** | ❌ 2 test utilities with duplicates | ✅ None found |
| **CLI Architecture** | ✅ Modern, clean | ✅ Modern, clean |
| **Test Utilities** | ❌ Use duplicate code | ⚠️ 1 with wrong imports |
| **Integration Tests** | ✅ Use production code | ✅ Use production code |
| **Validation Modes** | ✅ Multiple (validate, verify-ms) | ⚠️ Limited |
| **Dry-Run** | ✅ Available | ❌ Not available |
| **Overall Quality** | ⚠️ Needs cleanup | ✅ Good shape |

**Conclusion**: Calibration stage is in **better shape** than MS generation. Main improvements needed are convenience features (validation mode, dry-run) rather than architectural fixes.

