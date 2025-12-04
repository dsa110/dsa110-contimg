# Calibration Tables Migration: Complete

## Overview

**Status**: ✅ COMPLETED (December 2024)

The codebase has been fully migrated to use `caltables` as the canonical table name.
The legacy `calibration_tables` table and sync triggers have been removed.

## Changes Made

### Database Schema

- Removed `calibration_tables` table from `schema.sql`
- Removed sync triggers (`trg_calibration_tables_ai`, `trg_calibration_tables_au`, `trg_calibration_tables_ad`)
- All code now uses `caltables` directly

### Pipeline Context Keys

- Changed `context.outputs["calibration_tables"]` to `context.outputs["caltables"]`
- Updated in: `stages_impl.py`, `absurd/adapter.py`

### Function Renames

- `_register_calibration_tables()` to `_register_caltables()` (streaming_converter.py)
- `compare_calibration_tables()` to `compare_caltables()` (diagnostics.py)

### Parameter Renames

- `calibration_tables` to `caltables` in `save_group_definition()` (path_utils.py)

### Migration Files

- Updated `0003_add_cascade_delete.py` FK references to use `caltables`

### Tests

- Updated all test files to use `caltables`
- Removed `calibration_tables` from expected tables list

## Note

The function `_ensure_calibration_tables()` in `calibration/jobs.py` was NOT renamed
because it creates tracking tables (`calibration_solves`, `calibration_applications`),
not the `caltables` registry table. The name refers to ensuring tables for calibration
tracking exist, not the registry table itself.
