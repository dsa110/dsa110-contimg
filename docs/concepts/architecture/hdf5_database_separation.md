# HDF5 Database Separation - Implementation Status

**Date:** 2025-11-17 **Purpose:** Separate input data (HDF5 files) from output
products (MS, images, etc.)

## ✓ Completed

1. **Created new database module**:
   `/data/dsa110-contimg/src/dsa110_contimg/database/hdf5_db.py`
   - `ensure_hdf5_db()` function
   - `get_hdf5_db_path()` function
   - Database location: `/data/dsa110-contimg/state/hdf5.sqlite3`

2. **Database initialized**: HDF5 database created with proper schema
   - Table: `hdf5_file_index`
   - Table: `storage_locations`

3. **Cleaned up incorrect databases**:
   - Removed: `src/state/products.sqlite3` (wrong location)
   - Removed: `src/dsa110_contimg/state/products.sqlite3` (wrong location)
   - Removed: `state/logs/state/products.sqlite3` (wrong location)

4. **Cleaned products.sqlite3**: Removed deleted MS files from database

5. **Fixed MS registration bug**: MS files now automatically register in
   database when conversion is skipped

## ⚠️ Remaining Tasks

### High Priority

1. **Update `hdf5_index.py`** to use HDF5 database:
   - Change `ensure_products_db(products_db)` → `ensure_hdf5_db(hdf5_db)`
   - Update function signatures: `products_db` → `hdf5_db` parameter
   - Functions to update:
     - `index_hdf5_files()`
     - `find_subband_groups_from_db()`
     - `get_group_count()`
     - `is_group_complete()`

2. **Update CLI** (`database/cli.py`):
   - Update `index-hdf5` command to use HDF5 database
   - Update default database path

3. **Update orchestrator** (`mosaic/orchestrator.py`):
   - Update HDF5 group queries to use HDF5 database
   - Currently uses products DB for `find_subband_groups_from_db()`

### Medium Priority

4. **Update conversion code**:
   - `conversion/strategies/hdf5_orchestrator.py` - if it queries
     hdf5_file_index
   - `conversion/calibrator_ms_service.py` - if it queries hdf5_file_index

5. **Update environment variables**:
   - Add `HDF5_DB_PATH` to env setup scripts
   - Update documentation

6. **Remove `hdf5_file_index` from products.sqlite3 schema**:
   - Update `database/products.py` to remove HDF5 table creation
   - Migration: existing deployments may have data in products DB

### Documentation

7. **Update documentation**:
   - Add HDF5 database to architecture docs
   - Update database schema documentation
   - Add migration guide for existing deployments

## Database Locations

- **Products (output)**: `/data/dsa110-contimg/state/products.sqlite3`
- **HDF5 (input)**: `/data/dsa110-contimg/state/hdf5.sqlite3`

## Next Steps

1. Update `hdf5_index.py` to use new database
2. Test with `index-hdf5` CLI command
3. Run mosaic creation to verify integration
