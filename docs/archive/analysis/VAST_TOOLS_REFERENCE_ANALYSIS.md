# VAST Tools Reference Analysis

**Date:** 2025-11-12  
**Purpose:** Analysis of VAST Tools codebase as reference/template for DSA-110 pipeline development  
**Reference Repository:** `/data/dsa110-contimg/archive/references/vast-tools`  
**Source:** https://github.com/askap-vast/vast-tools

---

## Executive Summary

VAST Tools is a Python module for interacting with VAST Pipeline results, providing tools for light curve analysis, transient detection, crossmatching, and source exploration. This analysis identifies key patterns, functions, and architectural approaches that can inform DSA-110's ESE detection pipeline development.

**Key Relevance:**
- Light curve plotting and analysis (directly applicable to ESE detection)
- Variability metrics calculation (Vs, M, η metrics)
- Source class pattern for managing measurements and epochs
- Pipeline result interaction patterns
- Forced photometry integration

**Note:** We are NOT importing VAST Tools as a dependency. This analysis serves to identify code patterns and functions that can be adapted/copied directly into the DSA-110 codebase.

---

## 1. Architecture Overview

### 1.1 Core Modules

**`vasttools/source.py`** (~93KB)
- **Purpose:** Core class for representing and analyzing individual sources
- **Key Class:** `Source`
- **Relevance:** High - directly applicable to ESE candidate analysis

**`vasttools/pipeline.py`** (~95KB)
- **Purpose:** Interface with VAST Pipeline results
- **Key Classes:** `PipeRun`, `PipeAnalysis`, `Pipeline`
- **Relevance:** Medium - patterns for loading/analyzing pipeline outputs

**`vasttools/query.py`** (~112KB)
- **Purpose:** Query observational data and find sources
- **Key Class:** `Query`
- **Relevance:** Medium - patterns for catalog queries and crossmatching

**`vasttools/utils.py`** (~22KB)
- **Purpose:** Utility functions including variability metrics
- **Relevance:** High - contains variability calculation functions

**`vasttools/tools.py`** (~26KB)
- **Purpose:** General tools and helper functions
- **Relevance:** Low-Medium - various utility functions

**`vasttools/survey.py`** (~18KB)
- **Purpose:** Survey footprint and image handling
- **Relevance:** Low - survey-specific functionality

### 1.2 Key Dependencies

From `pyproject.toml`:
- `astropy` (^5.2) - Core astronomy library
- `pandas` (<2.0) - Data manipulation
- `matplotlib` (^3.7.0) - Plotting
- `bokeh` (^3.1) - Interactive plotting
- `dask` (^2022.01.0) - Parallel processing for large datasets
- `vaex-core` (^4.17) - Large dataset handling
- `forced-phot` - Forced photometry integration
- `scipy` (^1.4) - Scientific computing
- `radio-beam` (^0.3) - Beam handling

**Note:** DSA-110 already uses most of these (astropy, pandas, matplotlib, scipy). Consider `bokeh` for interactive plots and `dask`/`vaex` for large dataset handling.

---

## 2. Key Patterns and Code Structures

### 2.1 Source Class Pattern

**Location:** `vasttools/source.py`

**Purpose:** Represents a single source with measurements across multiple epochs.

**Key Attributes:**
```python
class Source:
    coord: SkyCoord              # Source coordinates
    name: str                    # Source name
    epochs: List[str]            # Epochs containing this source
    fields: List[str]            # Fields containing this source
    measurements: pd.DataFrame   # All measurements (flux, errors, dates)
    detections: int              # Number of detections
    limits: int                  # Number of upper limits
    forced_fits: bool            # Whether forced fits are included
```

**Relevance for DSA-110:**
- DSA-110 already has `photometry_timeseries` table with similar structure
- Could create a `Source` class wrapper around database queries
- Provides clean interface for ESE candidate analysis

**Key Methods:**
- `plot_lightcurve()` - Light curve visualization
- `plot_postagestamp()` - Image cutout visualization
- `crossmatch()` - Crossmatch to external catalogs

### 2.2 Light Curve Plotting

**Location:** `vasttools/source.py::Source.plot_lightcurve()`

**Key Features:**
- Handles both peak and integrated flux
- Upper limits visualization (sigma threshold)
- Forced photometry integration
- Multiple time axis options (datetime, MJD, days from start)
- Customizable figure size, DPI, grid, legend
- Error bars and detection/limit distinction

**Code Pattern:**
```python
def plot_lightcurve(
    self,
    sigma_thresh: int = 5,
    figsize: Tuple[int, int] = (8, 4),
    min_points: int = 2,
    min_detections: int = 0,
    mjd: bool = False,
    start_date: Optional[pd.Timestamp] = None,
    grid: bool = False,
    yaxis_start: str = "0",
    peak_flux: bool = True,
    save: bool = False,
    outfile: Optional[str] = None,
    use_forced_for_limits: bool = False,
    use_forced_for_all: bool = False,
    hide_legend: bool = False,
    plot_dpi: int = 150
) -> Union[None, matplotlib.figure.Figure]:
```

**Relevance for DSA-110:**
- **Directly applicable** - DSA-110 needs light curve plotting for ESE candidates
- Can adapt this method to work with `photometry_timeseries` table
- Already handles normalized flux (via `use_forced_for_all` pattern)

**Adaptation Notes:**
- DSA-110 uses normalized flux from differential photometry
- May need to add baseline visualization (first 10 epochs)
- Should highlight ESE candidate periods (14-180 days)

### 2.3 Variability Metrics

**Location:** `vasttools/utils.py`

#### 2.3.1 Pipeline Variability Metrics

**Function:** `pipeline_get_variable_metrics(df: pd.DataFrame) -> pd.Series`

**Calculates:**
- `v_int`: Fractional variability (std/mean) for integrated flux
- `v_peak`: Fractional variability (std/mean) for peak flux
- `eta_int`: η metric for integrated flux
- `eta_peak`: η metric for peak flux

**Code:**
```python
def pipeline_get_variable_metrics(df: pd.DataFrame) -> pd.Series:
    d = {}
    if df.shape[0] == 1:
        d['v_int'] = 0.
        d['v_peak'] = 0.
        d['eta_int'] = 0.
        d['eta_peak'] = 0.
    else:
        d['v_int'] = df['flux_int'].std() / df['flux_int'].mean()
        d['v_peak'] = df['flux_peak'].std() / df['flux_peak'].mean()
        d['eta_int'] = pipeline_get_eta_metric(df)
        d['eta_peak'] = pipeline_get_eta_metric(df, peak=True)
    return pd.Series(d)
```

**Relevance for DSA-110:**
- DSA-110 already calculates fractional variability (`V`) in `variability_stats` table
- Could add η metric calculation (complementary to χ²)
- Simple, clean implementation that can be copied directly

#### 2.3.2 Two-Epoch Variability Metrics

**Functions:**
- `calculate_vs_metric()` - t-statistic for variability between two epochs
- `calculate_m_metric()` - Modulation index (fractional variability) between two epochs

**Code:**
```python
def calculate_vs_metric(
    flux_a: float, flux_b: float, flux_err_a: float, flux_err_b: float
) -> float:
    """Vs metric: t-statistic that fluxes are variable."""
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """M metric: modulation index (fractional variability)."""
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))
```

**Reference:** Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105

**Relevance for DSA-110:**
- Useful for pairwise epoch comparisons
- Can identify rapid flux changes (ESEs have sharp caustic crossings)
- Simple functions that can be copied directly

**Usage in VAST:**
- Applied to measurement pairs for transient detection
- Used in `PipeRun` class for two-epoch analysis

### 2.4 Pipeline Result Loading

**Location:** `vasttools/pipeline.py`

**Key Class:** `PipeRun`

**Purpose:** Loads and manages pipeline output dataframes.

**Key Attributes:**
```python
class PipeRun:
    name: str
    images: pd.DataFrame
    skyregions: pd.DataFrame
    relations: pd.DataFrame
    sources: pd.DataFrame
    associations: pd.DataFrame
    bands: pd.DataFrame
    measurements: Union[pd.DataFrame, vaex.dataframe.DataFrame]
    measurement_pairs_file: List[str]
```

**Key Features:**
- Loads parquet files (associations, bands, images, measurements, etc.)
- Supports both pandas and vaex for large datasets
- Parallel processing support (dask)
- Two-epoch metrics calculation
- Variability analysis methods

**Relevance for DSA-110:**
- DSA-110 uses SQLite databases instead of parquet files
- Pattern of loading pipeline results into DataFrames is applicable
- Could create similar wrapper around `products.sqlite3` queries

**Adaptation Notes:**
- Replace parquet loading with SQLite queries
- Use existing `database/products.py` helpers
- Maintain similar interface for analysis methods

### 2.5 Query System

**Location:** `vasttools/query.py`

**Key Class:** `Query`

**Purpose:** Query observational data and find sources across epochs.

**Key Features:**
- Coordinate-based queries
- Source name queries
- Crossmatching to catalogs
- Forced photometry integration
- Field/epoch filtering
- Parallel processing support

**Relevance for DSA-110:**
- DSA-110 already has catalog querying (`catalog/` module)
- Pattern of query → Source objects could be useful
- Forced photometry integration pattern is relevant

**Adaptation Notes:**
- DSA-110's query system is more database-centric
- Could adapt Query pattern for ESE candidate queries
- Forced photometry already integrated in `photometry/forced.py`

---

## 3. Specific Code Snippets for Adaptation

### 3.1 Light Curve Plotting (High Priority)

**File:** `vasttools/source.py::Source.plot_lightcurve()`

**Why Adapt:**
- DSA-110 needs light curve visualization for ESE candidates
- Comprehensive feature set (error bars, limits, multiple time axes)
- Well-tested implementation

**Adaptation Strategy:**
1. Copy method structure
2. Adapt to use `photometry_timeseries` table
3. Add ESE-specific features:
   - Baseline period highlighting (first 10 epochs)
   - ESE candidate period highlighting (14-180 days)
   - Asymmetry visualization
4. Integrate with DSA-110's normalized flux data

**Location in DSA-110:**
- New module: `src/dsa110_contimg/qa/lightcurves.py`
- Or extend: `src/dsa110_contimg/photometry/visualization.py`

### 3.2 Variability Metrics (High Priority)

**Files:** `vasttools/utils.py::pipeline_get_variable_metrics()`, `calculate_vs_metric()`, `calculate_m_metric()`

**Why Adapt:**
- Simple, well-tested implementations
- Complementary to DSA-110's existing χ²-based metrics
- Useful for pairwise epoch comparisons

**Adaptation Strategy:**
1. Copy functions directly (they're pure functions)
2. Integrate into `variability_stats` calculation
3. Add to ESE detection algorithm

**Location in DSA-110:**
- `src/dsa110_contimg/photometry/variability.py` (new or extend existing)

### 3.3 Source Class Pattern (Medium Priority)

**File:** `vasttools/source.py::Source`

**Why Adapt:**
- Clean interface for source analysis
- Encapsulates measurements, plotting, crossmatching
- Useful for ESE candidate review workflow

**Adaptation Strategy:**
1. Create `Source` class wrapping database queries
2. Implement light curve and postage stamp plotting
3. Add ESE-specific analysis methods

**Location in DSA-110:**
- New module: `src/dsa110_contimg/photometry/source.py`

### 3.4 Postage Stamp Plotting (Medium Priority)

**File:** `vasttools/source.py::Source.plot_postagestamp()`

**Why Adapt:**
- Visual verification of ESE candidates
- Image cutout visualization
- Useful for quality assessment

**Adaptation Strategy:**
1. Adapt to use DSA-110 FITS images
2. Integrate with `qa/` module
3. Add to ESE candidate review tools

**Location in DSA-110:**
- `src/dsa110_contimg/qa/postage_stamps.py` (new)

### 3.5 Crossmatching Utilities (Low Priority)

**File:** `vasttools/source.py::Source.crossmatch()`

**Why Adapt:**
- DSA-110 already uses NVSS/VLASS catalogs
- Pattern for external catalog queries
- Useful for source identification

**Adaptation Strategy:**
- DSA-110 already has catalog querying
- May adapt crossmatch interface pattern
- Lower priority - existing functionality is sufficient

---

## 4. Architecture Patterns

### 4.1 Class-Based Source Representation

**Pattern:** Encapsulate source data and analysis methods in a single class.

**Benefits:**
- Clean API for source analysis
- Encapsulates complexity
- Easy to extend with new methods

**Application to DSA-110:**
- Create `ESECandidate` or `Source` class
- Wrap `photometry_timeseries` queries
- Provide plotting and analysis methods

### 4.2 Pipeline Result Wrapper

**Pattern:** Create wrapper classes around pipeline output data.

**Benefits:**
- Clean interface for pipeline results
- Hides data loading complexity
- Provides analysis methods

**Application to DSA-110:**
- Create wrapper around `products.sqlite3`
- Similar to existing `database/products.py` but more object-oriented
- Provide analysis methods (variability, ESE detection)

### 4.3 Query → Source Pipeline

**Pattern:** Query system returns Source objects for analysis.

**Benefits:**
- Consistent interface
- Easy to chain operations
- Supports both interactive and batch workflows

**Application to DSA-110:**
- Query ESE candidates → Source objects
- Analyze → Plot → Export workflow
- Integrate with API endpoints

---

## 5. DSA-110 Current State vs. VAST Tools

### 5.1 Already Implemented

**Photometry:**
- ✅ Forced photometry (`photometry/forced.py`)
- ✅ Differential normalization (`photometry/normalize.py`)
- ✅ Variability statistics (`variability_stats` table)
- ✅ Database storage (`photometry_timeseries` table)

**Catalogs:**
- ✅ NVSS/VLASS catalog loading (`catalog/`)
- ✅ Catalog queries (`catalog/query.py`)

**Pipeline:**
- ✅ Pipeline framework (`pipeline/`)
- ✅ Database products tracking (`database/products.py`)

### 5.2 Gaps / Missing Features

**Visualization:**
- ❌ Light curve plotting (high priority)
- ❌ Postage stamp plotting (medium priority)
- ❌ Interactive plots (low priority - bokeh)

**Variability Metrics:**
- ⚠️ Fractional variability (V) - implemented
- ❌ η metric (complementary to χ²)
- ❌ Two-epoch metrics (Vs, M) for rapid change detection

**Source Analysis:**
- ❌ Source class wrapper (medium priority)
- ❌ Crossmatching interface (low priority)

**API Integration:**
- ⚠️ ESE candidates endpoint exists but uses mock data
- ❌ Light curve endpoint
- ❌ Postage stamp endpoint

---

## 6. Recommended Implementation Plan

### Phase 1: High Priority (Immediate)

**1. Light Curve Plotting**
- **Effort:** 4-6 hours
- **Location:** `src/dsa110_contimg/qa/lightcurves.py`
- **Action:** Adapt `Source.plot_lightcurve()` from VAST Tools
- **Integration:** Add to ESE candidate review workflow

**2. Variability Metrics**
- **Effort:** 2-3 hours
- **Location:** `src/dsa110_contimg/photometry/variability.py`
- **Action:** Copy `calculate_vs_metric()`, `calculate_m_metric()`, `pipeline_get_variable_metrics()`
- **Integration:** Add to `variability_stats` calculation

### Phase 2: Medium Priority (Next Sprint)

**3. Source Class**
- **Effort:** 6-8 hours
- **Location:** `src/dsa110_contimg/photometry/source.py`
- **Action:** Create Source class wrapping database queries
- **Integration:** ESE candidate analysis workflow

**4. Postage Stamp Plotting**
- **Effort:** 4-6 hours
- **Location:** `src/dsa110_contimg/qa/postage_stamps.py`
- **Action:** Adapt `Source.plot_postagestamp()` from VAST Tools
- **Integration:** ESE candidate review tools

### Phase 3: Low Priority (Future)

**5. Interactive Plotting**
- **Effort:** 8-10 hours
- **Action:** Evaluate bokeh for interactive light curves
- **Integration:** Frontend dashboard

**6. Pipeline Result Wrapper**
- **Effort:** 6-8 hours
- **Action:** Create object-oriented wrapper around products database
- **Integration:** Analysis workflows

---

## 7. Code Examples

### 7.1 Light Curve Plotting (Adapted)

```python
# Location: src/dsa110_contimg/qa/lightcurves.py

from typing import Optional, Tuple
import pandas as pd
import matplotlib.pyplot as plt
from astropy.time import Time

def plot_lightcurve(
    source_id: str,
    measurements: pd.DataFrame,
    normalized: bool = True,
    figsize: Tuple[int, int] = (10, 6),
    baseline_epochs: int = 10,
    ese_period_days: Tuple[int, int] = (14, 180),
    save: bool = False,
    outfile: Optional[str] = None,
    plot_dpi: int = 150
) -> plt.Figure:
    """
    Plot light curve for ESE candidate analysis.
    
    Adapted from VAST Tools Source.plot_lightcurve()
    
    Args:
        source_id: Source identifier
        measurements: DataFrame with columns: dateobs, flux_norm, flux_err_norm
        normalized: Whether flux is normalized (default: True)
        figsize: Figure size
        baseline_epochs: Number of epochs for baseline establishment
        ese_period_days: ESE candidate period range (min, max) in days
        save: Save figure instead of returning
        outfile: Output filename
        plot_dpi: DPI for saved figure
        
    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Convert dates to MJD for plotting
    dates = pd.to_datetime(measurements['dateobs'])
    mjd = Time(dates).mjd
    
    # Plot measurements
    ax.errorbar(
        mjd,
        measurements['flux_norm'],
        yerr=measurements['flux_err_norm'],
        fmt='o',
        label='Normalized Flux'
    )
    
    # Highlight baseline period
    if len(measurements) >= baseline_epochs:
        baseline_mjd = mjd[:baseline_epochs]
        ax.axvspan(
            baseline_mjd.min(),
            baseline_mjd.max(),
            alpha=0.2,
            color='green',
            label='Baseline Period'
        )
    
    # Highlight ESE candidate periods (if detected)
    # TODO: Add ESE period detection logic
    
    ax.set_xlabel('MJD')
    ax.set_ylabel('Normalized Flux Density')
    ax.set_title(f'Light Curve: {source_id}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    if save:
        if outfile is None:
            outfile = f'{source_id}_lightcurve.png'
        fig.savefig(outfile, dpi=plot_dpi, bbox_inches='tight')
        plt.close(fig)
        return None
    
    return fig
```

### 7.2 Variability Metrics (Direct Copy)

```python
# Location: src/dsa110_contimg/photometry/variability.py

import numpy as np
import pandas as pd

def calculate_vs_metric(
    flux_a: float, flux_b: float, flux_err_a: float, flux_err_b: float
) -> float:
    """
    Calculate the Vs variability metric (t-statistic).
    
    Copied from VAST Tools vasttools/utils.py
    
    Reference: Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105
    
    Args:
        flux_a: Flux value "A"
        flux_b: Flux value "B"
        flux_err_a: Error of flux_a
        flux_err_b: Error of flux_b
        
    Returns:
        Vs metric (t-statistic)
    """
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)


def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """
    Calculate the M variability metric (modulation index).
    
    Copied from VAST Tools vasttools/utils.py
    
    Reference: Mooley et al. (2016), DOI: 10.3847/0004-637X/818/2/105
    
    Args:
        flux_a: Flux value "A"
        flux_b: Flux value "B"
        
    Returns:
        M metric (modulation index, fractional variability)
    """
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))


def pipeline_get_variable_metrics(df: pd.DataFrame) -> pd.Series:
    """
    Calculate variability metrics for a source.
    
    Adapted from VAST Tools vasttools/utils.py
    
    Args:
        df: DataFrame with grouped measurements (one source)
            Requires columns: flux_norm, flux_err_norm
        
    Returns:
        Series with metrics: v_norm, eta_norm
    """
    d = {}
    
    if df.shape[0] == 1:
        d['v_norm'] = 0.0
        d['eta_norm'] = 0.0
    else:
        # Fractional variability (std/mean)
        d['v_norm'] = df['flux_norm'].std() / df['flux_norm'].mean()
        
        # η metric (requires implementation of pipeline_get_eta_metric)
        # TODO: Implement eta metric calculation
        d['eta_norm'] = 0.0  # Placeholder
    
    return pd.Series(d)
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

**For Adapted Code:**
- Test light curve plotting with sample data
- Test variability metrics with known values
- Test edge cases (single epoch, empty data, etc.)

**Location:** `tests/unit/test_lightcurves.py`, `tests/unit/test_variability.py`

### 8.2 Integration Tests

**For Source Class:**
- Test database query integration
- Test plotting with real data
- Test ESE candidate workflow

**Location:** `tests/integration/test_source_analysis.py`

### 8.3 Reference Validation

**For Copied Functions:**
- Compare outputs with VAST Tools reference implementation
- Validate against published metrics (Mooley et al. 2016)
- Test with VAST Tools example data if available

---

## 9. Documentation

### 9.1 Code Documentation

- Add docstrings to all adapted functions
- Reference VAST Tools source in comments
- Document adaptations/changes from original

### 9.2 User Documentation

- Add light curve plotting guide
- Document variability metrics
- Add ESE candidate analysis workflow

**Location:** `docs/how-to/lightcurves.md`, `docs/reference/variability_metrics.md`

---

## 10. References

### 10.1 VAST Tools

- **Repository:** https://github.com/askap-vast/vast-tools
- **Documentation:** https://vast-survey.org/vast-tools/
- **License:** MIT
- **Version Analyzed:** 3.2.0-dev

### 10.2 Scientific References

- **Mooley et al. (2016):** Variability metrics (Vs, M, η)
  - DOI: 10.3847/0004-637X/818/2/105
  - Section 5: Variability Metrics

### 10.3 DSA-110 Documentation

- **Photometry Normalization:** `docs/concepts/science/photometry_normalization.md`
- **ESE Detection:** `docs/analysis/MOFFAT_ROTATION_ESE_SCIENCE.md`
- **Pipeline Overview:** `docs/concepts/pipeline_overview.md`

---

## 11. Conclusion

VAST Tools provides excellent reference implementations for:

1. **Light curve plotting** - Comprehensive, well-tested implementation
2. **Variability metrics** - Simple, pure functions ready to copy
3. **Source class pattern** - Clean architecture for source analysis
4. **Pipeline integration** - Patterns for loading and analyzing pipeline results

**Recommended Approach:**
- **Copy directly:** Variability metric functions (simple, pure functions)
- **Adapt:** Light curve plotting (needs DSA-110-specific features)
- **Inspire:** Source class pattern (create DSA-110-specific version)
- **Reference:** Architecture patterns (inform design decisions)

**Priority Order:**
1. Light curve plotting (high impact, immediate need)
2. Variability metrics (complementary to existing metrics)
3. Source class (improves analysis workflow)
4. Postage stamps (useful for verification)

**Estimated Total Effort:** 20-30 hours for high/medium priority items

---

**Last Updated:** 2025-11-12

