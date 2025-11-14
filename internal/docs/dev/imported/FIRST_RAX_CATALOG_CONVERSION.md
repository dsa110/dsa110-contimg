# FIRST and RAX Catalog SQLite Conversion

## Date: 2025-11-10

## Overview

Created CLI scripts to convert FIRST and RAX catalogs to SQLite databases, matching the existing NVSS conversion workflow.

## Implementation

### CLI Scripts Created

1. **`build_first_strip_cli.py`**
   - Converts FIRST catalog to SQLite database
   - Similar interface to `build_nvss_strip_cli.py`
   - Supports auto-download/caching of FIRST catalog

2. **`build_rax_strip_cli.py`**
   - Converts RAX catalog to SQLite database
   - Similar interface to `build_nvss_strip_cli.py`
   - Uses cached RAX catalog if available

### Builder Functions

Both scripts use existing builder functions from `builders.py`:
- `build_first_strip_db()` - Already existed
- `build_rax_strip_db()` - Already existed

## Usage

### FIRST Catalog

```bash
# Basic usage
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0

# With custom catalog path
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --first-catalog-path /path/to/FIRST.fits

# With flux threshold
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --min-flux-mjy 10.0
```

### RAX Catalog

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

# With flux threshold
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0 \
    --min-flux-mjy 10.0
```

## Output Format

Both scripts create SQLite databases in `state/catalogs/`:
- FIRST: `first_dec{dec_rounded:+.1f}.sqlite3`
- RAX: `rax_dec{dec_rounded:+.1f}.sqlite3`

Example: `first_dec+54.7.sqlite3`, `rax_dec+54.7.sqlite3`

## Integration

The existing catalog query system (`dsa110_contimg.catalog.query`) already supports FIRST and RAX:
- Queries automatically use SQLite databases if available
- Falls back to CSV/FITS files if databases don't exist
- Environment variables: `FIRST_CATALOG`, `RAX_CATALOG`

## Files Created

1. `src/dsa110_contimg/catalog/build_first_strip_cli.py` - FIRST CLI script
2. `src/dsa110_contimg/catalog/build_rax_strip_cli.py` - RAX CLI script
3. `docs/how-to/build-first-rax-catalogs.md` - User documentation

## Comparison with NVSS

| Feature | NVSS | FIRST | RAX |
|---------|------|-------|-----|
| **CLI Script** | ✓ | ✓ | ✓ |
| **Builder Function** | ✓ | ✓ | ✓ |
| **Auto-download** | ✓ | ✓ | Partial |
| **SQLite Format** | ✓ | ✓ | ✓ |
| **Declination Strips** | ✓ | ✓ | ✓ |
| **Flux Threshold** | ✓ | ✓ | ✓ |

## Status

✓ **COMPLETE** - FIRST and RAX catalog conversion scripts created and ready to use.

The scripts follow the same pattern as NVSS conversion, making it easy to build SQLite databases for all three catalogs using the same workflow.

## Related Files

- `src/dsa110_contimg/catalog/build_nvss_strip_cli.py` - NVSS CLI (reference)
- `src/dsa110_contimg/catalog/builders.py` - Builder functions
- `src/dsa110_contimg/catalog/query.py` - Catalog query interface
- `docs/how-to/build-first-rax-catalogs.md` - User documentation

