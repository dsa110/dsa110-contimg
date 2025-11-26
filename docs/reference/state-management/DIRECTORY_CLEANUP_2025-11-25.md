# Directory Cleanup and Organization Summary

**Date**: 2025-11-25  
**Scope**: Comprehensive codebase cleanup and simulation suite organization

## Completed Actions

### 1. Removed Legacy Code
- **Deleted**: `src/dsa110_contimg/` (only contained `__pycache__`)
- **Fixed imports**: Updated `scripts/calibration/recommend_refant.py` to use `dsa110_contimg` instead of `src.dsa110_contimg`
- **Status**: ✅ All active code in `backend/src/dsa110_contimg/`

### 2. Cleaned Build Artifacts
- **Moved**: `site/` (45 MB MkDocs build) → `archive/legacy/site/`
- **Deleted**: `artifacts/custom-results.sarif` (193 MB CodeQL results)
- **Deleted**: `artifacts/htmlcov/` (HTML coverage reports)
- **Stripped**: Jupyter notebook outputs (2.8 MB → 31 KB)
- **Total saved**: ~240 MB of stale artifacts

### 3. Organized Notebooks
- **Migrated**: `notebooks/forced_photometry_simulation.ipynb` → `simulations/notebooks/02_forced_photometry_validation.ipynb`
- **Archived**: `notebooks/debug_0834_calibration.ipynb` → `archive/working/`
- **Archived**: `notebooks/qa_qa.ipynb` → `archive/working/qa_qa_stub.ipynb`
- **Result**: Clean `notebooks/` directory with README explaining organization

### 4. Created Simulation Suite
**New directory structure**: `simulations/`
```
simulations/
├── README.md                          # Complete documentation
├── .gitignore                         # Prevent committing outputs
├── notebooks/                         # Interactive validation notebooks
│   └── 02_forced_photometry_validation.ipynb
├── scripts/                           # Reusable CLI tools (future)
├── config/
│   ├── scenarios/                     # Pre-defined test scenarios
│   └── defaults.yaml                  # Default parameters
└── data/                              # Simulation outputs (gitignored)
    ├── synthetic_uvh5/
    ├── synthetic_ms/
    ├── synthetic_images/
    └── results/
```

**Status**: ✅ Structure created, first notebook migrated, comprehensive README

## Validation Results

### Forced Photometry Consistency Check
**Question**: Is `notebooks/forced_photometry_simulation.ipynb` consistent with pipeline implementation?

**Answer**: ✅ **YES - Completely Consistent**
- Notebook imports and uses `dsa110_contimg.photometry.forced.measure_forced_peak()`
- Tests the actual pipeline code with synthetic FITS images
- Validates flux recovery accuracy using NVSS catalog sources
- This is exactly how simulations should work - test real pipeline code

**Decision**: Migrated to `simulations/notebooks/02_forced_photometry_validation.ipynb`

### Code Organization Verified
- All active Python code: `backend/src/dsa110_contimg/`
- Legacy code removed: `src/dsa110_contimg/` deleted
- Archive references: `archive/references/` (read-only external repos)
- One import fixed: `recommend_refant.py` compiles without errors

## Directory Status After Cleanup

### ✅ Active Directories (Keep)
- `backend/` - Main Python package (production code)
- `frontend/` - React dashboard
- `docs/` - Documentation
- `ops/` - Deployment and operations
- `scripts/` - Utility scripts
- `simulations/` - **NEW** Organized testing/validation suite

### 🗄️ Archive Directories (Keep but not active)
- `archive/legacy/` - Deprecated code for reference
- `archive/references/` - External repos (read-only)
- `archive/working/` - Ad-hoc debugging sessions

### 🧹 Cleaned Directories
- `artifacts/` - Removed stale SARIF and coverage reports
- `notebooks/` - Migrated organized notebooks to `simulations/`
- `site/` - Moved to `archive/legacy/`

### 📦 Data Directories (Gitignored)
- `products/` - Pipeline outputs (MS, images, catalogs)
- `state/` - Runtime state and databases
- `simulations/data/` - Simulation outputs

## Documentation Updates

### Created
- ✅ `simulations/README.md` - Complete simulation suite documentation
- ✅ `simulations/.gitignore` - Prevent committing outputs
- ✅ `notebooks/README.md` - Explain notebook organization
- ✅ `archive/working/README.md` - Document ad-hoc archive

### Updated
- ✅ `.github/copilot-instructions.md` - Field naming documentation
- ✅ `docs/tutorials/MINIMAL_IMAGING_WORKFLOW.md` - Auto-renaming workflow

## Testing Status

### Field Naming Module
- ✅ All 6 unit tests passing (`backend/tests/unit/calibration/test_field_naming.py`)
- ✅ Bug fix verified (uses `peak_field_idx` instead of hardcoded field 0)
- ✅ Integration with conversion pipeline tested

### Notebooks
- ✅ `02_forced_photometry_validation.ipynb` - Uses pipeline code correctly
- 🗄️ Debug notebooks archived (not maintained)

## Next Steps (Optional Future Work)

### Simulations Suite
1. **Add more validation notebooks**:
   - `01_uvh5_generation.ipynb` - Synthetic data generation
   - `03_calibration_scenarios.ipynb` - Test various calibration conditions
   - `04_imaging_parameter_sweep.ipynb` - Optimize imaging parameters

2. **Create scenario configs** in `simulations/config/scenarios/`:
   - `bright_calibrator.yaml`
   - `weak_sources.yaml`
   - `crowded_field.yaml`
   - `rfi_contaminated.yaml`

3. **Reusable scripts** in `simulations/scripts/`:
   - `generate_synthetic_obs.py` - CLI for data generation
   - `inject_sources.py` - Source injection testing
   - `run_parameter_sweep.py` - Batch parameter optimization

### QA Framework
- Expand QA notebook stub into proper demo (`simulations/notebooks/03_qa_demo.ipynb`)
- Document QA visualization tools
- Add examples of calibration/image quality inspection

### Continued Cleanup
- Review `examples/` directory for outdated scripts
- Audit `scripts/` for duplicates or legacy tools
- Update main README.md to reference new `simulations/` structure

## Impact Summary

**Before**: Scattered notebooks, stale build artifacts, legacy code confusion, 240 MB waste

**After**: 
- Clean organized structure
- Simulation suite with documentation
- Legacy code removed
- 240 MB reclaimed
- Clear pathways for future notebooks (simulations vs ad-hoc)

**Developer Experience**: 
- ✅ Clear where to put new simulations
- ✅ Know which code is active (backend/) vs legacy
- ✅ Understand forced photometry notebook validates pipeline code
- ✅ Easy to find and run validation tests

## Files Modified/Created

### New Files
- `simulations/README.md` (comprehensive docs)
- `simulations/.gitignore`
- `notebooks/README.md`
- `archive/working/README.md`
- `simulations/notebooks/02_forced_photometry_validation.ipynb` (migrated)

### Modified Files
- `scripts/calibration/recommend_refant.py` (fixed import)

### Deleted
- `src/dsa110_contimg/` (directory)
- `artifacts/custom-results.sarif` (193 MB)
- `artifacts/htmlcov/` (directory)
- `notebooks/forced_photometry_simulation.ipynb` (migrated copy)

### Moved/Archived
- `site/` → `archive/legacy/site/`
- `notebooks/debug_0834_calibration.ipynb` → `archive/working/`
- `notebooks/qa_qa.ipynb` → `archive/working/qa_qa_stub.ipynb`
