# Catalog Coverage Features - Testing Guide

## Overview

This guide provides instructions for testing the three catalog coverage
features:

1. Auto-build missing catalog databases
2. Coverage status in pipeline status reports
3. Coverage visualization tools

## Prerequisites

**CRITICAL: Environment Requirements**

- **Python 3.7+** (required - Python 3.6.9 will fail due to
  `from __future__ import annotations`)
- **Casa6 conda environment** (recommended - contains all dependencies)
- Required packages: `pandas`, `matplotlib`, `astropy`, `numpy`
- Access to ingest database (for status endpoint)
- Access to catalog databases or ability to build them

**Activating the correct environment:**

```bash
# Source developer setup (automatically activates casa6)
source /data/dsa110-contimg/scripts/dev/developer-setup.sh
```

**Note:** The `developer-setup.sh` script automatically:

- Activates the casa6 conda environment (Python 3.11.13)
- Wraps `python`, `python3`, `sqlite3`, and `pip` to use casa6 versions
- Ensures all required packages are available

**Alternative (if developer-setup.sh is not available):**

```bash
# Manually activate casa6 environment
conda activate casa6
```

**Note:** The system Python 3.6.9 environment will **not work** for these tests
due to:

- Missing `from __future__ import annotations` support
- Missing required packages (pandas, etc.)

## 1. Testing Auto-Build Functionality

### Test A.1: Verify Auto-Build Triggers

**When NVSS is queried:**

```python
from dsa110_contimg.calibration.catalogs import query_nvss_sources

# This should automatically check and build missing FIRST/RAX databases
sources = query_nvss_sources(
    ra_deg=180.0,
    dec_deg=54.6,  # Within NVSS/FIRST coverage
    radius_deg=1.0,
)
```

**Expected behavior:**

- Logs should show: "⚠️ FIRST catalog database is missing..."
- If `auto_build=True`, logs should show: "🔨 Auto-building FIRST catalog
  database..."
- Database should be created in `state/catalogs/`

### Test A.2: Verify Coverage Limits

```python
from dsa110_contimg.catalog.builders import CATALOG_COVERAGE_LIMITS

for catalog_type, limits in CATALOG_COVERAGE_LIMITS.items():
    print(f"{catalog_type}: {limits['dec_min']}° to {limits['dec_max']}°")
```

**Expected output:**

- NVSS: -40.0° to 90.0°
- FIRST: -40.0° to 90.0°
- RAX: -90.0° to 49.9°

### Test A.3: Test Outside Coverage

```python
from dsa110_contimg.catalog.builders import check_missing_catalog_databases

# Test declination outside coverage
results = check_missing_catalog_databases(dec_deg=-50.0, auto_build=False)
# Should not attempt to build databases outside coverage
```

### Test A.4: Manual Auto-Build

```python
from dsa110_contimg.catalog.builders import auto_build_missing_catalog_databases

built = auto_build_missing_catalog_databases(dec_deg=54.6)
print(f"Built databases: {built}")
```

## 2. Testing API Status Endpoint

### Test B.1: Verify Endpoint Returns Coverage Status

**Using curl:**

```bash
curl http://localhost:8000/api/status | jq .catalog_coverage
```

**Expected response:**

```json
{
  "dec_deg": 54.6,
  "nvss": {
    "exists": true,
    "within_coverage": true,
    "db_path": "/data/dsa110-contimg/state/catalogs/nvss_dec+54.6.sqlite3"
  },
  "first": {
    "exists": false,
    "within_coverage": true,
    "db_path": null
  },
  "rax": {
    "exists": false,
    "within_coverage": false,
    "db_path": null
  }
}
```

### Test B.2: Test with Different Declinations

1. Update pointing history with different declination
2. Query status endpoint
3. Verify coverage status reflects new declination

### Test B.3: Test Without Pointing History

1. Temporarily rename/remove ingest database
2. Query status endpoint
3. Verify `catalog_coverage` is `null` (not an error)

### Test B.4: Direct Function Test

```python
from dsa110_contimg.api.routers.status import get_catalog_coverage_status
from pathlib import Path

status = get_catalog_coverage_status(
    ingest_db_path=Path("state/ingest.sqlite3")
)
print(status)
```

## 3. Testing Visualization Tool

### Test C.1: Basic Plot Generation

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type coverage \
    --output-dir /tmp/test_plots
```

**Expected:**

- File created: `coverage_plot.png`
- Shows coverage bars for NVSS, FIRST, RAX
- Red dashed line at 54.6° declination
- Color-coded database status

### Test C.2: Summary Table

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --dec 54.6 \
    --plot-type table \
    --output-dir /tmp/test_plots
```

**Expected:**

- File created: `coverage_table.png`
- Table with catalog names, coverage ranges, status
- Color-coded cells (green=ready, red=missing)

### Test C.3: Auto-Detection of Declination

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --ingest-db state/ingest.sqlite3 \
    --plot-type both
```

**Expected:**

- Automatically reads declination from pointing history
- Generates both plot and table

### Test C.4: Without Declination

```bash
python -m dsa110_contimg.catalog.visualize_coverage \
    --plot-type coverage \
    --no-db-status
```

**Expected:**

- Plot generated without declination line
- No database status indicators

## 4. Integration Testing

### Test 4.1: Full Pipeline Flow

1. Start pipeline with new HDF5 file
2. Monitor logs for auto-build messages
3. Verify databases are created automatically
4. Check API status endpoint shows correct status
5. Generate visualization plots

### Test 4.2: Calibrator Selection

1. Trigger calibrator selection (new HDF5 file or declination change)
2. Verify NVSS query triggers auto-build
3. Check that missing databases are built
4. Verify calibrator is registered successfully

### Test 4.3: Real-Time Status Updates

1. Query `/api/status` endpoint
2. Build a missing database manually
3. Query endpoint again
4. Verify status reflects new database existence

### Test 4.4: Performance

1. Query status endpoint multiple times
2. Monitor response times
3. Verify no significant performance degradation
4. Check database query efficiency

## 5. Edge Cases and Error Handling

### Test 5.1: Missing Ingest Database

```python
from dsa110_contimg.api.routers.status import get_catalog_coverage_status
from pathlib import Path

status = get_catalog_coverage_status(
    ingest_db_path=Path("/tmp/nonexistent.sqlite3")
)
# Should return None, not raise exception
assert status is None
```

### Test 5.2: Empty Pointing History

1. Create empty ingest database
2. Query status endpoint
3. Verify graceful handling (returns None)

### Test 5.3: Corrupted Database

1. Create database file with invalid SQLite format
2. Attempt to query status
3. Verify error is caught and logged, doesn't crash

### Test 5.4: Missing Visualization Dependencies

```python
# Simulate missing matplotlib
import sys
sys.modules['matplotlib'] = None

# Should handle gracefully
from dsa110_contimg.catalog.visualize_coverage import plot_catalog_coverage
# Should raise ImportError or handle gracefully
```

## 6. Verification Script

Run the static verification script:

```bash
python3 verify_coverage_features.py
```

This checks:

- All files exist
- Functions are defined
- Classes are defined
- Integration points are present

## 7. Manual Checklist

- [ ] Auto-build triggers when NVSS is queried
- [ ] Auto-build only occurs within coverage limits
- [ ] Error handling works when build fails
- [ ] Logging output is clear and informative
- [ ] API endpoint returns `catalog_coverage` field
- [ ] Status reflects actual database existence
- [ ] Visualization tool generates plots correctly
- [ ] Auto-detection of declination works
- [ ] Color coding matches status
- [ ] Edge cases handled gracefully

## Troubleshooting

### Issue: Auto-build not triggering

**Check:**

1. `auto_build=True` is passed to `check_missing_catalog_databases`
2. Declination is within coverage limits
3. Logs show warnings about missing databases

### Issue: API endpoint returns null

**Check:**

1. Ingest database exists and is accessible
2. Pointing history table has entries
3. Database path is correct in config

### Issue: Visualization fails

**Check:**

1. Matplotlib is installed
2. Output directory is writable
3. Declination value is valid (if provided)

## Next Steps

After completing tests:

1. Document any issues found
2. Update implementation if needed
3. Add unit tests to test suite
4. Update user documentation
5. Consider performance optimizations
