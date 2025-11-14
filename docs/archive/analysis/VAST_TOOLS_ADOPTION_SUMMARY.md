# VAST Tools Adoption Summary

**Quick Reference:** Key features from VAST Tools that can be adopted by DSA-110

---

## Priority Matrix

| Feature | Priority | Effort | Impact | Status |
|---------|----------|--------|--------|--------|
| **Source Class Pattern** | High | 2-3 weeks | High | ❌ Missing |
| **Light Curve Plotting** | High | 1 week | High | ❌ Missing |
| **Variability Metrics (η, Vs, m)** | Medium | 1 week | Medium | ⚠️ Partial (V exists) |
| **Postage Stamps** | Medium | 2 weeks | Medium | ❌ Missing |
| **External Catalogs** | Low-Medium | 1-2 weeks | Low | ⚠️ Partial (NVSS/VLASS) |

---

## Quick Implementation Guide

### 1. Source Class (High Priority)

**Create:** `src/dsa110_contimg/photometry/source.py`

**Key Features:**
- Load measurements from `photometry_timeseries` table
- Properties: `coord`, `n_epochs`, `detections`
- Methods: `plot_lightcurve()`, `calc_variability_metrics()`, `show_all_cutouts()`

**Usage:**
```python
from dsa110_contimg.photometry.source import Source

source = Source(
    source_id="NVSS J123456+420312",
    ra_deg=123.456,
    dec_deg=42.0312,
    products_db=Path("state/products.sqlite3")
)

# Plot light curve
fig = source.plot_lightcurve(highlight_baseline=True)

# Get variability metrics
metrics = source.calc_variability_metrics()
```

### 2. Light Curve Plotting (High Priority)

**Create:** `src/dsa110_contimg/qa/lightcurves.py` (or add to Source class)

**Key Features:**
- Normalized flux plotting
- Baseline period highlighting (first 10 epochs)
- ESE candidate period highlighting (14-180 days)
- Error bars and detection/limit distinction
- Multiple time axes (datetime, MJD)

**Adopt from:** `vasttools/source.py::Source.plot_lightcurve()`

### 3. Variability Metrics (Medium Priority)

**Create:** `src/dsa110_contimg/photometry/variability.py`

**Metrics to Add:**
- **η metric**: Weighted variance (adopt from `vasttools/utils.py::pipeline_get_eta_metric()`)
- **Vs metric**: Two-epoch t-statistic (adopt from `vasttools/utils.py::calculate_vs_metric()`)
- **m metric**: Modulation index (adopt from `vasttools/utils.py::calculate_m_metric()`)

**Update:** `variability_stats` table to include `eta_metric` column

### 4. Postage Stamps (Medium Priority)

**Create:** `src/dsa110_contimg/qa/postage_stamps.py`

**Key Features:**
- Image cutout creation around source position
- All-epoch grid visualization
- Z-scale normalization
- Customizable size and layout

**Adopt from:** `vasttools/source.py::Source.show_all_png_cutouts()`

### 5. External Catalog Integration (Low-Medium Priority)

**Create:** `src/dsa110_contimg/catalog/external.py`

**Catalogs to Add:**
- SIMBAD (object identification)
- NED (extragalactic database)
- Gaia (astrometry)

**Adopt from:** `vasttools/utils.py::simbad_search()`, `vasttools/source.py::Source.simbad_search()`

---

## Code Patterns to Adopt

### Pattern 1: Source Class Structure
```python
class Source:
    def __init__(self, source_id, ra_deg, dec_deg, products_db):
        self.source_id = source_id
        self.ra_deg = ra_deg
        self.dec_deg = dec_deg
        self.measurements = self._load_measurements()
    
    @property
    def coord(self) -> SkyCoord:
        return SkyCoord(self.ra_deg, self.dec_deg, unit=(u.deg, u.deg))
    
    def plot_lightcurve(self, ...) -> Figure:
        # Implementation
```

### Pattern 2: Variability Metrics
```python
def calculate_eta_metric(df: pd.DataFrame) -> float:
    """Weighted variance metric."""
    weights = 1. / df['flux_err'].values**2
    fluxes = df['flux'].values
    eta = (len(df) / (len(df) - 1)) * (
        (weights * fluxes**2).mean() - (
            (weights * fluxes).mean()**2 / weights.mean()
        )
    )
    return eta
```

### Pattern 3: Light Curve Plotting
```python
def plot_lightcurve(self, highlight_baseline=True, ...):
    # Plot flux with error bars
    ax.errorbar(time, flux, yerr=flux_err, ...)
    
    # Highlight baseline
    if highlight_baseline:
        ax.axvspan(baseline_start, baseline_end, alpha=0.2, color='green')
    
    # Highlight ESE period
    if highlight_ese_period:
        ax.axvspan(ese_start, ese_end, alpha=0.1, color='red')
```

---

## Integration Points

### API Endpoints
```python
@router.get("/api/sources/{source_id}/lightcurve")
async def get_source_lightcurve(source_id: str):
    source = Source(source_id=source_id, products_db=products_db)
    return source.plot_lightcurve()

@router.get("/api/sources/{source_id}/variability")
async def get_source_variability(source_id: str):
    source = Source(source_id=source_id, products_db=products_db)
    return source.calc_variability_metrics()
```

### ESE Detection Workflow
```python
def analyze_ese_candidate(source_id: str):
    source = Source(source_id=source_id, products_db=products_db)
    
    # Generate visualizations
    lightcurve = source.plot_lightcurve(highlight_ese_period=True)
    postage_stamps = source.show_all_cutouts()
    
    # Get metrics
    metrics = source.calc_variability_metrics()
    
    return {
        'metrics': metrics,
        'lightcurve': lightcurve,
        'postage_stamps': postage_stamps
    }
```

---

## Dependencies

### Required
- **astroquery**: External catalog queries
  ```bash
  pip install astroquery
  ```

### Optional
- **bokeh**: Interactive plots (can add later)
  ```bash
  pip install bokeh
  ```

---

## Testing Strategy

### Unit Tests
- Source class creation and properties
- Light curve plotting
- Variability metric calculations
- Postage stamp creation

### Integration Tests
- Source class with real database
- API endpoints
- ESE detection workflow integration

---

## Timeline

**Phase 1 (High Priority):** 2-3 weeks
- Source class
- Light curve plotting
- Basic variability metrics

**Phase 2 (Medium Priority):** 2 weeks
- Postage stamps
- Enhanced variability metrics

**Phase 3 (Low-Medium Priority):** 1-2 weeks
- External catalog integration

**Total:** 5-7 weeks

---

## References

- **Detailed Comparison:** `docs/analysis/VAST_TOOLS_DSA110_DETAILED_COMPARISON.md`
- **VAST Tools Review:** `archive/references/vast-tools/VAST_TOOLS_CODEBASE_REVIEW.md`
- **VAST Tools Code:** `archive/references/vast-tools/vasttools/`

