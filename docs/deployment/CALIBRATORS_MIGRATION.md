# Calibrators.sqlite3 Migration - Production Deployment Guide

## Overview

This document describes the migration from storing bandpass calibrators in
`products.sqlite3` to the new dedicated `calibrators.sqlite3` database, along
with the unified catalog query interface and skymodel storage system.

## Architecture Changes

### Before Migration

- Bandpass calibrators stored in `products.sqlite3`
- No unified catalog interface
- No skymodel storage system

### After Migration

- Bandpass calibrators in `calibrators.sqlite3`
- Unified catalog query interface (`catalog_query.py`)
- Skymodel storage system (`skymodel_storage.py`)
- Support for multiple catalogs (VLA, NVSS, FIRST, RACS)

## Prerequisites

1. **Python Environment**: CASA6 Python 3.11.13
2. **Database Access**: Read/write access to `state/` directory
3. **Backup Space**: Sufficient space for database backups

## Deployment Steps

### 1. Pre-Deployment Checklist

- [ ] Verify `products.sqlite3` exists and is accessible
- [ ] Ensure sufficient disk space for backups
- [ ] Review current calibrator registrations
- [ ] Notify team of maintenance window (if needed)

### 2. Run Migration Script

```bash
# Navigate to project root
cd /data/dsa110-contimg

# Run automated deployment script
./scripts/deploy_calibrators_migration.sh
```

Or manually:

```bash
# Dry-run first
python backend/src/dsa110_contimg/database/migrate_calibrators.py \
    --products-db state/products.sqlite3 \
    --calibrators-db state/calibrators.sqlite3 \
    --dry-run

# Actual migration
python backend/src/dsa110_contimg/database/migrate_calibrators.py \
    --products-db state/products.sqlite3 \
    --calibrators-db state/calibrators.sqlite3
```

### 3. Verify Migration

```bash
# Check calibrator counts
python -c "
import sqlite3
conn = sqlite3.connect('state/calibrators.sqlite3')
cursor = conn.execute('SELECT COUNT(*) FROM bandpass_calibrators')
print(f'Calibrators migrated: {cursor.fetchone()[0]}')
conn.close()
"
```

### 4. Run Tests

```bash
# Integration tests
pytest tests/integration/test_calibrators_integration.py -v

# Unit tests
pytest tests/database/test_calibrators_db.py -v
pytest tests/database/test_catalog_query.py -v
pytest tests/database/test_skymodel_storage.py -v
```

### 5. Post-Deployment Verification

1. **Check Pipeline Logs**: Monitor for any errors related to calibrator queries
2. **Test Calibrator Registration**: Register a test calibrator and verify it
   appears
3. **Test Skymodel Creation**: Create a test skymodel and verify storage
4. **Monitor Performance**: Ensure database queries perform well under load

## Rollback Procedure

If issues are detected:

```bash
# Restore from backup
BACKUP_DIR="state/backups/YYYYMMDD_HHMMSS"  # Use actual backup directory
cp "$BACKUP_DIR/products.sqlite3.backup" state/products.sqlite3
cp "$BACKUP_DIR/calibrators.sqlite3.backup" state/calibrators.sqlite3

# Revert code changes (if needed)
git checkout main  # Or specific commit before migration
```

## API Changes

### For Pipeline Code

**Old (streaming_mosaic.py)**:

```python
# Direct SQL queries to products.sqlite3
self.products_db.execute("SELECT * FROM bandpass_calibrators ...")
```

**New**:

```python
from dsa110_contimg.database.calibrators import get_bandpass_calibrators

calibrators = get_bandpass_calibrators(dec_deg=30.0, status="active")
```

### For Calibrator Registration

**Old**:

```python
self.products_db.execute("INSERT INTO bandpass_calibrators ...")
```

**New**:

```python
from dsa110_contimg.database.calibrators import register_bandpass_calibrator

register_bandpass_calibrator(
    calibrator_name="3C286",
    ra_deg=202.7845,
    dec_deg=30.5092,
    dec_range_min=25.0,
    dec_range_max=35.0,
)
```

### For Skymodel Creation

**New Feature**:

```python
from dsa110_contimg.database.skymodel_storage import create_skymodel

skymodel_path = create_skymodel(
    field_id="field_001",
    sources=[
        {"source_name": "NVSS_J123456+123456", "ra_deg": 123.456,
         "dec_deg": 12.3456, "flux_jy": 5.0}
    ],
)
```

## Database Schema

### calibrators.sqlite3 Tables

1. **bandpass_calibrators**: Registered bandpass calibrators
2. **gain_calibrators**: Sources used for gain calibration
3. **catalog_sources**: Unified catalog sources (VLA/NVSS/FIRST/RACS)
4. **vla_calibrators**: VLA calibrator catalog
5. **vla_flux_info**: Frequency-dependent flux information
6. **skymodel_metadata**: Skymodel file metadata

See `backend/src/dsa110_contimg/database/calibrators.py` for full schema.

## Troubleshooting

### Issue: Migration finds 0 calibrators

**Cause**: `products.sqlite3` may not have had any calibrators registered yet.

**Solution**: This is normal for fresh installations. The migration will still
create the new database structure.

### Issue: "database is locked" errors

**Cause**: Concurrent access to SQLite database.

**Solution**: Ensure only one process is accessing the database at a time. The
system uses WAL mode and file locking to prevent corruption.

### Issue: Import errors after migration

**Cause**: Python path or module import issues.

**Solution**:

```bash
# Verify Python environment
which python
python -c "import dsa110_contimg.database.calibrators"

# Reinstall if needed
pip install -e .
```

## Performance Considerations

- **Database Size**: `calibrators.sqlite3` is typically small (< 10 MB)
- **Query Performance**: Indexes are optimized for declination-based queries
- **Concurrent Access**: WAL mode enables safe concurrent reads
- **Backup Frequency**: Recommend daily backups during active development

## Support

For issues or questions:

1. Check logs: `state/logs/`
2. Review test output: `pytest -v`
3. Contact development team

## Related Documentation

- Calibrators Database API
- Catalog Query Interface
- Skymodel Storage
