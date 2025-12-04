# Lightcurve Generation & ESE Detection Guide

**Purpose:** Concise, actionable guide for generating lightcurves for many sources and detecting Extreme Scattering Events (ESEs) using the DSA-110 continuum imaging pipeline.

**Last Updated:** December 4, 2025

---

## Quick Reference

```bash
# Environment
conda activate casa6
cd /data/dsa110-contimg/backend

# Key database
DB=/data/dsa110-contimg/state/db/pipeline.sqlite3
```

---

## 1. Pipeline Overview: Raw Data → Lightcurves → ESE

```
UVH5 files → MS → Calibration → Images → Photometry → Variability Stats → ESE Detection
     ↓                                        ↓                 ↓              ↓
/data/incoming                          FITS images      photometry table   ese_candidates table
```

**Key tables in `pipeline.sqlite3`:**

- `photometry` - Individual flux measurements (source, image, flux, error, MJD)
- `variability_stats` - Aggregated statistics per source (mean, std, χ²/ν, σ_deviation, η)
- `ese_candidates` - Flagged ESE candidates (source_id, significance, status)

---

## 2. Step 1: Run Photometry on Images

### Option A: Single Image (Interactive)

```bash
# Measure all NVSS sources in image field-of-view
python -m dsa110_contimg.photometry.cli nvss \
    --fits /stage/dsa110-contimg/images/observation.pbcor.fits \
    --min-mjy 10.0 \
    --products-db $DB
```

### Option B: Batch Photometry (Many Sources × Many Images)

```bash
# Create source list CSV (columns: name, ra, dec)
cat > sources.csv << EOF
name,ra,dec
3C286,202.784,30.509
J1331+3030,202.785,30.509
EOF

# Run batch photometry across all images
python -m dsa110_contimg.photometry.cli batch \
    --source-list sources.csv \
    --image-dir /stage/dsa110-contimg/images/ \
    --output photometry_results.csv \
    --products-db $DB
```

### Option C: Mosaic Photometry (Wide-Field)

```python
from pathlib import Path
from dsa110_contimg.photometry.manager import PhotometryManager, PhotometryConfig

manager = PhotometryManager(
    products_db_path=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
)

config = PhotometryConfig(
    catalog="nvss",        # or "first", "master"
    radius_deg=1.5,        # Search radius
    min_flux_mjy=5.0,      # Flux threshold
    detect_ese=True,       # Auto-run ESE detection
)

result = manager.measure_for_fits(
    fits_path=Path("/stage/dsa110-contimg/mosaics/mosaic.fits"),
    config=config,
)
print(f"Measured {result.measurements_successful} sources")
```

---

## 3. Step 2: Export Lightcurve Data

### CLI Export

```bash
# Export JSON lightcurve for a source
python -m dsa110_contimg.photometry.cli export \
    --source-id "NVSS J123456+420312" \
    --format json \
    --output lightcurve.json \
    --products-db $DB

# Export CSV format
python -m dsa110_contimg.photometry.cli export \
    --source-id "NVSS J123456+420312" \
    --format csv \
    --output lightcurve.csv
```

### Python API

```python
from dsa110_contimg.photometry.source import Source
from pathlib import Path

# Load source with all measurements
source = Source(
    source_id="NVSS J123456+420312",
    products_db=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
)

# Get measurements DataFrame
df = source.measurements
print(df[['mjd', 'peak_jyb', 'peak_err_jyb', 'normalized_flux_jy']])

# Plot lightcurve
fig = source.plot_lightcurve(
    use_normalized=True,
    highlight_ese_period=True,
    save=True,
    outfile="lightcurve.png"
)
```

---

## 4. Step 3: Compute Variability Statistics

Variability stats are auto-computed during ESE detection, but can be updated explicitly:

```python
from dsa110_contimg.photometry.ese_pipeline import update_variability_stats_for_source
from dsa110_contimg.database import ensure_products_db
from pathlib import Path

db_path = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
conn = ensure_products_db(db_path)

# Update stats for one source
update_variability_stats_for_source(conn, "NVSS J123456+420312", products_db=db_path)
conn.commit()
conn.close()
```

**Key metrics computed:**
| Metric | Description | ESE Relevance |
|--------|-------------|---------------|
| `mean_flux_mjy` | Mean flux across epochs | Baseline |
| `std_flux_mjy` | Standard deviation | Variability amplitude |
| `chi2_nu` | Reduced chi-squared | Significance of variability |
| `sigma_deviation` | Max deviation in σ units | **Primary ESE threshold** |
| `eta_metric` | Weighted variance (VAST) | Complementary metric |

---

## 5. Step 4: Detect ESE Candidates

### CLI Detection

```bash
# Conservative threshold (5σ)
python -m dsa110_contimg.photometry.cli ese-detect \
    --preset conservative \
    --products-db $DB

# Sensitive threshold (3σ)
python -m dsa110_contimg.photometry.cli ese-detect \
    --preset sensitive \
    --products-db $DB

# Custom threshold with composite scoring
python -m dsa110_contimg.photometry.cli ese-detect \
    --min-sigma 4.0 \
    --use-composite-scoring \
    --products-db $DB

# Check specific source
python -m dsa110_contimg.photometry.cli ese-detect \
    --source-id "NVSS J123456+420312" \
    --recompute \
    --products-db $DB
```

### Python API

```python
from dsa110_contimg.photometry.ese_detection import detect_ese_candidates
from pathlib import Path

candidates = detect_ese_candidates(
    products_db=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
    min_sigma=5.0,
    recompute=True,
    use_composite_scoring=True,
)

for c in candidates:
    print(f"{c['source_id']}: σ={c['significance']:.1f}, χ²/ν={c.get('chi2_nu', 0):.2f}")
```

### Auto-Detection After New Measurements

```python
from dsa110_contimg.photometry.ese_pipeline import auto_detect_ese_for_new_measurements
from pathlib import Path

# Called automatically by PhotometryManager when detect_ese=True
candidate = auto_detect_ese_for_new_measurements(
    products_db=Path("/data/dsa110-contimg/state/db/pipeline.sqlite3"),
    source_id="NVSS J123456+420312",
    min_sigma=5.0,
)

if candidate:
    print(f"ESE candidate detected: {candidate}")
```

---

## 6. Query Results from Database

### SQL Queries

```sql
-- List all ESE candidates (active)
SELECT e.source_id, e.significance, v.chi2_nu, v.eta_metric, v.n_obs
FROM ese_candidates e
JOIN variability_stats v ON e.source_id = v.source_id
WHERE e.status = 'active'
ORDER BY e.significance DESC;

-- Get lightcurve for a source
SELECT mjd, peak_jyb, peak_err_jyb, image_path
FROM photometry
WHERE source_id = 'NVSS J123456+420312'
ORDER BY mjd;

-- Find highly variable sources (not yet flagged)
SELECT source_id, sigma_deviation, chi2_nu, eta_metric, n_obs
FROM variability_stats
WHERE sigma_deviation >= 3.0 AND n_obs >= 10
ORDER BY sigma_deviation DESC
LIMIT 50;
```

### Run queries:

```bash
sqlite3 $DB "SELECT * FROM ese_candidates WHERE status='active';"
```

---

## 7. REST API Endpoints

| Endpoint                           | Method | Description                |
| ---------------------------------- | ------ | -------------------------- |
| `/api/v1/sources/{id}/lightcurve`  | GET    | Get lightcurve data points |
| `/api/v1/sources/{id}/variability` | GET    | Get variability analysis   |
| `/api/ese/candidates`              | GET    | List ESE candidates        |

```bash
# Get lightcurve via API
curl "http://localhost:8000/api/v1/sources/NVSS%20J123456%2B420312/lightcurve"

# Get ESE candidates
curl "http://localhost:8000/api/ese/candidates"
```

---

## 8. Visualization

### Lightcurve Plots

```python
from dsa110_contimg.visualization import plot_lightcurve, FigureConfig, PlotStyle
import numpy as np
from astropy.time import Time

# Basic plot
fig = plot_lightcurve(
    flux=np.array([1.2, 1.3, 0.8, 1.1]),
    times=Time([60000, 60001, 60002, 60003], format='mjd'),
    errors=np.array([0.1, 0.1, 0.1, 0.1]),
    config=FigureConfig(style=PlotStyle.PUBLICATION),
    title="3C286 Lightcurve",
    output="3c286_lightcurve.pdf"
)
```

### Source Analysis

```python
from dsa110_contimg.photometry.source import Source
from pathlib import Path

source = Source("NVSS J123456+420312", products_db=Path(DB))

# Plot with ESE features
source.plot_lightcurve(
    highlight_baseline=True,      # Mark first 10 epochs
    highlight_ese_period=True,    # Mark 14-180 day window
    save=True,
    outfile="ese_candidate.png"
)

# Get relative lightcurve using stable neighbors
relative = source.calculate_relative_lightcurve(
    radius_deg=0.5,
    max_eta=1.5,     # Exclude variable neighbors
    min_neighbors=3
)
```

---

## 9. ESE Detection Thresholds

| Preset         | σ_min | Use Case                        |
| -------------- | ----- | ------------------------------- |
| `conservative` | 5.0   | Production, low false positives |
| `moderate`     | 3.5   | Balanced                        |
| `sensitive`    | 3.0   | Research, more candidates       |

**Physical context:**

- ESE timescales: weeks to months (30-90 days typical)
- Flux variation: 10-50%, can reach 2-3× baseline
- DSA-110 cadence: ~5 min per MS, multiple epochs per day

---

## 10. Bulk Processing Workflow

### End-to-End Script

```python
#!/opt/miniforge/envs/casa6/bin/python
"""Batch lightcurve generation and ESE detection."""

from pathlib import Path
from glob import glob
from dsa110_contimg.photometry.manager import PhotometryManager, PhotometryConfig
from dsa110_contimg.photometry.ese_detection import detect_ese_candidates

DB = Path("/data/dsa110-contimg/state/db/pipeline.sqlite3")
IMAGE_DIR = Path("/stage/dsa110-contimg/images")

# 1. Initialize manager
manager = PhotometryManager(products_db_path=DB)
config = PhotometryConfig(
    catalog="nvss",
    min_flux_mjy=10.0,
    detect_ese=False,  # We'll run detection separately
)

# 2. Process all images
for fits_path in sorted(IMAGE_DIR.glob("*.pbcor.fits")):
    print(f"Processing {fits_path.name}")
    result = manager.measure_for_fits(fits_path, config=config)
    print(f"  → {result.measurements_successful} sources measured")

# 3. Run ESE detection on all sources
candidates = detect_ese_candidates(
    products_db=DB,
    min_sigma=5.0,
    recompute=True,
    use_composite_scoring=True,
)

print(f"\n=== ESE Candidates: {len(candidates)} ===")
for c in candidates:
    print(f"  {c['source_id']}: σ={c['significance']:.1f}")
```

---

## 11. Troubleshooting

| Issue                   | Solution                                    |
| ----------------------- | ------------------------------------------- |
| "No sources found"      | Check catalog path, increase `radius_deg`   |
| Empty variability_stats | Run `ese-detect --recompute`                |
| Low n_obs               | Need more images processed                  |
| Database locked         | Check for other processes, increase timeout |

```bash
# Check photometry count
sqlite3 $DB "SELECT COUNT(*) FROM photometry;"

# Check variability stats
sqlite3 $DB "SELECT COUNT(*) FROM variability_stats WHERE n_obs >= 5;"

# Debug catalog resolution
python -c "from dsa110_contimg.catalog.query import resolve_catalog_path; print(resolve_catalog_path('nvss', dec_strip=55.0))"
```

---

## Files Reference

| File                          | Purpose                                                         |
| ----------------------------- | --------------------------------------------------------------- |
| `photometry/cli.py`           | CLI commands (nvss, batch, ese-detect, export)                  |
| `photometry/manager.py`       | PhotometryManager class                                         |
| `photometry/ese_detection.py` | Core ESE detection logic                                        |
| `photometry/ese_pipeline.py`  | Auto-detection integration                                      |
| `photometry/variability.py`   | Variability metrics (η, Vs, m)                                  |
| `photometry/source.py`        | Source class with lightcurve plotting                           |
| `api/routes/sources.py`       | REST endpoints for sources/lightcurves                          |
| `database/schema.sql`         | Database schema (photometry, variability_stats, ese_candidates) |
