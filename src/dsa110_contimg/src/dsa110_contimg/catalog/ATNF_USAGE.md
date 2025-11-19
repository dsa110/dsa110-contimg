# ATNF Pulsar Catalogue Usage Guide

This document describes how to build and query the ATNF (Australia Telescope
National Facility) Pulsar Catalogue within the DSA-110 continuum imaging
pipeline.

## Overview

The ATNF Pulsar Catalogue is a comprehensive database of pulsar properties
maintained by the Australia Telescope National Facility. It contains information
on pulsar positions, periods, dispersion measures, flux densities, distances,
and associations.

**Coverage**: All-sky (declination range: -90° to +90°)

**Database Format**: SQLite3 (`atnf_pulsars.sqlite3`)

**Default Location**: `state/catalogs/atnf_pulsars.sqlite3`

## Building the Database

### Prerequisites

The ATNF builder requires the `psrqpy` package to download the catalog:

```bash
conda activate casa6
pip install psrqpy
```

### Basic Usage

Build the database with default settings (all pulsars):

```bash
python -m dsa110_contimg.catalog.build_atnf_pulsars
```

### Command-Line Options

```bash
python -m dsa110_contimg.catalog.build_atnf_pulsars \
    --output /path/to/atnf_pulsars.sqlite3 \
    --min-flux-mjy 1.0 \
    --force
```

**Options**:

- `--output`: Output SQLite database path (default:
  `state/catalogs/atnf_pulsars.sqlite3`)
- `--min-flux-mjy`: Minimum flux at 1400 MHz in mJy (filters pulsars during
  build)
- `--force`: Force rebuild even if database exists

### Programmatic Usage

```python
from dsa110_contimg.catalog import build_atnf_pulsar_db

# Build with default settings
db_path = build_atnf_pulsar_db()

# Build with custom output path and flux filter
db_path = build_atnf_pulsar_db(
    output_path="/data/catalogs/atnf_pulsars.sqlite3",
    min_flux_mjy=1.0,
    force_rebuild=False
)
```

## Querying Pulsars

### Basic Spatial Query

Query pulsars within a field of view:

```python
from dsa110_contimg.catalog import query_sources

# Query pulsars in a 1-degree radius around a field center
df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,  # degrees
    dec_center=45.0,  # degrees
    radius_deg=1.0
)

print(df[['pulsar_name', 'ra_deg', 'dec_deg', 'period_s', 'flux_1400mhz_mjy']])
```

### Query with Flux Filter

Filter pulsars by minimum flux at 1400 MHz:

```python
df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_flux_mjy=1.0  # Only pulsars with S1400 >= 1.0 mJy
)
```

### Query with Period Constraints

Filter pulsars by period (useful for millisecond pulsars or slow pulsars):

```python
# Millisecond pulsars (period < 0.01 seconds)
df_msps = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    max_period_s=0.01  # Period <= 10 ms
)

# Slow pulsars (period > 1 second)
df_slow = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_period_s=1.0  # Period >= 1 s
)

# Period range
df_range = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_period_s=0.001,
    max_period_s=0.1
)
```

### Query with Dispersion Measure Constraints

Filter pulsars by dispersion measure (DM):

```python
# Low DM pulsars (DM < 50 pc/cm³)
df_low_dm = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    max_dm_pc_cm3=50.0
)

# High DM pulsars (DM > 100 pc/cm³)
df_high_dm = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_dm_pc_cm3=100.0
)

# DM range
df_dm_range = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_dm_pc_cm3=10.0,
    max_dm_pc_cm3=100.0
)
```

### Combined Filters

Combine multiple filters:

```python
# Bright millisecond pulsars with low DM
df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    min_flux_mjy=1.0,
    max_period_s=0.01,
    max_dm_pc_cm3=50.0,
    max_sources=10  # Limit results
)
```

## Database Schema

The `atnf_pulsars.sqlite3` database contains a single table `pulsars` with the
following columns:

| Column             | Type               | Description                            |
| ------------------ | ------------------ | -------------------------------------- |
| `pulsar_name`      | TEXT (PRIMARY KEY) | Pulsar J2000 name (e.g., "J0437-4715") |
| `ra_deg`           | REAL               | Right ascension in degrees (J2000)     |
| `dec_deg`          | REAL               | Declination in degrees (J2000)         |
| `period_s`         | REAL               | Pulsar period in seconds               |
| `period_dot`       | REAL               | Period derivative (s/s)                |
| `dm_pc_cm3`        | REAL               | Dispersion measure in pc/cm³           |
| `flux_400mhz_mjy`  | REAL               | Flux density at 400 MHz in mJy         |
| `flux_1400mhz_mjy` | REAL               | Flux density at 1400 MHz in mJy        |
| `flux_2000mhz_mjy` | REAL               | Flux density at 2000 MHz in mJy        |
| `distance_kpc`     | REAL               | Distance in kiloparsecs                |
| `pulsar_type`      | TEXT               | Pulsar type classification             |
| `binary_type`      | TEXT               | Binary companion type (if applicable)  |
| `association`      | TEXT               | Associations (SNR, GC, etc.)           |

### Indexes

The database includes indexes for efficient querying:

- `idx_pulsars_radec`: Composite index on `(ra_deg, dec_deg)`
- `idx_pulsars_dec`: Index on `dec_deg`
- `idx_pulsars_flux1400`: Index on `flux_1400mhz_mjy`
- `idx_pulsars_period`: Index on `period_s`
- `idx_pulsars_dm`: Index on `dm_pc_cm3`

## Query Parameters Reference

### Standard Parameters

- `catalog_type`: Must be `"atnf"`
- `ra_center`: Field center RA in degrees (0-360)
- `dec_center`: Field center Dec in degrees (-90 to +90)
- `radius_deg`: Search radius in degrees
- `min_flux_mjy`: Minimum flux at 1400 MHz in mJy
- `max_sources`: Maximum number of sources to return
- `catalog_path`: Explicit path to database (overrides auto-resolution)

### ATNF-Specific Parameters (via `**kwargs`)

- `min_period_s`: Minimum pulsar period in seconds
- `max_period_s`: Maximum pulsar period in seconds
- `min_dm_pc_cm3`: Minimum dispersion measure in pc/cm³
- `max_dm_pc_cm3`: Maximum dispersion measure in pc/cm³

## Integration with Other Catalogs

The ATNF catalog can be queried alongside other catalogs using
`query_all_catalogs`:

```python
from dsa110_contimg.catalog import query_all_catalogs

# Query all catalogs including ATNF
results = query_all_catalogs(
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0,
    catalog_types=["nvss", "first", "atnf"]
)

# Access ATNF results
atnf_df = results.get("atnf", pd.DataFrame())
```

## Cross-Matching with Other Sources

Cross-match ATNF pulsars with sources from other catalogs:

```python
from dsa110_contimg.catalog import query_sources
from dsa110_contimg.catalog.crossmatch import crossmatch_sources

# Query NVSS sources
nvss_df = query_sources(
    catalog_type="nvss",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0
)

# Query ATNF pulsars
atnf_df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=1.0
)

# Cross-match within 30 arcseconds
matches = crossmatch_sources(
    nvss_df,
    atnf_df,
    max_separation_arcsec=30.0
)
```

## Example Use Cases

### 1. Finding Bright Pulsars in a Field

```python
from dsa110_contimg.catalog import query_sources

df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=0.5,
    min_flux_mjy=5.0,  # Bright pulsars only
    max_sources=20
)

print(f"Found {len(df)} bright pulsars")
print(df[['pulsar_name', 'ra_deg', 'dec_deg', 'flux_1400mhz_mjy', 'period_s']])
```

### 2. Identifying Millisecond Pulsars

```python
df_msps = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=2.0,
    max_period_s=0.01,  # Period < 10 ms
    min_flux_mjy=0.1
)

print(f"Found {len(df_msps)} millisecond pulsars")
```

### 3. High-DM Pulsars (Distant or High Electron Density)

```python
df_high_dm = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=2.0,
    min_dm_pc_cm3=100.0
)

print(f"Found {len(df_high_dm)} high-DM pulsars")
```

### 4. Pulsars Associated with Supernova Remnants

```python
df = query_sources(
    catalog_type="atnf",
    ra_center=180.0,
    dec_center=45.0,
    radius_deg=2.0
)

# Filter by association (post-processing)
snr_pulsars = df[df['association'].str.contains('SNR', na=False)]
print(f"Found {len(snr_pulsars)} pulsars associated with SNRs")
```

## Notes

- The database is built using `psrqpy`, which queries the ATNF online database.
  An internet connection is required for the initial build.
- Flux values are in mJy. The 1400 MHz flux (`flux_1400mhz_mjy`) is closest to
  DSA-110 observing frequencies.
- Period values are in seconds. Millisecond pulsars have periods < 0.01 s.
- Dispersion measure (DM) is in pc/cm³. Typical values range from ~1 to several
  hundred.
- Missing values (NULL) are represented as `NaN` in pandas DataFrames.
- Results are ordered by `flux_1400mhz_mjy` (descending) by default.

## Troubleshooting

### Database Not Found

If you get a `FileNotFoundError`, ensure the database has been built:

```bash
python -m dsa110_contimg.catalog.build_atnf_pulsars
```

### psrqpy Import Error

Install the required package:

```bash
conda activate casa6
pip install psrqpy
```

### Empty Results

- Check that your field center coordinates are correct (RA: 0-360°, Dec: -90 to
  +90°)
- Verify the search radius is appropriate
- Try removing flux/period/DM filters to see if any pulsars exist in the field
- Check that the database contains data:
  `sqlite3 state/catalogs/atnf_pulsars.sqlite3 "SELECT COUNT(*) FROM pulsars;"`
