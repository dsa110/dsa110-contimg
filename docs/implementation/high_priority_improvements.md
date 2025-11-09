# High-Priority Improvements Implementation Plan

Based on analysis of external radio astronomy repositories (MeerKAT, ASKAP, katdal, CARTA, MeerKAT-Cookbook), this document outlines detailed implementation plans for three critical improvements that will measurably enhance scientific correctness and operational reliability for monitoring ~10,000 compact objects.

---

## 1. Catalog-Based Validation (Astrometry & Flux Scale)

**Priority:** Critical (Scientific Correctness)  
**Source Pattern:** ASKAP continuum validation  
**Impact:** Ensures accurate monitoring of 10,000 compact objects by validating astrometry and flux scale against reference catalogs

### Overview

Implement automated validation of image astrometry and flux scale by comparing detected sources against reference radio catalogs (NVSS, VLASS). This will catch systematic errors in calibration, imaging, or coordinate transformations that could affect scientific results.

### Implementation Details

#### 1.1 New Module: `qa/catalog_validation.py`

**Purpose:** Core validation functions for catalog-based quality assessment

**Key Functions:**

```python
def validate_astrometry(
    image_path: str,
    catalog: str = "nvss",  # "nvss" or "vlass"
    search_radius_arcsec: float = 10.0,
    min_snr: float = 5.0,
    max_offset_arcsec: float = 5.0
) -> CatalogValidationResult:
    """
    Validate image astrometry by matching detected sources to reference catalog.
    
    Steps:
    1. Extract source positions from image (using existing source finder or PyBDSF)
    2. Query reference catalog (NVSS/VLASS) for sources in image field
    3. Match detected sources to catalog sources (nearest neighbor within search_radius)
    4. Calculate astrometric offsets (RA/Dec differences)
    5. Compute statistics: mean offset, RMS offset, max offset
    6. Flag if offsets exceed max_offset_arcsec threshold
    
    Returns:
        CatalogValidationResult with:
        - n_matched: Number of successfully matched sources
        - n_catalog: Number of catalog sources in field
        - n_detected: Number of detected sources
        - mean_offset_arcsec: Mean astrometric offset
        - rms_offset_arcsec: RMS astrometric offset
        - max_offset_arcsec: Maximum astrometric offset
        - offset_ra_arcsec: Mean RA offset
        - offset_dec_arcsec: Mean Dec offset
        - matched_pairs: List of (detected_pos, catalog_pos, offset) tuples
        - has_issues: bool (True if offsets exceed threshold)
        - issues: List[str] (descriptions of problems)
    """

def validate_flux_scale(
    image_path: str,
    catalog: str = "nvss",
    search_radius_arcsec: float = 10.0,
    min_snr: float = 5.0,
    flux_range_jy: Tuple[float, float] = (0.01, 10.0),
    max_flux_ratio_error: float = 0.2  # 20% tolerance
) -> CatalogValidationResult:
    """
    Validate image flux scale by comparing integrated fluxes to catalog fluxes.
    
    Steps:
    1. Extract source positions and integrated fluxes from image
    2. Match to catalog sources (same as astrometry validation)
    3. Compare image integrated flux to catalog flux
    4. Account for frequency scaling if catalog is at different frequency:
       - NVSS: 1.4 GHz
       - VLASS: 3 GHz
       - Use spectral index α = -0.7 (typical for synchrotron sources)
       - Scale: S_ν2 = S_ν1 * (ν2/ν1)^α
    5. Compute flux ratio statistics (image_flux / catalog_flux_scaled)
    6. Flag if flux scale differs significantly from expected
    
    Returns:
        CatalogValidationResult with:
        - n_matched: Number of matched sources with valid flux measurements
        - mean_flux_ratio: Mean ratio of image_flux / catalog_flux_scaled
        - rms_flux_ratio: RMS of flux ratios
        - flux_scale_error: Deviation from unity (1.0 = perfect scale)
        - matched_fluxes: List of (image_flux, catalog_flux, ratio) tuples
        - has_issues: bool (True if flux scale error exceeds threshold)
        - issues: List[str] (descriptions of problems)
    """

def validate_source_counts(
    image_path: str,
    catalog: str = "nvss",
    min_snr: float = 5.0,
    completeness_threshold: float = 0.7  # Expect 70% completeness
) -> CatalogValidationResult:
    """
    Validate source detection completeness by comparing counts to catalog.
    
    Steps:
    1. Count detected sources above min_snr threshold
    2. Count catalog sources in field above same flux threshold
    3. Calculate completeness ratio (detected / catalog)
    4. Flag if completeness is below threshold
    
    Returns:
        CatalogValidationResult with:
        - n_detected: Number of detected sources
        - n_catalog: Number of catalog sources
        - completeness: Ratio of detected/catalog
        - has_issues: bool (True if completeness below threshold)
    """

@dataclass
class CatalogValidationResult:
    """Results from catalog-based validation."""
    validation_type: str  # "astrometry", "flux_scale", "source_counts"
    image_path: str
    catalog_used: str
    n_matched: int
    n_catalog: int
    n_detected: int
    
    # Astrometry results
    mean_offset_arcsec: Optional[float] = None
    rms_offset_arcsec: Optional[float] = None
    max_offset_arcsec: Optional[float] = None
    offset_ra_arcsec: Optional[float] = None
    offset_dec_arcsec: Optional[float] = None
    
    # Flux scale results
    mean_flux_ratio: Optional[float] = None
    rms_flux_ratio: Optional[float] = None
    flux_scale_error: Optional[float] = None
    
    # Source counts results
    completeness: Optional[float] = None
    
    # Quality flags
    has_issues: bool = False
    has_warnings: bool = False
    issues: List[str] = None
    warnings: List[str] = None
    
    # Detailed data
    matched_pairs: Optional[List[Tuple]] = None
    matched_fluxes: Optional[List[Tuple]] = None
```

**Dependencies:**
- `astropy.coordinates` (already available) - for coordinate matching
- `astropy.units` (already available) - for unit conversions
- `dsa110_contimg.catalog` - existing catalog query functions
- `dsa110_contimg.qa.image_quality` - may need source extraction functions
- PyBDSF or similar for source extraction (may need to add)

**Integration Points:**
- Called from `qa/pipeline_quality.py` after imaging completes
- Results stored in QA database/registry
- Displayed in dashboard QA views

#### 1.2 Catalog Query Functions

**Location:** Extend `catalog/query.py` or create `catalog/reference_catalogs.py`

**New Functions:**

```python
def query_nvss_field(
    center_ra: float,
    center_dec: float,
    radius_deg: float,
    min_flux_jy: Optional[float] = None
) -> pd.DataFrame:
    """
    Query NVSS catalog for sources in a field.
    
    Uses existing NVSS catalog infrastructure (see catalog/build_nvss_strip_cli.py).
    Returns DataFrame with columns: ra, dec, flux_jy, etc.
    """

def query_vlass_field(
    center_ra: float,
    center_dec: float,
    radius_deg: float,
    min_flux_jy: Optional[float] = None
) -> pd.DataFrame:
    """
    Query VLASS catalog for sources in a field.
    
    Similar to NVSS query. May need to implement VLASS catalog access.
    """

def scale_flux_to_frequency(
    flux_jy: float,
    source_freq_hz: float,
    target_freq_hz: float,
    spectral_index: float = -0.7
) -> float:
    """
    Scale flux from one frequency to another using power-law spectrum.
    
    S_ν2 = S_ν1 * (ν2/ν1)^α
    """
```

#### 1.3 Source Extraction

**Options:**
1. Use PyBDSF (Python Blob Detector and Source Finder) - industry standard
2. Use existing source finder if available in `qa/image_quality.py`
3. Simple threshold-based extraction for initial implementation

**If PyBDSF needed:**
- Add to requirements: `pybdsf>=1.10.0`
- Create wrapper function in `qa/catalog_validation.py`

#### 1.4 API Integration

**Location:** `api/routes.py`

**New Endpoints:**

```python
@router.get("/api/qa/images/{image_id}/catalog-validation")
async def get_catalog_validation(
    image_id: str,
    catalog: str = "nvss",
    validation_type: str = "all"  # "astrometry", "flux_scale", "source_counts", "all"
):
    """
    Get catalog validation results for an image.
    """
    # Query validation results from database
    # Return JSON with validation metrics

@router.post("/api/qa/images/{image_id}/catalog-validation/run")
async def run_catalog_validation(
    image_id: str,
    catalog: str = "nvss",
    validation_types: List[str] = ["astrometry", "flux_scale", "source_counts"]
):
    """
    Run catalog validation for an image and store results.
    """
    # Run validation functions
    # Store results in database
    # Return validation results
```

#### 1.5 Dashboard Integration

**Location:** `frontend/src/pages/ImageDetailPage.tsx` or new `CatalogValidationPage.tsx`

**New Components:**

```typescript
// CatalogValidationPanel.tsx
- Display astrometry offsets (RA/Dec) with visual indicators
- Display flux scale ratio with pass/fail status
- Display source completeness percentage
- Show matched source pairs on image overlay (see item 3)
- Color-coded status: green (pass), yellow (warning), red (fail)
```

**Visualization:**
- Offset vectors plotted on image (see catalog overlay, item 3)
- Histogram of flux ratios
- Scatter plot: image_flux vs catalog_flux

#### 1.6 CLI Integration

**Location:** `qa/cli_qa.py` (if exists) or create new CLI

**New Command:**

```bash
python -m dsa110_contimg.qa.cli validate-catalog \
    --image /path/to/image.fits \
    --catalog nvss \
    --validation-type all
```

### Testing Strategy

1. **Unit Tests:** Test validation functions with synthetic data
2. **Integration Tests:** Test with real images and known catalog matches
3. **Validation:** Compare results to manual validation for known good/bad images

### Estimated Effort

- Core validation functions: 2-3 days
- Catalog query functions: 1 day
- Source extraction integration: 1-2 days
- API endpoints: 1 day
- Dashboard components: 2-3 days
- Testing: 1-2 days
- **Total: 8-12 days**

---

## 2. Expected Caltable Path Construction

**Priority:** Critical (Operational Reliability)  
**Source Pattern:** MeerKAT `bookkeeping.py`  
**Impact:** Catches calibration failures early by validating expected calibration tables exist

### Overview

Implement a function that constructs expected calibration table paths based on MS path and calibration parameters, then validates that all expected tables exist. This prevents downstream failures when calibration tables are missing or misnamed.

### Implementation Details

#### 2.1 New Module: `calibration/caltable_paths.py`

**Purpose:** Functions for constructing and validating expected caltable paths

**Key Functions:**

```python
def get_expected_caltables(
    ms_path: str,
    caltable_dir: Optional[str] = None,
    caltype: str = "all",  # "all", "K", "B", "G"
    spwmap: Optional[Dict[int, int]] = None
) -> Dict[str, List[str]]:
    """
    Construct expected calibration table paths for a Measurement Set.
    
    Expected naming convention (based on CASA standards):
    - Delay calibration: {ms_basename}.K
    - Bandpass calibration: {ms_basename}.B{spw_index}
    - Gain calibration: {ms_basename}.G
    
    Args:
        ms_path: Path to Measurement Set
        caltable_dir: Directory containing caltables (default: same as MS)
        caltype: Type of caltables to return ("all", "K", "B", "G")
        spwmap: Optional SPW mapping dict {spw_index: bptable_index}
    
    Returns:
        Dict with keys:
        - "K": List of delay caltable paths (typically 1)
        - "B": List of bandpass caltable paths (one per SPW or per mapped SPW)
        - "G": List of gain caltable paths (typically 1)
        - "all": List of all expected caltable paths
    
    Example:
        ms_path = "/data/obs123.ms"
        Returns:
        {
            "K": ["/data/obs123.K"],
            "B": ["/data/obs123.B0", "/data/obs123.B1"],
            "G": ["/data/obs123.G"],
            "all": ["/data/obs123.K", "/data/obs123.B0", "/data/obs123.B1", "/data/obs123.G"]
        }
    """
    ms_path_obj = Path(ms_path)
    ms_basename = ms_path_obj.stem  # "obs123" from "/data/obs123.ms"
    
    if caltable_dir is None:
        caltable_dir = ms_path_obj.parent
    else:
        caltable_dir = Path(caltable_dir)
    
    expected = {
        "K": [],
        "B": [],
        "G": [],
        "all": []
    }
    
    # Delay calibration (K)
    if caltype in ("all", "K"):
        k_table = caltable_dir / f"{ms_basename}.K"
        expected["K"].append(str(k_table))
    
    # Bandpass calibration (B)
    if caltype in ("all", "B"):
        # Need to determine number of SPWs from MS
        n_spws = _get_n_spws_from_ms(ms_path)
        if spwmap:
            # Use mapped SPW indices
            unique_bp_indices = set(spwmap.values())
            for bp_idx in unique_bp_indices:
                b_table = caltable_dir / f"{ms_basename}.B{bp_idx}"
                expected["B"].append(str(b_table))
        else:
            # One BP table per SPW
            for spw_idx in range(n_spws):
                b_table = caltable_dir / f"{ms_basename}.B{spw_idx}"
                expected["B"].append(str(b_table))
    
    # Gain calibration (G)
    if caltype in ("all", "G"):
        g_table = caltable_dir / f"{ms_basename}.G"
        expected["G"].append(str(g_table))
    
    # Collect all
    expected["all"] = expected["K"] + expected["B"] + expected["G"]
    
    return expected

def validate_caltables_exist(
    ms_path: str,
    caltable_dir: Optional[str] = None,
    caltype: str = "all",
    spwmap: Optional[Dict[int, int]] = None,
    raise_on_missing: bool = False
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    """
    Validate that expected calibration tables exist.
    
    Args:
        ms_path: Path to Measurement Set
        caltable_dir: Directory containing caltables
        caltype: Type of caltables to validate
        spwmap: Optional SPW mapping
        raise_on_missing: If True, raise exception if any tables missing
    
    Returns:
        Tuple of (existing_tables, missing_tables) dicts
        Each dict has keys: "K", "B", "G", "all"
    
    Raises:
        FileNotFoundError: If raise_on_missing=True and tables are missing
    """
    expected = get_expected_caltables(ms_path, caltable_dir, caltype, spwmap)
    
    existing = {"K": [], "B": [], "G": [], "all": []}
    missing = {"K": [], "B": [], "G": [], "all": []}
    
    for caltype_key in ["K", "B", "G"]:
        for table_path in expected[caltype_key]:
            if Path(table_path).exists():
                existing[caltype_key].append(table_path)
                existing["all"].append(table_path)
            else:
                missing[caltype_key].append(table_path)
                missing["all"].append(table_path)
    
    if raise_on_missing and missing["all"]:
        raise FileNotFoundError(
            f"Missing calibration tables for {ms_path}:\n"
            f"  K tables: {missing['K']}\n"
            f"  B tables: {missing['B']}\n"
            f"  G tables: {missing['G']}"
        )
    
    return existing, missing

def _get_n_spws_from_ms(ms_path: str) -> int:
    """Get number of spectral windows from MS."""
    try:
        from casacore.tables import table
        with table(str(ms_path) + "/SPECTRAL_WINDOW", ack=False) as spw_table:
            return len(spw_table)
    except Exception as e:
        logger.warning(f"Could not determine SPW count from MS: {e}")
        return 1  # Default to 1 SPW
```

#### 2.2 Integration with Calibration CLI

**Location:** `calibration/cli_calibrate.py`

**Integration Points:**

1. **After calibration completes:**
```python
# After successful calibration
from dsa110_contimg.calibration.caltable_paths import validate_caltables_exist

existing, missing = validate_caltables_exist(
    ms_path=ms_in,
    caltable_dir=caltable_dir,
    caltype="all"
)

if missing["all"]:
    logger.warning(f"Expected calibration tables missing: {missing['all']}")
    logger.info(f"Existing tables: {existing['all']}")
else:
    logger.info(f"✓ All expected calibration tables present: {existing['all']}")
```

2. **Before applying calibration:**
```python
# Before applying calibration in apply_service.py
from dsa110_contimg.calibration.caltable_paths import validate_caltables_exist

existing, missing = validate_caltables_exist(
    ms_path=ms_path_str,
    caltable_dir=caltable_dir,
    raise_on_missing=True  # Fail fast if tables missing
)
```

#### 2.3 Integration with QA System

**Location:** `qa/calibration_quality.py`

**New Function:**

```python
def check_caltable_completeness(
    ms_path: str,
    caltable_dir: Optional[str] = None
) -> Dict[str, Any]:
    """
    Check that all expected calibration tables exist for an MS.
    
    Returns:
        Dict with:
        - expected_tables: List of expected table paths
        - existing_tables: List of existing table paths
        - missing_tables: List of missing table paths
        - completeness: Fraction of expected tables that exist
        - has_issues: bool (True if any tables missing)
    """
    from dsa110_contimg.calibration.caltable_paths import (
        get_expected_caltables,
        validate_caltables_exist
    )
    
    expected = get_expected_caltables(ms_path, caltable_dir)
    existing, missing = validate_caltables_exist(ms_path, caltable_dir)
    
    n_expected = len(expected["all"])
    n_existing = len(existing["all"])
    completeness = n_existing / n_expected if n_expected > 0 else 0.0
    
    return {
        "expected_tables": expected["all"],
        "existing_tables": existing["all"],
        "missing_tables": missing["all"],
        "completeness": completeness,
        "has_issues": len(missing["all"]) > 0
    }
```

#### 2.4 API Integration

**Location:** `api/routes.py`

**New Endpoint:**

```python
@router.get("/api/qa/calibration/{ms_path:path}/caltable-completeness")
async def get_caltable_completeness(ms_path: str):
    """
    Check calibration table completeness for an MS.
    """
    from dsa110_contimg.qa.calibration_quality import check_caltable_completeness
    
    result = check_caltable_completeness(ms_path)
    return result
```

#### 2.5 Dashboard Integration

**Location:** `frontend/src/pages/CalibrationDetailPage.tsx` or QA views

**New Component:**

```typescript
// CaltableCompletenessPanel.tsx
- List expected caltables with checkmarks for existing
- Highlight missing caltables in red
- Show completeness percentage
- Link to calibration logs if tables missing
```

### Testing Strategy

1. **Unit Tests:** Test path construction with various MS paths and SPW configurations
2. **Integration Tests:** Test with real MS files and caltables
3. **Edge Cases:** Test with missing tables, renamed tables, different directory structures

### Estimated Effort

- Core path construction functions: 1 day
- Integration with calibration CLI: 0.5 days
- Integration with QA system: 0.5 days
- API endpoint: 0.5 days
- Dashboard component: 1 day
- Testing: 0.5 days
- **Total: 4 days**

---

## 3. Catalog Overlay Visualization

**Priority:** High (Operational Reliability)  
**Source Pattern:** CARTA visualization patterns  
**Impact:** Quick visual QA for operators by overlaying reference catalog sources on images

### Overview

Implement catalog overlay visualization in the dashboard, allowing operators to visually validate astrometry and flux scale by overlaying NVSS/VLASS catalog sources on images. This complements the automated catalog validation (item 1) with visual confirmation.

### Implementation Details

#### 3.1 Backend: Catalog Overlay Data API

**Location:** `api/routes.py`

**New Endpoint:**

```python
@router.get("/api/qa/images/{image_id}/catalog-overlay")
async def get_catalog_overlay(
    image_id: str,
    catalog: str = "nvss",
    search_radius_arcsec: float = 60.0,  # Larger radius for overlay
    min_flux_jy: Optional[float] = None
):
    """
    Get catalog sources for overlay on an image.
    
    Returns:
        JSON with:
        - sources: List of catalog sources with:
          - ra: Right ascension (deg)
          - dec: Declination (deg)
          - flux_jy: Flux density (Jy)
          - name: Source name/ID (optional)
        - image_info: Image center, size, pixel scale
        - catalog_used: Which catalog was queried
    """
    # Get image metadata (center, size, pixel scale)
    # Query catalog for sources in field
    # Return sources in JSON format suitable for frontend overlay
```

**Implementation:**

```python
from dsa110_contimg.catalog.reference_catalogs import query_nvss_field, query_vlass_field
from dsa110_contimg.qa.image_quality import get_image_metadata

# Get image metadata
image_metadata = get_image_metadata(image_path)
center_ra = image_metadata["center_ra"]
center_dec = image_metadata["center_dec"]
radius_deg = max(image_metadata["width_deg"], image_metadata["height_deg"]) / 2 + 0.01

# Query catalog
if catalog == "nvss":
    catalog_sources = query_nvss_field(center_ra, center_dec, radius_deg, min_flux_jy)
elif catalog == "vlass":
    catalog_sources = query_vlass_field(center_ra, center_dec, radius_deg, min_flux_jy)
else:
    raise ValueError(f"Unknown catalog: {catalog}")

# Format for frontend
sources_json = [
    {
        "ra": row["ra"],
        "dec": row["dec"],
        "flux_jy": row["flux_jy"],
        "name": row.get("name", f"Source_{i}")
    }
    for i, row in catalog_sources.iterrows()
]

return {
    "sources": sources_json,
    "image_info": image_metadata,
    "catalog_used": catalog
}
```

#### 3.2 Frontend: Catalog Overlay Component

**Location:** `frontend/src/components/CatalogOverlay.tsx`

**New Component:**

```typescript
interface CatalogSource {
  ra: number;
  dec: number;
  flux_jy: number;
  name?: string;
}

interface CatalogOverlayProps {
  imageId: string;
  catalog?: "nvss" | "vlass";
  showLabels?: boolean;
  color?: string;
  size?: number;
  onSourceClick?: (source: CatalogSource) => void;
}

export const CatalogOverlay: React.FC<CatalogOverlayProps> = ({
  imageId,
  catalog = "nvss",
  showLabels = false,
  color = "#00ff00",
  size = 4,
  onSourceClick
}) => {
  // Fetch catalog sources
  const { data: overlayData } = useCatalogOverlay(imageId, catalog);
  
  // Convert RA/Dec to pixel coordinates (need image WCS)
  // Render overlay markers on image canvas
  
  return (
    <g className="catalog-overlay">
      {overlayData?.sources.map((source, idx) => {
        const [x, y] = raDecToPixels(source.ra, source.dec, imageWCS);
        return (
          <circle
            key={idx}
            cx={x}
            cy={y}
            r={size}
            fill={color}
            stroke="white"
            strokeWidth={1}
            opacity={0.7}
            onClick={() => onSourceClick?.(source)}
          />
        );
      })}
    </g>
  );
};
```

**Dependencies:**
- Need WCS (World Coordinate System) handling for RA/Dec → pixel conversion
- Consider using `astropy.wcs` on backend or `wcs` library on frontend
- Or use existing image viewer library that supports WCS

#### 3.3 Integration with Image Viewer

**Location:** `frontend/src/pages/ImageDetailPage.tsx` or existing image viewer component

**Integration:**

```typescript
// In ImageDetailPage.tsx
const [showCatalogOverlay, setShowCatalogOverlay] = useState(false);
const [catalogType, setCatalogType] = useState<"nvss" | "vlass">("nvss");

// Toggle overlay
<Button onClick={() => setShowCatalogOverlay(!showCatalogOverlay)}>
  {showCatalogOverlay ? "Hide" : "Show"} Catalog Overlay
</Button>

// Catalog selector
<Select value={catalogType} onChange={setCatalogType}>
  <option value="nvss">NVSS</option>
  <option value="vlass">VLASS</option>
</Select>

// Render overlay
{showCatalogOverlay && (
  <CatalogOverlay
    imageId={imageId}
    catalog={catalogType}
    color="#00ff00"
    size={4}
    showLabels={false}
  />
)}
```

#### 3.4 Enhanced Features (Future)

1. **Matched Source Highlighting:**
   - Highlight catalog sources that match detected sources (from catalog validation)
   - Show offset vectors for matched sources
   - Color-code: green (good match), yellow (large offset), red (no match)

2. **Flux Visualization:**
   - Size markers proportional to catalog flux
   - Color-code by flux ratio (image_flux / catalog_flux)

3. **Interactive Features:**
   - Click catalog source to show details (RA, Dec, flux)
   - Toggle between NVSS and VLASS overlays
   - Adjust overlay opacity and size

4. **Offset Vectors:**
   - Draw arrows from catalog position to detected position
   - Show offset magnitude and direction

#### 3.5 WCS Handling

**Option 1: Backend Conversion**
- Convert RA/Dec to pixel coordinates on backend
- Return pixel coordinates in API response
- Simpler frontend, but requires image access on backend

**Option 2: Frontend Conversion**
- Return RA/Dec coordinates
- Use WCS library on frontend to convert to pixels
- More flexible, but requires WCS parsing on frontend

**Recommendation:** Start with Option 1 (backend conversion) for simplicity, migrate to Option 2 if needed for performance.

**Backend WCS Conversion:**

```python
from astropy.wcs import WCS
from astropy.io import fits

def get_catalog_overlay_pixels(
    image_path: str,
    catalog_sources: pd.DataFrame
) -> List[Dict]:
    """
    Convert catalog RA/Dec to pixel coordinates using image WCS.
    """
    with fits.open(image_path) as hdul:
        wcs = WCS(hdul[0].header)
    
    sources_pixels = []
    for _, source in catalog_sources.iterrows():
        ra, dec = source["ra"], source["dec"]
        x, y = wcs.wcs_world2pix(ra, dec, 0)
        
        sources_pixels.append({
            "x": float(x),
            "y": float(y),
            "ra": float(ra),
            "dec": float(dec),
            "flux_jy": float(source["flux_jy"]),
            "name": source.get("name", "")
        })
    
    return sources_pixels
```

### Testing Strategy

1. **Unit Tests:** Test catalog query functions
2. **Integration Tests:** Test overlay API with real images
3. **Visual Tests:** Manual verification of overlay accuracy
4. **Performance Tests:** Test with large catalogs (1000+ sources)

### Estimated Effort

- Backend API endpoint: 1 day
- WCS conversion functions: 1 day
- Frontend overlay component: 2-3 days
- Integration with image viewer: 1 day
- Testing: 1 day
- **Total: 6-7 days**

---

## Summary

### Implementation Order

1. **Expected Caltable Path Construction** (4 days) - Quick win, high impact
2. **Catalog-Based Validation** (8-12 days) - Critical for science
3. **Catalog Overlay Visualization** (6-7 days) - Complements validation

### Total Estimated Effort

**18-23 days** for all three improvements

### Dependencies

- `astropy` (already available)
- `pybdsf` (may need to add for source extraction)
- Existing catalog infrastructure (`dsa110_contimg.catalog`)
- Existing QA infrastructure (`dsa110_contimg.qa`)

### Risk Mitigation

1. **Catalog Access:** Ensure NVSS/VLASS catalogs are accessible and up-to-date
2. **WCS Handling:** Verify image WCS headers are correct and parseable
3. **Performance:** Catalog queries may be slow for large fields; consider caching
4. **Source Extraction:** May need to add PyBDSF or implement simple threshold-based extraction

### Success Criteria

1. **Catalog Validation:**
   - Detects astrometric offsets > 5 arcsec
   - Detects flux scale errors > 20%
   - Provides actionable warnings/errors

2. **Caltable Path Construction:**
   - Correctly identifies missing caltables
   - Prevents downstream failures
   - Provides clear error messages

3. **Catalog Overlay:**
   - Overlays catalog sources accurately on images
   - Enables quick visual validation
   - Integrates seamlessly with existing image viewer

---

## Next Steps

1. Review and approve implementation plan
2. Set up development branches for each feature
3. Begin implementation in priority order
4. Regular check-ins to review progress and adjust as needed

