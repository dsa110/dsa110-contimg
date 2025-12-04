# Calibration Tables Migration: `calibration_tables` → `caltables`

## Overview

This document records the migration from the legacy `calibration_tables` database
table to the canonical `caltables` table name.

## Background

The codebase historically had two table names:

- **`caltables`** - The canonical/production table name
- **`calibration_tables`** - Legacy table name kept for backward compatibility

A trigger-based sync mechanism was in place to keep both tables in sync:

- `trg_calibration_tables_ai` - After INSERT
- `trg_calibration_tables_au` - After UPDATE
- `trg_calibration_tables_ad` - After DELETE

## Migration Status

**Date**: December 2024

### Production Code (Already Using `caltables`)

- `src/dsa110_contimg/database/unified.py` - ✅ Uses `caltables`
- `src/dsa110_contimg/database/provenance.py` - ✅ Uses `caltables`
- `src/dsa110_contimg/monitoring/tasks.py` - ✅ Uses `caltables`

### Test Code (Migrated to `caltables`)

- `tests/unit/test_unified_database.py` - ✅ Migrated
- `tests/contract/test_database_contracts.py` - ✅ Migrated
- `tests/contract/test_calibration_contracts.py` - ✅ Migrated

### Archived Files

The following files were moved to `/data/dsa110-contimg/.local/archive/legacy/migrations/`:

- `0002_add_calibration_fk.py` - Historical migration referencing legacy table

## Schema Changes

The `calibration_tables` table and its triggers remain in `schema.sql` for:

1. Backward compatibility with any external tools
2. Historical data access
3. Graceful migration period

These will be removed in a future cleanup phase once all external dependencies are verified.

## Verification

All 1700+ tests pass after migration, confirming no regressions.
