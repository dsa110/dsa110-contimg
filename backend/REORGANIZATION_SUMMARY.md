# Backend Directory Reorganization (November 2025)

**Date**: November 26, 2025  
**Purpose**: Simplify directory structure for dashboard frontend and pipeline
development

## Summary

This document records the directory reorganization performed to consolidate
duplicated tests, scripts, documentation, and state directories into a cleaner,
standard Python project layout.

### 1. Tests Consolidated

**Before**: Tests were scattered across 3 locations:

- `tests/` (root)
- `src/dsa110_contimg/tests/`
- `src/tests/`

**After**: All tests now live in `tests/` at the project root:

- `tests/unit/` - Unit tests (including new `photometry/`, `catalog/`,
  `mosaic/`)
- `tests/integration/` - Integration tests (including new `transients/`,
  `absurd/`, `catalog/`)
- `tests/smoke/` - Smoke tests
- `tests/e2e/` - End-to-end tests
- `tests/fixtures/` - Test fixtures and mock data

### 2. Scripts Consolidated

**Before**: Scripts were in two locations:

- `src/scripts/` (25+ operational scripts)
- `src/dsa110_contimg/scripts/` (just `absurd/` subdirectory)

**After**: All scripts consolidated under the package:

- `src/dsa110_contimg/scripts/ops/` - Operational scripts (moved from
  `src/scripts/`)
- `src/dsa110_contimg/scripts/absurd/` - Absurd-related scripts

### 3. Documentation Consolidated

**Before**: Documentation nested deep in package:

- `src/dsa110_contimg/docs/` (architecture, concepts, operations, etc.)
- `src/examples/` (example scripts)

**After**: Top-level `docs/` directory:

- `docs/architecture/` - Architecture documentation
- `docs/concepts/` - Concept deep-dives
- `docs/operations/` - Operational guides
- `docs/deployment/` - Deployment documentation
- `docs/dev-notes/` - Developer scratch notes and investigations
- `docs/examples/` - Example scripts and notebooks
- `docs/reports/` - Historical reports
- `docs/runbooks/` - Operational runbooks
- `docs/absurd/` - Absurd integration docs

### 4. State Directories Consolidated

**Before**: Three `state/` directories with duplicate `products.sqlite3`:

- `state/` (root, empty files)
- `src/state/`
- `src/dsa110_contimg/state/`

**After**: Single `state/` at project root with actual data.

### 5. Removed Duplicates

- Removed duplicate `pytest.ini` from `src/dsa110_contimg/`
- Removed empty `notebooks/` directory
- Moved `sandbox/` contents to `tests/fixtures/`

### 6. New Utilities

- Added `scripts/clean_caches.sh` - Cleans `__pycache__`, `.mypy_cache`, etc.

## New Directory Structure

```
backend/
├── config/                 # Configuration files (YAML, Lua)
├── docs/                   # All documentation (NEW - consolidated)
│   ├── architecture/
│   ├── concepts/
│   ├── deployment/
│   ├── dev-notes/
│   ├── examples/           # Example scripts moved here
│   ├── operations/
│   ├── reports/
│   └── runbooks/
├── scripts/                # Top-level utility scripts
│   └── clean_caches.sh     # NEW - cache cleanup utility
├── src/
│   └── dsa110_contimg/     # Main Python package
│       ├── api/
│       ├── calibration/
│       ├── conversion/
│       ├── database/
│       ├── imaging/
│       ├── pipeline/
│       ├── scripts/        # Package scripts (consolidated)
│       │   ├── absurd/
│       │   └── ops/        # Operational scripts moved here
│       └── utils/
├── state/                  # SQLite databases (consolidated)
└── tests/                  # All tests (consolidated)
    ├── calibration/
    ├── conversion/
    ├── database/
    ├── e2e/
    ├── fixtures/           # Test fixtures (includes former sandbox/)
    ├── integration/
    │   ├── absurd/
    │   ├── catalog/
    │   └── transients/
    ├── performance/
    ├── science/
    ├── scripts/
    ├── smoke/
    ├── unit/
    │   ├── catalog/
    │   ├── mosaic/
    │   └── photometry/
    ├── utils/
    └── validation/
```

## Files Updated

- `src/README.md` - Updated with new structure references
- `src/dsa110_contimg/README.md` - Updated with correct doc paths
- `docs/README.md` - Updated with new layout
- `src/MANAGING_LARGE_REFACTORING.md` - Updated script paths
- `src/dsa110_contimg/scripts/ops/REFACTORING_TOOLS.md` - Fixed stale doc paths
- `tests/README.md` - Updated with current directory structure
- `tests/smoke/test_priority1_quick.py` - Fixed path references and pytest
  warnings

## Cleanup Commands

To clean generated caches:

```bash
./scripts/clean_caches.sh          # Dry run
./scripts/clean_caches.sh --force  # Actually delete
```
