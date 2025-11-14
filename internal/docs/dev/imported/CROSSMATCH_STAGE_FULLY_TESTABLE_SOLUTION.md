# CrossMatchStage Fully Testable Solution

## Problem

The `CrossMatchStage` was only **partially testable** because synthetic sources
wouldn't match real catalog sources (NVSS, FIRST, etc.). This prevented full
end-to-end testing of the cross-matching pipeline stage.

## Solution

Implemented **synthetic catalog generation** that creates catalog databases
matching synthetic source positions, enabling full testing of `CrossMatchStage`.

## Implementation

### 1. Synthetic Catalog Module (`synthetic_catalog.py`)

**New module:** `src/dsa110_contimg/simulation/synthetic_catalog.py`

**Key functions:**

- `create_synthetic_catalog_db()` - Creates SQLite catalog database matching
  real catalog format
- `create_synthetic_catalog_from_uvh5()` - Extracts source positions from UVH5
  metadata and creates catalog

**Features:**

- ✅ Same schema as real catalogs (`sources` table with `ra_deg`, `dec_deg`,
  `flux_mjy`)
- ✅ Realistic catalog errors (0.1" position, 5% flux uncertainty)
- ✅ Supports NVSS, FIRST, RAX, VLASS formats
- ✅ Metadata table with declination strip information

### 2. Integration with Synthetic Data Generation

**Updated:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`

**New CLI arguments:**

- `--create-catalog` - Create synthetic catalog database
- `--catalog-type` - Catalog type (nvss, first, rax, vlass)
- `--catalog-output` - Custom output path (auto-generated if not specified)

**Source position storage:**

- Stores `synthetic_source_ra_deg` and `synthetic_source_dec_deg` in UVH5
  `extra_keywords`
- Falls back to phase center if not explicitly set

### 3. Usage

**Generate synthetic data with catalog:**

```bash
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --template-free \
    --output /tmp/synthetic_data \
    --flux-jy 0.1 \
    --create-catalog \
    --catalog-type nvss
```

**Use catalog in pipeline:**

```bash
export NVSS_CATALOG=/tmp/synthetic_data/catalogs/nvss_dec35.0.sqlite3
```

**Run pipeline:**

```bash
python -m dsa110_contimg.pipeline.adapter \
    --input /tmp/synthetic_data/*.uvh5
```

## Result

### Before

- ⚠️ **Partially testable** - Algorithms worked, but real catalog queries
  differed
- ❌ Could not test full cross-matching workflow
- ❌ Could not validate astrometric offsets or flux scale corrections

### After

- ✅ **Fully testable** - Complete cross-matching workflow can be tested
- ✅ Synthetic catalog entries match synthetic source positions
- ✅ Can test position matching, flux comparison, astrometric offsets
- ✅ Can test database operations and error handling

## Coverage Update

**Pipeline Stage Coverage:**

- **Before:** 8 of 9 stages fully testable, 1 partially testable
- **After:** ✅ **9 of 9 stages fully testable**

**End-to-End Testing:**

- ✅ All 9 pipeline stages can be tested with synthetic data
- ✅ Complete workflow from UVH5 → MS → Calibration → Imaging → Cross-Match →
  Database

## Files Changed

1. **New:** `src/dsa110_contimg/simulation/synthetic_catalog.py`
   - Synthetic catalog generation functions
   - SQLite database creation matching real catalog format

2. **Updated:** `src/dsa110_contimg/simulation/make_synthetic_uvh5.py`
   - Added `--create-catalog`, `--catalog-type`, `--catalog-output` arguments
   - Integrated catalog generation into main workflow
   - Added source position storage in UVH5 metadata

3. **New:** `docs/how-to/testing_crossmatch_stage_with_synthetic_data.md`
   - Complete usage guide
   - Examples and validation procedures

4. **Updated:** `docs/analysis/SYNTHETIC_DATA_PIPELINE_STAGE_COVERAGE.md`
   - Updated CrossMatchStage status to "Fully Testable"
   - Updated summary statistics

## Testing

### Verify Catalog Generation

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("test_nvss_dec35.0.sqlite3")
sources = pd.read_sql("SELECT * FROM sources", conn)
print(f"Catalog contains {len(sources)} sources")
print(sources.head())
```

### Verify Cross-Match Results

After running pipeline, check database:

```python
from dsa110_contimg.database.products import get_products_db
import pandas as pd

conn = get_products_db()
df = pd.read_sql("SELECT * FROM crossmatch_results LIMIT 10", conn)
print(df)
```

## Related Documentation

- `docs/how-to/testing_crossmatch_stage_with_synthetic_data.md` - Usage guide
- `docs/analysis/SYNTHETIC_DATA_PIPELINE_STAGE_COVERAGE.md` - Coverage
  assessment
- `docs/concepts/pipeline_stage_architecture.md` - Pipeline stage documentation
