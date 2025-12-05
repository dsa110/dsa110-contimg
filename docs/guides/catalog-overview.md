# Catalog System Overview

Comprehensive guide to catalog usage in the DSA-110 continuum imaging pipeline.

---

## Table of Contents

- [Introduction](#introduction)
- [Radio Catalogs](#radio-catalogs)
  - [NVSS](#nvss-nrao-vla-sky-survey)
  - [FIRST](#first-faint-images-of-the-radio-sky-at-twenty-centimeters)
  - [RACS (RAX)](#racs-rapid-askap-continuum-survey)
  - [VLASS](#vlass-vla-sky-survey)
- [Pulsar Catalogs](#pulsar-catalogs)
  - [ATNF](#atnf-australia-telescope-national-facility-pulsar-catalogue)
  - [Pulsar Scraper](#pulsar-scraper)
- [Multi-wavelength Catalogs](#multi-wavelength-catalogs)
  - [Gaia](#gaia-dr3)
  - [SIMBAD](#simbad)
  - [NED](#ned-nasaipac-extragalactic-database)
  - [Other Vizier Catalogs](#other-vizier-catalogs)
- [Pipeline Usage](#pipeline-usage)
  - [Calibrator Selection](#calibrator-selection)
  - [Source Cross-Matching](#source-cross-matching)
  - [Flux Scale Validation](#flux-scale-validation)
  - [Source Classification](#source-classification)
- [Database Structure](#database-structure)
- [API Reference](#api-reference)
- [Building Catalog Databases](#building-catalog-databases)
- [Best Practices](#best-practices)

---

## Introduction

The DSA-110 pipeline uses multiple astronomical catalogs for:

1. **Calibrator selection** - Finding bright sources for bandpass/gain
   calibration
2. **Cross-matching** - Identifying known sources in DSA-110 images
3. **Flux scale validation** - Comparing DSA-110 photometry with reference
   catalogs
4. **Source classification** - Multi-wavelength identification (stars, AGN,
   pulsars, etc.)

Catalogs are organized into three categories:

- **Radio catalogs**: Primary references for calibration and validation (NVSS,
  FIRST, RACS, VLASS)
- **Pulsar catalogs**: Time-variable source identification (ATNF, Pulsar
  Scraper)
- **Multi-wavelength catalogs**: Source classification and proper motion (Gaia,
  SIMBAD, NED)

---

## Radio Catalogs

### NVSS (NRAO VLA Sky Survey)

**Frequency**: 1.4 GHz (L-band)  
**Coverage**: Dec > -40° (all-sky north of -40°)  
**Resolution**: ~45 arcsec  
**Epoch**: 1993-1996  
**Typical flux limit**: ~2.5 mJy (5σ)

**Pipeline Uses**:

- **Primary calibrator catalog** for bandpass/gain calibration
- Flux scale validation (close to DSA-110 frequency)
- Astrometry validation
- Cross-matching for known sources
- Photometry reference

**Database Location**: `state/catalogs/nvss_dec{declination}.sqlite3`

**Query Function**: `catalog.query.query_sources(catalog_type="nvss", ...)`

**Building Database**:

```bash
python -m dsa110_contimg.catalog.build_nvss_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/nvss_dec+30.0.sqlite3
```

**Schema**:

- `ra_deg`: Right ascension (degrees, J2000)
- `dec_deg`: Declination (degrees, J2000)
- `flux_mjy`: Integrated flux density (mJy)
- `maj_arcsec`: Major axis (arcsec, deconvolved)
- `min_arcsec`: Minor axis (arcsec, deconvolved)

**Notes**:

- NVSS is the default calibrator catalog due to excellent Dec > -40° coverage
- Used for VLA calibrator catalog cross-matching in `calibration/selection.py`
- Local SQLite databases preferred over Vizier queries for performance

---

### FIRST (Faint Images of the Radio Sky at Twenty-centimeters)

**Frequency**: 1.4 GHz (L-band)  
**Coverage**: Dec > -40° (limited areas, ~10,000 sq deg)  
**Resolution**: ~5 arcsec (much higher than NVSS)  
**Epoch**: 1993-2011  
**Typical flux limit**: ~1 mJy (5σ)

**Pipeline Uses**:

- **High-resolution complement** to NVSS
- Source morphology studies (resolved vs. compact)
- Astrometry validation (better positional accuracy)
- Cross-matching for known sources

**Database Location**: `state/catalogs/first_dec{declination}.sqlite3`

**Query Function**: `catalog.query.query_sources(catalog_type="first", ...)`

**Building Database**:

```bash
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/first_dec+30.0.sqlite3
```

**Schema**:

- `ra_deg`: Right ascension (degrees, J2000)
- `dec_deg`: Declination (degrees, J2000)
- `flux_mjy`: Peak flux density (mJy/beam)
- `maj_arcsec`: Major axis (arcsec, deconvolved)
- `min_arcsec`: Minor axis (arcsec, deconvolved)

**Notes**:

- Higher resolution than NVSS (5" vs 45") makes it excellent for astrometry
- Automatic download/caching from Vizier if not found locally
- Coverage check warnings issued for Dec < -40°

---

### RACS (Rapid ASKAP Continuum Survey)

**Internal Name**: `RAX` (for historical reasons)  
**Frequency**: ~888 MHz (lower than DSA-110's 1.4 GHz)  
**Coverage**: Dec < +41° (Southern hemisphere emphasis)  
**Resolution**: ~15 arcsec  
**Epoch**: 2019-2021  
**Typical flux limit**: ~0.2 mJy (5σ)

**Pipeline Uses**:

- **Southern sky complement** to NVSS/FIRST
- Cross-matching for Dec < +41° observations
- Flux scale validation (with spectral index correction)

**Database Location**: `state/catalogs/rax_dec{declination}.sqlite3`

**Query Function**: `catalog.query.query_sources(catalog_type="rax", ...)`

**Building Database**:

```bash
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --dec-center -20.0 \
    --dec-width 1.0 \
    --output state/catalogs/rax_dec-20.0.sqlite3
```

**Schema**:

- `ra_deg`: Right ascension (degrees, J2000)
- `dec_deg`: Declination (degrees, J2000)
- `flux_mjy`: Integrated flux density (mJy)

**Notes**:

- Frequency difference (888 MHz vs 1.4 GHz) requires spectral index for flux
  comparison
- Excellent deep southern coverage where NVSS/FIRST limited
- Name "RAX" used internally to avoid filename conflicts

---

### VLASS (VLA Sky Survey)

**Frequency**: 3.0 GHz (S-band)  
**Coverage**: Dec > -40° (all-sky north of -40°)  
**Resolution**: ~2.5 arcsec  
**Epoch**: 2017-present (ongoing)  
**Typical flux limit**: ~0.12 mJy (5σ)

**Pipeline Uses**:

- Flux scale validation at higher frequency
- **Spectral index calculation** (combined with NVSS at 1.4 GHz)
- Modern high-resolution reference
- Cross-matching for source identification

**Query Function**: `catalog.query.query_sources(catalog_type="vlass", ...)`

**Access**: Queries Vizier or local database if available

**Schema**:

- `ra_deg`: Right ascension (degrees, J2000)
- `dec_deg`: Declination (degrees, J2000)
- `flux_mjy`: Integrated flux density (mJy)

**Notes**:

- Higher frequency (3 GHz vs 1.4 GHz) allows spectral index determination
- Used in QA validation for flux scale checks (`qa/catalog_validation.py`)
- Excellent for identifying steep/flat spectrum sources

---

## Pulsar Catalogs

### ATNF (Australia Telescope National Facility Pulsar Catalogue)

**Coverage**: All-sky  
**Frequency**: Various (typically reports 1400 MHz flux)  
**Number of pulsars**: ~3000  
**Update frequency**: Regularly updated by ATNF

**Pipeline Uses**:

- **Pulsar identification** in DSA-110 images
- Time-variable source flagging
- Proper motion corrections (epoch propagation)
- Known source classification

**Database Location**: `state/catalogs/atnf_pulsars.sqlite3` (all-sky) or
`state/catalogs/atnf_dec{declination}.sqlite3` (strips)

**Query Function**: `catalog.query.query_sources(catalog_type="atnf", ...)`

**Building Database**:

```bash
# Full all-sky database
python -m dsa110_contimg.catalog.build_atnf_pulsars \
    --output state/catalogs/atnf_pulsars.sqlite3 \
    --min-flux-mjy 1.0

# Declination strip database
python -m dsa110_contimg.catalog.build_atnf_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/atnf_dec+30.0.sqlite3
```

**Schema**:

- `ra_deg`: Right ascension (degrees, J2000)
- `dec_deg`: Declination (degrees, J2000)
- `flux_1400_mjy`: Flux at 1400 MHz (mJy)
- `name`: Pulsar J-name (e.g., J1234+5678)
- `period_ms`: Pulse period (milliseconds)
- `dm`: Dispersion measure (pc/cm³)
- `pmra`: Proper motion in RA (mas/yr)
- `pmdec`: Proper motion in Dec (mas/yr)

**Multi-wavelength Query** (with proper motion correction):

```python
from dsa110_contimg.catalog.multiwavelength import check_atnf
from astropy.coordinates import SkyCoord
from astropy.time import Time
import astropy.units as u

coord = SkyCoord(ra=123.456*u.deg, dec=12.345*u.deg)
t = Time('2025-01-01T00:00:00', format='isot')
matches = check_atnf(coord, t=t, radius=15*u.arcsec)
# Returns: {'J1234+1234': 3.2 arcsec, ...}
```

**Prerequisites**:

```bash
pip install psrqpy  # Required for ATNF downloads
```

**Documentation**: See `catalog/ATNF_USAGE.md` for comprehensive guide

**Notes**:

- Pulsars are time-variable; flux measurements may not match catalog values
- QA validation uses ATNF but flags flux mismatches as expected
- Proper motion corrections essential for accurate matching (some pulsars have
  high PM)

---

### Pulsar Scraper

**Source**: https://pulsar.cgca-hub.org/api  
**Coverage**: Curated pulsar database  
**Access**: REST API queries

**Pipeline Uses**:

- Alternative pulsar database (complements ATNF)
- Cross-validation of pulsar identifications

**Query Function**:

```python
from dsa110_contimg.catalog.multiwavelength import check_pulsarscraper
matches = check_pulsarscraper(coord, radius=15*u.arcsec)
```

**Notes**:

- Requires internet connection for API queries
- Used in `photometry/source.py` for multi-catalog checks
- Complements ATNF (some pulsars only in one catalog or the other)

---

## Multi-wavelength Catalogs

### Gaia DR3

**Wavelength**: Optical (G, BP, RP bands)  
**Coverage**: All-sky  
**Number of sources**: ~1.8 billion  
**Astrometry**: Sub-mas precision parallax and proper motion

**Pipeline Uses**:

- **Stellar contamination identification** (remove stars from radio catalogs)
- Proper motion corrections for accurate positions
- Parallax measurements (distance estimates)
- Optical counterpart identification

**Query Function**:

```python
from dsa110_contimg.catalog.external import gaia_search
result = gaia_search(coord, radius_arcsec=5.0)
```

**Multi-wavelength Query**:

```python
from dsa110_contimg.catalog.multiwavelength import check_gaia
matches = check_gaia(coord, t=Time('2025-01-01'), radius=15*u.arcsec)
# Automatically applies proper motion correction
```

**API Integration**: `/api/sources/{id}/external?catalogs=gaia`

**Schema** (returned dict):

- `gaia_id`: Gaia DR3 source ID
- `ra`, `dec`: Position (degrees, corrected for proper motion)
- `pmra`, `pmdec`: Proper motion (mas/yr)
- `parallax`: Parallax (mas)
- `separation_arcsec`: Distance from query position
- `g_mag`: G-band magnitude
- `bp_mag`, `rp_mag`: Blue/red photometer magnitudes

**Notes**:

- Proper motion corrections critical for accurate matching (some stars move >1
  arcsec/yr)
- Used to flag potential stellar contamination in radio catalogs
- Queries astroquery.gaia (requires internet)

---

### SIMBAD

**Service**: Set of Identifications, Measurements and Bibliography for
Astronomical Data  
**Coverage**: All-sky (millions of objects)  
**Content**: Object identification, types, bibliographic references

**Pipeline Uses**:

- **Object type classification** (star, galaxy, QSO, radio source, etc.)
- Alternative names and cross-identifications
- Proper motion corrections (for stars)
- Bibliography references

**Query Function**:

```python
from dsa110_contimg.catalog.external import simbad_search
result = simbad_search(coord, radius_arcsec=5.0)
```

**Multi-wavelength Query**:

```python
from dsa110_contimg.catalog.multiwavelength import check_simbad
matches = check_simbad(coord, t=Time('2025-01-01'), radius=15*u.arcsec)
```

**API Integration**: `/api/sources/{id}/external?catalogs=simbad`

**Schema** (returned dict):

- `main_id`: Primary identifier (e.g., "M 31", "3C 273")
- `otype`: Object type (e.g., "Radio", "QSO", "Star")
- `ra`, `dec`: Position (degrees)
- `separation_arcsec`: Distance from query position
- `flux_v`: V-band magnitude (if available)
- `redshift`: Redshift (if available)
- `names`: List of alternative names
- `bibcode`: Bibliographic reference

**Notes**:

- Excellent for multi-wavelength identification
- Object type classification useful for filtering (e.g., exclude stars)
- Queries astroquery.simbad (requires internet)

---

### NED (NASA/IPAC Extragalactic Database)

**Service**: NASA/IPAC Extragalactic Database  
**Coverage**: Extragalactic sources (galaxies, QSOs, etc.)  
**Content**: Redshifts, classifications, multi-wavelength photometry

**Pipeline Uses**:

- **Redshift determination** for extragalactic sources
- Object classification (galaxy type, QSO, etc.)
- Distance estimates
- Multi-wavelength photometry

**Query Function**:

```python
from dsa110_contimg.catalog.external import ned_search
result = ned_search(coord, radius_arcsec=5.0)
```

**API Integration**: `/api/sources/{id}/external?catalogs=ned`

**Schema** (returned dict):

- `ned_name`: NED object name
- `object_type`: Object classification
- `ra`, `dec`: Position (degrees)
- `separation_arcsec`: Distance from query position
- `redshift`: Redshift value
- `redshift_type`: Redshift type (e.g., 'z', 'v', 'q')
- `velocity`: Recession velocity (km/s)
- `distance`: Distance (Mpc)
- `magnitude`: Optical magnitude
- `flux_1_4ghz`: 1.4 GHz flux (mJy, if available)

**Notes**:

- Focus on extragalactic sources (complements SIMBAD)
- Redshift critical for cosmological studies
- Queries astroquery.ned (requires internet)

---

### Other Vizier Catalogs

Additional catalogs accessible via Vizier queries:

**TGSS (TIFR GMRT Sky Survey)**:

- Frequency: 150 MHz (low frequency)
- Coverage: Dec > -53°
- Function: `check_tgss(coord, radius=15*u.arcsec)`

**MilliQuas (Million Quasars Catalog)**:

- Content: QSO/AGN catalog
- Function: `check_milliquas(coord, radius=15*u.arcsec)`

**WISE AGN Catalog**:

- Wavelength: Infrared (WISE bands)
- Content: AGN candidates
- Function: `check_wiseagn(coord, radius=15*u.arcsec)`

**LQAC (Large Quasar Astrometric Catalogue)**:

- Content: Quasars with accurate astrometry
- Function: `check_lqac(coord, radius=15*u.arcsec)`

**SDSS QSO (Sloan Digital Sky Survey Quasar Catalog)**:

- Content: DR16 quasar catalog
- Function: `check_sdssqso(coord, radius=15*u.arcsec)`

**Usage**:

```python
from dsa110_contimg.catalog.multiwavelength import (
    check_tgss, check_milliquas, check_wiseagn,
    check_lqac, check_sdssqso, check_all_services
)

# Query all catalogs at once
coord = SkyCoord(ra=123.456*u.deg, dec=12.345*u.deg)
results = check_all_services(coord, t=Time('2025-01-01'), radius=15*u.arcsec)
# Returns: {'Gaia': {...}, 'Simbad': {...}, 'ATNF': {...}, 'NVSS': {...}, ...}
```

**Notes**:

- All use Vizier TAP/cone search services
- Require internet connection
- Useful for comprehensive source classification

---

## Pipeline Usage

### Calibrator Selection

**Purpose**: Find bright, compact sources for bandpass and gain calibration

**Catalogs Used**: NVSS (primary), FIRST (for Dec > -40°), RACS (for Dec < +41°)

**Implementation**: `calibration/selection.py`

**Workflow**:

1. Determine MS declination (`determine_ms_type()`)
2. Select appropriate catalog based on declination:
   - Dec > -40°: NVSS or FIRST
   - Dec < +41°: RACS (RAX)
3. Query catalog for bright sources (>1 Jy) within search radius (1-15°)
4. Calculate primary beam weights for each field
5. Select field with maximum weighted flux

**Example**:

```python
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

field_sel, indices, flux, calibrator_info, peak_idx = select_bandpass_from_catalog(
    ms_path="/path/to/calibrator.ms",
    search_radius_deg=15.0,
    min_pb=0.1  # Minimum primary beam response
)
# Returns: field="0~2", indices=[0,1,2], flux=[12.3, 14.5, 10.1],
#          calibrator_info=("3C286", 123.456, 12.345, 14.5), peak_idx=1
```

**Functions**:

- `select_bandpass_from_catalog()`: Automatic catalog selection with SQLite
  support
- `select_bandpass_fields()`: Manual catalog specification (CSV)

**Notes**:

- SQLite databases preferred for speed (no CSV parsing)
- VLA calibrator catalog used as reference (bright, well-characterized sources)
- Primary beam weighting ensures good sensitivity on calibrator

---

### Source Cross-Matching

**Purpose**: Identify known sources in DSA-110 images, calculate astrometric
offsets and flux scales

**Catalogs Used**: NVSS, FIRST, RACS, VLASS (configurable)

**Implementation**: `catalog/crossmatch.py`,
`pipeline/stages_impl.py::CrossMatchStage`

**Workflow**:

1. Extract sources from DSA-110 image (photometry or validation stage)
2. Query reference catalogs in image field (1.5° radius)
3. Perform nearest-neighbor matching (configurable radius, typically 10")
4. Identify best match across all catalogs (`multi_catalog_match()`)
5. Calculate positional offsets (RA/Dec systematic errors)
6. Calculate flux scale (DSA-110 / catalog flux ratio)
7. Store results in `cross_matches` database table

**Example**:

```python
from dsa110_contimg.catalog.crossmatch import cross_match_sources

matches_df = cross_match_sources(
    detected_ra=detected_sources["ra_deg"].values,
    detected_dec=detected_sources["dec_deg"].values,
    catalog_ra=nvss_sources["ra_deg"].values,
    catalog_dec=nvss_sources["dec_deg"].values,
    radius_arcsec=10.0,
    detected_flux=detected_sources["flux_mjy"].values,
    catalog_flux=nvss_sources["flux_mjy"].values
)
# Returns DataFrame with columns: detected_idx, catalog_idx, separation_arcsec,
#                                  flux_ratio, flux_ratio_err, etc.
```

**Functions**:

- `cross_match_sources()`: Basic nearest-neighbor matching
- `multi_catalog_match()`: Best match across multiple catalogs
- `calculate_positional_offsets()`: Astrometric offset statistics
- `calculate_flux_scale()`: Flux scale ratio and uncertainty
- `identify_duplicate_catalog_sources()`: Flag catalog sources with multiple
  matches

**Configuration** (`pipeline/config.py`):

```python
class CrossMatchConfig:
    enabled: bool = True  # Enable cross-matching stage
    catalog_types: List[str] = ["nvss", "rax"]  # Query NVSS + RACS by default
    radius_arcsec: float = 10.0  # Matching radius
    method: str = "basic"  # Matching method: "basic" (nearest) or "advanced"
    store_in_database: bool = True  # Persist matches in products DB
    min_separation_arcsec: float = 0.1
    max_separation_arcsec: float = 60.0
    calculate_spectral_indices: bool = True
```

**Pipeline Stage**:

```python
# Automatic cross-matching in pipeline
config.crossmatch.enabled = True  # default
# NVSS + RACS are queried automatically; append FIRST/VLASS if desired
config.crossmatch.catalog_types = ["nvss", "rax", "first"]
# Stage executes automatically after imaging/photometry
```

**Database Storage** (`database/schema.sql`):

```sql
CREATE TABLE cross_matches (
    id INTEGER PRIMARY KEY,
    source_id TEXT,  -- DSA-110 source ID
    catalog_type TEXT,  -- "nvss", "first", etc.
    catalog_id TEXT,  -- Catalog source ID
    separation_arcsec REAL,
    match_quality TEXT,  -- "unique", "ambiguous", "none"
    ra_offset_arcsec REAL,
    dec_offset_arcsec REAL,
    flux_ratio REAL,
    created_at TEXT
);
```

**Notes**:

- Cross-matching is enabled by default (NVSS + RACS) but can be disabled for
  speed or sandbox runs
- RACS strip resolution tolerates filenames up to ±6° from the requested
  declination to match the 12° strip width produced by `build_rax_strip_db`
- Results are used for QA validation, catalog comparisons, and systematic error
  characterization

---

### Flux Scale Validation

**Purpose**: Validate DSA-110 flux calibration against reference catalogs

**Catalogs Used**: NVSS (primary, 1.4 GHz), VLASS (3 GHz), RACS (888 MHz)

**Implementation**: `qa/catalog_validation.py`

**Workflow**:

1. Extract sources from DSA-110 image
2. Cross-match with reference catalog (NVSS/VLASS)
3. Calculate flux ratio distribution (DSA-110 / catalog)
4. Compute median, MAD, and outlier fraction
5. Flag systematic flux scale errors (>20% deviation)

**Example**:

```python
from dsa110_contimg.qa.catalog_validation import validate_flux_scale

validation = validate_flux_scale(
    image_path="/path/to/mosaic.fits",
    catalog="nvss",
    min_snr=5.0,
    match_radius_arcsec=10.0
)
# Returns: {
#     "median_ratio": 0.98,
#     "mad_ratio": 0.15,
#     "n_matches": 127,
#     "outlier_fraction": 0.08,
#     "systematic_offset": -0.02,
#     "validation_status": "pass"
# }
```

**Catalog Frequencies**:

- NVSS: 1.4 GHz (matches DSA-110 closely)
- VLASS: 3.0 GHz (requires spectral index correction)
- RACS: 888 MHz (requires spectral index correction)
- ATNF: 1.4 GHz (but time-variable, flux mismatches expected)

**Spectral Index Correction**:

```python
# If using VLASS (3 GHz) to validate DSA-110 (1.4 GHz):
# Assume S ∝ ν^α, where α is spectral index (typically -0.7 for radio sources)
catalog_flux_corrected = catalog_flux_3ghz * (1.4 / 3.0)**alpha
```

**QA Thresholds**:

- Median flux ratio: 0.8 - 1.2 (±20%)
- MAD: < 0.3 (30% scatter)
- Outlier fraction: < 0.15 (15%)

**Notes**:

- NVSS preferred for flux validation (same frequency as DSA-110)
- VLASS useful for spectral index studies (1.4 GHz and 3 GHz)
- ATNF flux mismatches expected (pulsars are time-variable)

---

### Source Classification

**Purpose**: Classify detected sources using multi-wavelength information

**Catalogs Used**: Gaia (stars), SIMBAD (all types), NED (extragalactic), ATNF
(pulsars)

**Implementation**: `photometry/source.py`, `catalog/multiwavelength.py`

**Workflow**:

1. Detect source in DSA-110 image
2. Query multi-wavelength catalogs (Gaia, SIMBAD, NED, ATNF)
3. Check for matches within search radius (typically 5-15")
4. Classify based on nearest match:
   - Gaia match :arrow_right: likely stellar contamination
   - SIMBAD "QSO" :arrow_right: quasar
   - NED match with z > 0 :arrow_right: extragalactic
   - ATNF match :arrow_right: pulsar
5. Store classification in source database

**Example**:

```python
from dsa110_contimg.photometry.source import query_external_catalogs

classifications = query_external_catalogs(
    ra=123.456,
    dec=12.345,
    catalogs=["Gaia", "Simbad", "ATNF", "NED"],
    radius_arcsec=10.0
)
# Returns: {
#     "Gaia": {"GaiaDR3_12345": 2.3*u.arcsec},
#     "Simbad": {"3C 273": 1.8*u.arcsec},
#     "NED": {},
#     "ATNF": {}
# }
```

**Classification Logic**:

```python
if gaia_matches:
    classification = "star"  # Flag as stellar contamination
elif atnf_matches:
    classification = "pulsar"
elif simbad_matches and simbad_type == "QSO":
    classification = "quasar"
elif ned_matches and redshift > 0:
    classification = "galaxy"
else:
    classification = "unknown"
```

**API Integration**:

```bash
# Query external catalogs for a source
curl "http://localhost:8000/api/sources/12345/external?catalogs=simbad,ned,gaia"
```

**Notes**:

- Gaia matches important for flagging stellar contamination
- SIMBAD provides comprehensive object types
- NED specializes in extragalactic sources (redshifts)
- ATNF critical for pulsar identification

---

## Database Structure

### SQLite Strip Databases

**Purpose**: Fast cone searches within declination strips

**File Naming Convention**:

- NVSS: `nvss_dec{declination:+.1f}.sqlite3` (e.g., `nvss_dec+30.0.sqlite3`)
- FIRST: `first_dec{declination:+.1f}.sqlite3`
- RACS: `rax_dec{declination:+.1f}.sqlite3`
- ATNF: `atnf_dec{declination:+.1f}.sqlite3`

**Standard Location**: `state/catalogs/`

**Table Schema** (per-catalog):

```sql
CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_mjy REAL,
    maj_arcsec REAL,  -- Optional (NVSS, FIRST)
    min_arcsec REAL,  -- Optional (NVSS, FIRST)
    -- Catalog-specific columns...
);

CREATE INDEX idx_position ON sources(dec_deg, ra_deg);
CREATE INDEX idx_flux ON sources(flux_mjy DESC);
```

**Query Example**:

```python
from dsa110_contimg.catalog.query import query_sources

sources = query_sources(
    catalog_type="nvss",
    ra_center=123.456,
    dec_center=12.345,
    radius_deg=1.0
)
# Returns pandas DataFrame with sources
```

**Declination Strip Width**: ±0.5° (1.0° total width)

**Automatic Resolution**:

1. Check explicit path (if provided)
2. Check environment variable (e.g., `NVSS_CATALOG`)
3. Check per-declination SQLite database
4. Check nearest declination match (within 1.0° tolerance)
5. Fall back to Vizier queries (slower)

---

### Cross-Match Database Table

**Database**: `state/db/products.sqlite3`

**Table**: `cross_matches`

**Schema**:

```sql
CREATE TABLE cross_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,  -- DSA-110 source ID (from photometry)
    catalog_type TEXT NOT NULL,  -- "nvss", "first", "rax", "vlass", "atnf"
    catalog_id TEXT,  -- Catalog source ID (if available)
    master_catalog_id TEXT,  -- Master catalog ID (if linked)
    ra_catalog REAL,  -- Catalog source RA (degrees)
    dec_catalog REAL,  -- Catalog source Dec (degrees)
    separation_arcsec REAL,  -- Angular separation
    match_quality TEXT,  -- "unique", "ambiguous", "none"
    flux_catalog_mjy REAL,  -- Catalog flux
    flux_ratio REAL,  -- DSA-110 flux / catalog flux
    flux_ratio_err REAL,  -- Flux ratio uncertainty
    ra_offset_arcsec REAL,  -- RA offset (DSA - catalog)
    dec_offset_arcsec REAL,  -- Dec offset (DSA - catalog)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cross_matches_source ON cross_matches(source_id);
CREATE INDEX idx_cross_matches_catalog ON cross_matches(catalog_type);
CREATE INDEX idx_cross_matches_quality ON cross_matches(match_quality);
CREATE INDEX idx_cross_matches_created ON cross_matches(created_at);
CREATE INDEX idx_cross_matches_master ON cross_matches(master_catalog_id);
```

**Match Quality Values**:

- `"unique"`: Single unambiguous match
- `"ambiguous"`: Multiple potential matches within radius
- `"none"`: No match found

**Usage**:

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect("state/db/products.sqlite3")
matches = pd.read_sql_query(
    "SELECT * FROM cross_matches WHERE catalog_type='nvss' AND match_quality='unique'",
    conn
)
```

---

## API Reference

### Query Functions

**Location**: `catalog/query.py`

#### `query_sources()`

Query a catalog for sources near a position.

```python
def query_sources(
    catalog_type: str,
    ra_center: float,
    dec_center: float,
    radius_deg: float,
    min_flux_mjy: Optional[float] = None,
    explicit_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Args:
        catalog_type: One of "nvss", "first", "rax", "vlass", "master", "atnf"
        ra_center: Center RA in degrees
        dec_center: Center declination in degrees
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux threshold (optional)
        explicit_path: Override catalog path (optional)

    Returns:
        DataFrame with columns: ra_deg, dec_deg, flux_mjy, [maj_arcsec, min_arcsec]
    """
```

**Example**:

```python
from dsa110_contimg.catalog.query import query_sources

sources = query_sources(
    catalog_type="nvss",
    ra_center=123.456,
    dec_center=12.345,
    radius_deg=1.0,
    min_flux_mjy=5.0  # Only sources > 5 mJy
)
```

#### `resolve_catalog_path()`

Resolve path to catalog database using standard precedence.

```python
def resolve_catalog_path(
    catalog_type: str,
    dec_strip: Optional[float] = None,
    explicit_path: Optional[str] = None
) -> Path:
    """
    Precedence:
    1. Explicit path (highest priority)
    2. Environment variable (e.g., NVSS_CATALOG)
    3. Per-declination SQLite database
    4. Nearest declination match (within 1.0° tolerance)

    Raises:
        FileNotFoundError: If no catalog found
    """
```

---

### Cross-Match Functions

**Location**: `catalog/crossmatch.py`

#### `cross_match_sources()`

Perform basic nearest-neighbor cross-matching.

```python
def cross_match_sources(
    detected_ra: np.ndarray,
    detected_dec: np.ndarray,
    catalog_ra: np.ndarray,
    catalog_dec: np.ndarray,
    radius_arcsec: float = 10.0,
    detected_flux: Optional[np.ndarray] = None,
    catalog_flux: Optional[np.ndarray] = None,
    detected_flux_err: Optional[np.ndarray] = None,
    catalog_flux_err: Optional[np.ndarray] = None,
    detected_ids: Optional[np.ndarray] = None,
    catalog_ids: Optional[np.ndarray] = None
) -> pd.DataFrame:
    """
    Returns DataFrame with columns:
        - detected_idx: Index in detected arrays
        - catalog_idx: Index in catalog arrays
        - separation_arcsec: Angular separation
        - flux_ratio: detected_flux / catalog_flux (if fluxes provided)
        - flux_ratio_err: Propagated uncertainty
    """
```

#### `multi_catalog_match()`

Find best match across multiple catalogs.

```python
def multi_catalog_match(
    detected_ra: np.ndarray,
    detected_dec: np.ndarray,
    catalog_data: Dict[str, Dict[str, np.ndarray]],
    radius_arcsec: float = 10.0
) -> pd.DataFrame:
    """
    Args:
        catalog_data: Dictionary mapping catalog names to data dictionaries
            {
                "nvss": {"ra": [...], "dec": [...], "flux": [...], "id": [...]},
                "first": {"ra": [...], "dec": [...], "flux": [...], "id": [...]},
                ...
            }

    Returns DataFrame with columns:
        - detected_idx: Index in detected arrays
        - best_catalog: Catalog with closest match
        - catalog_id: Source ID in best catalog
        - separation_arcsec: Separation to best match
        - n_catalogs_matched: Number of catalogs with matches
    """
```

#### `calculate_positional_offsets()`

Calculate astrometric offset statistics.

```python
def calculate_positional_offsets(
    matches_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Returns dictionary with:
        - median_ra_offset_arcsec: Median RA offset
        - median_dec_offset_arcsec: Median Dec offset
        - mad_ra_arcsec: MAD of RA offsets
        - mad_dec_arcsec: MAD of Dec offsets
        - rms_offset_arcsec: RMS positional offset
        - n_matches: Number of matches used
    """
```

#### `calculate_flux_scale()`

Calculate flux scale statistics.

```python
def calculate_flux_scale(
    matches_df: pd.DataFrame
) -> Dict[str, float]:
    """
    Returns dictionary with:
        - median_flux_ratio: Median DSA-110/catalog flux ratio
        - mad_flux_ratio: MAD of flux ratios
        - systematic_offset: log10(median_ratio)
        - outlier_fraction: Fraction of >3σ outliers
        - n_matches: Number of matches used
    """
```

---

### Multi-wavelength Functions

**Location**: `catalog/multiwavelength.py`

All functions follow the same signature:

```python
def check_{catalog}(
    source: SkyCoord,
    t: Optional[Time] = None,  # Required for proper motion corrections
    radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, u.Quantity]:
    """
    Returns dictionary mapping source names to separations:
        {"3C 273": 1.8*u.arcsec, "NGC 1234": 5.2*u.arcsec, ...}

    Returns empty dict if no matches or query error.
    """
```

**Available Functions**:

- `check_gaia()`: Gaia DR3 (with proper motion)
- `check_simbad()`: SIMBAD (with proper motion)
- `check_atnf()`: ATNF pulsars (with proper motion)
- `check_pulsarscraper()`: Pulsar Scraper API
- `check_nvss()`: NVSS (local DB preferred)
- `check_first()`: FIRST via Vizier
- `check_vlass()`: VLASS (local DB preferred)
- `check_tgss()`: TGSS via Vizier
- `check_milliquas()`: MilliQuas via Vizier
- `check_wiseagn()`: WISE AGN via Vizier
- `check_lqac()`: LQAC via Vizier
- `check_sdssqso()`: SDSS QSO via Vizier

**Comprehensive Check**:

```python
def check_all_services(
    source: SkyCoord,
    t: Optional[Time] = None,
    radius: u.Quantity = 15 * u.arcsec
) -> Dict[str, Dict[str, u.Quantity]]:
    """
    Query all available catalogs and return nested dictionary:
    {
        "Gaia": {"GaiaDR3_12345": 2.3*u.arcsec, ...},
        "Simbad": {"3C 273": 1.8*u.arcsec, ...},
        "ATNF": {"J1234+1234": 5.1*u.arcsec, ...},
        ...
    }
    """
```

---

### External Catalog Functions

**Location**: `catalog/external.py`

Simplified interfaces returning structured dictionaries.

#### `simbad_search()`

```python
def simbad_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0,
    timeout: float = 30.0
) -> Optional[Dict[str, any]]:
    """
    Returns dictionary with keys:
        - main_id: Primary identifier
        - otype: Object type ("Radio", "QSO", "Star", etc.)
        - ra, dec: Position (degrees)
        - separation_arcsec: Distance from query
        - flux_v: V-band magnitude
        - redshift: Redshift (if available)
        - names: List of alternative names
        - bibcode: Bibliographic reference
    """
```

#### `ned_search()`

```python
def ned_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0,
    timeout: float = 30.0
) -> Optional[Dict[str, any]]:
    """
    Returns dictionary with keys:
        - ned_name: NED object name
        - object_type: Object classification
        - ra, dec: Position (degrees)
        - separation_arcsec: Distance from query
        - redshift: Redshift value
        - redshift_type: Redshift type ('z', 'v', 'q')
        - velocity: Recession velocity (km/s)
        - distance: Distance (Mpc)
        - magnitude: Optical magnitude
        - flux_1_4ghz: 1.4 GHz flux (mJy)
    """
```

#### `gaia_search()`

```python
def gaia_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0,
    timeout: float = 30.0
) -> Optional[Dict[str, any]]:
    """
    Returns dictionary with keys:
        - gaia_id: Gaia DR3 source ID
        - ra, dec: Position (degrees)
        - separation_arcsec: Distance from query
        - pmra, pmdec: Proper motion (mas/yr)
        - parallax: Parallax (mas)
        - g_mag: G-band magnitude
        - bp_mag, rp_mag: Blue/red photometer magnitudes
    """
```

#### `search_all_external()`

```python
def search_all_external(
    coord: SkyCoord,
    radius_arcsec: float = 5.0,
    timeout: float = 30.0
) -> Dict[str, Optional[Dict[str, any]]]:
    """
    Query all external catalogs (SIMBAD, NED, Gaia) at once.

    Returns:
        {
            "simbad": {...} or None,
            "ned": {...} or None,
            "gaia": {...} or None
        }
    """
```

---

## Building Catalog Databases

### Prerequisites

```bash
# Install required packages
conda activate casa6
pip install psrqpy  # For ATNF
pip install astroquery  # For Vizier/SIMBAD/NED/Gaia queries
```

### Building NVSS Database

```bash
# Single declination strip
python -m dsa110_contimg.catalog.build_nvss_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/nvss_dec+30.0.sqlite3 \
    --min-flux-mjy 2.5

# Multiple strips (batch)
for dec in -10 0 10 20 30 40; do
    python -m dsa110_contimg.catalog.build_nvss_strip_cli \
        --dec-center $dec \
        --dec-width 1.0 \
        --output state/catalogs/nvss_dec+${dec}.0.sqlite3
done
```

**Options**:

- `--dec-center`: Center declination (degrees)
- `--dec-width`: Strip width (degrees, default: 1.0)
- `--output`: Output database path
- `--min-flux-mjy`: Minimum flux threshold (mJy)
- `--force`: Overwrite existing database

---

### Building FIRST Database

```bash
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/first_dec+30.0.sqlite3 \
    --cache-dir .cache/catalogs
```

**Options** (same as NVSS, plus):

- `--cache-dir`: Directory for caching downloaded FIRST catalog
- `--first-catalog-path`: Explicit path to FIRST catalog (CSV/FITS)

**Notes**:

- Automatically downloads FIRST catalog from Vizier if not found
- Coverage warnings issued for Dec < -40°

---

### Building RACS (RAX) Database

```bash
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --dec-center -20.0 \
    --dec-width 1.0 \
    --output state/catalogs/rax_dec-20.0.sqlite3
```

**Notes**:

- Best for southern declinations (Dec < +41°)
- Automatic download/caching from Vizier

---

### Building ATNF Database

**All-sky database** (recommended):

```bash
python -m dsa110_contimg.catalog.build_atnf_pulsars \
    --output state/catalogs/atnf_pulsars.sqlite3 \
    --min-flux-mjy 1.0 \
    --force
```

**Declination strip** (for compatibility with other catalogs):

```bash
python -m dsa110_contimg.catalog.build_atnf_strip_cli \
    --dec-center 30.0 \
    --dec-width 1.0 \
    --output state/catalogs/atnf_dec+30.0.sqlite3 \
    --min-flux-mjy 1.0
```

**Options**:

- `--min-flux-mjy`: Minimum 1400 MHz flux (mJy, default: 1.0)
- `--force`: Overwrite existing database

**See Also**: `catalog/ATNF_USAGE.md` for comprehensive ATNF guide

---

### Building All Catalogs

**Script** (create `scripts/build_all_catalogs.sh`):

```bash
#!/bin/bash
# Build catalog databases for all declination strips

CATALOG_DIR="state/catalogs"
mkdir -p "$CATALOG_DIR"

# Declination range for DSA-110 observations
# (adjust based on your actual observing range)
for dec in $(seq -30 5 70); do
    echo "Building catalogs for Dec = $dec°..."

    # NVSS (Dec > -40°)
    if [ $dec -gt -40 ]; then
        python -m dsa110_contimg.catalog.build_nvss_strip_cli \
            --dec-center $dec \
            --dec-width 1.0 \
            --output "$CATALOG_DIR/nvss_dec${dec}.0.sqlite3"
    fi

    # FIRST (Dec > -40°)
    if [ $dec -gt -40 ]; then
        python -m dsa110_contimg.catalog.build_first_strip_cli \
            --dec-center $dec \
            --dec-width 1.0 \
            --output "$CATALOG_DIR/first_dec${dec}.0.sqlite3"
    fi

    # RACS (Dec < +41°)
    if [ $dec -lt 41 ]; then
        python -m dsa110_contimg.catalog.build_rax_strip_cli \
            --dec-center $dec \
            --dec-width 1.0 \
            --output "$CATALOG_DIR/rax_dec${dec}.0.sqlite3"
    fi

    # ATNF (all declinations)
    python -m dsa110_contimg.catalog.build_atnf_strip_cli \
        --dec-center $dec \
        --dec-width 1.0 \
        --output "$CATALOG_DIR/atnf_dec${dec}.0.sqlite3"
done

# Build all-sky ATNF database
python -m dsa110_contimg.catalog.build_atnf_pulsars \
    --output "$CATALOG_DIR/atnf_pulsars.sqlite3"

echo "Catalog building complete!"
```

**Run**:

```bash
chmod +x scripts/build_all_catalogs.sh
./scripts/build_all_catalogs.sh
```

---

### Catalog Coverage Limits

Automatic coverage warnings are issued when building databases outside coverage
limits:

```python
CATALOG_COVERAGE_LIMITS = {
    "nvss": {"dec_min": -40.0, "dec_max": 90.0},
    "first": {"dec_min": -40.0, "dec_max": 90.0},
    "rax": {"dec_min": -90.0, "dec_max": 41.0},
    "vlass": {"dec_min": -40.0, "dec_max": 90.0},
    "atnf": {"dec_min": -90.0, "dec_max": 90.0},  # All-sky
}
```

---

## Best Practices

### Catalog Selection

**For Calibrator Selection**:

1. Use NVSS as primary (excellent coverage Dec > -40°, well-characterized)
2. Use FIRST for high-resolution astrometry (5" vs 45")
3. Use RACS for southern observations (Dec < +41°)

**For Cross-Matching**:

1. Query multiple catalogs (NVSS + FIRST + RACS)
2. Use `multi_catalog_match()` to find best match across all
3. Prefer higher-resolution catalogs (FIRST > NVSS) when available

**For Flux Validation**:

1. Use NVSS as primary reference (1.4 GHz, close to DSA-110)
2. Use VLASS for spectral index studies (3 GHz)
3. Avoid ATNF for flux validation (pulsars time-variable)

**For Source Classification**:

1. Always check Gaia first (flag stellar contamination)
2. Use SIMBAD for general object types
3. Use NED for extragalactic sources (redshifts)
4. Use ATNF for pulsar identification

---

### Database Management

**Storage Recommendations**:

- Each declination strip: ~5-50 MB (varies by catalog and strip width)
- Total for full declination range (-30° to +70°): ~2-10 GB
- Store in `state/catalogs/` for automatic resolution

**Environment Variables**:

```bash
# Override catalog locations
export NVSS_CATALOG=/data/catalogs/nvss_full.sqlite3
export FIRST_CATALOG=/data/catalogs/first_full.sqlite3
export ATNF_CATALOG=/data/catalogs/atnf_pulsars.sqlite3
```

**Rebuild Frequency**:

- NVSS/FIRST: Static (no updates needed)
- RACS: Occasionally (survey ongoing, infrequent updates)
- VLASS: Occasionally (survey ongoing)
- ATNF: Monthly/quarterly (actively maintained, new pulsars added)
- Gaia/SIMBAD/NED: Real-time via API (no local databases)

---

### Performance Optimization

**Use Local SQLite Databases**:

```python
# Fast (local database)
sources = query_sources("nvss", ra_center=123.456, dec_center=12.345, radius_deg=1.0)

# Slow (Vizier query over internet)
from dsa110_contimg.catalog.multiwavelength import check_nvss
matches = check_nvss(coord, radius=1.0*u.deg)  # Falls back to Vizier if no local DB
```

**Batch Queries**:

```python
# Query once and reuse results
nvss_sources = query_sources("nvss", ra_center, dec_center, radius_deg=2.0)
first_sources = query_sources("first", ra_center, dec_center, radius_deg=2.0)

# Now cross-match all detected sources against cached catalog results
for detected_source in detected_sources:
    matches = cross_match_sources(
        detected_ra=[detected_source["ra"]],
        detected_dec=[detected_source["dec"]],
        catalog_ra=nvss_sources["ra_deg"].values,
        catalog_dec=nvss_sources["dec_deg"].values,
        radius_arcsec=10.0
    )
```

**Index Usage**:

- SQLite databases have spatial indices on `(dec_deg, ra_deg)`
- Queries automatically use indices for fast cone searches
- Flux indices enable fast bright source queries

---

### Error Handling

**Missing Catalogs**:

```python
from dsa110_contimg.catalog.query import query_sources

try:
    sources = query_sources("nvss", ra_center, dec_center, radius_deg=1.0)
except FileNotFoundError:
    logger.warning("NVSS catalog not found, falling back to Vizier")
    from dsa110_contimg.catalog.multiwavelength import check_nvss
    matches = check_nvss(coord, radius=1.0*u.deg)
```

**API Timeouts**:

```python
from dsa110_contimg.catalog.external import simbad_search

result = simbad_search(coord, radius_arcsec=5.0, timeout=30.0)
if result is None:
    logger.warning("SIMBAD query failed or timed out")
    # Proceed without SIMBAD classification
```

**Coverage Limits**:

```python
# Automatic warnings for out-of-coverage queries
sources = query_sources("first", ra_center=123.456, dec_center=-50.0, radius_deg=1.0)
# WARNING: Declination -50.0° is outside FIRST coverage (southern limit: -40.0°)
# Database may be empty or have very few sources.
```

---

### Testing

**Verify Catalog Installation**:

```python
from dsa110_contimg.catalog.query import query_sources

# Test NVSS
nvss = query_sources("nvss", ra_center=123.456, dec_center=12.345, radius_deg=0.5)
print(f"NVSS: {len(nvss)} sources found")

# Test FIRST
first = query_sources("first", ra_center=123.456, dec_center=12.345, radius_deg=0.5)
print(f"FIRST: {len(first)} sources found")

# Test ATNF
atnf = query_sources("atnf", ra_center=123.456, dec_center=12.345, radius_deg=1.0)
print(f"ATNF: {len(atnf)} pulsars found")
```

**Test External APIs**:

```python
from dsa110_contimg.catalog.external import search_all_external
from astropy.coordinates import SkyCoord
import astropy.units as u

# Test known source (e.g., 3C 273)
coord = SkyCoord(ra=187.2779*u.deg, dec=2.0525*u.deg)
results = search_all_external(coord, radius_arcsec=10.0)

print(f"SIMBAD: {results['simbad']['main_id'] if results['simbad'] else 'No match'}")
print(f"NED: {results['ned']['ned_name'] if results['ned'] else 'No match'}")
print(f"Gaia: {results['gaia']['gaia_id'] if results['gaia'] else 'No match'}")
```

---

## Troubleshooting

### Common Issues

**Q: Catalog queries return no results**

A: Check:

1. Declination coverage (FIRST/NVSS require Dec > -40°)
2. Database exists: `ls state/catalogs/nvss_dec*.sqlite3`
3. Declination strip matches observation (within 1.0° tolerance)
4. Search radius appropriate (try increasing `radius_deg`)

**Q: ATNF database build fails**

A: Ensure `psrqpy` installed:

```bash
pip install psrqpy
python -c "import psrqpy; print('psrqpy OK')"
```

**Q: External catalog queries timeout**

A: Check:

1. Internet connection active
2. Increase timeout: `simbad_search(coord, timeout=60.0)`
3. Check astroquery services: https://astroquery.readthedocs.io/

**Q: Flux validation fails (large systematic offset)**

A: Check:

1. Catalog frequency matches DSA-110 (NVSS at 1.4 GHz best)
2. Flux units consistent (mJy in all databases)
3. Sufficient matches (need >20 for reliable statistics)
4. Not using ATNF for flux validation (pulsars time-variable)

---

## Related Documentation

- **ATNF_USAGE.md**: Comprehensive ATNF pulsar catalog guide
- **README_PIPELINE_DOCUMENTATION.md**: Pipeline overview (mentions
  cross-matching)
- **qa/catalog_validation.py**: Flux scale validation implementation
- **calibration/selection.py**: Calibrator selection implementation
- **photometry/source.py**: Source classification implementation

---

## Version History

- **v1.0** (2025-11-19): Initial comprehensive catalog documentation

---

## Support

For questions or issues:

1. Check this documentation first
2. Review code docstrings in `catalog/` modules
3. See `catalog/ATNF_USAGE.md` for ATNF-specific questions
4. Check integration tests in `tests/integration/catalog/`
