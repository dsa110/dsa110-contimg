# VAST Tools → DSA-110 Detailed Comparison and Adoption Plan

**Date:** 2025-01-XX  
**Purpose:** Comprehensive comparison of VAST Tools and DSA-110 pipeline, with detailed recommendations for adopting VAST patterns  
**Reference:** `/data/dsa110-contimg/archive/references/vast-tools`

---

## Executive Summary

This document provides a detailed comparison between VAST Tools and the DSA-110 continuum imaging pipeline, identifying specific features, patterns, and capabilities that can be adopted from VAST to enhance DSA-110's ESE detection and source analysis capabilities.

**Key Finding:** DSA-110 has strong foundations (photometry, normalization, database) but lacks the rich source analysis interface and visualization tools that VAST Tools provides. Adopting VAST patterns would significantly improve ESE candidate analysis workflows.

---

## 1. Current State Comparison

### 1.1 DSA-110 Current Capabilities

#### **Photometry & Normalization** ✅
- **Location:** `src/dsa110_contimg/photometry/`
- **Status:** Well-implemented
- **Features:**
  - Forced photometry (`forced.py`)
  - Differential normalization (`normalize.py`)
  - Reference source ensemble correction
  - 1-2% relative flux precision achieved
- **Database:** `photometry_timeseries` table with normalized fluxes

#### **Variability Analysis** ⚠️ Partial
- **Location:** `database/schema_evolution.py`, `api/data_access.py`
- **Status:** Basic implementation
- **Features:**
  - `variability_stats` table with:
    - `chi2_reduced`
    - `fractional_variability` (V metric)
    - `ese_score`
    - `significance`
  - Missing: η metric, two-epoch metrics (Vs, m)

#### **Source Representation** ❌ Missing
- **Status:** No Source class pattern
- **Current:** Database queries only (`fetch_source_timeseries()`)
- **Limitation:** No object-oriented interface for source analysis

#### **Light Curve Plotting** ❌ Missing
- **Status:** No dedicated light curve plotting
- **Current:** Only validation plots (`qa/validation_plots.py`)
- **Limitation:** No ESE candidate visualization

#### **Postage Stamps** ❌ Missing
- **Status:** No image cutout visualization
- **Current:** Only full image QA plots
- **Limitation:** Cannot visualize individual sources across epochs

#### **External Catalog Integration** ⚠️ Partial
- **Location:** `catalog/query.py`, `imaging/nvss_tools.py`
- **Status:** NVSS/VLASS only
- **Missing:** SIMBAD, NED, CASDA, Gaia integration

### 1.2 VAST Tools Capabilities

#### **Source Class** ✅
- **Location:** `vasttools/source.py` (~2,800 lines)
- **Features:**
  - Rich Source object with measurements, coordinates, epochs
  - Built-in plotting methods
  - Crossmatching capabilities
  - Variability metric calculations

#### **Light Curve Plotting** ✅
- **Location:** `vasttools/source.py::Source.plot_lightcurve()`
- **Features:**
  - Peak and integrated flux support
  - Upper limits visualization
  - Multiple time axes (datetime, MJD, days from start)
  - Customizable styling
  - Error bars and detection/limit distinction
  - Bokeh interactive plots

#### **Variability Metrics** ✅
- **Location:** `vasttools/utils.py`
- **Metrics:**
  - η metric (weighted variance)
  - V metric (coefficient of variation)
  - Vs metric (two-epoch t-statistic)
  - m metric (modulation index)

#### **Postage Stamps** ✅
- **Location:** `vasttools/source.py::Source.show_png_cutout()`
- **Features:**
  - Individual epoch cutouts
  - All-epoch grid visualization
  - Selavy overlay options
  - SkyView contour overlays

#### **External Catalog Integration** ✅
- **Location:** `vasttools/source.py`
- **Services:**
  - SIMBAD (object identification)
  - NED (extragalactic database)
  - CASDA (ASKAP archive)
  - Gaia (astrometry)
  - Vizier (catalog queries)

---

## 2. Detailed Feature Comparison

### 2.1 Source Representation

#### VAST Tools Pattern
```python
class Source:
    coord: SkyCoord
    name: str
    epochs: List[str]
    fields: List[str]
    measurements: pd.DataFrame
    detections: int
    limits: int
    
    def plot_lightcurve(...) -> Figure
    def show_png_cutout(...) -> Figure
    def calc_eta_and_v_metrics(...) -> dict
    def simbad_search(...) -> Table
    def casda_search(...) -> Table
```

#### DSA-110 Current State
```python
# No Source class - only database queries
def fetch_source_timeseries(products_db: Path, source_id: str) -> Optional[dict]:
    # Returns dictionary with flux points
    # No methods for plotting or analysis
```

#### **Recommendation: Adopt Source Class Pattern**
- **Priority:** High
- **Benefit:** Clean interface for ESE candidate analysis
- **Implementation:** Create `src/dsa110_contimg/photometry/source.py`

### 2.2 Light Curve Plotting

#### VAST Tools Features
- Handles both peak and integrated flux
- Upper limits visualization (sigma threshold)
- Multiple time axis options
- Customizable figure size, DPI, grid, legend
- Error bars and detection/limit distinction
- Bokeh interactive plots

#### DSA-110 Current State
- No dedicated light curve plotting
- Only validation plots (`plot_flux_ratio_histogram`, `plot_flux_vs_offset`)

#### **Recommendation: Adopt Light Curve Plotting**
- **Priority:** High
- **Benefit:** Essential for ESE candidate visualization
- **Implementation:** Create `src/dsa110_contimg/qa/lightcurves.py`

### 2.3 Variability Metrics

#### VAST Tools Metrics
```python
# η metric (weighted variance)
def pipeline_get_eta_metric(df: pd.DataFrame, peak: bool = False) -> float:
    weights = 1. / df[f'flux_{suffix}_err'].values**2
    fluxes = df[f'flux_{suffix}'].values
    eta = (df.shape[0] / (df.shape[0] - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta

# V metric (coefficient of variation)
v = df['flux'].std() / df['flux'].mean()

# Vs metric (two-epoch t-statistic)
def calculate_vs_metric(flux_a, flux_b, flux_err_a, flux_err_b) -> float:
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

# m metric (modulation index)
def calculate_m_metric(flux_a, flux_b) -> float:
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))
```

#### DSA-110 Current Metrics
- `fractional_variability` (V metric) ✅
- `chi2_reduced` ✅
- Missing: η metric, Vs metric, m metric

#### **Recommendation: Add Missing Metrics**
- **Priority:** Medium
- **Benefit:** Complementary to χ² for variability detection
- **Implementation:** Extend `src/dsa110_contimg/photometry/variability.py`

### 2.4 Postage Stamp Visualization

#### VAST Tools Features
- Individual epoch cutouts (`show_png_cutout()`)
- All-epoch grid (`show_all_png_cutouts()`)
- Selavy overlay options
- SkyView contour overlays
- Customizable size, columns, figure size

#### DSA-110 Current State
- No postage stamp visualization
- Only full image QA plots

#### **Recommendation: Add Postage Stamps**
- **Priority:** Medium
- **Benefit:** Visual verification of ESE candidates
- **Implementation:** Create `src/dsa110_contimg/qa/postage_stamps.py`

### 2.5 External Catalog Integration

#### VAST Tools Integration
- SIMBAD: Object identification
- NED: Extragalactic database
- CASDA: ASKAP archive
- Gaia: Astrometry
- Vizier: Catalog queries

#### DSA-110 Current Integration
- NVSS: ✅ (`catalog/query.py`, `imaging/nvss_tools.py`)
- VLASS: ✅ (`catalog/query.py`)
- Missing: SIMBAD, NED, CASDA, Gaia

#### **Recommendation: Expand Catalog Integration**
- **Priority:** Low-Medium
- **Benefit:** Better source identification and crossmatching
- **Implementation:** Extend `src/dsa110_contimg/catalog/query.py`

---

## 3. Detailed Adoption Plan

### 3.1 High Priority: Source Class Pattern

#### **Why Adopt**
- Clean interface for ESE candidate analysis
- Encapsulates measurements, plotting, crossmatching
- Enables method chaining and workflow automation
- Improves code organization and reusability

#### **Implementation Strategy**

**Step 1: Create Source Class**
```python
# src/dsa110_contimg/photometry/source.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
import sqlite3

@dataclass
class Source:
    """Represents a single source with measurements across epochs."""
    source_id: str
    ra_deg: float
    dec_deg: float
    name: Optional[str] = None
    products_db: Optional[Path] = None
    
    def __post_init__(self):
        """Load measurements from database."""
        if self.products_db:
            self.measurements = self._load_measurements()
        else:
            self.measurements = pd.DataFrame()
    
    def _load_measurements(self) -> pd.DataFrame:
        """Load photometry measurements from database."""
        conn = sqlite3.connect(str(self.products_db))
        query = """
            SELECT 
                mjd, normalized_flux_jy, normalized_flux_err_jy,
                peak_jyb, peak_err_jyb, image_path, measured_at
            FROM photometry_timeseries
            WHERE source_id = ?
            ORDER BY mjd ASC
        """
        df = pd.read_sql_query(query, conn, params=(self.source_id,))
        conn.close()
        return df
    
    @property
    def coord(self) -> SkyCoord:
        """Source coordinates as SkyCoord."""
        return SkyCoord(self.ra_deg, self.dec_deg, unit=(u.deg, u.deg))
    
    @property
    def n_epochs(self) -> int:
        """Number of epochs with measurements."""
        return len(self.measurements)
    
    @property
    def detections(self) -> int:
        """Number of detections (SNR > 5)."""
        if 'snr' in self.measurements.columns:
            return (self.measurements['snr'] > 5).sum()
        return len(self.measurements)
    
    def plot_lightcurve(self, ...) -> matplotlib.figure.Figure:
        """Plot light curve (adopt from VAST)."""
        # Implementation below
    
    def calc_variability_metrics(self) -> dict:
        """Calculate variability metrics."""
        # Implementation below
```

**Step 2: Adopt Light Curve Plotting**
```python
def plot_lightcurve(
    self,
    use_normalized: bool = True,
    figsize: Tuple[int, int] = (10, 6),
    min_points: int = 2,
    mjd: bool = False,
    grid: bool = True,
    yaxis_start: str = "auto",
    highlight_baseline: bool = True,
    highlight_ese_period: bool = True,
    save: bool = False,
    outfile: Optional[str] = None,
    plot_dpi: int = 150
) -> matplotlib.figure.Figure:
    """Plot light curve with ESE-specific features.
    
    Args:
        use_normalized: Use normalized flux (default) or raw flux
        highlight_baseline: Highlight first 10 epochs as baseline
        highlight_ese_period: Highlight 14-180 day ESE candidate period
        ... (other args from VAST)
    """
    import matplotlib.pyplot as plt
    
    if len(self.measurements) < min_points:
        raise ValueError(f"Need at least {min_points} measurements")
    
    fig, ax = plt.subplots(figsize=figsize, dpi=plot_dpi)
    
    # Select flux column
    flux_col = 'normalized_flux_jy' if use_normalized else 'peak_jyb'
    err_col = 'normalized_flux_err_jy' if use_normalized else 'peak_err_jyb'
    
    # Time axis
    if mjd:
        time = self.measurements['mjd']
        xlabel = 'MJD'
    else:
        time = pd.to_datetime(self.measurements['measured_at'], unit='s')
        xlabel = 'Date'
    
    # Plot flux with error bars
    ax.errorbar(
        time, self.measurements[flux_col], 
        yerr=self.measurements[err_col],
        fmt='o', capsize=3, capthick=1.5,
        label='Normalized Flux' if use_normalized else 'Peak Flux'
    )
    
    # Highlight baseline period (first 10 epochs)
    if highlight_baseline and len(self.measurements) >= 10:
        baseline_time = time.iloc[:10]
        baseline_flux = self.measurements[flux_col].iloc[:10]
        ax.axvspan(
            baseline_time.min(), baseline_time.max(),
            alpha=0.2, color='green', label='Baseline Period'
        )
        # Plot baseline median
        baseline_median = baseline_flux.median()
        ax.axhline(
            baseline_median, color='green', linestyle='--',
            label=f'Baseline Median: {baseline_median:.4f} Jy'
        )
    
    # Highlight ESE candidate period (14-180 days)
    if highlight_ese_period and len(self.measurements) > 1:
        time_range_days = (time.max() - time.min()).total_seconds() / 86400
        if 14 <= time_range_days <= 180:
            ax.axvspan(
                time.min(), time.max(),
                alpha=0.1, color='red', label='ESE Candidate Period'
            )
    
    ax.set_xlabel(xlabel)
    ax.set_ylabel('Flux (Jy)' if not use_normalized else 'Normalized Flux')
    ax.set_title(f'Light Curve: {self.name or self.source_id}')
    ax.grid(grid)
    
    if yaxis_start == "0":
        ax.set_ylim(bottom=0)
    
    ax.legend()
    
    if save and outfile:
        fig.savefig(outfile, dpi=plot_dpi, bbox_inches='tight')
    
    return fig
```

**Step 3: Add Variability Metrics**
```python
def calc_variability_metrics(self) -> dict:
    """Calculate variability metrics (adopt from VAST)."""
    from dsa110_contimg.photometry.variability import (
        calculate_eta_metric,
        calculate_vs_metric,
        calculate_m_metric
    )
    
    if len(self.measurements) < 2:
        return {
            'v': 0.0,
            'eta': 0.0,
            'n_epochs': len(self.measurements)
        }
    
    flux = self.measurements['normalized_flux_jy'].values
    flux_err = self.measurements['normalized_flux_err_jy'].values
    
    # V metric (coefficient of variation)
    v = np.std(flux) / np.mean(flux)
    
    # η metric (weighted variance)
    eta = calculate_eta_metric(
        self.measurements[['normalized_flux_jy', 'normalized_flux_err_jy']]
    )
    
    # Two-epoch metrics (if applicable)
    vs_metrics = []
    m_metrics = []
    if len(flux) >= 2:
        for i in range(len(flux) - 1):
            vs = calculate_vs_metric(
                flux[i], flux[i+1], flux_err[i], flux_err[i+1]
            )
            m = calculate_m_metric(flux[i], flux[i+1])
            vs_metrics.append(vs)
            m_metrics.append(m)
    
    return {
        'v': float(v),
        'eta': float(eta),
        'vs_mean': float(np.mean(vs_metrics)) if vs_metrics else None,
        'm_mean': float(np.mean(m_metrics)) if m_metrics else None,
        'n_epochs': len(self.measurements)
    }
```

**Step 4: Create Variability Utilities Module**
```python
# src/dsa110_contimg/photometry/variability.py

import numpy as np
import pandas as pd

def calculate_eta_metric(
    df: pd.DataFrame,
    flux_col: str = 'normalized_flux_jy',
    err_col: str = 'normalized_flux_err_jy'
) -> float:
    """Calculate η metric (weighted variance) - adopted from VAST.
    
    See VAST Tools: vasttools/utils.py::pipeline_get_eta_metric()
    """
    if len(df) <= 1:
        return 0.0
    
    weights = 1. / df[err_col].values**2
    fluxes = df[flux_col].values
    
    eta = (len(df) / (len(df) - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    
    return float(eta)

def calculate_vs_metric(
    flux_a: float,
    flux_b: float,
    flux_err_a: float,
    flux_err_b: float
) -> float:
    """Calculate Vs metric (two-epoch t-statistic) - adopted from VAST.
    
    See VAST Tools: vasttools/utils.py::calculate_vs_metric()
    """
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """Calculate m metric (modulation index) - adopted from VAST.
    
    See VAST Tools: vasttools/utils.py::calculate_m_metric()
    """
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))
```

### 3.2 Medium Priority: Postage Stamp Visualization

#### **Why Adopt**
- Visual verification of ESE candidates
- Quality assessment of measurements
- Useful for publication figures

#### **Implementation Strategy**

**Create Postage Stamp Module**
```python
# src/dsa110_contimg/qa/postage_stamps.py

from pathlib import Path
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.wcs import WCS
from astropy.nddata.utils import Cutout2D
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.visualization import ZScaleInterval, ImageNormalize
import numpy as np

def create_cutout(
    fits_path: Path,
    ra_deg: float,
    dec_deg: float,
    size_arcmin: float = 2.0
) -> Tuple[np.ndarray, WCS]:
    """Create image cutout around source position."""
    coord = SkyCoord(ra_deg, dec_deg, unit=(u.deg, u.deg))
    size = size_arcmin * u.arcmin
    
    with fits.open(fits_path) as hdul:
        data = hdul[0].data.squeeze()
        wcs = WCS(hdul[0].header).celestial
    
    cutout = Cutout2D(data, coord, size, wcs=wcs)
    return cutout.data, cutout.wcs_celestial

def show_all_cutouts(
    source: 'Source',  # From photometry/source.py
    size_arcmin: float = 2.0,
    columns: int = 5,
    figsize: Tuple[int, int] = (20, 8),
    save: bool = False,
    outfile: Optional[str] = None
) -> plt.Figure:
    """Show all epoch cutouts in a grid - adopted from VAST.
    
    See VAST Tools: vasttools/source.py::Source.show_all_png_cutouts()
    """
    n_epochs = len(source.measurements)
    rows = (n_epochs + columns - 1) // columns
    
    fig, axes = plt.subplots(rows, columns, figsize=figsize)
    axes = axes.flatten() if n_epochs > 1 else [axes]
    
    for i, (idx, row) in enumerate(source.measurements.iterrows()):
        if i >= len(axes):
            break
        
        ax = axes[i]
        image_path = Path(row['image_path'])
        
        if not image_path.exists():
            ax.text(0.5, 0.5, 'Image not found', 
                   ha='center', va='center', transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            continue
        
        try:
            data, wcs = create_cutout(
                image_path, source.ra_deg, source.dec_deg, size_arcmin
            )
            
            # Z-scale normalization
            interval = ZScaleInterval()
            vmin, vmax = interval.get_limits(data)
            norm = ImageNormalize(data, vmin=vmin, vmax=vmax)
            
            ax.imshow(data, origin='lower', cmap='gray', norm=norm)
            ax.set_title(f"Epoch {i+1}\nMJD: {row['mjd']:.1f}")
            ax.set_xlabel('RA')
            ax.set_ylabel('Dec')
            
        except Exception as e:
            ax.text(0.5, 0.5, f'Error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
    
    # Hide unused axes
    for i in range(n_epochs, len(axes)):
        axes[i].set_visible(False)
    
    fig.suptitle(f'Postage Stamps: {source.name or source.source_id}', 
                 fontsize=14)
    plt.tight_layout()
    
    if save and outfile:
        fig.savefig(outfile, dpi=150, bbox_inches='tight')
    
    return fig
```

### 3.3 Low-Medium Priority: External Catalog Integration

#### **Why Adopt**
- Better source identification
- Crossmatching with external surveys
- Proper motion handling

#### **Implementation Strategy**

**Extend Catalog Query Module**
```python
# src/dsa110_contimg/catalog/external.py

from astroquery.simbad import Simbad
from astroquery.ipac.ned import Ned
from astroquery.gaia import Gaia
from astropy.coordinates import SkyCoord
from astropy import units as u
from typing import Optional, List, Tuple
import pandas as pd

def simbad_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0
) -> Optional[pd.DataFrame]:
    """Search SIMBAD for object at coordinates - adopted from VAST.
    
    See VAST Tools: vasttools/utils.py::simbad_search()
    """
    try:
        Simbad.add_votable_fields('ra(d)', 'dec(d)', 'typed_id', 'main_id')
        result = Simbad.query_region(coord, radius=f"{radius_arcsec}s")
        
        if result is None or len(result) == 0:
            return None
        
        return result.to_pandas()
    except Exception as e:
        print(f"SIMBAD search failed: {e}")
        return None

def ned_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0
) -> Optional[pd.DataFrame]:
    """Search NED for object at coordinates."""
    try:
        result = Ned.query_region(coord, radius=f"{radius_arcsec}s")
        
        if result is None or len(result) == 0:
            return None
        
        return result.to_pandas()
    except Exception as e:
        print(f"NED search failed: {e}")
        return None

def gaia_search(
    coord: SkyCoord,
    radius_arcsec: float = 5.0
) -> Optional[pd.DataFrame]:
    """Search Gaia for astrometric data."""
    try:
        # Convert to degrees
        radius_deg = radius_arcsec / 3600.0
        
        job = Gaia.launch_job_async(
            f"""
            SELECT *
            FROM gaiadr3.gaia_source
            WHERE 1=CONTAINS(
                POINT('ICRS', {coord.ra.deg}, {coord.dec.deg}),
                CIRCLE('ICRS', ra, dec, {radius_deg})
            )
            """
        )
        
        result = job.get_results()
        
        if len(result) == 0:
            return None
        
        return result.to_pandas()
    except Exception as e:
        print(f"Gaia search failed: {e}")
        return None

# Add to Source class
class Source:
    # ... existing methods ...
    
    def crossmatch_external(self) -> dict:
        """Crossmatch with external catalogs."""
        results = {}
        
        results['simbad'] = simbad_search(self.coord)
        results['ned'] = ned_search(self.coord)
        results['gaia'] = gaia_search(self.coord)
        
        return results
```

---

## 4. Implementation Roadmap

### Phase 1: Core Source Class (High Priority)
**Timeline:** 2-3 weeks

1. **Week 1:**
   - Create `src/dsa110_contimg/photometry/source.py`
   - Implement basic Source class with database loading
   - Add `coord`, `n_epochs`, `detections` properties
   - Unit tests

2. **Week 2:**
   - Adopt light curve plotting from VAST
   - Add ESE-specific features (baseline highlighting, ESE period highlighting)
   - Integration tests with real data

3. **Week 3:**
   - Add variability metrics calculation
   - Create `src/dsa110_contimg/photometry/variability.py`
   - Update `variability_stats` table to include η metric
   - Documentation

### Phase 2: Visualization Tools (Medium Priority)
**Timeline:** 2 weeks

1. **Week 1:**
   - Create `src/dsa110_contimg/qa/postage_stamps.py`
   - Implement cutout creation and grid visualization
   - Integration with Source class

2. **Week 2:**
   - Add to QA module
   - Create API endpoints for postage stamps
   - Documentation and examples

### Phase 3: External Catalog Integration (Low-Medium Priority)
**Timeline:** 1-2 weeks

1. **Week 1:**
   - Create `src/dsa110_contimg/catalog/external.py`
   - Implement SIMBAD, NED, Gaia queries
   - Add to Source class

2. **Week 2:**
   - Integration tests
   - Documentation
   - API endpoints (optional)

---

## 5. Code Examples: Before and After

### Before (Current DSA-110)
```python
# Current: Database queries only
from dsa110_contimg.api.data_access import fetch_source_timeseries

timeseries = fetch_source_timeseries(products_db, "NVSS J123456+420312")
if timeseries:
    # Manual plotting required
    import matplotlib.pyplot as plt
    plt.plot(timeseries['mjd'], timeseries['flux_jy'])
    plt.show()
    
    # Manual variability calculation
    fluxes = timeseries['flux_jy']
    v = np.std(fluxes) / np.mean(fluxes)
```

### After (With VAST Patterns)
```python
# New: Rich Source object
from dsa110_contimg.photometry.source import Source

source = Source(
    source_id="NVSS J123456+420312",
    ra_deg=123.456,
    dec_deg=42.0312,
    products_db=Path("state/products.sqlite3")
)

# Automatic light curve plotting
fig = source.plot_lightcurve(
    highlight_baseline=True,
    highlight_ese_period=True
)
fig.savefig("lightcurve.png")

# Automatic variability metrics
metrics = source.calc_variability_metrics()
print(f"V: {metrics['v']:.4f}, η: {metrics['eta']:.4f}")

# Postage stamps
fig = source.show_all_cutouts(columns=5)
fig.savefig("postage_stamps.png")

# External catalog crossmatch
external = source.crossmatch_external()
if external['simbad']:
    print(f"SIMBAD name: {external['simbad']['MAIN_ID'].iloc[0]}")
```

---

## 6. Integration Points

### 6.1 API Integration
```python
# src/dsa110_contimg/api/routes.py

from dsa110_contimg.photometry.source import Source

@router.get("/api/sources/{source_id}/lightcurve")
async def get_source_lightcurve(source_id: str):
    """Get light curve plot for a source."""
    source = Source(source_id=source_id, products_db=products_db)
    fig = source.plot_lightcurve()
    # Convert to base64 or save to file
    return {"image_url": "/static/lightcurves/{source_id}.png"}

@router.get("/api/sources/{source_id}/postage_stamps")
async def get_source_postage_stamps(source_id: str):
    """Get postage stamp grid for a source."""
    source = Source(source_id=source_id, products_db=products_db)
    fig = source.show_all_cutouts()
    return {"image_url": "/static/postage_stamps/{source_id}.png"}

@router.get("/api/sources/{source_id}/variability")
async def get_source_variability(source_id: str):
    """Get variability metrics for a source."""
    source = Source(source_id=source_id, products_db=products_db)
    metrics = source.calc_variability_metrics()
    return metrics
```

### 6.2 ESE Detection Integration
```python
# src/dsa110_contimg/science/ese_detection.py

from dsa110_contimg.photometry.source import Source

def analyze_ese_candidate(source_id: str, products_db: Path):
    """Analyze an ESE candidate using Source class."""
    source = Source(source_id=source_id, products_db=products_db)
    
    # Get variability metrics
    metrics = source.calc_variability_metrics()
    
    # Generate visualizations
    lightcurve_fig = source.plot_lightcurve(
        highlight_baseline=True,
        highlight_ese_period=True
    )
    postage_fig = source.show_all_cutouts()
    
    # Crossmatch with external catalogs
    external = source.crossmatch_external()
    
    return {
        'metrics': metrics,
        'lightcurve_path': save_figure(lightcurve_fig, f"{source_id}_lc.png"),
        'postage_path': save_figure(postage_fig, f"{source_id}_stamps.png"),
        'external_catalogs': external
    }
```

---

## 7. Testing Strategy

### Unit Tests
```python
# tests/unit/test_source.py

def test_source_creation():
    """Test Source object creation."""
    source = Source(
        source_id="TEST001",
        ra_deg=123.0,
        dec_deg=45.0,
        products_db=test_db
    )
    assert source.coord.ra.deg == 123.0
    assert source.coord.dec.deg == 45.0

def test_lightcurve_plotting():
    """Test light curve plotting."""
    source = create_test_source_with_measurements()
    fig = source.plot_lightcurve()
    assert fig is not None
    assert len(fig.axes) == 1

def test_variability_metrics():
    """Test variability metric calculation."""
    source = create_test_source_with_measurements()
    metrics = source.calc_variability_metrics()
    assert 'v' in metrics
    assert 'eta' in metrics
    assert metrics['n_epochs'] > 0
```

### Integration Tests
```python
# tests/integration/test_source_integration.py

def test_source_with_real_data():
    """Test Source class with real products database."""
    source = Source(
        source_id="NVSS J123456+420312",
        ra_deg=123.456,
        dec_deg=42.0312,
        products_db=real_products_db
    )
    
    # Should load measurements
    assert len(source.measurements) > 0
    
    # Should generate plots
    fig = source.plot_lightcurve()
    assert fig is not None
```

---

## 8. Dependencies

### New Dependencies Required
- **astroquery**: External catalog queries (SIMBAD, NED, Gaia)
  - Already used by VAST Tools
  - Add to `requirements.txt` or `pyproject.toml`

### Optional Dependencies
- **bokeh**: Interactive plots (if adopting Bokeh light curves)
  - VAST Tools uses Bokeh for interactive plots
  - Can start with matplotlib, add Bokeh later

---

## 9. Migration Path

### Step 1: Add Source Class (Non-Breaking)
- Create new `photometry/source.py` module
- No changes to existing code
- Can be used alongside existing database queries

### Step 2: Update Variability Stats (Database Migration)
- Add `eta_metric` column to `variability_stats` table
- Update calculation code to include η metric
- Backfill existing records

### Step 3: Add Visualization (New Features)
- Create `qa/postage_stamps.py`
- Add API endpoints
- No breaking changes

### Step 4: External Catalogs (Optional Enhancement)
- Create `catalog/external.py`
- Add to Source class
- No breaking changes

---

## 10. Success Metrics

### Quantitative
- **Source Class Usage**: Track adoption in codebase
- **API Endpoint Usage**: Monitor `/api/sources/*` endpoints
- **Visualization Generation**: Count light curve/postage stamp requests
- **Variability Metrics**: Track η metric usage vs. χ²

### Qualitative
- **Developer Experience**: Feedback on Source class usability
- **ESE Analysis Workflow**: Time saved in candidate analysis
- **Code Quality**: Reduction in duplicate plotting code

---

## 11. Conclusion

Adopting VAST Tools patterns would significantly enhance DSA-110's ESE detection and source analysis capabilities. The Source class pattern provides a clean, object-oriented interface that encapsulates measurements, plotting, and analysis methods. Light curve plotting and postage stamp visualization are essential for ESE candidate verification and publication.

**Recommended Priority:**
1. **High**: Source class + light curve plotting
2. **Medium**: Postage stamps + variability metrics
3. **Low-Medium**: External catalog integration

**Estimated Effort:**
- Phase 1 (Core): 2-3 weeks
- Phase 2 (Visualization): 2 weeks
- Phase 3 (External Catalogs): 1-2 weeks
- **Total**: 5-7 weeks

**Risk Assessment:**
- **Low Risk**: Adopting well-tested patterns from VAST Tools
- **Non-Breaking**: Can be added incrementally without breaking existing code
- **High Value**: Significantly improves ESE analysis workflow

---

## References

- VAST Tools Repository: `/data/dsa110-contimg/archive/references/vast-tools`
- VAST Tools Review: `archive/references/vast-tools/VAST_TOOLS_CODEBASE_REVIEW.md`
- VAST Tools Analysis: `docs/analysis/VAST_TOOLS_REFERENCE_ANALYSIS.md`
- DSA-110 Database Schema: `docs/reference/database_schema.md`

