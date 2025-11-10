# VAST Architecture Deep Dive Analysis

## Executive Summary

This document provides a comprehensive analysis of the VAST (Variables and Slow Transients) pipeline architecture, focusing on patterns, design decisions, and implementation details that are directly applicable to the DSA-110 Continuum Imaging dashboard. VAST is a radio continuum imaging pipeline with similar science goals to DSA-110, making it an excellent reference architecture.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Patterns](#architecture-patterns)
3. [Database Design](#database-design)
4. [Web Interface Architecture](#web-interface-architecture)
5. [Analysis Tools & Workflows](#analysis-tools--workflows)
6. [Visualization Patterns](#visualization-patterns)
7. [Key Design Decisions](#key-design-decisions)
8. [Recommendations for DSA-110](#recommendations-for-dsa-110)

---

## System Overview

### Core Components

VAST consists of several interconnected repositories:

1. **vast-pipeline** - Main Django web application and pipeline processing
2. **vast-tools** - Python library for interactive analysis and data exploration
3. **vaster-webapp** - Django web app for transient candidate classification
4. **vast-post-processing** - Post-processing utilities
5. **vast-fastdetection** - Fast transient detection pipeline
6. **dstools** - Data science tools for CASA/MS manipulation
7. **forced_phot** - Forced photometry module

### Technology Stack

**Backend:**
- Django 3.2+ (web framework)
- PostgreSQL 12+ with Q3C plugin (spatial queries)
- Django REST Framework (API)
- Django Q (async task processing)
- Dask (parallel processing)
- Astropy (astronomical calculations)
- Pandas (data manipulation)

**Frontend:**
- Bootstrap 4 (UI framework)
- DataTables (interactive tables)
- Bokeh 2.4.2 (interactive plots)
- JS9 (FITS image viewer)
- Aladin Lite (sky viewer)
- D3.js (custom visualizations)
- Holoviews + Datashader (large dataset visualization)

**Data Formats:**
- FITS (images)
- Parquet/Arrow (measurements)
- SQLite/PostgreSQL (metadata)

---

## Architecture Patterns

### 1. Multi-Run Pipeline Architecture

**Pattern:** Each pipeline run is completely independent and self-aware.

**Implementation:**
- Images are shared across runs (many-to-many relationship)
- Each run has its own configuration and results
- Runs can be compared side-by-side
- Users can create multiple runs with different parameters

**Key Insight:** This allows experimentation without affecting existing results.

**DSA-110 Application:**
- Support multiple calibration strategies
- Compare different imaging parameters
- Track different processing epochs
- Enable A/B testing of algorithms

### 2. Measurement-Source Association Model

**Pattern:** Two-tier data model: Measurements → Sources

**Structure:**
```
Image → Measurement → Source
```

- **Measurement**: Single detection from one image
- **Source**: Group of measurements representing the same astrophysical object
- **Association**: Algorithm that groups measurements into sources

**Key Features:**
- Measurements can belong to multiple sources (many-to-many)
- Sources track aggregate statistics
- Association methods: basic, advanced, De Ruiter, epoch-based
- Forced measurements fill gaps in light curves

**DSA-110 Application:**
- Track individual detections per image
- Associate detections across epochs
- Build source light curves
- Support forced photometry for non-detections

### 3. Commentable Model Pattern

**Pattern:** Generic foreign keys for comments on any model.

**Implementation:**
```python
class CommentableModel(models.Model):
    comment = GenericRelation(Comment, ...)
    
class Comment(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
```

**Benefits:**
- Comments on Runs, Sources, Images, Measurements
- User avatars from GitHub OAuth
- Threaded discussions
- Audit trail

**DSA-110 Application:**
- Annotate problematic sources
- Document calibration decisions
- Track investigation notes
- Collaborative analysis

### 4. Tag System

**Pattern:** Flexible tagging with autocomplete.

**Implementation:**
- Django-tagulous for tag management
- Autocomplete via AJAX
- Tags filterable in queries
- User-specific favorites

**DSA-110 Application:**
- Tag ESE candidates
- Mark calibration issues
- Organize sources by science case
- Personal favorites system

### 5. Async Task Processing

**Pattern:** Django Q for background jobs.

**Use Cases:**
- Pipeline processing
- Arrow file generation
- Image cutout creation
- Large queries

**DSA-110 Application:**
- Streaming pipeline monitoring
- Background calibration
- Mosaic generation
- Report generation

---

## Database Design

### Core Models

#### Run
- Represents a single pipeline execution
- Tracks status: INI, QUE, RUN, END, ERR, RES, DEL
- Stores configuration as YAML
- Links to user who created it
- Tracks statistics: n_images, n_sources, n_measurements

#### Image
- FITS image metadata
- Many-to-many with Runs
- Stores: datetime, frequency, RA/Dec, RMS, beam properties
- Unique by filename

#### Measurement
- Single source detection from an image
- Links to Image and Source (many-to-many)
- Stores: position, flux, errors, SNR, forced flag
- Can belong to multiple sources

#### Source
- Aggregated measurements representing one object
- Calculated statistics: weighted avg position, flux stats, variability metrics
- Tracks: n_meas, n_rel, n_sibl, new source flag
- Variability metrics: η, V, Vs, m

### Key Relationships

```
Run ←→ Image (many-to-many)
Image → Measurement (one-to-many)
Measurement ←→ Source (many-to-many)
Source → Source (self-referential for relations)
```

### Spatial Queries

**Q3C Plugin:**
- PostgreSQL extension for fast spatial queries
- Cone searches on RA/Dec
- Efficient for large catalogs
- Used extensively in source queries

**DSA-110 Application:**
- Fast source queries by position
- Crossmatch with external catalogs
- Spatial clustering analysis
- Mosaic footprint queries

---

## Web Interface Architecture

### Page Structure

#### 1. Homepage
- Welcome message
- Quick links to common pages
- Pipeline run overview

#### 2. Pipeline Runs (`/piperuns/`)
- List all runs with DataTables
- Create new run via form
- Status indicators
- Links to run detail pages

**Key Features:**
- Form validation
- Config file upload/editing
- Run status tracking
- Delete/restore functionality

#### 3. Run Detail (`/piperuns/<id>/`)
- Run configuration display
- Image list (DataTables)
- Log file viewer
- Comments section
- Action buttons: Process, Delete, Generate Arrow

**Key Features:**
- Config validation
- Real-time status updates
- Sky region visualization (D3 Celestial)
- Arrow file generation

#### 4. Source Query (`/sources/query/`)
- Advanced filtering form
- Cone search with name resolver
- Metric thresholds
- Tag filtering
- Results table (DataTables)

**Key Features:**
- Coordinate validation
- SIMBAD/NED name resolution
- Session-based result storage
- Export to η-V analysis

#### 5. Source Detail (`/sources/<id>/`)
- Source information panel
- Light curve (Bokeh)
- Postage stamps (JS9)
- Sky viewer (Aladin Lite)
- Measurements table
- Related sources
- Comments and tags

**Key Features:**
- Interactive light curve
- Image cutouts on demand
- External catalog overlays
- Previous/Next navigation
- Favorite button

#### 6. η-V Analysis (`/sources/query/plot/`)
- Interactive scatter plot (Bokeh)
- Gaussian fit with sigma cut
- Source selection → light curve
- Datashader for large datasets

**Key Features:**
- Interactive point selection
- Dynamic light curve loading
- Configurable sigma threshold
- Performance optimization for >20k sources

### UI Components

#### DataTables Integration
- Server-side processing for large datasets
- Custom column rendering
- Search and filtering
- Export functionality
- Column visibility controls

**Implementation:**
```python
datatable = {
    'api': reverse('api_sources-list') + '?format=datatables',
    'colsFields': colsfields,
    'colsNames': [...],
    'search': True,
    'order': [1, 'asc']
}
```

#### Bokeh Plots
- Light curves with error bars
- η-V scatter plots
- Interactive hover/selection
- Custom tooltips
- Linked plots

**Key Pattern:**
- Server-side plot generation
- JSON embedding in templates
- Client-side interactivity
- Dynamic updates via AJAX

#### JS9 Integration
- FITS image display
- Cutout generation
- Multiple image support
- Coordinate overlays

**Pattern:**
- Lazy loading of cutouts
- Caching in database
- Multiple size options
- PNG fallback

#### Aladin Lite Integration
- Sky survey overlays
- Catalog overlays (VizieR)
- Coordinate display
- Survey switching

**Pattern:**
- Async script loading
- Dynamic catalog loading
- Color-coded catalogs
- Configurable radius

---

## Analysis Tools & Workflows

### 1. Source Query Workflow

**Steps:**
1. User defines query criteria (position, metrics, tags)
2. Form validation and coordinate resolution
3. Database query with filters
4. Results stored in session
5. Display in DataTables
6. Option to export to η-V analysis

**Key Features:**
- Real-time coordinate validation
- Name resolver integration (SIMBAD, NED)
- Complex filter combinations
- Session persistence

### 2. η-V Analysis Workflow

**Steps:**
1. Load sources from query session
2. Filter bad sources (n_meas=1, η=0, V=0)
3. Calculate Gaussian fits
4. Generate interactive plot
5. User selects source → load light curve
6. Display source info and crossmatches

**Key Features:**
- Automatic bad source filtering
- Configurable sigma threshold
- Datashader for performance
- Dynamic source loading

### 3. Source Investigation Workflow

**Steps:**
1. Navigate to source detail page
2. View light curve and postage stamps
3. Check external catalogs (Aladin)
4. Review measurements table
5. Check related sources
6. Add comments/tags
7. Navigate to next/previous source

**Key Features:**
- Comprehensive source view
- Multiple visualization types
- External catalog integration
- Collaborative annotations

### 4. Pipeline Run Workflow

**Steps:**
1. Create run with configuration
2. Upload images and catalogs
3. Validate configuration
4. Initialize run
5. Process run (async)
6. Monitor status
7. View results
8. Generate Arrow files (optional)

**Key Features:**
- Configuration validation
- Async processing
- Status tracking
- Error handling
- Log file access

---

## Visualization Patterns

### 1. Light Curve Visualization

**Technology:** Bokeh

**Features:**
- Time series plot
- Error bars
- Method coloring (Selavy vs Forced)
- Interactive hover
- Cutout links
- Measurement pair graph

**Pattern:**
```python
def plot_lightcurve(source, vs_abs_min=4.3, m_abs_min=0.26):
    # Query measurements
    # Create Bokeh figure
    # Add scatter with hover
    # Add error bars
    # Create measurement pair graph
    # Return Row layout
```

**DSA-110 Application:**
- ESE candidate light curves
- Source variability tracking
- Calibration monitoring
- Forced photometry results

### 2. η-V Scatter Plot

**Technology:** Bokeh + Datashader

**Features:**
- Log-log plot
- Gaussian fit overlay
- Sigma cut region
- Color by n_meas
- Interactive selection
- Performance optimization

**Pattern:**
- Use Datashader for >20k sources
- Interactive points only in transient region
- Dynamic light curve loading
- Configurable thresholds

**DSA-110 Application:**
- Variability analysis
- Transient identification
- Source classification
- Quality assessment

### 3. Sky Visualization

**Technology:** Aladin Lite + D3 Celestial

**Features:**
- Survey overlays
- Catalog overlays
- Coordinate display
- Field footprints
- Source positions

**Pattern:**
- Async Aladin loading
- Dynamic catalog queries
- Color-coded overlays
- Configurable surveys

**DSA-110 Application:**
- Pointing visualization
- Source distribution
- Mosaic coverage
- External catalog comparison

### 4. Image Display

**Technology:** JS9

**Features:**
- FITS image rendering
- Cutout generation
- Multiple images
- Coordinate overlays
- Scaling/stretching

**Pattern:**
- Lazy cutout generation
- Database caching
- Multiple size options
- PNG fallback

**DSA-110 Application:**
- Image QA display
- Source postage stamps
- Mosaic visualization
- Calibration comparison

---

## Key Design Decisions

### 1. Separation of Pipeline and Web App

**Decision:** Pipeline processing is separate from web interface.

**Rationale:**
- Pipeline can run standalone (CLI)
- Web app provides monitoring and analysis
- Clear separation of concerns
- Easier testing and deployment

**DSA-110 Application:**
- Keep streaming pipeline independent
- Dashboard monitors and controls
- Clear API boundaries
- Flexible deployment

### 2. Many-to-Many Relationships

**Decision:** Images ↔ Runs, Measurements ↔ Sources

**Rationale:**
- Avoid data duplication
- Enable comparison across runs
- Flexible association methods
- Efficient storage

**DSA-110 Application:**
- Share images across runs
- Compare calibration strategies
- Flexible source association
- Efficient data management

### 3. Session-Based Query Results

**Decision:** Store query results in Django session.

**Rationale:**
- Fast navigation between pages
- No database overhead
- User-specific results
- Simple implementation

**Trade-off:**
- Session size limits
- Not persistent across sessions
- Server memory usage

**DSA-110 Application:**
- Consider Redis for larger sessions
- Or database-backed query results
- User-specific workspaces

### 4. Arrow/Parquet for Measurements

**Decision:** Use Arrow format for large measurement datasets.

**Rationale:**
- Fast columnar access
- Efficient for analysis
- Compatible with Pandas/Dask
- Smaller file size

**DSA-110 Application:**
- Export measurements to Arrow
- Fast analysis queries
- Integration with analysis tools
- Efficient data transfer

### 5. Generic Comments System

**Decision:** Use Django ContentTypes for comments.

**Rationale:**
- Reusable across models
- Simple implementation
- Flexible annotation
- Easy to extend

**DSA-110 Application:**
- Comments on all entities
- Collaborative analysis
- Audit trail
- Knowledge sharing

### 6. Tag System

**Decision:** Use django-tagulous for tagging.

**Rationale:**
- Flexible tagging
- Autocomplete support
- Query filtering
- User-friendly

**DSA-110 Application:**
- Organize sources
- Mark candidates
- Filter queries
- Personal organization

### 7. Async Task Processing

**Decision:** Use Django Q for background tasks.

**Rationale:**
- Non-blocking operations
- Scalable processing
- Status tracking
- Error handling

**DSA-110 Application:**
- Pipeline monitoring
- Background processing
- Report generation
- Data export

### 8. REST API with DataTables

**Decision:** Use Django REST Framework + DataTables.

**Rationale:**
- Server-side processing
- Efficient for large datasets
- Standard API
- Easy filtering/sorting

**DSA-110 Application:**
- Consistent API design
- Efficient data tables
- Easy filtering
- Export capabilities

---

## Recommendations for DSA-110

### 1. Adopt Similar Data Model

**Recommendation:** Use Measurement → Source association pattern.

**Benefits:**
- Track individual detections
- Build light curves
- Support forced photometry
- Enable source association

**Implementation:**
- Measurement model per image
- Source model for associations
- Many-to-many relationship
- Aggregate statistics

### 2. Implement Similar Web Interface Patterns

**Recommendation:** Adopt VAST's page structure and workflows.

**Key Pages:**
- Pipeline status dashboard
- Source query interface
- Source detail page
- Analysis workspace

**Features:**
- DataTables for large datasets
- Interactive visualizations
- External catalog integration
- Comments and tags

### 3. Use Similar Visualization Stack

**Recommendation:** Adopt Bokeh, JS9, Aladin Lite.

**Rationale:**
- Proven in radio astronomy
- Interactive capabilities
- Good performance
- Active development

**Alternatives:**
- Consider Plotly.js (already in use)
- Keep JS9 for FITS
- Consider CARTA for advanced features

### 4. Implement Query System

**Recommendation:** Build flexible source query interface.

**Features:**
- Cone search with name resolver
- Metric filtering
- Tag filtering
- Session-based results
- Export capabilities

**Implementation:**
- Django forms for query
- REST API for results
- DataTables for display
- Session storage

### 5. Add Analysis Workspace

**Recommendation:** Build on VAST's η-V analysis pattern.

**Features:**
- Interactive scatter plots
- Source selection
- Light curve display
- Crossmatch results
- Export capabilities

**Enhancement:**
- Use Golden Layout for flexibility
- Multiple analysis tools
- Reproducibility features
- Trust indicators

### 6. Implement Comment System

**Recommendation:** Use generic comments like VAST.

**Benefits:**
- Collaborative analysis
- Knowledge sharing
- Audit trail
- User annotations

**Implementation:**
- Django ContentTypes
- User avatars
- Threaded discussions
- Rich text support

### 7. Add Tag System

**Recommendation:** Implement flexible tagging.

**Features:**
- Autocomplete
- Query filtering
- User favorites
- Personal organization

**Implementation:**
- django-tagulous or custom
- AJAX autocomplete
- Filter integration
- Export support

### 8. Optimize for Large Datasets

**Recommendation:** Use techniques from VAST.

**Techniques:**
- Server-side DataTables processing
- Datashader for large plots
- Arrow/Parquet for measurements
- Lazy loading of images
- Database caching

**DSA-110 Specific:**
- Streaming data handling
- Real-time updates
- Efficient queries
- Caching strategy

### 9. External Catalog Integration

**Recommendation:** Integrate external catalogs like VAST.

**Catalogs:**
- NVSS, VLASS, FIRST (radio)
- Gaia, SIMBAD, NED (general)
- Custom catalogs

**Implementation:**
- Aladin Lite overlays
- VizieR queries
- Crossmatch API
- Results display

### 10. Pipeline Monitoring

**Recommendation:** Build monitoring similar to VAST run pages.

**Features:**
- Status tracking
- Log file viewing
- Configuration display
- Statistics display
- Action buttons

**DSA-110 Specific:**
- Streaming pipeline status
- Real-time metrics
- Queue monitoring
- Error tracking

---

## Code Patterns to Adopt

### 1. View Pattern for Detail Pages

```python
@login_required
def SourceDetail(request, pk):
    # Fetch source data
    source = Source.objects.filter(id=pk).annotate(...).values().get()
    
    # Prepare measurements
    measurements = Measurement.objects.filter(...).values(...)
    
    # Generate context
    context = {
        'source': source,
        'datatables': [measurements_table],
        'cutout_measurements': cutouts,
    }
    
    # Process forms
    if request.method == "POST":
        # Handle form submission
        pass
    
    return render(request, 'source_detail.html', context)
```

### 2. REST API ViewSet Pattern

```python
class SourceViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        # Custom endpoint
        pass
```

### 3. Plot Generation Pattern

```python
def plot_lightcurve(source, **kwargs):
    # Query data
    measurements = Measurement.objects.filter(...).values(...)
    
    # Create Bokeh figure
    fig = figure(...)
    
    # Add plots
    fig.scatter(...)
    fig.line(...)
    
    # Return JSON
    return json_item(fig, "plot-id")
```

### 4. DataTables Configuration Pattern

```python
datatable = {
    'api': reverse('api_sources-list') + '?format=datatables',
    'colsFields': generate_colsfields(fields, api_col_dict),
    'colsNames': [...],
    'search': True,
    'order': [1, 'asc']
}
```

---

## Performance Considerations

### 1. Database Optimization

**VAST Techniques:**
- Q3C for spatial queries
- Indexed columns
- Bulk operations
- Query optimization

**DSA-110 Application:**
- Spatial indexes for RA/Dec
- Indexed timestamps
- Efficient joins
- Query analysis

### 2. Frontend Optimization

**VAST Techniques:**
- Server-side DataTables processing
- Datashader for large plots
- Lazy image loading
- Caching cutouts

**DSA-110 Application:**
- Pagination for large datasets
- Virtual scrolling
- Image lazy loading
- Result caching

### 3. API Optimization

**VAST Techniques:**
- Pagination
- Filtering at database level
- Efficient serialization
- Caching

**DSA-110 Application:**
- REST API best practices
- Efficient queries
- Response caching
- Rate limiting

---

## Security Considerations

### 1. Authentication

**VAST:** Django authentication + GitHub OAuth

**DSA-110 Application:**
- Django authentication (initially)
- OAuth for future (GitHub, Google)
- Session management
- CSRF protection

### 2. Authorization

**VAST:** User-based permissions, admin roles

**DSA-110 Application:**
- User roles (initially simple)
- Run ownership
- Admin capabilities
- Future: fine-grained permissions

### 3. Data Access

**VAST:** User-specific data, shared runs

**DSA-110 Application:**
- Initially: open access
- Future: user workspaces
- Data sharing capabilities
- Export controls

---

## Testing Patterns

### 1. Unit Tests

**VAST:** pytest, Django test framework

**DSA-110 Application:**
- Unit tests for models
- View tests
- API tests
- Utility function tests

### 2. Integration Tests

**VAST:** End-to-end workflow tests

**DSA-110 Application:**
- Pipeline workflow tests
- Web interface tests
- API integration tests
- Database tests

### 3. Performance Tests

**VAST:** Large dataset tests

**DSA-110 Application:**
- Query performance tests
- Visualization performance
- API response time tests
- Database query optimization

---

## Documentation Patterns

### 1. Architecture Documentation

**VAST:** Comprehensive docs with diagrams

**DSA-110 Application:**
- System architecture docs
- Database schema docs
- API documentation
- Workflow documentation

### 2. User Documentation

**VAST:** Step-by-step guides, screenshots

**DSA-110 Application:**
- User guides
- Tutorials
- FAQ
- Video tutorials (future)

### 3. Developer Documentation

**VAST:** Code examples, contribution guides

**DSA-110 Application:**
- Development setup
- Code style guide
- API reference
- Contribution guidelines

---

---

## Deep Implementation Details

### Frontend JavaScript Patterns

#### DataTables Configuration Pattern

VAST uses a sophisticated DataTables configuration system:

**Key Features:**
- Server-side processing for large datasets
- Custom renderers for URLs, floats, booleans
- Deferred loading (don't fetch until query submitted)
- Column visibility controls
- Export buttons (CSV, Excel)
- Nested field support (e.g., `run.name`)

**Pattern:**
```javascript
// Configuration object passed from Django template
datatable = {
    'api': reverse('api_sources-list') + '?format=datatables',
    'colsFields': generate_colsfields(fields, url_prefix_dict),
    'colsNames': [...],
    'search': True,
    'order': [1, 'asc'],
    'deferLoading': 0  // Don't load until query
}

// JavaScript processes configuration
function obj_formatter(obj) {
    if (obj.render.hasOwnProperty('url')) {
        // Generate href renderer
    } else if (obj.render.hasOwnProperty('float')) {
        // Generate float formatter with precision/scale
    }
}
```

**DSA-110 Application:**
- Use similar DataTables configuration
- Support nested fields (e.g., `calibration.name`)
- Custom renderers for astronomical data
- Deferred loading for query results

#### Aladin Lite Integration Pattern

VAST creates custom survey overlays for Aladin:

**Pattern:**
```javascript
function configureAladin(aladin, aladinConf) {
    // Create custom surveys
    var vast_epoch_01 = aladin.createImageSurvey(
        'VAST Pilot 01', 'VAST Pilot 01', 
        'https://.../VAST1_I4', 'equatorial', 6, 
        {imgFormat: 'png'}
    );
    
    // Set default survey
    aladin.setImageSurvey(racs);
    
    // Add overlays (boxes, circles, polygons)
    if (aladinConf.hasOwnProperty('aladin_box_ra')) {
        var overlay = A.graphicOverlay({color: '#ee2345'});
        overlay.addFootprints([A.polygon([...])]);
    }
}
```

**DSA-110 Application:**
- Create DSA-110 survey overlays
- Add pointing footprints
- Overlay calibration regions
- Show mosaic coverage

#### Form Handling Pattern

VAST uses extensive form validation and AJAX:

**Pattern:**
```javascript
// Coordinate validation on blur
$("#coordInput").on('blur', function (e) {
    $.get(validatorUrl, {
        coord: coordString,
        frame: coordFrame
    }).done(function (data) {
        coordInput.addClass('is-valid');
    }).fail(function (jqxhr) {
        coordInput.addClass('is-invalid');
    });
});

// Name resolver
$("#objectResolveButton").on('click', function (e) {
    $.get(sesameUrl, {
        object_name: objectNameInput.val(),
        service: sesameService
    }).done(function (data) {
        coordInput.val(data['coord']);
    });
});
```

**DSA-110 Application:**
- Real-time coordinate validation
- Name resolver integration
- Form state management
- Error feedback

### Backend Form & Serializer Patterns

#### Django Forms with Crispy Forms

VAST uses django-crispy-forms for form rendering:

**Pattern:**
```python
class PipelineRunForm(forms.Form):
    run_name = forms.CharField(max_length=64)
    monitor = forms.BooleanField(required=False)
    association_method = forms.CharField()
    # ... many fields

class TagWithCommentsForm(forms.Form):
    comment = forms.CharField(required=False, widget=forms.Textarea())
    tags = tagulous.forms.TagField(
        required=False,
        tag_options=tagulous.models.TagOptions(**Source.tags.tag_options.items()),
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field("tags"),
            Field("comment", rows=2),
            Submit("submit", "Submit", css_class="btn-block"),
        )
```

**DSA-110 Application:**
- Use crispy-forms for consistent styling
- Tag integration for sources
- Form validation
- Helper layouts

#### REST API Serializers

VAST uses DRF serializers with DataTables support:

**Pattern:**
```python
class SourceSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    run = RunNameSerializer()
    wavg_ra = serializers.SerializerMethodField()
    wavg_dec = serializers.SerializerMethodField()
    
    class Meta:
        model = Source
        fields = "__all__"
        datatables_always_serialize = ('id',)  # Always include ID
    
    def get_wavg_ra(self, source):
        return deg2hms(source.wavg_ra, hms_format=True)
```

**Key Features:**
- Nested serializers for relationships
- Method fields for computed values
- DataTables-specific metadata
- Coordinate formatting

**DSA-110 Application:**
- Similar serializer patterns
- Coordinate formatting utilities
- Nested relationships
- DataTables integration

### Pipeline Processing Patterns

#### Association Algorithm

VAST implements sophisticated source association:

**Key Methods:**
1. **Basic Association**: Simple distance-based matching
2. **Advanced Association**: De Ruiter radius calculation
3. **One-to-Many Handling**: Fork sources when multiple matches
4. **Many-to-One Handling**: Merge sources when appropriate

**Pattern:**
```python
def calc_de_ruiter(df: pd.DataFrame) -> np.ndarray:
    """Calculate unitless de Ruiter radius"""
    # Complex calculation using RA/Dec errors
    dr1 = (ra_1 - ra_2) * (ra_1 - ra_2)
    dr1 *= np.cos((dec_1 + dec_2) / 2.) ** 2
    dr1 /= ra_1_err**2 + ra_2_err**2
    # ... more calculations
    return np.sqrt(dr1 + dr2)

def one_to_many_basic(skyc2_srcs, sources_df, id_incr_par_assoc=0):
    """Handle one-to-many associations"""
    # Find duplicated matches
    # Assign new IDs to non-nearest matches
    # Fork sources in sources_df
    # Update related fields
```

**DSA-110 Application:**
- Implement similar association methods
- Support multiple association strategies
- Handle edge cases (one-to-many, many-to-one)
- Track source relationships

#### Image Ingestion Utilities

VAST has sophisticated FITS handling:

**Pattern:**
```python
def open_fits(fits_path, memmap=True, comp_nan_fill=True):
    """Open compressed or uncompressed FITS"""
    hdul = fits.open(fits_path, memmap=memmap)
    if isinstance(hdul[1], fits.hdu.compressed.CompImageHDU):
        if comp_nan_fill:
            data = hdul[1].data
            data[data < comp_nan_fill_cut] = np.nan
    return hdul

def calc_condon_flux_errors(row, theta_B, theta_b, ...):
    """Calculate flux errors using Condon (1997) method"""
    # Complex error propagation calculations
    # Returns: peak_err, int_err, major_err, minor_err, pa_err, ra_err, dec_err
```

**DSA-110 Application:**
- Robust FITS file handling
- Support compressed FITS
- Error calculation utilities
- Image metadata extraction

### External Query Patterns

VAST integrates multiple external catalogs:

**Supported Services:**
- SIMBAD (astroquery)
- NED (astroquery)
- TNS (Transient Name Server)
- Fink
- DAS (Data Central)

**Pattern:**
```python
def simbad(coord: SkyCoord, radius: Angle) -> List[Dict]:
    CustomSimbad = Simbad()
    CustomSimbad.add_votable_fields("otype(S)", "otype(V)", ...)
    try:
        result_table = CustomSimbad.query_region(coord, radius=radius)
    except requests.HTTPError:
        # Try Harvard mirror
        CustomSimbad.SIMBAD_URL = "https://simbad.harvard.edu/..."
        result_table = CustomSimbad.query_region(coord, radius=radius)
    
    # Format results
    results_df = result_table.to_pandas()
    results_df["database"] = "SIMBAD"
    return results_df.to_dict(orient="records")
```

**DSA-110 Application:**
- Integrate radio catalogs (NVSS, VLASS, FIRST)
- Add optical catalogs (Gaia, PanSTARRS)
- Error handling and fallbacks
- Consistent result format

### Management Commands

VAST uses Django management commands extensively:

**Key Commands:**
- `initpiperun` - Initialize new pipeline run
- `runpipeline` - Execute pipeline processing
- `ingestimages` - Ingest images and catalogs
- `createmeasarrow` - Generate Arrow files
- `restorepiperun` - Restore deleted run
- `clearpiperun` - Clean up run data

**Pattern:**
```python
class Command(BaseCommand):
    help = 'Initialize a new pipeline run'
    
    def add_arguments(self, parser):
        parser.add_argument('run_name', type=str)
        parser.add_argument('--config', type=str)
    
    def handle(self, *args, **options):
        # Validate inputs
        # Create run directory
        # Write config file
        # Initialize database records
```

**DSA-110 Application:**
- Similar command structure
- Validation and error handling
- Database initialization
- File system management

### Template Patterns

#### Query Form Template

VAST's source query form is comprehensive:

**Features:**
- Collapsible sections
- Tooltips for help
- Real-time validation
- Select2 for tag selection
- Coordinate frame selection
- Multiple filter types

**Pattern:**
```html
<fieldset>
  <legend>Cone Search</legend>
  <!-- Object name resolver -->
  <input id="objectNameInput" ...>
  <button id="objectResolveButton" data-sesame-url="...">Resolve</button>
  
  <!-- Coordinate input with validation -->
  <input id="coordInput" data-validator-url="...">
  <select id="coordFrameSelect">...</select>
  
  <!-- Radius input -->
  <input id="radiusSelect" ...>
  <select id="radiusUnit">...</select>
</fieldset>

<fieldset>
  <legend>Table Filters</legend>
  <!-- Many filter rows -->
  <div class="form-group form-row">
    <label>Min. Flux</label>
    <input id="fluxMinMinSelect" ...>
    <input id="fluxMaxMinSelect" ...>
    <select id="minFluxSelect">...</select>
  </div>
</fieldset>
```

**DSA-110 Application:**
- Similar form structure
- Collapsible sections
- Tooltips and help text
- Real-time validation
- Consistent styling

#### Detail Page Template

VAST's source detail page is information-dense:

**Layout:**
- Three-column layout (Details, Postage Stamp, Sky Viewer)
- Multiple cards for different information
- Tabs for measurements and related sources
- External catalog results table
- Comments and tags section

**Pattern:**
```html
<div class="row">
  <!-- Details Card -->
  <div class="col-xl-4">
    <div class="card">
      <div class="card-header">Details</div>
      <div class="card-body">
        <!-- Source information -->
      </div>
    </div>
  </div>
  
  <!-- JS9 Postage Stamp -->
  <div class="col-xl-4">
    <div class="card">
      <div class="JS9" id="JS9_..." data-width="450px"></div>
    </div>
  </div>
  
  <!-- Aladin Sky Viewer -->
  <div class="col-xl-4">
    <div id="aladin-lite-div"></div>
  </div>
</div>
```

**DSA-110 Application:**
- Similar card-based layout
- Multiple visualization types
- Information hierarchy
- Responsive design

### Utility Patterns

#### Coordinate Formatting

VAST has comprehensive coordinate utilities:

**Pattern:**
```python
def deg2dms(deg, dms_format=False, precision=2, truncate=False, latitude=True):
    """Convert degrees to DMS string"""
    AngleClass = Latitude if latitude else Longitude
    angle = AngleClass(deg, unit="deg")
    return angle.to_string(
        unit="deg",
        sep="fromunit" if dms_format else ":",
        precision=precision,
        alwayssign=True,
        pad=True,
    )

def deg2hms(deg, hms_format=False, precision=2, truncate=False):
    """Convert degrees to HMS string"""
    return deg2dms(deg / 15.0, dms_format=hms_format, ...)
```

**DSA-110 Application:**
- Similar coordinate utilities
- Consistent formatting
- Support multiple formats
- Precision control

#### View Utilities

VAST has helper functions for views:

**Pattern:**
```python
FLOAT_FIELDS = {
    'ra': {'precision': 4, 'scale': 1},
    'ra_err': {'precision': 4, 'scale': 3600.},
    'flux_peak': {'precision': 3, 'scale': 1},
    # ... many more
}

def generate_colsfields(fields, url_prefix_dict, not_orderable_col=None):
    """Generate DataTables column configuration"""
    colsfields = []
    for col in fields:
        if col == 'name':
            field2append = {'data': col, 'render': {'url': {...}}}
        elif col in FLOAT_FIELDS:
            field2append = {'data': col, 'render': {'float': {...}}}
        # ... more cases
    return colsfields
```

**DSA-110 Application:**
- Similar utility functions
- Consistent field formatting
- DataTables integration
- Reusable patterns

---

## Additional Deep Implementation Patterns (Third Pass)

### Complete Data Model Understanding

#### Source Model Deep Dive
- **Weighted averages**: `wavg_ra`, `wavg_dec`, `wavg_uncertainty_ew`, `wavg_uncertainty_ns` - calculated from measurements
- **Aggregate flux metrics**: `avg_flux_int`, `avg_flux_peak`, `max_flux_peak`, `min_flux_peak`, `max_flux_int`, `min_flux_int`
- **Variability metrics**: `v_int`, `v_peak`, `eta_int`, `eta_peak` - calculated from measurement pairs
- **New source detection**: `new_high_sigma` - maximum sigma if source placed in previous images
- **Neighbor metrics**: `n_neighbour_dist` - distance to nearest neighbor
- **Pair metrics aggregates**: `vs_abs_significant_max_int`, `m_abs_significant_max_int`, `vs_abs_significant_max_peak`, `m_abs_significant_max_peak` - only for pairs exceeding threshold
- **Count metrics**: `n_meas`, `n_meas_sel`, `n_meas_forced`, `n_rel`, `n_sibl`
- **Method**: `get_measurement_pairs()` - calculates measurement pair metrics on-demand

#### Measurement Model Deep Dive
- **Position**: `ra`, `dec`, `ra_err`, `dec_err`, `uncertainty_ew`, `uncertainty_ns` (quadratic sum)
- **Flux**: `flux_int`, `flux_int_err`, `flux_peak`, `flux_peak_err` (mJy/beam)
- **Island ratios**: `flux_int_isl_ratio`, `flux_peak_isl_ratio` - component to island flux ratio
- **Fit quality**: `chi_squared_fit`, `spectral_index`, `spectral_index_from_TT`
- **Local properties**: `local_rms`, `snr`, `compactness` (int/peak flux ratio)
- **Flags**: `flag_c4` (Selavy fit flag), `has_siblings` (multi-component island), `forced` (forced extraction)
- **Component tracking**: `component_id`, `island_id` - links to Selavy catalog

#### Association Model
- **Distance metrics**: `d2d` (astronomical distance in arcsec), `dr` (De Ruiter radius)
- **Many-to-many**: Source ↔ Measurement through Association table
- **Flexible association**: Different methods produce different associations

#### RelatedSource Model
- **Self-referential**: Many-to-many relationship between Sources
- **Through table**: Explicit `RelatedSource` model with `from_source` and `to_source`
- **Unique constraint**: Prevents duplicate relationships
- **Use case**: Related sources (e.g., components of extended sources)

#### SourceFav Model
- **User favorites**: Links User to Source
- **Comment field**: Optional 500-character comment explaining why favorited
- **Use case**: Personal bookmarking system

### Admin Interface Patterns

#### Django Admin Customization
- **Custom admin classes**: `RunAdmin`, `ImageAdmin`, `SourceAdmin`, `MeasurementAdmin`, `SourceFavAdmin`
- **List display**: Custom columns shown in admin list view
- **List filters**: Filter by status, new sources, forced measurements
- **Search fields**: Search by name for images, sources, measurements
- **Excluded fields**: Hide technical fields like `path`, `measurements_path` from admin forms
- **Site customization**: Custom site title and header

**DSA-110 Application:**
- Use Django admin for quick data inspection
- Customize admin for common operations
- Hide technical implementation details

### Template Architecture Deep Dive

#### Base Template (`base.html`)
- **Sidebar navigation**: Collapsible accordion menu
- **Breadcrumbs**: Context-aware navigation trail
- **User dropdown**: GitHub avatar, favorites link, logout
- **Maintenance banner**: Context processor injects maintenance messages
- **Version display**: Pipeline version with link to GitHub releases
- **Responsive design**: Bootstrap 4 grid system

#### Generic Table Template (`generic_table.html`)
- **Reusable DataTables**: Single template for all table views
- **Dynamic columns**: Columns defined in view context
- **API integration**: DataTables AJAX source from REST API
- **Search/filter**: Built-in DataTables search
- **Export buttons**: CSV, Excel, PDF export via DataTables Buttons
- **Column visibility**: Show/hide columns dynamically

**Key Pattern:**
```python
# View defines table structure
datatable = {
    'api': reverse('api-endpoint') + '?format=datatables',
    'colsFields': generate_colsfields(fields, link_map),
    'colsNames': ['Column 1', 'Column 2', ...],
    'search': True,
}
```

#### Detail Page Templates
- **Three-column layout**: Details card, visualization, comments
- **Collapsible sections**: Bootstrap collapse for measurements, runs tables
- **Navigation**: Previous/Next buttons for sequential browsing
- **Aladin integration**: Embedded sky viewer with source overlay
- **DataTables**: Nested tables for related objects
- **Comments component**: Reusable comment form and display

### Pipeline Processing Deep Dive

#### Final Operations (`finalise.py`)
- **Source statistics**: Parallel groupby to calculate aggregate metrics
- **Nearest neighbor**: Astropy SkyCoord matching for `n_neighbour_dist`
- **Measurement pairs**: Optional calculation of 2-epoch variability metrics
- **Pair aggregates**: Maximum Vs and m metrics per source (only significant pairs)
- **Bulk upload**: Batch creation of sources, associations, relations
- **Parquet export**: Save sources, associations, relations, measurement pairs
- **Add mode**: Update existing sources vs create new ones
- **Memory management**: Track memory usage throughout process

**Key Functions:**
- `calculate_measurement_pair_aggregate_metrics()` - Filter pairs by Vs threshold, find max m metric
- `final_operations()` - Orchestrates all finalization steps

#### Forced Extraction (`forced_extraction.py`)
- **Purpose**: Fill gaps in light curves by extracting flux at known positions
- **Image loading**: Memmap option for large images
- **SkyCoord conversion**: Convert RA/Dec to pixel coordinates
- **Edge detection**: Skip sources near image edges (configurable buffer)
- **NaN handling**: Check for NaN values in background/noise maps
- **Batch processing**: Process multiple images in parallel
- **Parquet storage**: Save forced measurements to separate parquet files

**Key Functions:**
- `extract_from_image()` - Extract flux for sources in one image
- `remove_forced_meas()` - Clean up forced measurements from database
- `get_data_from_parquet()` - Get prefix and max ID for component naming

#### Measurement Pairs (`pairs.py`)
- **Purpose**: Calculate 2-epoch variability metrics (Vs, m) for all measurement pairs
- **Dask parallelization**: Group by source, generate combinations in parallel
- **Date ordering**: Ensure pairs are in chronological order (a < b)
- **Metrics calculation**: `calculate_vs_metric()`, `calculate_m_metric()`
- **Memory optimization**: Configurable partition size

**Key Functions:**
- `calculate_vs_metric()` - T-statistic for variability (Mooley et al. 2016)
- `calculate_m_metric()` - Modulation index (fractional variability)
- `calculate_measurement_pair_metrics()` - Generate all pairs with metrics

#### Pipeline Loading (`loading.py`)
- **Bulk upload pattern**: Generator-based batch creation
- **Transaction management**: Atomic transactions for consistency
- **Memory tracking**: Log memory usage at each step
- **Parquet storage**: Save measurements to parquet immediately after upload
- **Image-band relationship**: Get or create Band objects
- **Sky region management**: Create or reuse SkyRegion objects

**Key Functions:**
- `bulk_upload_model()` - Generic bulk upload with batch size control
- `make_upload_images()` - Process images, create measurements
- `make_upload_sources()` - Bulk create sources with batch processing
- `make_upload_associations()` - Create Association records
- `make_upload_related_sources()` - Create RelatedSource records

### Configuration Management

#### PipelineConfig Class (`config.py`)
- **YAML schema**: StrictYAML schema validation
- **Jinja2 templates**: Generate config files from templates
- **Input validation**: Check file existence, match images to catalogs
- **Epoch mode**: Support for user-defined epochs vs auto-detection
- **Glob expressions**: Resolve glob patterns to file lists
- **Default values**: Sensible defaults from Django settings
- **Validation**: Separate validation for schema vs inputs

**Key Features:**
- `make_config_template()` - Render Jinja2 template
- `from_file()` - Load and parse YAML config
- `validate()` - Validate schema and inputs
- `_resolve_glob_expressions()` - Expand glob patterns
- `_create_input_epochs()` - Auto-create epochs from file dates

**Config Structure:**
```yaml
run:
  path: /path/to/run
  suppress_astropy_warnings: true
inputs:
  image: {...}
  selavy: {...}
  noise: {...}
source_association:
  method: basic|advanced|deruiter
  radius: 5.0
  ...
source_monitoring:
  monitor: false
  min_sigma: 5.0
  ...
variability:
  pair_metrics: true
  source_aggregate_pair_metrics_min_abs_vs: 3.0
```

### Authentication & Authorization

#### GitHub OAuth Integration (`utils/auth.py`)
- **Social auth**: python-social-auth for GitHub OAuth
- **Admin team**: Check GitHub team membership for admin privileges
- **Avatar loading**: Store GitHub avatar URL in extra_data
- **Auto-admin**: Grant Django admin to team members

**Key Functions:**
- `create_admin_user()` - Pipeline function for social auth
- `load_github_avatar()` - Store avatar URL

**DSA-110 Application:**
- Consider GitHub OAuth for team authentication
- Use team membership for access control
- Store user avatars for UI display

### Management Commands

VAST provides Django management commands for common operations:

1. **`runpipeline.py`** - Execute pipeline run
2. **`initpiperun.py`** - Initialize new pipeline run
3. **`ingestimages.py`** - Ingest images into database
4. **`clearpiperun.py`** - Delete pipeline run and associated data
5. **`restorepiperun.py`** - Restore deleted pipeline run
6. **`createmeasarrow.py`** - Create Arrow files from Parquet
7. **`cleanup_cutouts.py`** - Clean up image cutouts
8. **`debugrun.py`** - Debug pipeline run

**Pattern:** CLI tools as Django management commands for consistency

### API Endpoints Deep Dive

#### Region Export (`views.py`)
- **Cone search**: Filter measurements by RA/Dec/radius
- **Region file**: Generate DS9 region file format
- **Selection highlighting**: Color selected source/measurement differently
- **Forced indicator**: Dashed lines for forced measurements
- **Ellipse shapes**: Use beam parameters for ellipse size

**Endpoint:** `/api/images/{id}/regions/`

#### Raw Image List (`views.py`)
- **File discovery**: Glob patterns for FITS and Selavy files
- **Parallel search**: Dask bag for parallel file discovery
- **User home data**: Include user's home directory data
- **Title/tokens**: Generate HTML option attributes for Bootstrap Select
- **Response format**: Separate lists for FITS and Selavy files

**Endpoint:** `/api/rawimages/`

#### Run Config API (`views.py`)
- **Validation**: Validate config file against schema
- **Write**: Update config file from UI
- **Error handling**: Return detailed error messages
- **Success feedback**: Django messages framework

**Endpoints:**
- `POST /api/runs/{id}/config/validate/` - Validate config
- `POST /api/runs/{id}/config/write/` - Write config

#### Run Log API (`views.py`)
- **Log fetching**: Retrieve log files from run directory
- **Multiple logs**: Support different log types (run, restore, arrow)
- **File streaming**: Stream log content to response
- **Error handling**: 404 if log doesn't exist

**Endpoint:** `GET /api/runs/{id}/logs/fetch/?logname=run.log`

### Utility Patterns

#### Delete Run (`utils/delete_run.py`)
- **Raw SQL**: Use raw SQL for performance on large deletions
- **Batch deletion**: Delete in batches to avoid memory issues
- **Orphan cleanup**: Delete images and sky regions not used by other runs
- **Cascade handling**: Manually handle cascades for performance
- **Transaction safety**: Wrap in transaction for atomicity

**Key Functions:**
- `delete_pipeline_run_raw_sql()` - Main deletion function
- `clear_run_sources()` - Delete sources in batches

**DSA-110 Application:**
- Use raw SQL for bulk deletions
- Batch operations for large datasets
- Manual cascade handling for performance

#### Unit Tags (`utils/unit_tags.py`)
- **Template filters**: Django template filters for unit conversion
- **deg_to_arcsec**: Convert degrees to arcseconds
- **deg_to_arcmin**: Convert degrees to arcminutes

**Usage:**
```django
{{ image.beam_bmaj|deg_to_arcsec|floatformat:3 }}"
```

#### Context Processors (`context_processors.py`)
- **Maintenance banner**: Inject maintenance messages into all templates
- **Version display**: Add pipeline version to context
- **Global context**: Available in all templates

### New Sources Detection (`pipeline/new_sources.py`)
- **Purpose**: Identify sources that appear for the first time
- **Method**: Check if source would have been detected in previous images
- **RMS measurement**: Measure RMS at source position in previous images
- **Sigma calculation**: Calculate SNR if source placed at minimum RMS
- **Threshold**: Flag as new if SNR > `new_source_min_sigma`
- **Parallel processing**: Use Dask for parallel RMS measurements

**Key Functions:**
- `get_image_rms_measurements()` - Measure RMS at coordinates
- `parallel_get_rms_measurements()` - Parallel version
- `check_primary_image()` - Verify primary image in image list

### Vast-Tools Integration

#### PipeRun Class (`vasttools/pipeline.py`)
- **Purpose**: Python interface to pipeline results
- **Data loading**: Load parquet files into DataFrames
- **Vaex support**: Option to use Vaex for large datasets
- **Measurement pairs**: Lazy loading of measurement pairs
- **Combine runs**: Merge multiple runs for comparison
- **SkyCoord**: Pre-compute SkyCoord for spatial queries

**Key Features:**
- Load measurements, sources, associations, relations
- Support for Arrow files (faster than Parquet)
- Combine multiple runs
- Query by position, flux, variability

#### Tools Module (`vasttools/tools.py`)
- **MOC operations**: Create and query MOC (Multi-Order Coverage) maps
- **Credible levels**: Calculate credible regions from skymaps
- **Beam information**: Parse beam files into DataFrames
- **Epoch tools**: Utilities for epoch-based analysis

**Key Functions:**
- `skymap2moc()` - Convert skymap to MOC
- `find_in_moc()` - Find sources in MOC region
- `add_credible_levels()` - Add credible level to dataframe

## Conclusion

VAST provides an excellent reference architecture for DSA-110's dashboard. Key takeaways:

1. **Data Model**: Measurement → Source association is powerful
2. **Web Interface**: Proven patterns for radio astronomy workflows
3. **Visualization**: Bokeh, JS9, Aladin Lite are excellent choices
4. **Performance**: Server-side processing and optimization techniques
5. **User Experience**: Query system, detail pages, analysis tools
6. **Implementation**: Comprehensive JavaScript patterns, form handling, utilities

The main differences for DSA-110:
- **Streaming focus**: Real-time pipeline monitoring
- **Autonomous operations**: Less manual intervention
- **Analysis workspace**: More flexible than VAST's fixed pages
- **Unified command center**: Integration with streaming pipeline

By adopting VAST's proven patterns while enhancing for DSA-110's specific needs, we can build a world-class dashboard for continuum imaging and ESE detection.

