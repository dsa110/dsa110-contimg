# Building FIRST and RAX SQLite Catalogs

## Overview

Similar to NVSS catalog conversion, FIRST and RAX catalogs can be converted to
SQLite databases for efficient querying. This document describes how to build
these catalogs.

## Prerequisites

- HDF5 file with pointing information (to extract declination)
- FIRST/RAX catalog files (CSV/FITS) - will be auto-downloaded/cached if not
  provided
- Python environment with DSA-110 dependencies

## Building FIRST Catalog

### Using CLI Script

```bash
# Basic usage (auto-downloads FIRST catalog if needed)
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0

# With custom catalog path
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --first-catalog-path /path/to/FIRST.fits

# With minimum flux threshold
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --min-flux-mjy 10.0

# Custom output path
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --output /custom/path/first_dec54.7.sqlite3
```

### Using Python API

```python
from dsa110_contimg.catalog.builders import build_first_strip_db

output_path = build_first_strip_db(
    dec_center=54.7,
    dec_range=(48.7, 60.7),  # ±6 degrees
    output_path=None,  # Auto-generated
    first_catalog_path=None,  # Auto-download if needed
    min_flux_mjy=10.0,  # Optional flux threshold
    cache_dir=".cache/catalogs"
)

print(f"FIRST database created: {output_path}")
```

## Building RAX Catalog

### Using CLI Script

```bash
# Basic usage
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0

# With custom catalog path
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --rax-catalog-path /path/to/RAX.fits

# With minimum flux threshold
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --min-flux-mjy 10.0
```

### Using Python API

```python
from dsa110_contimg.catalog.builders import build_rax_strip_db

output_path = build_rax_strip_db(
    dec_center=54.7,
    dec_range=(48.7, 60.7),  # ±6 degrees
    output_path=None,  # Auto-generated
    rax_catalog_path=None,  # Uses cached if available
    min_flux_mjy=10.0,  # Optional flux threshold
    cache_dir=".cache/catalogs"
)

print(f"RAX database created: {output_path}")
```

## Output Format

Both scripts create SQLite databases in `state/catalogs/` with naming
convention:

- FIRST: `first_dec{dec_rounded:+.1f}.sqlite3`
- RAX: `rax_dec{dec_rounded:+.1f}.sqlite3`

Example: `first_dec+54.7.sqlite3`, `rax_dec+54.7.sqlite3`

## Database Schema

### FIRST Database

- **Table:** `sources`
- **Columns:**
  - `ra_deg`: Right ascension (degrees)
  - `dec_deg`: Declination (degrees)
  - `flux_mjy`: Peak flux (mJy/beam)
  - `major_arcsec`: Major axis (arcseconds)
  - `minor_arcsec`: Minor axis (arcseconds)
  - `pa_deg`: Position angle (degrees)
  - Additional FIRST-specific columns

### RAX Database

- **Table:** `sources`
- **Columns:**
  - `ra_deg`: Right ascension (degrees)
  - `dec_deg`: Declination (degrees)
  - `flux_mjy`: Flux (mJy)
  - Additional RAX-specific columns

## Usage in Pipeline

Once built, these databases are automatically used by the catalog query system:

```python
from dsa110_contimg.catalog.query import query_sources

# Query FIRST sources
first_sources = query_sources(
    ra_deg=122.0,
    dec_deg=54.7,
    radius_deg=0.5,
    catalog_type="first"
)

# Query RAX sources
rax_sources = query_sources(
    ra_deg=122.0,
    dec_deg=54.7,
    radius_deg=0.5,
    catalog_type="rax"
)
```

## Environment Variables

The catalog system uses environment variables to locate databases:

- `FIRST_CATALOG`: Path to FIRST catalog directory or file
- `RAX_CATALOG`: Path to RAX catalog directory or file

If not set, the system will:

1. Look for databases in `state/catalogs/`
2. Attempt to auto-download/cache catalog files
3. Fall back to CSV files if available

## Comparison with NVSS

| Feature                | NVSS | FIRST | RAX     |
| ---------------------- | ---- | ----- | ------- |
| **CLI Script**         | ✓    | ✓     | ✓       |
| **Auto-download**      | ✓    | ✓     | Partial |
| **SQLite Format**      | ✓    | ✓     | ✓       |
| **Declination Strips** | ✓    | ✓     | ✓       |
| **Flux Threshold**     | ✓    | ✓     | ✓       |

## Notes

1. **FIRST Catalog**: May require manual download from FIRST survey website
2. **RAX Catalog**: May need to be provided manually or cached
3. **Declination Range**: Default ±6 degrees matches NVSS convention
4. **Caching**: Catalog files are cached in `.cache/catalogs/` to avoid
   re-downloading

## Related Documentation

- `docs/reference/CATALOG_DOCUMENTATION_INDEX.md` - NVSS catalog building
  (similar process)
- `src/dsa110_contimg/catalog/builders.py` - Builder functions
- `src/dsa110_contimg/catalog/query.py` - Catalog query interface
