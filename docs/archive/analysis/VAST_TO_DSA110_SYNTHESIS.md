# VAST to DSA-110 Synthesis: Practical Implementation Guide

## Executive Summary

This document synthesizes VAST architecture patterns into actionable recommendations for the DSA-110 Continuum Imaging pipeline and dashboard. It maps VAST's proven patterns to DSA-110's specific needs, identifying what to adopt, adapt, or skip.

## Table of Contents

1. [Architecture Mapping](#architecture-mapping)
2. [Data Model Patterns](#data-model-patterns)
3. [Pipeline Processing Patterns](#pipeline-processing-patterns)
4. [Web Interface Patterns](#web-interface-patterns)
5. [Analysis & Exploration Patterns](#analysis--exploration-patterns)
6. [Implementation Priorities](#implementation-priorities)
7. [Key Differences & Adaptations](#key-differences--adaptations)

---

## Architecture Mapping

### VAST Pattern → DSA-110 Application

| VAST Pattern | DSA-110 Equivalent | Status | Notes |
|-------------|-------------------|--------|-------|
| Multi-run pipeline | Multiple calibration/imaging runs | ✅ Adopt | Track different processing strategies |
| Measurement → Source association | Detection → Source tracking | ✅ Adopt | Core to ESE detection |
| Forced extraction | Gap filling in light curves | ✅ Adopt | Critical for ESE monitoring |
| Measurement pairs | Variability metrics | ✅ Adopt | Essential for transient detection |
| Parquet/Arrow storage | Efficient data storage | ✅ Adopt | Already using Parquet |
| Django web framework | FastAPI backend | ⚠️ Adapt | Different framework, similar patterns |
| Bootstrap + DataTables | React + Material-UI | ⚠️ Adapt | Modern React patterns |
| Bokeh plots | Plotly.js | ⚠️ Adapt | Already using Plotly |
| JS9 image viewer | JS9 integration | ✅ Adopt | Already planned |
| Aladin Lite | Sky viewer | ✅ Adopt | Already planned |
| Generic table template | Reusable table component | ✅ Adopt | React component pattern |
| Detail pages | Source/image detail views | ✅ Adopt | Core analysis workflow |
| Comments system | Collaborative annotations | ✅ Adopt | Future enhancement |
| Favorites/bookmarks | User favorites | ✅ Adopt | Personal workflow |
| Config management | YAML config validation | ✅ Adopt | Already using YAML |
| Management commands | CLI tools | ✅ Adopt | Already have CLI |

---

## Data Model Patterns

### Core Entities

#### 1. Measurement Model (VAST) → Detection Model (DSA-110)

**VAST Structure:**
- Position (RA, Dec, errors, uncertainties)
- Flux (int, peak, errors, island ratios)
- Fit quality (chi-squared, spectral index)
- Local properties (RMS, SNR, compactness)
- Flags (forced, has_siblings, flag_c4)
- Component tracking (component_id, island_id)

**DSA-110 Adaptation:**
```python
class Detection(models.Model):
    # Position
    ra = models.FloatField()
    dec = models.FloatField()
    ra_err = models.FloatField()
    dec_err = models.FloatField()
    uncertainty_ew = models.FloatField()  # Quadratic sum
    uncertainty_ns = models.FloatField()  # Quadratic sum
    
    # Flux
    flux_int = models.FloatField()  # mJy
    flux_int_err = models.FloatField()
    flux_peak = models.FloatField()  # mJy/beam
    flux_peak_err = models.FloatField()
    
    # Fit quality
    chi_squared_fit = models.FloatField()
    spectral_index = models.FloatField(null=True)
    
    # Local properties
    local_rms = models.FloatField()  # mJy/beam
    snr = models.FloatField()
    compactness = models.FloatField()  # int/peak ratio
    
    # Flags
    forced = models.BooleanField(default=False)
    has_siblings = models.BooleanField(default=False)
    
    # Relationships
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    source = models.ManyToManyField('Source', through='Association')
    
    # Component tracking (if using source finder)
    component_id = models.CharField(max_length=64, null=True)
    island_id = models.CharField(max_length=64, null=True)
```

**Key Differences:**
- DSA-110 may use different source finder (not Selavy)
- Component/island IDs may differ
- May need additional fields for ESE-specific metrics

#### 2. Source Model (VAST) → Source Model (DSA-110)

**VAST Structure:**
- Weighted averages (position, uncertainties)
- Aggregate flux metrics (avg, max, min)
- Variability metrics (v, eta)
- Pair metrics aggregates (vs_max, m_max)
- Count metrics (n_meas, n_forced, etc.)
- New source detection (new_high_sigma)

**DSA-110 Adaptation:**
```python
class Source(models.Model):
    # Basic identification
    name = models.CharField(max_length=100, unique=True)
    run = models.ForeignKey(Run, on_delete=models.CASCADE, null=True)
    
    # Weighted averages from measurements
    wavg_ra = models.FloatField()
    wavg_dec = models.FloatField()
    wavg_uncertainty_ew = models.FloatField()
    wavg_uncertainty_ns = models.FloatField()
    
    # Aggregate flux metrics
    avg_flux_int = models.FloatField()
    avg_flux_peak = models.FloatField()
    max_flux_peak = models.FloatField()
    min_flux_peak = models.FloatField()
    
    # Variability metrics (for ESE detection)
    v_int = models.FloatField()
    v_peak = models.FloatField()
    eta_int = models.FloatField()
    eta_peak = models.FloatField()
    
    # ESE-specific metrics
    ese_probability = models.FloatField(null=True)
    ese_significance = models.FloatField(null=True)
    light_curve_completeness = models.FloatField()  # Fraction of epochs with detections
    
    # Pair metrics (2-epoch variability)
    vs_abs_significant_max_int = models.FloatField(default=0.0)
    m_abs_significant_max_int = models.FloatField(default=0.0)
    vs_abs_significant_max_peak = models.FloatField(default=0.0)
    m_abs_significant_max_peak = models.FloatField(default=0.0)
    
    # Count metrics
    n_meas = models.IntegerField()
    n_meas_forced = models.IntegerField(default=0)
    n_rel = models.IntegerField(default=0)  # Related sources
    
    # Flags
    new = models.BooleanField(default=False)
    ese_candidate = models.BooleanField(default=False)
    
    # Relationships
    related = models.ManyToManyField('self', through='RelatedSource', symmetrical=False)
    tags = TagField(...)  # For categorization
    
    def get_measurement_pairs(self):
        """Calculate measurement pair metrics for variability analysis."""
        # Similar to VAST implementation
        pass
```

**Key Additions for DSA-110:**
- ESE-specific probability and significance
- Light curve completeness metric
- ESE candidate flag
- May need additional metrics for continuum imaging

#### 3. Association Model

**VAST Pattern:**
- Many-to-many through Association table
- Distance metrics (d2d, dr)
- Flexible association methods

**DSA-110 Adaptation:**
```python
class Association(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    detection = models.ForeignKey(Detection, on_delete=models.CASCADE)
    
    # Distance metrics
    d2d = models.FloatField(default=0.0)  # Astronomical distance (arcsec)
    dr = models.FloatField(default=0.0)   # De Ruiter radius (if using)
    
    # Association method used
    method = models.CharField(max_length=20)  # 'basic', 'advanced', 'deruiter'
    
    class Meta:
        unique_together = ['source', 'detection']
```

#### 4. RelatedSource Model

**VAST Pattern:**
- Self-referential many-to-many
- Through table with unique constraint

**DSA-110 Adaptation:**
```python
class RelatedSource(models.Model):
    from_source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='related_from')
    to_source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='related_to')
    
    # Relationship type
    relation_type = models.CharField(max_length=50)  # 'component', 'extended', etc.
    
    class Meta:
        unique_together = ['from_source', 'to_source']
```

### Database Optimizations

**VAST Patterns to Adopt:**
1. **Parquet storage**: Store measurements in Parquet files per image
2. **Arrow format**: For very large datasets (faster than Parquet)
3. **Spatial indexing**: Q3C plugin for PostgreSQL (or PostGIS)
4. **Batch operations**: Bulk create/update for performance
5. **Lazy loading**: Load measurement pairs on-demand

**DSA-110 Implementation:**
- Already using Parquet for some data
- Consider Arrow for measurement pairs
- Use spatial indexes for cone searches
- Implement bulk operations for large datasets

---

## Pipeline Processing Patterns

### 1. Association Algorithms

**VAST Methods:**
- **Basic**: Astropy nearest match
- **Advanced**: Astropy search around sky (all potential matches)
- **De Ruiter**: Advanced with De Ruiter radius metric

**DSA-110 Adaptation:**
```python
def associate_detections(
    detections_df: pd.DataFrame,
    method: str = 'basic',
    radius: float = 5.0,  # arcsec
    deruiter_radius: float = None,
    deruiter_beamwidth_limit: float = None,
) -> pd.DataFrame:
    """
    Associate detections into sources.
    
    Methods:
    - 'basic': Nearest neighbor match
    - 'advanced': Search around all potential matches
    - 'deruiter': Advanced with De Ruiter radius
    """
    if method == 'basic':
        return basic_association(detections_df, radius)
    elif method == 'advanced':
        return advanced_association(detections_df, radius)
    elif method == 'deruiter':
        return deruiter_association(
            detections_df, 
            deruiter_radius, 
            deruiter_beamwidth_limit
        )
```

**Key Considerations:**
- DSA-110 may need custom association for ESE detection
- Consider temporal constraints (same epoch)
- May need to handle extended sources differently

### 2. Forced Extraction

**VAST Pattern:**
- Fill gaps in light curves
- Extract flux at known positions
- Handle edge cases and NaN values

**DSA-110 Adaptation:**
```python
def forced_extraction(
    sources: pd.DataFrame,
    image_path: str,
    background_path: str,
    noise_path: str,
    edge_buffer: float = 1.0,
    cluster_threshold: float = 3.0,
    allow_nan: bool = False,
) -> pd.DataFrame:
    """
    Extract flux for sources at known positions in image.
    
    Critical for ESE detection - need complete light curves.
    """
    # Similar to VAST implementation
    # Use forced_phot library or custom implementation
    pass
```

**Key Considerations:**
- Essential for ESE monitoring
- Need to handle DSA-110 specific image formats
- May need different edge detection logic

### 3. Measurement Pair Metrics

**VAST Pattern:**
- Calculate 2-epoch variability metrics (Vs, m)
- Parallel processing with Dask
- Aggregate metrics per source

**DSA-110 Adaptation:**
```python
def calculate_measurement_pair_metrics(
    detections_df: pd.DataFrame,
    n_cpu: int = 0,
    max_partition_mb: int = 15,
) -> pd.DataFrame:
    """
    Calculate 2-epoch variability metrics for all detection pairs.
    
    Returns DataFrame with columns:
    - source_id
    - detection_a_id, detection_b_id
    - vs_peak, vs_int (variability t-statistic)
    - m_peak, m_int (modulation index)
    """
    # Use VAST's implementation as reference
    # Adapt for DSA-110 detection model
    pass

def calculate_vs_metric(
    flux_a: float, flux_b: float, 
    flux_err_a: float, flux_err_b: float
) -> float:
    """T-statistic for variability (Mooley et al. 2016)."""
    return (flux_a - flux_b) / np.hypot(flux_err_a, flux_err_b)

def calculate_m_metric(flux_a: float, flux_b: float) -> float:
    """Modulation index (fractional variability)."""
    return 2 * ((flux_a - flux_b) / (flux_a + flux_b))
```

**Key Considerations:**
- Essential for ESE detection
- May need additional metrics specific to ESE
- Consider temporal weighting

### 4. Source Statistics Calculation

**VAST Pattern:**
- Parallel groupby for aggregate metrics
- Weighted averages
- Nearest neighbor calculation
- Pair metrics aggregation

**DSA-110 Adaptation:**
```python
def calculate_source_statistics(
    detections_df: pd.DataFrame,
    sources_df: pd.DataFrame,
    n_cpu: int = 0,
    max_partition_mb: int = 15,
) -> pd.DataFrame:
    """
    Calculate aggregate statistics for sources.
    
    Includes:
    - Weighted averages (position, uncertainties)
    - Aggregate flux metrics (avg, max, min)
    - Variability metrics (v, eta)
    - Nearest neighbor distance
    - Pair metrics aggregates
    """
    # Use VAST's parallel_groupby pattern
    # Adapt for DSA-110 specific metrics
    pass
```

### 5. Final Operations

**VAST Pattern:**
- Bulk upload sources
- Create associations
- Create related sources
- Export to Parquet
- Calculate pair metrics

**DSA-110 Adaptation:**
```python
def finalize_pipeline_run(
    run: Run,
    detections_df: pd.DataFrame,
    sources_df: pd.DataFrame,
    calculate_pairs: bool = True,
    add_mode: bool = False,
) -> Tuple[int, int]:
    """
    Finalize pipeline run:
    1. Calculate source statistics
    2. Upload sources to database
    3. Create associations
    4. Calculate measurement pairs (optional)
    5. Export to Parquet
    
    Returns: (n_sources, n_new_sources)
    """
    # Follow VAST's final_operations pattern
    # Adapt for DSA-110 workflow
    pass
```

---

## Web Interface Patterns

### 1. Generic Table Component

**VAST Pattern:**
- Single reusable template for all tables
- Dynamic columns from view context
- DataTables AJAX integration
- Export buttons

**DSA-110 React Adaptation:**
```typescript
// frontend/src/components/GenericTable.tsx

interface TableColumn {
  field: string;
  label: string;
  sortable?: boolean;
  searchable?: boolean;
  render?: (value: any, row: any) => React.ReactNode;
  link?: (row: any) => string;
}

interface GenericTableProps {
  apiEndpoint: string;
  columns: TableColumn[];
  title?: string;
  description?: string;
  searchable?: boolean;
  exportable?: boolean;
}

export function GenericTable({
  apiEndpoint,
  columns,
  title,
  description,
  searchable = true,
  exportable = true,
}: GenericTableProps) {
  // Use TanStack Table (React Table) or AG Grid
  // Similar to VAST's generic_table.html pattern
  // Support DataTables-like features:
  // - Server-side pagination
  // - Search/filter
  // - Column visibility
  // - Export (CSV, Excel)
  // - Sorting
}
```

**Key Features:**
- Server-side pagination (like DataTables)
- Column configuration from props
- Link generation for detail pages
- Export functionality
- Responsive design

### 2. Detail Page Pattern

**VAST Pattern:**
- Three-column layout: Details, Visualization, Comments
- Collapsible sections
- Previous/Next navigation
- Embedded visualizations

**DSA-110 React Adaptation:**
```typescript
// frontend/src/pages/SourceDetailPage.tsx

export function SourceDetailPage({ sourceId }: { sourceId: string }) {
  const { data: source } = useSourceDetail(sourceId);
  
  return (
    <Container maxWidth="xl">
      <Grid container spacing={3}>
        {/* Column 1: Details */}
        <Grid item xs={12} md={4}>
          <SourceDetailsCard source={source} />
        </Grid>
        
        {/* Column 2: Visualization */}
        <Grid item xs={12} md={4}>
          <SourceVisualizationCard source={source} />
          {/* Aladin Lite or custom sky viewer */}
        </Grid>
        
        {/* Column 3: Comments/Annotations */}
        <Grid item xs={12} md={4}>
          <CommentsPanel sourceId={sourceId} />
        </Grid>
        
        {/* Full width: Light curve */}
        <Grid item xs={12}>
          <CollapsibleSection title="Light Curve">
            <SourceLightCurve sourceId={sourceId} />
          </CollapsibleSection>
        </Grid>
        
        {/* Full width: Detections table */}
        <Grid item xs={12}>
          <CollapsibleSection title="Detections">
            <GenericTable
              apiEndpoint={`/api/sources/${sourceId}/detections`}
              columns={detectionColumns}
            />
          </CollapsibleSection>
        </Grid>
      </Grid>
      
      {/* Navigation */}
      <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
        <Button onClick={goToPrevious}>Previous</Button>
        <Button onClick={goToNext}>Next</Button>
      </Box>
    </Container>
  );
}
```

### 3. Query Interface

**VAST Pattern:**
- Complex query builder
- Filter by multiple criteria
- Save queries
- Export results

**DSA-110 Adaptation:**
```typescript
// frontend/src/components/SourceQueryBuilder.tsx

export function SourceQueryBuilder() {
  // Similar to VAST's source_query.html
  // Use React JSON Schema Form for dynamic forms
  // Support:
  // - Position (RA/Dec, radius)
  // - Flux range
  // - Variability metrics
  // - ESE candidate flag
  // - Date range
  // - Run selection
  // - Tags
}
```

### 4. Visualization Components

**VAST Patterns:**
- Bokeh plots → Plotly.js (already using)
- JS9 image viewer → JS9 integration
- Aladin Lite → Aladin Lite integration
- Datashader for large datasets → Plotly with WebGL

**DSA-110 Implementation:**
```typescript
// Already have Plotly integration
// Add JS9 and Aladin Lite

// frontend/src/components/JS9ImageViewer.tsx
export function JS9ImageViewer({ imagePath }: { imagePath: string }) {
  // Integrate JS9 for FITS viewing
}

// frontend/src/components/AladinSkyViewer.tsx
export function AladinSkyViewer({ 
  ra, dec, sources 
}: { 
  ra: number; 
  dec: number; 
  sources: Source[] 
}) {
  // Integrate Aladin Lite for sky visualization
}
```

---

## Analysis & Exploration Patterns

### 1. Eta-V Plot

**VAST Pattern:**
- Plot eta vs V metrics
- Identify variable sources
- Datashader for large datasets

**DSA-110 Adaptation:**
```typescript
// frontend/src/components/EtaVPlot.tsx

export function EtaVPlot({ sources }: { sources: Source[] }) {
  // Use Plotly.js
  // Color by ESE probability or significance
  // Interactive selection
  // Link to source detail pages
}
```

### 2. Light Curve Visualization

**VAST Pattern:**
- Interactive Bokeh plots
- Hover tooltips with cutouts
- Measurement pair graph

**DSA-110 Adaptation:**
```typescript
// frontend/src/components/SourceLightCurve.tsx

export function SourceLightCurve({ sourceId }: { sourceId: string }) {
  // Use Plotly.js
  // Show forced vs detected measurements differently
  // Interactive hover with image cutouts
  // Link to measurement detail pages
  // Show ESE model fits if available
}
```

### 3. Catalog Comparison

**VAST Pattern:**
- External catalog queries
- Match radius
- Offset calculation

**DSA-110 Adaptation:**
```typescript
// frontend/src/components/CatalogComparison.tsx

export function CatalogComparison({ sourceId }: { sourceId: string }) {
  // Compare against:
  // - NVSS
  // - VLASS
  // - FIRST
  // - Custom catalogs
  // Show matches with offsets
  // Visualize on sky viewer
}
```

---

## Implementation Priorities

### Phase 1: Core Data Model (Weeks 1-2)
1. ✅ Implement Detection model
2. ✅ Implement Source model
3. ✅ Implement Association model
4. ✅ Implement RelatedSource model
5. ✅ Set up Parquet storage

### Phase 2: Pipeline Processing (Weeks 3-4)
1. ✅ Implement association algorithms
2. ✅ Implement forced extraction
3. ✅ Implement measurement pair metrics
4. ✅ Implement source statistics calculation
5. ✅ Implement final operations

### Phase 3: Web Interface Foundation (Weeks 5-6)
1. ✅ Generic table component
2. ✅ Source detail page
3. ✅ Image detail page
4. ✅ Query interface
5. ✅ Basic visualizations

### Phase 4: Advanced Features (Weeks 7-8)
1. ✅ Light curve visualization
2. ✅ Eta-V plot
3. ✅ Catalog comparison
4. ✅ Comments/annotations
5. ✅ Favorites/bookmarks

### Phase 5: Analysis Workspace (Weeks 9-12)
1. ✅ Golden Layout integration
2. ✅ Analysis tools (from ANTICIPATORY_DASHBOARD_IMPLEMENTATION.md)
3. ✅ Reproducibility system
4. ✅ Trust indicators

---

## Key Differences & Adaptations

### 1. Framework Differences

**VAST:** Django (server-side rendering)
**DSA-110:** FastAPI + React (API + SPA)

**Adaptations:**
- VAST templates → React components
- Django views → FastAPI endpoints
- Django forms → React forms with validation
- Django admin → Custom admin interface (or keep Django admin for backend)

### 2. Science Goals

**VAST:** Variables and Slow Transients
**DSA-110:** ESE Detection + Continuum Imaging

**Adaptations:**
- Add ESE-specific metrics
- Add ESE probability calculations
- Add ESE model fitting
- May need different association logic
- May need different visualization priorities

### 3. Data Volume

**VAST:** Large-scale survey (millions of sources)
**DSA-110:** Focused observations (thousands to tens of thousands)

**Adaptations:**
- May not need Datashader (smaller datasets)
- Can use more interactive visualizations
- Less need for Arrow format (Parquet sufficient)
- Can load more data into memory

### 4. Workflow Differences

**VAST:** Batch processing, manual review
**DSA-110:** Streaming pipeline, autonomous + manual override

**Adaptations:**
- Real-time updates (WebSocket)
- Autonomous operation monitoring
- Manual override capabilities
- Streaming-specific metrics

---

## Next Steps

1. **Review this synthesis** with team
2. **Prioritize features** based on science goals
3. **Create detailed implementation plans** for each phase
4. **Set up development environment** with VAST-inspired patterns
5. **Begin Phase 1** implementation

---

## References

- VAST Architecture Analysis: `VAST_ARCHITECTURE_ANALYSIS.md`
- Anticipatory Dashboard Implementation: `ANTICIPATORY_DASHBOARD_IMPLEMENTATION.md`
- VAST Pipeline Repository: `archive/references/vast/vast-pipeline/`
- VAST Tools Repository: `archive/references/vast/vast-tools/`

