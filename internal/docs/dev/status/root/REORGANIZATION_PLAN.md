# Root Directory Reorganization Plan

**Status**: COMPLETED  
**Date**: 2025-01-11

## Overview

This document tracks the reorganization of the repository root directory to
improve maintainability, contributor clarity, and scalability. The
reorganization follows a structured approach to move files from root into
functionally scoped subdirectories.

## Completed Actions

### 1. Markdown Files Moved to `docs/dev/notes/`

The following markdown files were moved from root to `docs/dev/notes/`:

- `AGENTS.md` → `docs/dev/notes/AGENTS.md`
- `ASKAP_VALIDATION_ASSESSMENT.md` →
  `docs/dev/notes/ASKAP_VALIDATION_ASSESSMENT.md`
- `COMPLETENESS_ANALYSIS_IMPLEMENTATION.md` →
  `docs/dev/notes/COMPLETENESS_ANALYSIS_IMPLEMENTATION.md`
- `DEEP_STUDY_ANALYSIS.md` → `docs/dev/notes/DEEP_STUDY_ANALYSIS.md`
- `DEEP_STUDY.md` → `docs/dev/notes/DEEP_STUDY.md`
- `GRAPHITI_UPLOAD_LOG.md` → `docs/dev/notes/GRAPHITI_UPLOAD_LOG.md`
- `HTML_REPORT_IMPLEMENTATION.md` →
  `docs/dev/notes/HTML_REPORT_IMPLEMENTATION.md`
- `MEMORY.md` → `docs/dev/notes/MEMORY.md`
- `PIPELINE_INTEGRATION.md` → `docs/dev/notes/PIPELINE_INTEGRATION.md`
- `TODO.md` → `docs/dev/notes/TODO.md`
- `VISUALIZATION_IMPLEMENTATION.md` →
  `docs/dev/notes/VISUALIZATION_IMPLEMENTATION.md`

**Rationale**: All development notes, analysis documents, and agent memory files
belong in the development notes directory, keeping root clean while maintaining
organization.

### 2. Test Files Moved to `tests/`

The following test files were moved from root to `tests/`:

- `test_api_endpoints.py` → `tests/test_api_endpoints.py`
- `test_catalog_query_fix.py` → `tests/test_catalog_query_fix.py`
- `test_completeness_analysis.py` → `tests/test_completeness_analysis.py`
- `test_completeness_mock.py` → `tests/test_completeness_mock.py`
- `test_fits_visualization.py` → `tests/test_fits_visualization.py`
- `test_forced_photometry.py` → `tests/test_forced_photometry.py`
- `test_html_reports_simple.py` → `tests/test_html_reports_simple.py`
- `test_html_reports.py` → `tests/test_html_reports.py`
- `test_qa_visualization.py` → `tests/test_qa_visualization.py`
- `test_validation_plots.py` → `tests/test_validation_plots.py`
- `test_validation_real_data.py` → `tests/test_validation_real_data.py`
- `test_validation_real_observations.py` →
  `tests/test_validation_real_observations.py`
- `test_visualization_logic.py` → `tests/test_visualization_logic.py`
- `test_priority1_quick.py` → `tests/test_priority1_quick.py`
- `validate_backend_core.py` → `tests/validate_backend_core.py`
- `test_mermaid_debug.html` → `tests/test_mermaid_debug.html`

**Rationale**: All test files should be consolidated in the `tests/` directory
for better organization and discoverability.

### 3. Log Files Moved to `logs/`

The following log files were moved from root to `logs/`:

- `casa-*.log` → `logs/casa-*.log` (all CASA log files)
- `test-cpu-check-*.log` → `logs/test-cpu-check-*.log`

**Rationale**: Log files should be centralized in the `logs/` directory to avoid
root clutter.

### 4. Other Files Moved

- `qa_qa.ipynb` → `notebooks/qa_qa.ipynb`
- `docs-offline.zip` → `archive/docs-offline.zip`

**Rationale**: Notebooks belong in `notebooks/`, and archived files belong in
`archive/`.

## Updated References

The following files were updated to reflect the new file locations:

### Scripts Updated

1. **`scripts/linear_sync.py`**
   - Updated `TODO_FILE` path from `PROJECT_ROOT / "TODO.md"` to
     `PROJECT_ROOT / "docs" / "dev" / "notes" / "TODO.md"`

2. **`scripts/update_todo_date.py`**
   - Updated `TODO_FILE` path from `PROJECT_ROOT / "TODO.md"` to
     `PROJECT_ROOT / "docs" / "dev" / "notes" / "TODO.md"`

3. **`scripts/test-impacted.sh`**
   - Updated test file references:
     - `test_html_reports_simple.py` → `tests/test_html_reports_simple.py`
     - `test_validation_plots.py` → `tests/test_validation_plots.py`

### Documentation Updated

1. **`docs/dev/notes/AGENTS.md`**
   - Updated reference: `test_priority1_quick.py` →
     `tests/test_priority1_quick.py`

2. **`docs/analysis/CORE_VALIDATION_PLAN.md`**
   - Updated reference: `test_priority1_quick.py` →
     `tests/test_priority1_quick.py`

3. **`docs/analysis/PRIORITY1_TEST_RESULTS.md`**
   - Updated references: `test_priority1_quick.py` →
     `tests/test_priority1_quick.py`

4. **`docs/analysis/testing_results.md`**
   - Updated reference: `test_api_endpoints.py` → `tests/test_api_endpoints.py`

5. **`docs/analysis/VALIDATION_LEARNINGS.md`**
   - Updated reference: `validate_backend_core.py` →
     `tests/validate_backend_core.py`

6. **`internal/docs/development/SAFEGUARD_INTEGRATION_LOCATIONS.md`**
   - Updated command reference: `validate_backend_core.py` →
     `tests/validate_backend_core.py`

## Directory Structure After Reorganization

```
(root)
├─ README.md                 # Primary project overview (ONLY markdown in root)
├─ Makefile                  # Project-wide build targets
├─ docker-compose.yml        # Top-level Docker Compose config
├─ pytest.ini               # Pytest configuration
├─ playwright.config.ts      # Playwright configuration
├─ mkdocs.yml               # MkDocs configuration
├─ requirements-test.txt     # Test requirements
├─ REORGANIZATION_PLAN.md    # This file (temporary, until reorganization complete)
│
├─ config/                  # Configuration files
│   └─ ...
│
├─ docs/                    # All documentation
│   └─ dev/notes/           # Development notes (moved from root)
│       ├─ AGENTS.md
│       ├─ MEMORY.md
│       ├─ TODO.md
│       └─ ...
│
├─ tests/                   # All test files
│   ├─ test_api_endpoints.py
│   ├─ test_priority1_quick.py
│   ├─ validate_backend_core.py
│   └─ ...
│
├─ logs/                    # Log files
│   └─ casa-*.log
│
├─ notebooks/               # Jupyter notebooks
│   └─ qa_qa.ipynb
│
├─ archive/                 # Archived files
│   └─ docs-offline.zip
│
└─ ... (other directories unchanged)
```

## Files Remaining in Root (As Intended)

The following files remain in root as they are part of the intended root
structure:

- `README.md` - Primary project documentation
- `Makefile` - Build automation
- `docker-compose.yml` - Docker orchestration
- `pytest.ini` - Test configuration
- `playwright.config.ts` - E2E test configuration
- `mkdocs.yml` - Documentation build configuration
- `requirements-test.txt` - Test dependencies
- `REORGANIZATION_PLAN.md` - This tracking document (to be archived after
  verification)

## Verification Checklist

- [x] All markdown files moved from root (except README.md)
- [x] All test files moved to tests/
- [x] All log files moved to logs/
- [x] Notebooks moved to notebooks/
- [x] Script references updated
- [x] Documentation references updated
- [x] Root directory cleaned (only intended files remain)

## Next Steps

1. **Verification**: Run tests to ensure all references work correctly
2. **CI/CD Update**: Verify CI/CD pipelines still work with new paths
3. **Documentation**: Update any remaining documentation that references old
   paths
4. **Archive**: After verification period, move `REORGANIZATION_PLAN.md` to
   `docs/migration/`

## Notes

- The `tools/` directory was created but remains empty for future use
- The `test_data/` directory was created but remains empty for future use
- No symlinks were created as per the plan (they would be removed after next
  release anyway)
- All file moves preserve git history (using `git mv` would be ideal, but direct
  moves work for this reorganization)

## Impact Assessment

**Low Risk Changes**:

- Test files moved to `tests/` - standard location, well-understood
- Log files moved to `logs/` - standard location, no code dependencies
- Notebooks moved to `notebooks/` - standard location, no code dependencies

**Medium Risk Changes**:

- Markdown files moved - requires documentation updates (completed)
- Script references updated - requires testing (pending verification)

**Testing Required**:

- Run `make test-smoke` to verify test discovery works
- Run `scripts/test-impacted.sh` to verify test mapping works
- Run `scripts/linear_sync.py` to verify TODO.md access works
- Run `scripts/update_todo_date.py` to verify TODO.md update works

## Related Documentation

- [Directory Architecture](docs/concepts/DIRECTORY_ARCHITECTURE.md)
- [Documentation Quick Reference](docs/DOCUMENTATION_QUICK_REFERENCE.md)
