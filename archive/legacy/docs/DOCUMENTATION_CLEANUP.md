# Documentation Cleanup Recommendations

**Date:** 2025-01-XX  
**Purpose:** Identify documentation that references non-existent code, deprecated features, or outdated patterns

## Critical Issues (Should Update or Remove)

### 1. `docs/legacy-overview.md` - Contradictory dask-ms Documentation

**Location:** Lines 60-91

**Problem:** 
- Line 61 says: "An experimental dask‑ms writer was previously explored and referenced here. It is not part of the current tree and is unsupported."
- Lines 65-91 then describe dask-ms features as if they exist, including:
  - `--dask-write` flag` (doesn't exist)
  - `uvh5_to_ms_converter_v2.py` (doesn't exist)
  - Usage examples with `--dask-write` flags

**Files Referenced (Don't Exist):**
- `dsa110_contimg/conversion/uvh5_to_ms_converter_v2.py`

**Recommendation:**
- Remove lines 65-91 (the detailed dask-ms description)
- Keep line 61 as a historical note
- Or move the entire dask-ms section to a clearly marked "Historical/Deprecated" section

### 2. `docs/reports/CONVERSION_PROCESS_SUMMARY.md` - References Non-Existent Scripts

**Location:** Throughout document, especially lines 88-104

**Problem:**
- Describes `simple_uvh5_to_ms.py` (doesn't exist)
- Describes `dsa110_uvh5_to_ms.py` (doesn't exist)
- Describes UVFITS import flow that may not be supported

**Recommendation:**
- Rewrite to reflect current orchestrator-based conversion
- Reference `hdf5_orchestrator.py` CLI instead
- Or mark entire document as "Historical - See current docs in pipeline/"

### 3. `docs/notebooks/ms_staging_workflow.ipynb` - References Non-Existent Module

**Location:** Line 155

**Problem:**
- References `dsa110_contimg.conversion.uvh5_to_ms_converter_v2` which doesn't exist

**Recommendation:**
- Update to use current orchestrator: `dsa110_contimg.conversion.strategies.hdf5_orchestrator`
- Or update to use CLI: `dsa110_contimg.conversion.cli`

## Historical Documentation (Okay to Keep)

These documents reference archived/removed code but serve as historical records:

- `docs/reviews/MS_GENERATION_REFACTORING_COMPLETE.md` - Documents refactoring that archived old scripts ✓
- `docs/reviews/MS_GENERATION_REVIEW.md` - Historical review of issues that were fixed ✓
- `docs/reviews/CALIBRATION_STAGE_REVIEW.md` - Documents outdated script (`cal_ms_demo.py`) as a known issue ✓

## Documentation That Needs Updates

### 4. Various Reports Reference Old Script Names

These documents mention archived scripts but provide context:
- `docs/reports/PYUVDATA_3.2.4_COMPATIBILITY_SUMMARY.md` - Mentions `simple_uvh5_to_ms.py`
- `docs/reports/DSA110_SUBBAND_UPDATE_SUMMARY.md` - Mentions `simple_uvh5_to_ms.py`

**Recommendation:** Add note at top: "⚠️ Historical document - scripts referenced may be archived"

## Summary

**High Priority:**
1. Fix `docs/legacy-overview.md` - Remove contradictory dask-ms section (lines 65-91)
2. Update or archive `docs/reports/CONVERSION_PROCESS_SUMMARY.md`
3. Update `docs/notebooks/ms_staging_workflow.ipynb` to use current modules

**Medium Priority:**
4. Add historical markers to reports that reference archived scripts

**Low Priority:**
5. Review other reports for consistency with current codebase

## Action Items

- [x] Clean up `docs/legacy-overview.md` dask-ms section ✓
- [x] Update `docs/reports/CONVERSION_PROCESS_SUMMARY.md` with historical notes ✓
- [x] Update notebook to use current orchestrator ✓
- [ ] Add historical markers to other reports (optional - low priority)

