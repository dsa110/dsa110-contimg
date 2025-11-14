# Testing CrossMatchStage with Synthetic Data

## Overview

The `CrossMatchStage` can now be **fully tested** using synthetic data by
generating matching catalog entries that correspond to synthetic source
positions. This enables complete end-to-end testing of the cross-matching
pipeline stage.

## Quick Start

### 1. Generate Synthetic Data with Catalog

```bash
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --template-free \
    --output /tmp/synthetic_data \
    --flux-jy 0.1 \
    --source-model gaussian \
    --source-size-arcsec 10.0 \
    --add-noise \
    --add-cal-errors \
    --create-catalog \
    --catalog-type nvss
```

This will:

- Generate synthetic UVH5 files
- Create a matching NVSS catalog database at
  `/tmp/synthetic_data/catalogs/nvss_dec{dec}.sqlite3`
- Print instructions for using the catalog in pipeline testing

### 2. Use Catalog in Pipeline Testing

Set the environment variable to point to the synthetic catalog:

```bash
export NVSS_CATALOG=/tmp/synthetic_data/catalogs/nvss_dec35.0.sqlite3
```

Or use explicit path in pipeline configuration:

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig(
    crossmatch=CrossMatchConfig(
        enabled=True,
        catalog_types=["nvss"],
        # ... other settings
    )
)

# In CrossMatchStage, catalog_path can be explicitly set
# via catalog_path parameter in query_sources()
```

### 3. Run Pipeline with Synthetic Data

```bash
# Run pipeline with synthetic UVH5 files
python -m dsa110_contimg.pipeline.adapter \
    --input /tmp/synthetic_data/*.uvh5 \
    --config pipeline_config.yaml
```

The `CrossMatchStage` will now:

- Query the synthetic catalog (via `NVSS_CATALOG` environment variable)
- Match detected sources from images with catalog entries
- Calculate astrometric offsets and flux scale corrections
- Store cross-match results in database

## How It Works

### Synthetic Catalog Generation

The `create_synthetic_catalog_db()` function creates a SQLite database in the
same format as real catalog databases (NVSS, FIRST, RAX, etc.) with entries that
match synthetic source positions.

**Key Features:**

- **Format compatibility:** Same schema as real catalogs (`sources` table with
  `ra_deg`, `dec_deg`, `flux_mjy`)
- **Realistic errors:** Adds small position and flux uncertainties (default:
  0.1" position, 5% flux)
- **Metadata:** Includes declination strip information and synthetic flag
- **Multiple catalogs:** Supports NVSS, FIRST, RAX, VLASS formats

### Source Position Extraction

The catalog generation extracts source positions from UVH5 file metadata:

1. **Primary:** Uses `synthetic_source_ra_deg` and `synthetic_source_dec_deg`
   from `extra_keywords`
2. **Fallback:** Uses phase center (`phase_center_ra_degrees`,
   `phase_center_dec_degrees`)
3. **Multiple sources:** Supports JSON array in `synthetic_sources` keyword
   (future enhancement)

### Catalog Query Integration

The `query_sources()` function in `dsa110_contimg.catalog.query` automatically
uses the synthetic catalog when:

1. **Environment variable** is set:
   `NVSS_CATALOG=/path/to/synthetic_catalog.sqlite3`
2. **Explicit path** is provided: `catalog_path` parameter in `query_sources()`
3. **Standard location:** Catalog is in `state/catalogs/` with correct naming
   (`nvss_dec{dec}.sqlite3`)

## Advanced Usage

### Custom Catalog Output Path

```bash
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --create-catalog \
    --catalog-output /custom/path/test_catalog.sqlite3 \
    --catalog-type first
```

### Multiple Catalog Types

Generate multiple catalog types for comprehensive testing:

```bash
# Generate NVSS catalog
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --create-catalog --catalog-type nvss --output /tmp/synth

# Generate FIRST catalog (different output path)
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --create-catalog --catalog-type first \
    --catalog-output /tmp/synth/catalogs/first_dec35.0.sqlite3 \
    --output /tmp/synth
```

### Programmatic Catalog Creation

```python
from pathlib import Path
from dsa110_contimg.simulation.synthetic_catalog import create_synthetic_catalog_db
import numpy as np

# Define source positions (RA, Dec, flux in Jy)
sources = [
    (180.0, 35.0, 0.1),  # Source 1
    (180.1, 35.0, 0.05),  # Source 2
    (179.9, 35.1, 0.08),  # Source 3
]

# Create catalog database
catalog_path = create_synthetic_catalog_db(
    output_path=Path("test_nvss_dec35.0.sqlite3"),
    source_positions=sources,
    catalog_type="nvss",
    dec_strip=35.0,
    add_noise=True,  # Add realistic catalog errors
    position_noise_arcsec=0.1,  # 0.1" position uncertainty
    flux_noise_fraction=0.05,  # 5% flux uncertainty
)

print(f"Created catalog: {catalog_path}")
```

### From UVH5 File

```python
from pathlib import Path
from dsa110_contimg.simulation.synthetic_catalog import (
    create_synthetic_catalog_from_uvh5,
)

# Extract source positions from UVH5 metadata
catalog_path = create_synthetic_catalog_from_uvh5(
    uvh5_path=Path("synthetic_data_00.uvh5"),
    catalog_output_path=Path("test_nvss_dec35.0.sqlite3"),
    catalog_type="nvss",
    add_noise=True,
)
```

## Testing Workflow

### Complete End-to-End Test

```bash
# 1. Generate synthetic data with catalog
python src/dsa110_contimg/simulation/make_synthetic_uvh5.py \
    --template-free \
    --output /tmp/test_pipeline \
    --flux-jy 0.1 \
    --source-model gaussian \
    --add-noise \
    --add-cal-errors \
    --create-catalog \
    --catalog-type nvss \
    --seed 42

# 2. Set catalog environment variable
export NVSS_CATALOG=/tmp/test_pipeline/catalogs/nvss_dec35.0.sqlite3

# 3. Run pipeline
python -m dsa110_contimg.pipeline.adapter \
    --input /tmp/test_pipeline/*.uvh5 \
    --config pipeline_config.yaml

# 4. Verify cross-match results
python -c "
from dsa110_contimg.database.products import get_products_db
import pandas as pd

conn = get_products_db()
df = pd.read_sql('SELECT * FROM crossmatch_results LIMIT 10', conn)
print(df)
"
```

## Validation

### Verify Catalog Contents

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("test_nvss_dec35.0.sqlite3")

# Check sources
sources = pd.read_sql("SELECT * FROM sources", conn)
print(f"Catalog contains {len(sources)} sources")
print(sources.head())

# Check metadata
meta = pd.read_sql("SELECT * FROM meta", conn)
print("\nMetadata:")
print(meta)
```

### Verify Cross-Match Results

After running the pipeline, check that:

1. **Sources are matched:** Cross-match results contain entries
2. **Positions match:** Astrometric offsets are small (< 1 arcsec)
3. **Fluxes match:** Flux scale corrections are near 1.0
4. **Database entries:** Cross-match results are stored in database

## Limitations

### Current Limitations

1. **Single source per UVH5:** Currently supports one source per file (phase
   center)
2. **Simple source models:** Point, Gaussian, disk only (no complex
   morphologies)
3. **No spectral index:** Flux is constant across frequency
4. **No time variability:** Sources are static

### Future Enhancements

1. **Multiple sources:** Support `--n-sources` parameter for multi-source fields
2. **Spectral index:** Add `--spectral-index` for frequency-dependent flux
3. **Time variability:** Add `--variability` for time-dependent flux
4. **Complex morphologies:** Support for extended sources with multiple
   components

## Related Documentation

- `docs/analysis/SYNTHETIC_DATA_PIPELINE_STAGE_COVERAGE.md` - Pipeline stage
  coverage assessment
- `docs/analysis/SYNTHETIC_DATA_REPRESENTATIVENESS.md` - Synthetic data
  representativeness
- `docs/concepts/pipeline_stage_architecture.md` - Pipeline stage documentation
