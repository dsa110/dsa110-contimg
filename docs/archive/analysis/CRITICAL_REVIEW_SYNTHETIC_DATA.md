# Critical Review: Synthetic Data Generation and Use Capabilities

**Date:** 2025-01-XX  
**Reviewer:** AI Agent  
**Scope:** Complete review of synthetic data generation, validation, provenance
tracking, and usage patterns

---

## Executive Summary

The codebase has **three main synthetic data generation capabilities**:

1. **Synthetic UVH5 visibility data** (`make_synthetic_uvh5.py`) - For
   end-to-end pipeline testing
2. **Synthetic FITS images** (`create_synthetic_images.py`) - For
   dashboard/SkyView testing
3. **Mock database data** (`create_mock_dashboard_data.py`) - For UI testing

**Overall Assessment:** Functional but with **critical gaps** in provenance
tracking, template dependencies, and validation coverage.

---

## 1. Critical Issues

### 1.1 Template Dependency (BLOCKER)

**Severity:** HIGH  
**Location:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`

**Problem:** The UVH5 generator **cannot create synthetic data from scratch**.
It requires an existing template UVH5 file:

```python
DEFAULT_TEMPLATE = (
    REPO_ROOT / "data-samples" / "ms" / "test_8subbands_concatenated.hdf5"
)
```

**Impact:**

- Circular dependency: Need real UVH5 to generate synthetic UVH5
- Blocks first-time users without access to template
- Misleading documentation (claims to generate from scratch)
- Test failures when template missing (see `test_pipeline_end_to_end.sh` lines
  163-174)

**Evidence:**

- `archive/legacy/docs/CRITICAL_ISSUE_TEMPLATE_DEPENDENCY.md` documents this
- Script unconditionally reads template (line 357-364)
- Template used for antenna positions, baselines, time arrays, UVW coordinates

**Recommendation:** Implement **Option 3 (Hybrid Approach)** from legacy docs:

- Check if template exists
- If not, build UVData from scratch using `get_itrf()` and config files
- If yes, use template for scaffolding (current behavior)

**Priority:** HIGH - Blocks new users and CI/CD without template

---

### 1.2 Inconsistent Data Provenance Marking

**Severity:** MEDIUM  
**Location:** Multiple files

**Problem:** Synthetic data is not consistently marked or tracked:

1. **FITS Images:**
   - ✅ Has `DATE-OBS` header (line 105 in `create_synthetic_images.py`)
   - ✅ Has `OBJECT = 'Synthetic Test Image'` (line 106)
   - ❌ **Missing `TELESCOP` field** (should be "SYNTHETIC" or absent)
   - ❌ Not all synthetic images tagged in database `data_tags` table

2. **UVH5 Files:**
   - ✅ History field updated: `"Synthetic point-source dataset generated"`
   - ❌ No explicit provenance metadata in extra_keywords
   - ❌ No database tracking of synthetic UVH5 files

3. **Database Tagging:**
   - ✅ Some synthetic tiles tagged (see `docs/dev/SYNTHETIC_TILES_FLAGGED.md`)
   - ❌ Tagging not automatic - requires manual intervention
   - ❌ No tagging for UVH5 files or MS files

**Impact:**

- Risk of treating synthetic data as real observations
- Validation code exists (`_verify_real_observation` in `qa/html_reports.py`)
  but not consistently applied
- Database queries may mix synthetic and real data

**Recommendation:**

1. **Automatic tagging:** Add `data_tags` entry when synthetic data created
2. **Standardize headers:** All synthetic FITS should have:
   - `TELESCOP = 'SYNTHETIC'` (or absent)
   - `OBJECT = 'Synthetic Test Image'`
   - `SYNTHETIC = True` (custom keyword)
3. **UVH5 metadata:** Add `extra_keywords['synthetic'] = True`
4. **Database schema:** Ensure all synthetic data has `data_tags` entry

**Priority:** MEDIUM - Data integrity risk

---

### 1.3 Duplicate Implementation of `create_synthetic_fits`

**Severity:** LOW  
**Location:** Multiple files

**Problem:** `create_synthetic_fits()` function exists in **three different
locations** with slightly different signatures:

1. `scripts/create_synthetic_images.py` (lines 37-111)
   - Used for dashboard testing
   - Adds to database
   - Output: `/data/dsa110-contimg/state/synth/images/`

2. `tests/integration/test_forced_photometry_simulation.py` (lines 24-127)
   - Used for photometry validation tests
   - Different parameter names (`pixel_scale` vs `pixel_scale_arcsec`)
   - Different beam calculation

3. `tests/test_forced_photometry.py` (lines 50-59, signature only shown)
   - Likely another variant

**Impact:**

- Code duplication
- Inconsistent behavior
- Maintenance burden
- Potential bugs from divergence

**Recommendation:**

1. **Consolidate** into single utility function in
   `src/dsa110_contimg/simulation/`
2. **Standardize** parameter names and defaults
3. **Import** from central location in all test/script files

**Priority:** LOW - Technical debt, not blocking

---

## 2. Validation and Testing Gaps

### 2.1 Limited Validation Coverage

**Current State:**

- ✅ Validation script exists:
  `src/dsa110_contimg/simulation/validate_synthetic.py`
- ✅ Unit tests exist: `tests/unit/simulation/test_validate_synthetic.py`
- ❌ **Validation not run automatically** after generation
- ❌ **No validation in CI/CD** for generated synthetic data

**Missing Validations:**

1. **UVH5 files:**
   - ✅ Basic structure checks (Nants, Nfreqs, Npols)
   - ✅ Integration time checks
   - ❌ **No flux verification** (check that visibilities match requested flux)
   - ❌ **No UVW consistency** checks (verify phase center matches)
   - ❌ **No frequency ordering** validation

2. **FITS Images:**
   - ✅ WCS header validation (implicit via astropy)
   - ❌ **No source recovery validation** (verify sources are detectable)
   - ❌ **No flux accuracy** checks
   - ❌ **No noise level** verification

**Recommendation:**

1. Add validation step to generation scripts
2. Add flux verification for UVH5 (compare requested vs actual visibility
   amplitude)
3. Add source recovery test for FITS (run forced photometry on generated
   sources)
4. Integrate validation into CI/CD pipeline

**Priority:** MEDIUM - Quality assurance

---

### 2.2 Test Coverage Gaps

**Current Test Coverage:**

- ✅ Unit tests for validation functions
- ✅ Integration test for forced photometry with synthetic data
- ✅ End-to-end pipeline test uses synthetic UVH5
- ❌ **No tests for template-free generation** (doesn't exist yet)
- ❌ **No tests for provenance marking**
- ❌ **No tests for database tagging**
- ❌ **No performance benchmarks** for generation speed

**Recommendation:** Add tests for:

1. Template-free generation (once implemented)
2. Automatic provenance marking
3. Database tagging consistency
4. Generation performance (time/memory)

**Priority:** LOW - Nice to have

---

## 3. Documentation Issues

### 3.1 Misleading Claims

**Issue:** Documentation claims capabilities that don't exist:

1. **`docs/SYNTHETIC_DATA_GENERATION.md`** (line 26):
   - Claims: "Configurable duration, frequency coverage, and source flux"
   - Reality: ✅ True, but **requires template file** (not mentioned in
     capabilities list)

2. **`docs/tutorials/simulation-tutorial.md`**:
   - Shows usage examples but doesn't emphasize template requirement upfront
   - Template dependency mentioned in "Known Limitations" but should be in
     "Requirements"

**Recommendation:**

1. Add **"Requirements"** section to all synthetic data docs
2. List template dependency prominently
3. Provide instructions for obtaining template or generating without it

**Priority:** LOW - Documentation clarity

---

### 3.2 Incomplete Limitations Documentation

**Current Limitations Listed:**

- ✅ Point sources only
- ✅ No RFI
- ✅ Simplified noise model
- ❌ **Missing:** Template dependency
- ❌ **Missing:** No validation of generated data
- ❌ **Missing:** Limited to single source at phase center
- ❌ **Missing:** No support for extended sources in UVH5

**Recommendation:** Expand limitations section with all known constraints.

**Priority:** LOW - Documentation completeness

---

## 4. Functional Limitations

### 4.1 UVH5 Generation Limitations

**Current Capabilities:**

- ✅ Multi-subband support (4-16 subbands)
- ✅ Realistic antenna positions (ITRF coordinates)
- ✅ Proper UVW calculation (fringestopping)
- ✅ Configurable flux, duration, frequency

**Limitations:**

1. **Single point source only** at phase center
2. **No noise** - visibilities are deterministic
3. **No RFI** simulation
4. **Perfect calibration** - no gain/phase errors
5. **Static sky** - flux doesn't vary with time
6. **Template dependency** (critical)

**Impact:**

- Cannot test noise-limited scenarios
- Cannot test RFI mitigation
- Cannot test calibration robustness
- Cannot test time-variable sources

**Recommendation:** Prioritize enhancements based on testing needs:

1. **High priority:** Template-free generation
2. **Medium priority:** Thermal noise simulation
3. **Low priority:** RFI, calibration errors, time variability

**Priority:** MEDIUM - Feature completeness

---

### 4.2 FITS Image Generation Limitations

**Current Capabilities:**

- ✅ Valid WCS headers
- ✅ Gaussian point sources
- ✅ Configurable noise
- ✅ Database integration

**Limitations:**

1. **2D images only** (no frequency/Stokes axes)
2. **Point sources only** (no extended sources)
3. **Gaussian noise only** (no realistic calibration artifacts)
4. **No primary beam** simulation (PB image is separate)
5. **Random source positions** (not configurable per-source)

**Impact:**

- Cannot test multi-frequency imaging
- Cannot test extended source recovery
- Cannot test primary beam correction accuracy
- Cannot test specific source configurations

**Recommendation:** For current use case (SkyView testing), limitations are
acceptable.  
For photometry validation, consider adding:

- Configurable source positions (not just random)
- Extended source models (Gaussian, disk)

**Priority:** LOW - Current limitations acceptable for stated purpose

---

## 5. Data Provenance Verification

### 5.1 Verification Function Exists But Underused

**Location:** `src/dsa110_contimg/qa/html_reports.py` (lines 506-564)

**Current Implementation:**

```python
def _verify_real_observation(image_path: str) -> Tuple[bool, List[str]]:
    # Checks:
    # 1. File location (test directories)
    # 2. Filename patterns
    # 3. FITS header (DATE-OBS, TELESCOP, OBJECT)
```

**Issues:**

1. **Only used in HTML reports** - not in database queries
2. **Not called automatically** - manual verification required
3. **FITS-only** - no verification for UVH5 or MS files

**Recommendation:**

1. **Integrate into database queries:**
   - Add `is_synthetic` column to `images` table (or use `data_tags`)
   - Auto-populate during insertion
   - Filter synthetic data in production queries

2. **Extend to UVH5:**
   - Check history field for "Synthetic" keyword
   - Check extra_keywords for synthetic flag

3. **Add to validation pipeline:**
   - Verify provenance before processing
   - Warn if synthetic data used in production workflows

**Priority:** MEDIUM - Data integrity

---

### 5.2 Database Tagging Inconsistency

**Current State:**

- ✅ Some synthetic tiles tagged (see `docs/dev/SYNTHETIC_TILES_FLAGGED.md`)
- ❌ Tagging done manually, not automatically
- ❌ No tagging for UVH5 or MS files
- ❌ No standard query to filter synthetic data

**Evidence:**

```sql
-- Manual tagging query (from SYNTHETIC_TILES_FLAGGED.md)
SELECT i.path, i.type, i.created_at
FROM images i
JOIN data_tags dt ON dt.data_id = CAST(i.id AS TEXT)
WHERE dt.tag = 'synthetic' AND i.pbcor = 1
```

**Recommendation:**

1. **Automatic tagging:**
   - Tag all synthetic data at creation time
   - Add `data_tags` entry with `tag = 'synthetic'`

2. **Standard query:**
   - Create view: `real_images` (excludes synthetic)
   - Use in production queries

3. **Extend to all data types:**
   - Tag synthetic UVH5 files (track in separate table or file registry)
   - Tag synthetic MS files

**Priority:** MEDIUM - Data management

---

## 6. Integration and Usage Patterns

### 6.1 Good Integration Points

**Strengths:**

1. ✅ **End-to-end testing:** `test_pipeline_end_to_end.sh` uses synthetic UVH5
2. ✅ **Photometry validation:** `test_forced_photometry_simulation.py` uses
   synthetic FITS
3. ✅ **Dashboard testing:** `create_synthetic_images.py` populates database
4. ✅ **Quick smoke tests:** `create_minimal_test_ms()` generates on-the-fly

**Well-Designed:**

- Synthetic data generation is **modular** and **reusable**
- Multiple entry points for different use cases
- Good separation between generation and validation

---

### 6.2 Usage Pattern Issues

**Issues:**

1. **No cleanup strategy:**
   - Synthetic data accumulates in `/data/dsa110-contimg/state/synth/`
   - No automatic cleanup after tests
   - Risk of disk space issues

2. **No versioning:**
   - Generated synthetic data has no version metadata
   - Cannot track which generator version created data
   - Difficult to reproduce results

3. **No sharing mechanism:**
   - Each test generates its own synthetic data
   - No shared synthetic data repository
   - Wastes time regenerating same data

**Recommendation:**

1. **Cleanup policy:**
   - Add `--cleanup` flag to generation scripts
   - Auto-cleanup in test fixtures
   - Document retention policy

2. **Versioning:**
   - Add generator version to metadata
   - Include git commit hash in synthetic data
   - Document in FITS history or UVH5 extra_keywords

3. **Shared repository:**
   - Create `/data/dsa110-contimg/data-samples/synthetic/` directory
   - Pre-generate common test datasets
   - Document how to use shared data

**Priority:** LOW - Operational efficiency

---

## 7. Recommendations Summary

### Critical (Must Fix)

1. **Template Dependency (1.1)**
   - Implement template-free generation mode
   - Priority: HIGH
   - Effort: Medium (2-3 days)

2. **Automatic Provenance Marking (1.2)**
   - Add automatic tagging to all generation scripts
   - Standardize FITS headers
   - Priority: MEDIUM
   - Effort: Low (1 day)

### Important (Should Fix)

3. **Validation Integration (2.1)**
   - Add validation step to generation scripts
   - Integrate into CI/CD
   - Priority: MEDIUM
   - Effort: Medium (2 days)

4. **Database Tagging Consistency (5.2)**
   - Automatic tagging at creation
   - Standard query patterns
   - Priority: MEDIUM
   - Effort: Low (1 day)

### Nice to Have (Could Fix)

5. **Code Consolidation (1.3)**
   - Merge duplicate `create_synthetic_fits` implementations
   - Priority: LOW
   - Effort: Low (0.5 days)

6. **Documentation Updates (3.1, 3.2)**
   - Add requirements sections
   - Expand limitations
   - Priority: LOW
   - Effort: Low (0.5 days)

7. **Usage Pattern Improvements (6.2)**
   - Cleanup policies
   - Versioning
   - Shared repository
   - Priority: LOW
   - Effort: Medium (2 days)

---

## 8. Positive Aspects

**Well-Implemented:**

1. ✅ **Modular design** - Separate generation, validation, and usage
2. ✅ **Good documentation** - Comprehensive usage examples
3. ✅ **Validation framework** - Exists and is extensible
4. ✅ **Integration** - Works well with pipeline and dashboard
5. ✅ **Flexibility** - Configurable parameters for different scenarios

**Best Practices:**

- Uses proper WCS headers in FITS
- Realistic antenna positions from ITRF
- Proper UVW calculation with fringestopping
- Database integration for easy access

---

## 9. Conclusion

**Overall Assessment:** The synthetic data generation capabilities are
**functional and useful** but have **critical gaps** that limit usability and
create data integrity risks.

**Key Strengths:**

- Multiple generation modes for different use cases
- Good integration with pipeline and dashboard
- Validation framework exists

**Key Weaknesses:**

- Template dependency blocks new users
- Inconsistent provenance marking
- Limited validation coverage
- Code duplication

**Recommendation:** Address critical issues (template dependency, provenance
marking) before expanding capabilities. The foundation is solid but needs these
fixes to be production-ready.

---

**Review Completed:** 2025-01-XX
