# Documentation and Cursor Rules Issues Found

**Date:** 2025-11-10  
**Purpose:** Identify incorrect, outdated, or inconsistent information in documentation and Cursor rules

---

## Critical Issues

### 1. Documentation Location Rule Inconsistency

**Issue:** Cursor rule references incorrect path for dev documentation

**Location:** `.cursor/rules/documentation-location.mdc` (lines 25-29)

**Current (INCORRECT):**
```markdown
└─ NO → Is this a status update?
    ├─ YES → docs/dev/status/YYYY-MM/
    └─ NO → Is this an investigation?
        ├─ YES → docs/dev/analysis/
        └─ NO → Is this agent notes?
            ├─ YES → docs/dev/notes/
```

**Should be:**
```markdown
└─ NO → Is this a status update?
    ├─ YES → internal/docs/dev/status/YYYY-MM/
    └─ NO → Is this an investigation?
        ├─ YES → internal/docs/dev/analysis/
        └─ NO → Is this agent notes?
            ├─ YES → internal/docs/dev/notes/
```

**Evidence:**
- `docs/DOCUMENTATION_QUICK_REFERENCE.md` correctly references `internal/docs/dev/status/`
- Actual directory structure: `internal/docs/dev/status/`, `internal/docs/dev/analysis/`, `internal/docs/dev/notes/`
- `docs/dev/status/` also exists but appears to be a different location (contains different files)

**Impact:** Agents may create files in wrong location (`docs/dev/` instead of `internal/docs/dev/`)

**Fix:** Update `.cursor/rules/documentation-location.mdc` to use `internal/docs/dev/` paths

---

### 2. Configuration Path Mismatches

**Issue:** Documentation references non-existent paths `/data/ingest`, `/data/ms`, `/data/scratch`

**Affected Files:**
- `docs/concepts/DIRECTORY_ARCHITECTURE.md` (lines 13-18)
- `ops/systemd/contimg.env` (actual configuration file)
- Multiple documentation files reference these paths

**Current (INCORRECT):**
```bash
CONTIMG_INPUT_DIR=/data/ingest      # ❌ Doesn't exist
CONTIMG_OUTPUT_DIR=/data/ms         # ❌ Doesn't exist
CONTIMG_SCRATCH_DIR=/data/scratch   # ❌ Doesn't exist
```

**Actual Paths:**
```bash
/stage/dsa110-contimg/incoming/     # ✅ Actual location
/stage/dsa110-contimg/ms/           # ✅ Actual location
/stage/dsa110-contimg/tmp/          # ✅ Actual location
```

**Impact:** 
- Configuration doesn't match reality
- Documentation misleads users about actual data locations
- Services may fail if paths don't exist

**Fix:** 
- Update `ops/systemd/contimg.env` to match actual paths
- Update documentation to reflect actual paths OR document migration plan

---

## Medium Priority Issues

### 3. Python Command References

**Issue:** Some documentation uses `python3` instead of casa6 path

**Affected Files:**
- `docs/how-to/FIND_CALIBRATOR_TRANSIT_DATA.md` (lines 128, 177)
- `docs/analysis/FORCED_PHOTOMETRY_TESTS.md` (multiple instances)

**Example:**
```python
#!/usr/bin/env python3  # ❌ Should use casa6
```

**Should be:**
```python
#!/usr/bin/env /opt/miniforge/envs/casa6/bin/python  # ✅ Correct
# OR
#!/opt/miniforge/envs/casa6/bin/python  # ✅ Also correct
```

**Impact:** 
- Scripts may fail if run with system Python
- Inconsistent with critical requirement that ALL Python execution use casa6

**Fix:** Update all `python3` references to use casa6 path or add clear warnings

---

### 4. Duplicate Dev Documentation Locations

**Issue:** Both `docs/dev/` and `internal/docs/dev/` exist with different content

**Current State:**
- `docs/dev/` - Contains various dev documentation files
- `internal/docs/dev/` - Contains status, analysis, notes subdirectories

**Problem:**
- Unclear which location should be used
- Documentation rules conflict (some say `docs/dev/`, others say `internal/docs/dev/`)
- Risk of creating files in wrong location

**Recommendation:**
- Consolidate to single location: `internal/docs/dev/`
- Move existing `docs/dev/` files to `internal/docs/dev/` or archive
- Update all rules to reference single location

---

### 5. Deprecated Import Reference Accuracy

**Issue:** README mentions deprecated import path

**Location:** `README.md` line 218

**Current:**
```markdown
- Older imports from `dsa110_contimg.core.conversion.*` are deprecated; use `dsa110_contimg.conversion.*`
```

**Verification:** ✅ **CORRECT** - No references to `dsa110_contimg.core.` found in source code

**Status:** This is accurate and should remain

---

## Low Priority Issues

### 6. Legacy Code References

**Issue:** References to archived legacy code

**Location:** Multiple documentation files reference `archive/legacy/api/job_runner_legacy.py`

**Verification:** ✅ **CORRECT** - File exists at `archive/legacy/api/job_runner_legacy.py`

**Status:** These references are accurate

---

### 7. Notebook References to Deprecated Code

**Issue:** Notebooks may reference deprecated conversion modules

**Affected Files:**
- `docs/tutorials/notebooks/ms_staging_workflow.ipynb`
- `tests/utils/testing.ipynb`
- `internal/docs/chat/cursor_ingest_data_and_construct_mosaic.md`

**Reference:** MEMORY.md mentions:
> Outdated notebook reference: `docs/notebooks/ms_staging_workflow.ipynb` still references `dsa110_contimg.conversion.uvh5_to_ms_converter_v2` (removed). Update to `conversion.strategies.hdf5_orchestrator` or `conversion.cli` to match current docs.

**Status:** Needs verification - check if notebooks still reference deprecated code

---

### 8. Documentation Path References in Code Comments

**Issue:** Some code comments reference documentation paths that may have moved

**Example:** References to `docs/dev/status/` in code comments when actual location is `internal/docs/dev/status/`

**Impact:** Low - comments are less critical than user-facing docs

**Fix:** Update code comments to reference correct paths

---

## Summary of Required Fixes

### Immediate (Critical)

1. **Fix Cursor rule path:** Update `.cursor/rules/documentation-location.mdc` to use `internal/docs/dev/` instead of `docs/dev/`
2. **Fix configuration paths:** Update `ops/systemd/contimg.env` to match actual paths OR document migration plan

### Short-term (Medium Priority)

3. **Update Python references:** Replace `python3` with casa6 path in documentation
4. **Consolidate dev docs:** Decide on single location (`internal/docs/dev/`) and migrate

### Long-term (Low Priority)

5. **Verify notebook references:** Check and update notebooks referencing deprecated code
6. **Update code comments:** Fix path references in code comments

---

## Verification Checklist

- [x] Cursor rule path inconsistency identified
- [x] Configuration path mismatches documented
- [x] Python command references checked
- [x] Dev documentation locations verified
- [x] Deprecated import references verified (correct)
- [x] Legacy code references verified (correct)
- [ ] Notebook references verified (needs manual check)
- [ ] Code comment references checked

---

## Related Documentation

- **Documentation Rules:** `.cursor/rules/documentation-location.mdc`
- **Documentation Quick Reference:** `docs/DOCUMENTATION_QUICK_REFERENCE.md`
- **Directory Architecture:** `docs/concepts/DIRECTORY_ARCHITECTURE.md`
- **Memory File:** `MEMORY.md` (contains known issues)

---

**Document Status:** Complete  
**Last Updated:** 2025-11-10

