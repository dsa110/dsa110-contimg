# MS Generation Stage Review

## Current Architecture

### Primary Entry Points (Production)

1. **Unified CLI** (`src/dsa110_contimg/conversion/cli.py`)
   - Subcommand: `groups` → delegates to `hdf5_orchestrator.py`
   - Subcommand: `single` → delegates to `uvh5_to_ms.py`
   - Subcommand: `create-test-ms` → creates smaller test MS from full MS
   - **Status**: ✓ Modern, clean, uses shared utilities

2. **Strategy Orchestrator** (`src/dsa110_contimg/conversion/strategies/hdf5_orchestrator.py`)
   - Main production converter for batch processing
   - Discovers complete subband groups
   - Supports multiple writers (parallel-subband, direct-subband, pyuvdata)
   - Supports calibrator transit mode
   - **Status**: ✓ Production-ready, well-maintained

3. **Single File Converter** (`src/dsa110_contimg/conversion/uvh5_to_ms.py`)
   - Handles single UVH5 file or loose directory conversion
   - **Status**: ✓ Clean module, good separation of concerns

### Wrapper Scripts

4. **Bash Wrapper** (`scripts/run_conversion.sh`)
   - Wraps orchestrator with environment setup
   - Handles scratch directory management
   - Includes MS validation checks
   - **Status**: ⚠️ Utility script, but adds value (env setup, validation)

### Test Utilities (Questionable)

5. **Standalone Converter** (`tests/utils/convert_uvh5_standalone.py`)
   - 356 lines
   - Duplicates `find_subband_groups` and `_load_and_merge_subbands` logic
   - Includes calibrator catalog search functionality
   - **Status**: ❌ Duplicates production code, should use main modules

6. **Simple Converter** (`tests/utils/convert_uvh5_simple.py`)
   - 310 lines  
   - Python 2.7 compatibility comments (legacy?)
   - Duplicates core conversion logic
   - **Status**: ❌ Duplicates production code, appears legacy

---

## Question 1: Multiple Scripts Analysis

### Why Multiple Scripts Exist

**Problem Identified**: There are **2 duplicate test utilities** that reimplement core conversion logic instead of using the production modules.

#### `tests/utils/convert_uvh5_standalone.py` duplicates:
- `find_subband_groups()` - Exact duplicate of orchestrator logic
- `_load_and_merge_subbands()` - Exact duplicate of orchestrator logic  
- Core conversion workflow - Reimplements what `hdf5_orchestrator` does

**Why this happened:**
- Likely created to avoid circular import issues (comment mentions this)
- But now creates maintenance burden - changes in production code aren't reflected in tests
- Tests may pass while production code has bugs

**`tests/utils/convert_uvh5_simple.py` duplicates:**
- Same issues as standalone
- Python 2.7 comments suggest it's legacy code
- Should be deprecated or refactored

**Recommendation**: 
- ✅ Refactor test utilities to **import and use** production modules
- ✅ If circular imports are a concern, fix the architecture (dependency injection, better module structure)
- ✅ Remove duplicate code - maintain single source of truth

### Bash Script Justification

`scripts/run_conversion.sh` **IS justified** because it:
- Sets up complex environment (CASA, scratch dirs, HDF5 locking)
- Provides scratch directory management workflow
- Includes MS validation checks that are useful but not part of core conversion
- Acts as a deployment/operations script

**Status**: ✅ Keep, but could be documented better

---

## Question 2: Testing Improvements

### Current Testing Capabilities

**Available:**
- `create-test-ms` subcommand - Creates smaller MS from full MS for testing
- `--dry-run` flag - Validates inputs without writing
- `--find-only` flag - Lists files without converting
- Progress indicators for long operations

### What Users Might Want for Easier Testing

#### 1. **Synthetic Data Generation** ✓ Already exists
- `make_synthetic_uvh5.py` can generate test data
- Could be better integrated with conversion testing

#### 2. **Incremental/Resumable Conversion**
**What**: Ability to resume failed conversions or convert only missing groups
**Implementation**:
```python
# Add to hdf5_orchestrator:
--skip-existing  # Skip groups that already have MS files
--resume         # Resume from last successful group (checkpoint file)
```
**Benefit**: Faster iteration during testing, handles failures gracefully

#### 3. **Validation-Only Mode**
**What**: Validate UVH5 files without converting
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.conversion.cli validate \
    --input-dir /data/incoming \
    --start-time "2025-10-30 10:00:00" \
    --end-time "2025-10-30 11:00:00"
```
**Benefit**: Quick checks before committing to long conversion

#### 4. **MS Structure Verification Tool**
**What**: Quick tool to verify MS has required columns, structure
**Implementation**:
```python
# Add to CLI:
dsa110_contimg.conversion.cli verify-ms \
    --ms /path/to/test.ms \
    --check-imaging-columns \
    --check-field-structure
```
**Benefit**: Fast feedback on MS quality after conversion

#### 5. **Minimal Test MS Generator** ✓ Partially exists
**Current**: `create-test-ms` reduces size but requires full MS first
**Enhancement**: Direct generation from minimal synthetic data:
```python
# Could enhance:
dsa110_contimg.conversion.cli create-minimal-test-ms \
    --output /tmp/test.ms \
    --duration-minutes 1 \
    --subbands 4 \
    --baselines 20
```
**Benefit**: Faster test cycle (don't need real data or full conversion)

#### 6. **Conversion Stage Isolation**
**What**: Test individual stages (group discovery, phasing, writing) separately
**Implementation**:
```python
# Add debug/development mode:
dsa110_contimg.conversion.cli groups \
    --stop-after discover  # Stop after group discovery, print results
    --stop-after phasing   # Stop after phasing, save intermediate UVData
```
**Benefit**: Debug specific stages without full conversion

#### 7. **Better Error Context**
**What**: When conversion fails, provide diagnostic info
**Implementation**:
- Already improving with Phase 3 error messages
- Could add: "Which subband failed? What was the error context?"
- Could add: "Conversion checkpoint" with partial results saved

#### 8. **Quick Smoke Test**
**What**: Very fast end-to-end test that proves pipeline works
**Implementation**:
```python
# Add test command:
dsa110_contimg.conversion.cli smoke-test \
    --output /tmp/smoke-test.ms
# Generates minimal synthetic data, converts, validates in < 1 minute
```
**Benefit**: Quick sanity check after environment changes

#### 9. **Conversion Comparison Tool**
**What**: Compare two MS files to verify identical outputs
**Implementation**:
```python
dsa110_contimg.conversion.cli compare-ms \
    --ms1 /path/to/ms1.ms \
    --ms2 /path/to/ms2.ms \
    --tolerance 1e-6
```
**Benefit**: Regression testing, verify fixes don't break existing conversions

#### 10. **Test Data Repository Helper**
**What**: Manage small test datasets that can be reused
**Implementation**:
```python
# Could add test data management:
dsa110_contimg.conversion.cli test-data \
    --save /data/test-sets/minimal-4sb \
    --load minimal-4sb
```
**Benefit**: Consistent test baseline across developers

---

## Recommendations Summary

### Immediate Actions

1. **Remove Duplicate Test Utilities** ❌
   - Refactor `convert_uvh5_standalone.py` to use production modules
   - Remove or archive `convert_uvh5_simple.py` (appears legacy)
   - Fix any circular import issues properly

2. **Enhance Testing CLI** ✅
   - Add `validate` subcommand for UVH5 validation
   - Add `verify-ms` subcommand for MS structure checks
   - Add `smoke-test` subcommand for quick sanity checks
   - Add `--skip-existing` flag to avoid re-converting

3. **Improve Error Diagnostics** ✅
   - Add subband-level error reporting (which file failed?)
   - Add conversion checkpoint/resume capability
   - Save partial results on failure for debugging

### Long-term Improvements

4. **Test Data Management**
   - Centralized test data repository
   - Synthetic data generation integrated with testing workflow

5. **Conversion Monitoring**
   - Better progress reporting (already improving)
   - Resource usage tracking (memory, disk)
   - Performance benchmarking tools

---

## Code Quality Assessment

**Strengths:**
- ✅ Clean separation: orchestrator vs single-file converter
- ✅ Good use of shared utilities (helpers, validation)
- ✅ Modern CLI architecture with subcommands
- ✅ Progress indicators and error messages (Phase 3 improvements)

**Weaknesses:**
- ❌ Duplicate code in test utilities
- ⚠️ Bash script could be better documented
- ⚠️ No validation-only mode
- ⚠️ No conversion resume/checkpoint capability

