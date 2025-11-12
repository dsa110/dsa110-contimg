# Docker Configuration Update - Products Database

## Summary
Updated Docker configuration to use the standard `products.sqlite3` filename instead of `products.db`.

## Changes Made

### 1. Updated `.env` File
**File**: `ops/docker/.env`

**Changed**:
```bash
# Before
CONTIMG_PRODUCTS_DB=/data/dsa110-contimg/state/products.db

# After
CONTIMG_PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3
```

### 2. Restarted API Container
Restarted `contimg-api` container to pick up the new configuration.

### 3. Verified Endpoints
All dashboard endpoints tested and confirmed working with `products.sqlite3`:
- ✅ ESE Candidates endpoint
- ✅ Mosaic Query endpoint
- ✅ Source Search endpoint
- ✅ Alert History endpoint

### 4. Removed Duplicate Database
Removed `state/products.db` since:
- All data was already in `products.sqlite3` (which had more complete data)
- The codebase default is `products.sqlite3`
- No unique data was found in `products.db`

## Rationale

1. **Consistency**: The codebase uses `products.sqlite3` as the default throughout
2. **Standardization**: All database files use `.sqlite3` extension (e.g., `ingest.sqlite3`, `cal_registry.sqlite3`)
3. **Data Completeness**: `products.sqlite3` had more complete data (178 photometry rows vs 100)

## Impact

- **API Container**: Now uses `products.sqlite3` (matches codebase default)
- **Other Containers**: Will also use `products.sqlite3` when restarted
- **No Data Loss**: All data preserved in `products.sqlite3`

## Verification

To verify the configuration is correct:
```bash
docker exec contimg-api env | grep PIPELINE_PRODUCTS_DB
# Should show: PIPELINE_PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3
```

## Next Steps

If other containers (scheduler, stream) are running, they should be restarted to pick up the new configuration:
```bash
docker restart contimg-scheduler contimg-stream
```

