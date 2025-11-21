# Directory Structure Migration Guide

This guide explains how to migrate from the legacy directory structure to the
new stage-based structure.

## Overview

The new structure provides:

- **Clear data provenance**: Raw → Calibrated → Images → Mosaics
- **Better organization**: Directories mirror the 9-stage pipeline
- **Improved debugging**: Active processing visible in workspace
- **Scientific alignment**: Structure matches the actual workflow

## Migration Phases

### Phase 1: Initialize New Structure (Non-Breaking)

This creates the new directory structure without moving any data.

```bash
# Initialize new directories
python initialize_new_structure.py
```

This creates:

- `/stage/dsa110-contimg/raw/` - Raw MS files
- `/stage/dsa110-contimg/calibrated/` - Calibrated MS and tables
- `/stage/dsa110-contimg/workspace/` - Active processing
- `/stage/dsa110-contimg/products/` - Validated products
- `/data/dsa110-contimg/products/` - Published products

### Phase 2: Migrate Data

Migrate existing data to the new structure.

```bash
# Dry run (see what would be moved)
python migrate_to_new_structure.py --dry-run

# Execute migration
python migrate_to_new_structure.py
```

The migration script will:

1. Move MS files from `ms/` to `raw/ms/`
2. Move calibration tables to `calibrated/tables/`
3. Create symlinks for backward compatibility
4. Update database references

### Phase 3: Enable New Structure

Enable the new structure in the pipeline.

```bash
# Set environment variable
export CONTIMG_USE_NEW_STRUCTURE=1

# Or add to your shell profile
echo 'export CONTIMG_USE_NEW_STRUCTURE=1' >> ~/.bashrc
```

### Phase 4: Verify and Test

1. **Verify data locations**:

   ```bash
   ls -la /stage/dsa110-contimg/raw/ms/
   ls -la /stage/dsa110-contimg/calibrated/ms/
   ```

2. **Test pipeline**:

   ```bash
   # Run a test mosaic creation (see MOSAIC_ORCHESTRATOR_USAGE.md for full options)
   python create_10min_mosaic.py
   ```

3. **Check database**:
   ```bash
   sqlite3 /data/dsa110-contimg/state/data_registry.sqlite3 \
     "SELECT data_type, COUNT(*) FROM data_registry GROUP BY data_type;"
   ```

### Phase 5: Cleanup (Optional, After Verification)

After verifying everything works:

1. Remove symlinks (if no longer needed)
2. Remove old empty directories
3. Update documentation

## Rollback

If you need to rollback:

1. **Disable new structure**:

   ```bash
   unset CONTIMG_USE_NEW_STRUCTURE
   # Or remove from environment
   ```

2. **Restore from backup** (if you created one):
   ```bash
   # Restore original structure
   ```

## Environment Variables

| Variable                    | Default                 | Description                       |
| --------------------------- | ----------------------- | --------------------------------- |
| `CONTIMG_USE_NEW_STRUCTURE` | `0`                     | Enable new structure (set to `1`) |
| `CONTIMG_STAGE_BASE`        | `/stage/dsa110-contimg` | Base staging directory            |
| `CONTIMG_DATA_BASE`         | `/data/dsa110-contimg`  | Base data directory               |

## Directory Mapping

### Legacy → New Structure

| Legacy            | New                   | Notes                                   |
| ----------------- | --------------------- | --------------------------------------- |
| `ms/science/`     | `raw/ms/science/`     | Raw science MS                          |
| `ms/calibrators/` | `raw/ms/calibrators/` | Raw calibrator MS                       |
| `calib_ms/`       | `calibrated/ms/`      | Calibrated MS (moved after calibration) |
| `caltables/`      | `calibrated/tables/`  | Calibration tables                      |
| `images/`         | `images/`             | Same location                           |
| `mosaics/`        | `mosaics/`            | Same location                           |
| `catalogs/`       | `products/catalogs/`  | Moved to products                       |
| `qa/`             | `products/qa/`        | Moved to products                       |
| `metadata/`       | `products/metadata/`  | Moved to products                       |
| N/A               | `raw/groups/`         | New: Group definitions                  |
| N/A               | `workspace/active/`   | New: Active processing                  |
| N/A               | `workspace/failed/`   | New: Failed jobs                        |

## Data Types

### Legacy Types

- `ms` - Measurement sets
- `calib_ms` - Calibrated MS (stays in original location)
- `caltable` - Calibration tables

### New Types

- `raw_ms` - Raw (uncalibrated) MS files
- `calibrated_ms` - Calibrated MS files (moved to calibrated directory)
- `calibration_table` - Calibration tables

## Troubleshooting

### Issue: Migration fails with permission errors

**Solution**: Ensure you have write permissions:

```bash
sudo chown -R $USER:$USER /stage/dsa110-contimg
sudo chown -R $USER:$USER /data/dsa110-contimg
```

### Issue: Database update fails

**Solution**: Backup database first:

```bash
cp /data/dsa110-contimg/state/data_registry.sqlite3 \
   /data/dsa110-contimg/state/data_registry.sqlite3.backup
```

### Issue: Symlinks not working

**Solution**: Check if old directories still have files:

```bash
ls -la /stage/dsa110-contimg/ms/
# If not empty, migration may have failed
```

## Support

For issues or questions:

1. Check migration logs
2. Review `pipeline_redesign_proposal.md`
3. Check database for path references

## Next Steps After Migration

1. ✅ Verify all data migrated correctly
2. ✅ Test pipeline with new structure
3. ✅ Monitor for any path-related errors
4. ✅ Update any custom scripts using old paths
5. ✅ Update documentation
6. ✅ Remove symlinks after verification (Phase 4)
