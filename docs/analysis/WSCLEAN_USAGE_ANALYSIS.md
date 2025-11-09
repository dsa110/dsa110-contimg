# WSClean Usage Analysis

## Overview

WSClean is the **default imaging backend** for the DSA-110 continuum imaging pipeline, providing 2-5x faster performance compared to CASA's `tclean`. This document details how WSClean is integrated and configured within the imaging workflow.

## Architecture

### Entry Point: `image_ms()` Function

The main imaging function `image_ms()` in `src/dsa110_contimg/imaging/cli_imaging.py` serves as the unified interface for both WSClean and CASA tclean backends:

```python
def image_ms(
    ms_path: str,
    *,
    imagename: str,
    backend: str = "wsclean",  # Default is WSClean
    ...
) -> None:
```

**Key Features:**
- Default backend is `"wsclean"` (can be overridden to `"tclean"`)
- Automatically detects and uses `CORRECTED_DATA` when present, otherwise falls back to `DATA`
- Handles NVSS sky model seeding before imaging
- Performs quality validation after imaging
- Supports quality tiers: `development`, `standard`, `high_precision`

### WSClean Execution: `run_wsclean()` Function

The `run_wsclean()` function (lines 36-271 in `cli_imaging.py`) constructs and executes the WSClean command-line:

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
) -> None:
```

## WSClean Executable Discovery

The system uses a **priority-based discovery** mechanism:

1. **Native WSClean** (preferred, 2-5x faster):
   - Checks `PATH` for `wsclean` executable
   - Can be explicitly specified via `wsclean_path` parameter
   - Environment variable: `WSCLEAN_PATH`

2. **Docker Fallback**:
   - Uses Docker image: `wsclean-everybeam-0.7.4`
   - Mounts `/scratch` and `/data` volumes
   - Only used if native WSClean is unavailable

**Code Logic:**
```python
# Priority: Prefer native WSClean over Docker for better performance
wsclean_cmd = shutil.which("wsclean")
if not wsclean_cmd:
    # Fall back to Docker container
    docker_cmd = shutil.which("docker")
    if docker_cmd:
        wsclean_cmd = [docker_cmd, "run", "--rm", 
                       "-v", "/scratch:/scratch", 
                       "-v", "/data:/data",
                       "wsclean-everybeam-0.7.4", "wsclean"]
```

## Command-Line Parameter Mapping

WSClean parameters are mapped from CASA tclean equivalents:

### Basic Imaging Parameters

| CASA tclean | WSClean | Notes |
|------------|---------|-------|
| `imsize` | `-size <N> <N>` | Square images |
| `cell` | `-scale <arcsec>arcsec` | Pixel scale |
| `datacolumn="CORRECTED_DATA"` | `-data-column CORRECTED_DATA` | Only if corrected |
| `field` | `-field <field>` | Field selection |

### Weighting

| CASA | WSClean | Example |
|------|---------|---------|
| `weighting="briggs"`, `robust=0.0` | `-weight briggs 0.0` | Briggs weighting |
| `weighting="natural"` | `-weight natural` | Natural weighting |
| `weighting="uniform"` | `-weight uniform` | Uniform weighting |

### Deconvolution

| CASA | WSClean | Notes |
|------|---------|-------|
| `deconvolver="hogbom"` | (default) | No flag needed |
| `deconvolver="multiscale"` | `-multiscale` | With scales `0,5,15,45` |
| `specmode="mfs"`, `nterms>1` | `-fit-spectral-pol <nterms>` | Multi-term MFS |
| | `-channels-out 8` | Default for multi-term |
| | `-join-channels` | Required for multi-term |

### Iteration and Threshold

| CASA | WSClean | Notes |
|------|---------|-------|
| `niter=1000` | `-niter 1000` | Number of iterations |
| `threshold="0.005Jy"` | `-abs-threshold 0.005Jy` | Absolute threshold |
| `threshold="0.1mJy"` | `-abs-threshold 0.0001Jy` | Converts mJy to Jy |

### Primary Beam and UV Filtering

| CASA | WSClean | Notes |
|------|---------|-------|
| `pbcor=True` | `-apply-primary-beam` | Primary beam correction |
| `pblimit=0.2` | `-primary-beam-limit 0.2` | PB cutoff |
| `uvrange=">1klambda"` | `-minuv-l 1000` | Parses `>1klambda` format |
| `uvrange="<10klambda"` | `-maxuv-l 10000` | Parses `<10klambda` format |

### Wide-Field Gridding

| CASA | WSClean | Notes |
|------|---------|-------|
| `gridder="wproject"` | `-use-wgridder` | WGridder algorithm |
| `imsize > 1024` | `-use-wgridder` | Auto-enabled for large images |
| `wprojplanes` | (not directly supported) | WGridder auto-optimizes |

## Critical WSClean-Specific Parameters

### Data Reordering (CRITICAL)

**Always enabled** for correct multi-SPW processing:

```python
cmd.append("-reorder")
```

**Rationale:** Ensures proper channel ordering across subbands. This is required regardless of quality tier to handle multi-spectral window data correctly.

### Auto-Masking and Convergence

```python
cmd.extend(["-auto-mask", "3"])        # Auto-masking sensitivity
cmd.extend(["-auto-threshold", "0.5"]) # Auto-threshold level
cmd.extend(["-mgain", "0.8"])          # Major cycle gain
```

These parameters help with deconvolution convergence and automatic source detection.

### Performance Optimization

**Threading:**
```python
num_threads = os.getenv("WSCLEAN_THREADS", str(multiprocessing.cpu_count()))
cmd.extend(["-j", num_threads])
```
- Uses all available CPU cores by default
- Can be controlled via `WSCLEAN_THREADS` environment variable

**Memory Allocation:**
```python
# Development tier: 16GB default
# Production: 16GB (imsize <= 2048) or 32GB (imsize > 2048)
abs_mem = os.getenv("WSCLEAN_ABS_MEM", "16" or "32")
cmd.extend(["-abs-mem", abs_mem])
```
- Scales with image size for optimal performance
- Can be overridden via `WSCLEAN_ABS_MEM` environment variable

### Polarization

```python
cmd.extend(["-pol", "I"])  # Stokes I only
```

## Workflow Integration

### Pre-Imaging Steps

1. **MS Validation:**
   - Validates MS structure and required columns
   - Checks `CORRECTED_DATA` quality if present
   - Validates disk space for output images

2. **Image Geometry Calculation:**
   - Enforces fixed 3.5° × 3.5° image extent
   - Calculates `imsize` from `cell_arcsec` to maintain extent
   - Ensures even `imsize` (CASA requirement)

3. **Sky Model Seeding (MODEL_DATA):**
   - **Calibrator seeding:** If `calib_ra_deg`, `calib_dec_deg`, `calib_flux_jy` provided
   - **NVSS seeding:** Sources > `nvss_min_mjy` within FoV
     - Limited to primary beam extent when `pbcor=True`
     - Uses `ft_from_cl()` to seed MODEL_DATA
   - **Critical:** Seeding must happen BEFORE WSClean execution

4. **VP Table Registration:**
   - If `vptable` provided, registers for telescope
   - Supports AWProject gridding

### Post-Imaging Steps

1. **Quality Validation:**
   - Checks image quality using `check_image_quality()`
   - WSClean outputs: `{imagename}-image.fits`
   - CASA outputs: `{imagename}.image` (CASA table)

2. **FITS Export:**
   - WSClean outputs FITS directly (no export needed)
   - CASA requires `exportfits()` for `.image`, `.pb`, `.pbcor`, `.residual`, `.model`

## Quality Tiers

### Development Tier (NON-SCIENCE)

```python
if quality_tier == "development":
    cell_arcsec *= 4.0  # 4x coarser resolution
    niter = min(niter, 300)  # Fewer iterations
    nvss_min_mjy = 10.0  # Higher threshold
```

**Warning:** Explicitly marked as NON-SCIENCE QUALITY for code testing only.

### Standard Tier (Recommended)

- Full quality imaging
- Default settings optimized for science
- Used in production pipeline

### High Precision Tier

```python
elif quality_tier == "high_precision":
    niter = max(niter, 2000)  # More iterations
    nvss_min_mjy = 5.0  # Lower threshold for cleaner sky model
```

## Pipeline Integration Points

### 1. Direct CLI Usage

```python
from dsa110_contimg.imaging.cli_imaging import image_ms

image_ms(
    ms_path,
    imagename=imagename,
    backend="wsclean",  # Default
    quality_tier="standard",
    ...
)
```

### 2. Pipeline Stage (`ImagingStage`)

Located in `src/dsa110_contimg/pipeline/stages_impl.py`:

```python
class ImagingStage(PipelineStage):
    def execute(self, context: PipelineContext):
        image_ms(
            ms_path,
            imagename=imagename,
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",
            ...
        )
```

### 3. Operational Scripts

Multiple operational scripts use `image_ms()`:
- `ops/pipeline/image_groups_in_timerange.py`
- `ops/pipeline/build_transit_mosaic.py`
- `ops/pipeline/build_calibrator_transit_offsets.py`
- `scripts/milestone1_pipeline.py`

## Output Products

### WSClean Outputs (FITS format)

- `{imagename}-image.fits` - Main image
- `{imagename}-image-pbcor.fits` - Primary beam corrected (if `pbcor=True`)
- `{imagename}-residual.fits` - Residual image
- `{imagename}-model.fits` - Model image
- `{imagename}-beam-0.fits` - Primary beam pattern
- `{imagename}-psf.fits` - Point spread function

### CASA Outputs (CASA table format)

- `{imagename}.image` - Main image (CASA table)
- `{imagename}.pb` - Primary beam (CASA table)
- `{imagename}.pbcor` - PB-corrected (CASA table)
- `{imagename}.residual` - Residual (CASA table)
- `{imagename}.model` - Model (CASA table)

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WSCLEAN_THREADS` | `multiprocessing.cpu_count()` | Number of threads |
| `WSCLEAN_ABS_MEM` | `16` (dev) or `16-32` (prod) | Memory allocation (GB) |
| `WSCLEAN_PATH` | (auto-detect) | Path to WSClean executable |

## Error Handling

The `run_wsclean()` function includes comprehensive error handling:

1. **FileNotFoundError:** Provides suggestions for WSClean installation
2. **CalledProcessError:** Logs exit code and provides troubleshooting steps
3. **General Exceptions:** Contextual error messages with suggestions

Error messages include:
- Check WSClean installation
- Verify MS path and permissions
- Check disk space
- Review WSClean parameters

## Performance Characteristics

### Speed Comparison

- **WSClean:** 2-5x faster than CASA tclean
- **Native vs Docker:** Native WSClean is 2-5x faster than Docker

### Memory Usage

- Development tier: 16GB default
- Production: Scales with image size (16-32GB)
- Can be tuned via `WSCLEAN_ABS_MEM`

### Threading

- Uses all available CPU cores by default
- Critical for performance on multi-core systems

## Known Considerations

### MODEL_DATA Seeding

**Critical:** MODEL_DATA must be seeded BEFORE WSClean execution. The `image_ms()` function handles this automatically via:
- `ft_from_cl()` for NVSS/calibrator sources
- Must clear existing MODEL_DATA if present (WSClean compatibility issue)

### Multi-SPW Processing

**Always reorders data** (`-reorder` flag) to ensure correct channel ordering across subbands. This is required regardless of quality tier.

### Wide-Field Gridding

- Automatically enabled for `imsize > 1024` or `gridder="wproject"`
- Uses WGridder algorithm (optimized wide-field gridding)
- `wprojplanes` parameter not directly supported (WGridder auto-optimizes)

## References

- **WSClean Documentation:** https://gitlab.com/aroffringa/wsclean
- **Main Implementation:** `src/dsa110_contimg/imaging/cli_imaging.py`
- **Pipeline Integration:** `src/dsa110_contimg/pipeline/stages_impl.py`
- **CLI Interface:** `src/dsa110_contimg/imaging/cli.py`

