# Masking Toggle Implementation Plan

## Current State

### What We Have

1. **CLI Support**: `create-nvss-mask` command exists but creates CRTF masks (not integrated into imaging)
2. **NVSS Infrastructure**: NVSS catalog access and seeding already implemented
3. **Dashboard**: ControlPage has imaging parameter UI (gridder, wprojplanes, datacolumn)
4. **Pipeline Config**: `ImagingConfig` class in `pipeline/config.py` with imaging parameters
5. **API**: `/jobs/image` endpoint accepts `JobParams` with imaging parameters

### What We're Missing

1. **Masking Toggle**: No parameter to enable/disable masked imaging
2. **FITS Mask Generation**: Current `create_nvss_mask()` only creates CRTF (CASA format)
3. **WSClean Integration**: No `-fits-mask` parameter passed to WSClean
4. **Dashboard UI**: No masking toggle in ControlPage
5. **Pipeline Config**: No `use_nvss_mask` field in `ImagingConfig`

## Implementation Plan

### Phase 1: Backend Implementation

#### 1.1 Add Masking Parameter to Pipeline Config

**File**: `src/dsa110_contimg/pipeline/config.py`

```python
class ImagingConfig(BaseModel):
    """Configuration for imaging stage."""
    
    field: Optional[str] = Field(None, description="Field name or coordinates")
    refant: Optional[str] = Field(default="103", description="Reference antenna")
    gridder: str = Field(default="wproject", description="Gridding algorithm")
    wprojplanes: int = Field(default=-1, description="W-projection planes (-1 for auto)")
    run_catalog_validation: bool = Field(default=True, description="Run catalog-based flux scale validation after imaging")
    catalog_validation_catalog: str = Field(default="nvss", description="Catalog to use for validation ('nvss' or 'vlass')")
    
    # NEW: Masking parameters
    use_nvss_mask: bool = Field(default=True, description="Use NVSS-based mask for imaging (2-4x faster)")
    mask_radius_arcsec: float = Field(default=60.0, ge=10.0, le=300.0, description="Mask radius around NVSS sources (arcsec)")
```

#### 1.2 Create FITS Mask Generation Function

**File**: `src/dsa110_contimg/imaging/nvss_tools.py`

```python
def create_nvss_fits_mask(
    imagename: str,
    imsize: int,
    cell_arcsec: float,
    phasecenter: Optional[str],
    nvss_min_mjy: float,
    radius_arcsec: float = 60.0,
    out_path: Optional[str] = None,
) -> str:
    """Create FITS mask from NVSS sources for WSClean.
    
    Creates a FITS mask file with circular regions around NVSS sources.
    Zero values = not cleaned, non-zero values = cleaned.
    
    Args:
        imagename: Base image name (used to determine output path)
        imsize: Image size in pixels
        cell_arcsec: Pixel scale in arcseconds
        phasecenter: Phase center string (e.g., "J2000 08h34m54.9 +55d34m21.1")
        nvss_min_mjy: Minimum NVSS flux in mJy
        radius_arcsec: Mask radius around each source in arcseconds
        out_path: Optional output path (defaults to {imagename}.nvss_mask.fits)
        
    Returns:
        Path to created FITS mask file
    """
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    import numpy as np
    
    # Determine phase center
    if phasecenter:
        # Parse phase center string
        # Format: "J2000 08h34m54.9 +55d34m21.1"
        # TODO: Parse phase center string
        ra0_deg = dec0_deg = None  # Placeholder
    else:
        # Use image center (need to get from MS)
        ra0_deg = dec0_deg = None  # Placeholder - need MS access
    
    # Create WCS for mask
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [imsize / 2.0, imsize / 2.0]
    wcs.wcs.crval = [ra0_deg, dec0_deg]
    wcs.wcs.cdelt = [-cell_arcsec / 3600.0, cell_arcsec / 3600.0]  # Negative RA for standard convention
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    
    # Initialize mask (all zeros = not cleaned)
    mask = np.zeros((imsize, imsize), dtype=np.float32)
    
    # Query NVSS sources
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog
    df = read_nvss_catalog()
    sc = SkyCoord(df['ra'].values * u.deg, df['dec'].values * u.deg, frame='icrs')
    center = SkyCoord(ra0_deg * u.deg, dec0_deg * u.deg, frame='icrs')
    
    # Calculate FoV radius
    fov_radius_deg = (cell_arcsec * imsize) / 3600.0 / 2.0
    sep = sc.separation(center).deg
    flux_mjy = np.asarray(df['flux_20_cm'].values, float)
    
    # Select sources within FoV and above threshold
    keep = (sep <= fov_radius_deg) & (flux_mjy >= float(nvss_min_mjy))
    sources = df.loc[keep]
    
    # Create circular masks for each source
    radius_pixels = radius_arcsec / cell_arcsec
    
    for _, row in sources.iterrows():
        coord = SkyCoord(row['ra'] * u.deg, row['dec'] * u.deg, frame='icrs')
        x, y = wcs.world_to_pixel(coord)
        
        # Create circular mask
        y_grid, x_grid = np.ogrid[:imsize, :imsize]
        dist_sq = (x_grid - x)**2 + (y_grid - y)**2
        mask[dist_sq <= radius_pixels**2] = 1.0
    
    # Write FITS mask
    if out_path is None:
        out_path = f"{imagename}.nvss_mask.fits"
    
    hdu = fits.PrimaryHDU(data=mask, header=wcs.to_header())
    hdu.writeto(out_path, overwrite=True)
    
    return out_path
```

#### 1.3 Add Mask Parameter to `run_wsclean()`

**File**: `src/dsa110_contimg/imaging/cli_imaging.py`

```python
@track_performance("wsclean", log_result=True)
def run_wsclean(
    ms_path: str,
    imagename: str,
    datacolumn: str,
    field: str,
    imsize: int,
    cell_arcsec: float,
    weighting: str,
    robust: float,
    specmode: str,
    deconvolver: str,
    nterms: int,
    niter: int,
    threshold: str,
    pbcor: bool,
    uvrange: str,
    pblimit: float,
    quality_tier: str,
    wsclean_path: Optional[str] = None,
    gridder: str = "standard",
    mask_path: Optional[str] = None,  # NEW
) -> None:
    """Run WSClean with parameters mapped from tclean equivalents."""
    
    # ... existing code ...
    
    # Mask file (if provided)
    if mask_path:
        cmd.extend(["-fits-mask", mask_path])
        LOG.info("Using mask file: %s", mask_path)
    
    # ... rest of existing code ...
```

#### 1.4 Integrate Mask Generation into `image_ms()`

**File**: `src/dsa110_contimg/imaging/cli_imaging.py`

```python
@track_performance("imaging", log_result=True)
def image_ms(
    ms_path: str,
    *,
    imagename: str,
    field: str = "",
    spw: str = "",
    imsize: int = 1024,
    cell_arcsec: Optional[float] = None,
    weighting: str = "briggs",
    robust: float = 0.0,
    specmode: str = "mfs",
    deconvolver: str = "hogbom",
    nterms: int = 1,
    niter: int = 1000,
    threshold: str = "0.0Jy",
    pbcor: bool = True,
    phasecenter: Optional[str] = None,
    gridder: str = "standard",
    wprojplanes: int = 0,
    uvrange: str = "",
    pblimit: float = 0.2,
    psfcutoff: Optional[float] = None,
    quality_tier: str = "standard",
    skip_fits: bool = False,
    vptable: Optional[str] = None,
    wbawp: Optional[bool] = None,
    cfcache: Optional[str] = None,
    nvss_min_mjy: Optional[float] = None,
    calib_ra_deg: Optional[float] = None,
    calib_dec_deg: Optional[float] = None,
    calib_flux_jy: Optional[float] = None,
    backend: str = "wsclean",
    wsclean_path: Optional[str] = None,
    export_model_image: bool = False,
    use_nvss_mask: bool = True,  # NEW
    mask_radius_arcsec: float = 60.0,  # NEW
) -> None:
    """Main imaging function for Measurement Sets."""
    
    # ... existing validation and setup code ...
    
    # Generate mask if requested and NVSS threshold specified
    mask_path = None
    if use_nvss_mask and nvss_min_mjy is not None and backend == "wsclean":
        try:
            from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask
            
            # Get phase center from MS if not provided
            if phasecenter is None:
                with table(f"{ms_path}::FIELD", readonly=True) as fld:
                    ph = fld.getcol("PHASE_DIR")[0]
                    ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                    dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
                    phasecenter = f"J2000 {ra0_deg:.6f}deg {dec0_deg:.6f}deg"
            
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                phasecenter=phasecenter,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=mask_radius_arcsec,
            )
            LOG.info("Generated NVSS mask: %s (radius=%.1f arcsec)", mask_path, mask_radius_arcsec)
        except Exception as exc:
            LOG.warning("Failed to generate NVSS mask, continuing without mask: %s", exc)
            mask_path = None
    
    # Route to appropriate backend
    if backend == "wsclean":
        run_wsclean(
            # ... existing parameters ...
            mask_path=mask_path,  # NEW
        )
    else:
        # CASA tclean doesn't support FITS masks directly
        # Would need to convert mask to CASA format or skip
        if mask_path:
            LOG.warning("Masking not supported for CASA tclean backend, ignoring mask")
        tclean(**kwargs)
```

#### 1.5 Add CLI Parameter

**File**: `src/dsa110_contimg/imaging/cli.py`

```python
    # Masking parameters
    img_parser.add_argument(
        "--no-nvss-mask",
        action="store_true",
        help="Disable NVSS-based masking (masking is enabled by default for efficiency)",
    )
    img_parser.add_argument(
        "--mask-radius-arcsec",
        type=float,
        default=60.0,
        help="Mask radius around NVSS sources in arcseconds (default: 60.0, ~2-3× beam)",
    )
    
    # ... in main() function ...
    
    image_ms(
        # ... existing parameters ...
        use_nvss_mask=not args.no_nvss_mask,
        mask_radius_arcsec=args.mask_radius_arcsec,
    )
```

### Phase 2: Dashboard Integration

#### 2.1 Add Masking Toggle to ControlPage

**File**: `frontend/src/pages/ControlPage.tsx`

```typescript
  const [imageParams, setImageParams] = useState<JobParams>({
    gridder: 'wproject',
    wprojplanes: -1,
    datacolumn: 'corrected',
    quick: false,
    skip_fits: true,
    use_nvss_mask: true,  // NEW
    mask_radius_arcsec: 60.0,  // NEW
  });
  
  // ... in Image Tab JSX ...
  
  <FormControlLabel
    control={
      <Switch
        checked={imageParams.use_nvss_mask ?? true}
        onChange={(e) => setImageParams({ 
          ...imageParams, 
          use_nvss_mask: e.target.checked 
        })}
        color="primary"
      />
    }
    label={
      <Box>
        <Typography variant="body2">
          Use NVSS Masking
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Enable masked imaging (2-4x faster, recommended)
        </Typography>
      </Box>
    }
    sx={{ mb: 2 }}
  />
  
  {imageParams.use_nvss_mask && (
    <TextField
      fullWidth
      label="Mask Radius (arcsec)"
      type="number"
      value={imageParams.mask_radius_arcsec ?? 60.0}
      onChange={(e) => {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val >= 10 && val <= 300) {
          setImageParams({ 
            ...imageParams, 
            mask_radius_arcsec: val 
          });
        }
      }}
      sx={{ mb: 2 }}
      size="small"
      helperText="Radius around NVSS sources (default: 60 arcsec, ~2-3× beam)"
      inputProps={{ min: 10, max: 300, step: 5 }}
    />
  )}
```

#### 2.2 Update API Models

**File**: `src/dsa110_contimg/api/models.py` (or wherever JobParams is defined)

```python
class JobParams(BaseModel):
    """Imaging job parameters."""
    
    gridder: Optional[str] = None
    wprojplanes: Optional[int] = None
    datacolumn: Optional[str] = None
    quick: Optional[bool] = None
    skip_fits: Optional[bool] = None
    
    # NEW: Masking parameters
    use_nvss_mask: Optional[bool] = True
    mask_radius_arcsec: Optional[float] = 60.0
```

#### 2.3 Update Job Adapter

**File**: `src/dsa110_contimg/api/job_adapters.py`

```python
def run_image_job(job_id: int, ms_path: str, params: dict, products_db: Path) -> None:
    """Run imaging job using new pipeline framework."""
    
    # ... existing code ...
    
    # Extract masking parameters
    use_nvss_mask = params.get("use_nvss_mask", True)
    mask_radius_arcsec = params.get("mask_radius_arcsec", 60.0)
    
    # Add to imaging config
    if "imaging" not in config_dict:
        config_dict["imaging"] = {}
    config_dict["imaging"]["use_nvss_mask"] = use_nvss_mask
    config_dict["imaging"]["mask_radius_arcsec"] = mask_radius_arcsec
    
    # ... rest of existing code ...
```

### Phase 3: Pipeline Stage Integration

#### 3.1 Update ImagingStage

**File**: `src/dsa110_contimg/pipeline/stages_impl.py`

```python
class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS."""
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        
        # ... existing code ...
        
        # Run imaging with masking parameters
        image_ms(
            ms_path,
            imagename=imagename,
            field=context.config.imaging.field or "",
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",
            skip_fits=False,
            use_nvss_mask=context.config.imaging.use_nvss_mask,  # NEW
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,  # NEW
        )
        
        # ... rest of existing code ...
```

## Testing Plan

### Unit Tests

1. **Mask Generation**:
   - Test `create_nvss_fits_mask()` creates valid FITS file
   - Test mask has correct dimensions and WCS
   - Test mask includes correct sources (within FoV, above threshold)
   - Test mask radius is correct

2. **WSClean Integration**:
   - Test `-fits-mask` parameter is passed when mask_path provided
   - Test mask is not passed when mask_path is None
   - Test error handling when mask generation fails

3. **Pipeline Config**:
   - Test `use_nvss_mask` defaults to True
   - Test `mask_radius_arcsec` validation (10-300 arcsec)
   - Test config loading from environment variables

### Integration Tests

1. **End-to-End Imaging**:
   - Test imaging with masking enabled
   - Test imaging with masking disabled
   - Test mask generation failure fallback
   - Compare image quality with/without masking

2. **Dashboard**:
   - Test masking toggle in UI
   - Test mask radius input validation
   - Test API accepts masking parameters

## Documentation Updates

1. **CLI Help**: Update `--help` output for imaging command
2. **Dashboard Guide**: Document masking toggle in dashboard quickstart
3. **API Docs**: Update API reference with masking parameters
4. **Configuration Guide**: Document masking in pipeline configuration docs

## Migration Notes

### Backward Compatibility

- **Default behavior**: Masking enabled by default (more efficient)
- **Existing configs**: Will automatically use masking (no changes needed)
- **CLI**: Existing scripts continue to work (masking enabled by default)
- **API**: Existing API calls continue to work (masking enabled by default)

### Breaking Changes

- None (masking is opt-out, not opt-in)

## Benefits Summary

1. **Performance**: 2-4x faster imaging (especially for development tier)
2. **Quality**: Better image quality (reduced artifacts)
3. **Flexibility**: Toggle masking on/off as needed
4. **User Experience**: Dashboard control for non-technical users
5. **Consistency**: Same masking logic across all quality tiers

## Implementation Priority

1. **High**: Backend implementation (Phases 1.1-1.4)
2. **Medium**: CLI parameter (Phase 1.5)
3. **Medium**: Dashboard integration (Phase 2)
4. **Low**: Pipeline stage integration (Phase 3) - only if using pipeline framework

## Estimated Effort

- **Backend**: 4-6 hours
- **CLI**: 1 hour
- **Dashboard**: 2-3 hours
- **Testing**: 2-3 hours
- **Documentation**: 1 hour
- **Total**: ~10-15 hours

