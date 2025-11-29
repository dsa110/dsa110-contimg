# Scripts Directory Inventory

**Purpose**: This document catalogs all scripts in `/scripts/` and categorizes
them for consolidation into the main codebase.

**Date**: 2025-01-15  
**Status**: DRAFT - For review and migration planning

---

## Summary Statistics

- **Total scripts**: 43 files
  - Python: 33
  - Bash: 10

## Categories

### 1. REDUNDANT / ARCHIVE

Scripts that duplicate existing CLI functionality or are superseded by the
unified orchestrator CLI.

#### Conversion/Transit Scripts (Archive)

- **`generate_calibrator_ms.py`** :warning: **REDUNDANT**
  - Purpose: Finds most recent calibrator transit and generates MS
  - **Superseded by**: `hdf5_orchestrator` CLI with `--calibrator` flag
  - Action: Archive to `archive/scripts/`

- **`generate_transit_hour_ms.py`** :warning: **REDUNDANT**
  - Purpose: Generates multiple MS files spanning 1 hour around transit
  - **Superseded by**: `hdf5_orchestrator` CLI with `--calibrator` and time
    windows
  - Action: Archive OR migrate core logic to orchestrator if useful as
    `--multi-group` flag

- **`list_calibrator_transits.py`** :check: **KEEP (but migrate to CLI)**
  - Purpose: Lists all available transits with data
  - **Action**: Migrate to `dsa110_contimg.calibration.cli` as `list-transits`
    subcommand
  - Reason: Useful utility, should be part of calibration/transit CLI

- **`find_daily_transit_groups.py`** :warning: **REDUNDANT**
  - Purpose: Finds transit groups for a specific day
  - **Superseded by**: `hdf5_orchestrator` with `--calibrator --transit-date`
  - Action: Archive

- **`find_latest_transit_group.py`** :warning: **REDUNDANT**
  - Purpose: Finds latest transit group
  - **Superseded by**: `hdf5_orchestrator` with `--calibrator` (uses most recent
    by default)
  - Action: Archive

- **`run_conversion.sh`** :check: **KEEP (Operational)**
  - Purpose: Bash wrapper for orchestrator with staging/scratch setup
  - **Action**: Keep as operational script (not part of main codebase)
  - Reason: System-specific staging logic, useful for ops team

#### Bash Wrappers (Archive or Keep)

- **`image_ms.sh`** :warning: **REDUNDANT**
  - Purpose: Bash wrapper for imaging CLI
  - **Superseded by**: `dsa110_contimg.imaging.cli`
  - Action: Archive OR document as convenience wrapper

- **`calibrate_bandpass.sh`** :warning: **REDUNDANT**
  - Purpose: Bash wrapper for calibration
  - **Superseded by**: `dsa110_contimg.calibration.cli`
  - Action: Archive OR document as convenience wrapper

### 2. TEST SCRIPTS (Move to tests/)

These should be moved to `tests/` directory with proper test structure.

- **`test_pipeline_end_to_end.sh`** :check: **MOVE TO tests/**
  - Purpose: Comprehensive end-to-end pipeline test
  - **Action**: Move to `tests/integration/test_pipeline_end_to_end.sh`
  - Note: Already well-structured, just needs relocation

- **`comprehensive_test_suite.py`** :check: **MOVE TO tests/**
  - Purpose: Comprehensive Python test suite for all modules
  - **Action**: Move to `tests/comprehensive_test_suite.py` or break into module
    tests
  - Note: Could be refactored into pytest structure

- **`test_qa_integration.py`** :check: **MOVE TO tests/**
- **`test_qa_modules.py`** :check: **MOVE TO tests/**
- **`test_data_accessibility.py`** :check: **MOVE TO tests/**
- **`test_integration_points.py`** :check: **MOVE TO tests/**
- **`test_photometry_without_db.py`** :check: **MOVE TO tests/**
- **`test_alerting.py`** :check: **MOVE TO tests/**
- **`test_monitor_daemon.py`** :check: **MOVE TO tests/**
- **`test_ingest_vla_catalog.py`** :check: **MOVE TO tests/**
- **`test_catalog_builder.py`** :check: **MOVE TO tests/**
- **`test_graphiti_mcp.py`** :check: **MOVE TO tests/**

### 3. USEFUL - MIGRATE TO CLI

Scripts with valuable functionality that should become CLI commands.

#### QA/Inspection Utilities (Migrate to QA CLI)

- **`check_upstream_delays.py`** :check: **MIGRATE TO CLI**
  - Purpose: Check if instrumental delays are already corrected upstream
  - **Action**: Migrate to `dsa110_contimg.calibration.cli` as `check-delays`
    subcommand
  - Value: Useful diagnostic tool

- **`verify_kcal_delays.py`** :check: **MIGRATE TO CLI**
  - Purpose: Verify K-calibration delay solutions
  - **Action**: Migrate to `dsa110_contimg.calibration.cli` as `verify-delays`
    subcommand
  - Value: Useful QA tool for calibration validation

- **`inspect_kcal_simple.py`** :check: **MIGRATE TO CLI**
  - Purpose: Simple inspection of K-calibration tables
  - **Action**: Migrate to `dsa110_contimg.calibration.cli` as `inspect-delays`
    subcommand
  - Value: Useful diagnostic tool

#### Transit/Pointing Utilities (Migrate to Calibration/Pointing CLI)

- **`crossmatch_transits_pointings.py`** :check: **MIGRATE TO CLI**
  - Purpose: Crossmatch transit times with pointing history
  - **Action**: Migrate to `dsa110_contimg.pointing.cli` (create if needed) or
    `calibration.cli`
  - Value: Useful for validation and analysis

- **`plot_observation_timeline.py`** :check: **MIGRATE TO CLI**
  - Purpose: Plot observation timeline with declination
  - **Action**: Migrate to `dsa110_contimg.pointing.cli` (create if needed) as
    `plot-timeline` command
  - Value: Already established as preferred plotting method (replaced
    `plot_dec_history.py`)

#### Imaging/Export Utilities (Migrate to Imaging CLI)

- **`export_to_fits_and_png.py`** :check: **MIGRATE TO CLI**
  - Purpose: Export images to FITS and PNG formats
  - **Action**: Migrate to `dsa110_contimg.imaging.cli` as `export` subcommand
  - Value: Useful utility, should be part of imaging workflow

- **`make_nvss_mask_crtf.py`** :check: **MIGRATE TO CLI**
  - Purpose: Create NVSS mask in CASA region format
  - **Action**: Migrate to `dsa110_contimg.imaging.cli` as `create-nvss-mask`
    subcommand
  - Value: Useful for source masking

- **`make_nvss_overlay.py`** :check: **MIGRATE TO CLI**
  - Purpose: Create NVSS overlay visualization
  - **Action**: Migrate to `dsa110_contimg.imaging.cli` as `create-nvss-overlay`
    subcommand
  - Value: Useful for visualization

#### Test Data Creation (Keep or Migrate)

- **`create_test_ms.py`** :check: **MIGRATE TO CLI**
  - Purpose: Create smaller test MS from full MS
  - **Action**: Migrate to `dsa110_contimg.conversion.cli` as `create-test-ms`
    subcommand
  - Value: Useful for testing and development
  - Note: Could also stay in `scripts/` if considered operational tool

- **`create_test_catalog.py`** :check: **KEEP OR ARCHIVE**
  - Purpose: Create test catalog for testing
  - **Action**: Determine if still needed; if yes, move to `tests/fixtures/` or
    archive
  - Value: Likely only needed during initial development

### 4. OPERATIONAL / SYSTEM SCRIPTS (Keep)

Scripts for system management, monitoring, and operational tasks. These should
stay in `scripts/` as they're not part of the core pipeline.

#### CASA Log Management

- **`casa_log_daemon.py`** :check: **KEEP**
  - Purpose: Daemon to move CASA log files
  - **Action**: Keep in `scripts/` (operational tool)

- **`move_casa_logs.sh`** :check: **KEEP**
  - Purpose: One-time bulk move of CASA logs
  - **Action**: Keep in `scripts/` (operational tool)

- **`cleanup_casa_logs.sh`** :check: **KEEP**
  - Purpose: Cleanup old CASA logs
  - **Action**: Keep in `scripts/` (operational tool)

- **`setup_casa_log_fallback.sh`** :check: **KEEP**
  - Purpose: Setup log fallback configuration
  - **Action**: Keep in `scripts/` (operational tool)

- **`casa_wrapper.sh`** :check: **KEEP**
  - Purpose: Wrapper for CASA commands
  - **Action**: Keep in `scripts/` (operational tool)

- **`casa-log-daemon.service`** :check: **KEEP**
- **`casa-log-cleanup.service`** :check: **KEEP**
- **`casa-log-cleanup.timer`** :check: **KEEP**
- **`casa-log-mover.service`** :check: **KEEP**
  - Purpose: Systemd service files for CASA log management
  - **Action**: Keep in `scripts/` (operational/deployment files)

#### System Management

- **`manage-services.sh`** :check: **KEEP**
  - Purpose: Manage system services
  - **Action**: Keep in `scripts/` (operational tool)

- **`scratch_sync.sh`** :check: **KEEP**
  - Purpose: Sync scratch directory
  - **Action**: Keep in `scripts/` (operational tool)

### 5. Knowledge Graph Scripts (Keep Separately)

Knowledge graph–specific scripts for graph management. These should stay in
`scripts/` but could be organized into a subdirectory.

- **`graphiti_ingest_docs.py`** :check: **KEEP (Maybe move to scripts/graphiti/)**
- **`graphiti_guardrails_check.py`** :check: **KEEP (Maybe move to
  scripts/graphiti/)**
- **`graphiti_add_components_from_manifests.py`** :check: **KEEP (Maybe move to
  scripts/graphiti/)**
- **`graphiti_import_cursor_memory.py`** :check: **KEEP (Maybe move to
  scripts/graphiti/)**
- **`graphiti_reembed_all.py`** :check: **KEEP (Maybe move to scripts/graphiti/)**
- **`graphiti_reembed_mismatched.py`** :check: **KEEP (Maybe move to
  scripts/graphiti/)**

**Action**: Consider organizing into `scripts/graph/` subdirectory for clarity.

### 6. DOCUMENTATION FILES

- **`README.md`** :check: **KEEP**
  - Purpose: Documents CASA log management and MS utilities
  - **Action**: Update to reflect new structure after migration

- **`TEST_SCRIPT_VERIFICATION.md`** :check: **KEEP**
  - Purpose: Documents test script verification
  - **Action**: Move to `tests/` or `docs/testing/` if relevant

---

## Migration Plan

### Phase 1: Archive Redundant Scripts

1. Move redundant conversion/transit scripts to `archive/scripts/`
2. Update any references to archived scripts in documentation

### Phase 2: Migrate Test Scripts

1. Move all `test_*.py` and `test_*.sh` to `tests/` directory
2. Refactor to use pytest structure where appropriate
3. Update test documentation

### Phase 3: Migrate Utilities to CLI

1. **Calibration CLI enhancements:**
   - Add `check-delays` subcommand (from `check_upstream_delays.py`)
   - Add `verify-delays` subcommand (from `verify_kcal_delays.py`)
   - Add `inspect-delays` subcommand (from `inspect_kcal_simple.py`)
   - Add `list-transits` subcommand (from `list_calibrator_transits.py`)

2. **Imaging CLI enhancements:**
   - Add `export` subcommand (from `export_to_fits_and_png.py`)
   - Add `create-nvss-mask` subcommand (from `make_nvss_mask_crtf.py`)
   - Add `create-nvss-overlay` subcommand (from `make_nvss_overlay.py`)

3. **Pointing CLI (create new):**
   - Create `dsa110_contimg.pointing.cli` module
   - Add `plot-timeline` command (from `plot_observation_timeline.py`)
   - Add `crossmatch-transits` command (from `crossmatch_transits_pointings.py`)

4. **Conversion CLI enhancements:**
   - Add `create-test-ms` subcommand (from `create_test_ms.py`)

### Phase 4: Organize Operational Scripts

1. Keep operational scripts in `scripts/`
2. Consider organizing knowledge graph scripts into `scripts/graph/`
3. Update `scripts/README.md` to reflect new structure

---

## Quick Reference: Script Status

| Script                             | Status       | Action                        |
| ---------------------------------- | ------------ | ----------------------------- |
| `generate_calibrator_ms.py`        | :cross: Redundant | Archive                       |
| `generate_transit_hour_ms.py`      | :cross: Redundant | Archive                       |
| `list_calibrator_transits.py`      | :check: Migrate   | :arrow_right: `calibration.cli`           |
| `find_daily_transit_groups.py`     | :cross: Redundant | Archive                       |
| `find_latest_transit_group.py`     | :cross: Redundant | Archive                       |
| `check_upstream_delays.py`         | :check: Migrate   | :arrow_right: `calibration.cli`           |
| `verify_kcal_delays.py`            | :check: Migrate   | :arrow_right: `calibration.cli`           |
| `inspect_kcal_simple.py`           | :check: Migrate   | :arrow_right: `calibration.cli`           |
| `plot_observation_timeline.py`     | :check: Migrate   | :arrow_right: `pointing.cli`              |
| `crossmatch_transits_pointings.py` | :check: Migrate   | :arrow_right: `pointing.cli`              |
| `export_to_fits_and_png.py`        | :check: Migrate   | :arrow_right: `imaging.cli`               |
| `make_nvss_mask_crtf.py`           | :check: Migrate   | :arrow_right: `imaging.cli`               |
| `make_nvss_overlay.py`             | :check: Migrate   | :arrow_right: `imaging.cli`               |
| `create_test_ms.py`                | :check: Migrate   | :arrow_right: `conversion.cli`            |
| All `test_*.py`                    | :check: Move      | :arrow_right: `tests/`                    |
| `test_pipeline_end_to_end.sh`      | :check: Move      | :arrow_right: `tests/`                    |
| `comprehensive_test_suite.py`      | :check: Move      | :arrow_right: `tests/`                    |
| Knowledge graph scripts            | :check: Keep      | :arrow_right: `scripts/graph/` (organize) |
| CASA log scripts                   | :check: Keep      | Stay in `scripts/`            |
| System management scripts          | :check: Keep      | Stay in `scripts/`            |
