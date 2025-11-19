"""Core imaging functions for imaging CLI."""

import logging
import os
import shutil
import subprocess
import time
from typing import Optional

# Initialize CASA environment before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

# Prefer module import so mocks on casacore.tables.table are respected at call time
import casacore.tables as casatables
import numpy as np

# Back-compat symbol for tests that patch dsa110_contimg.imaging.cli_imaging.table
table = casatables.table  # noqa: N816 (kept for test patchability)
from casatasks import exportfits, tclean  # type: ignore[import]

try:
    from casatools import msmetadata as _msmd  # type: ignore[import]
    from casatools import vpmanager as _vpmanager  # type: ignore[import]
except Exception:  # pragma: no cover
    _vpmanager = None
    _msmd = None

from dsa110_contimg.imaging.cli_utils import default_cell_arcsec, detect_datacolumn
from dsa110_contimg.utils.error_context import format_ms_error_with_suggestions
from dsa110_contimg.utils.performance import track_performance
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python
from dsa110_contimg.utils.validation import ValidationError, validate_ms

LOG = logging.getLogger(__name__)

# Fixed image extent: all images should be 3.5° x 3.5° regardless of resolution
FIXED_IMAGE_EXTENT_DEG = 3.5

try:
    from dsa110_contimg.utils.tempdirs import (
        derive_default_scratch_root,
        prepare_temp_environment,
    )
except Exception:  # pragma: no cover - defensive import
    prepare_temp_environment = None  # type: ignore
    derive_default_scratch_root = None  # type: ignore


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
    mask_path: Optional[str] = None,
    target_mask: Optional[str] = None,
    galvin_clip_mask: Optional[str] = None,
    erode_beam_shape: bool = False,
) -> None:
    """Run WSClean with parameters mapped from tclean equivalents.

    This function builds a WSClean command-line that matches the tclean
    parameters as closely as possible. MODEL_DATA seeding should be done
    before calling this function via CASA ft().

    Args:
        quality_tier: Imaging quality tier ("development", "standard", or
            "high_precision"). Development tier uses 4x coarser cell size
            and fewer iterations for faster processing (non-science quality).
            Data is always reordered regardless of quality tier to ensure
            correct multi-SPW processing.
    """
    # Prepare mask if needed
    if mask_path or target_mask or galvin_clip_mask or erode_beam_shape:
        from dsa110_contimg.imaging.cli_utils import prepare_cleaning_mask

        # If we have advanced masking options but no base mask_path, we need to decide what to do.
        # For WSClean, we typically start with a base mask.
        # If mask_path is None but others are set, we might need a dummy or full-field mask?
        # For now, assume mask_path is the primary mask being modified.

        if mask_path:
            try:
                prepared_mask = prepare_cleaning_mask(
                    fits_mask=mask_path,
                    target_mask=target_mask,
                    galvin_clip_mask=galvin_clip_mask,
                    erode_beam_shape=erode_beam_shape,
                )
                if prepared_mask:
                    mask_path = str(prepared_mask)
            except Exception as e:
                LOG.warning(
                    f"Failed to prepare advanced mask: {e}. Proceeding with original mask if any."
                )

    # Find WSClean executable
    # Priority: Prefer native WSClean over Docker for better performance (2-5x faster)
    if wsclean_path:
        if wsclean_path == "docker":
            # Check for native WSClean first (faster than Docker)
            native_wsclean = shutil.which("wsclean")
            if native_wsclean:
                LOG.info("Using native WSClean (faster than Docker)")
                wsclean_cmd = [native_wsclean]
            else:
                # Fall back to Docker if native not available
                docker_cmd = shutil.which("docker")
                if not docker_cmd:
                    raise RuntimeError("Docker not found but --wsclean-path=docker was specified")
                wsclean_cmd = [
                    docker_cmd,
                    "run",
                    "--rm",
                    "-v",
                    "/scratch:/scratch",
                    "-v",
                    "/data:/data",
                    "-v",
                    "/stage:/stage",
                    "-v",
                    "/dev/shm:/dev/shm",
                    "wsclean-everybeam-0.7.4",
                    "wsclean",
                ]
        else:
            wsclean_cmd = [wsclean_path]
    else:
        # Check for native WSClean first (preferred)
        wsclean_cmd = shutil.which("wsclean")
        if not wsclean_cmd:
            # Fall back to Docker container if native not available
            docker_cmd = shutil.which("docker")
            if docker_cmd:
                wsclean_cmd = [
                    docker_cmd,
                    "run",
                    "--rm",
                    "-v",
                    "/scratch:/scratch",
                    "-v",
                    "/data:/data",
                    "-v",
                    "/stage:/stage",
                    "-v",
                    "/dev/shm:/dev/shm",
                    "wsclean-everybeam-0.7.4",
                    "wsclean",
                ]
            else:
                raise RuntimeError(
                    "WSClean not found. Install WSClean or set WSCLEAN_PATH environment variable, "
                    "or ensure Docker is available with wsclean-everybeam-0.7.4 image."
                )
        else:
            wsclean_cmd = [wsclean_cmd]
            LOG.debug("Using native WSClean (faster than Docker)")

    # Build command
    cmd = wsclean_cmd.copy()

    # Output name (use same path for Docker since volumes are mounted)
    cmd.extend(["-name", imagename])

    # Image size and pixel scale
    cmd.extend(["-size", str(imsize), str(imsize)])
    cmd.extend(["-scale", f"{cell_arcsec:.3f}arcsec"])

    # Data column
    if datacolumn == "corrected":
        cmd.extend(["-data-column", "CORRECTED_DATA"])

    # Field selection (if specified)
    if field:
        cmd.extend(["-field", field])

    # Weighting
    if weighting.lower() == "briggs":
        cmd.extend(["-weight", "briggs", str(robust)])
    elif weighting.lower() == "natural":
        cmd.extend(["-weight", "natural"])
    elif weighting.lower() == "uniform":
        cmd.extend(["-weight", "uniform"])

    # Multi-term deconvolution (mtmfs equivalent)
    if specmode == "mfs" and nterms > 1:
        cmd.extend(["-fit-spectral-pol", str(nterms)])
        cmd.extend(["-channels-out", "8"])  # Reasonable default for multi-term
        cmd.extend(["-join-channels"])

    # Deconvolver
    if deconvolver == "multiscale":
        cmd.append("-multiscale")
        # Default scales if not specified
        cmd.extend(["-multiscale-scales", "0,5,15,45"])
    elif deconvolver == "hogbom":
        # Default is hogbom, no flag needed
        pass

    # Iterations and threshold
    cmd.extend(["-niter", str(niter)])

    # Parse threshold string (e.g., "0.005Jy" or "0.1mJy")
    threshold_lower = threshold.lower().strip()
    if threshold_lower.endswith("jy"):
        threshold_val = float(threshold_lower[:-2])
        if threshold_val > 0:
            cmd.extend(["-abs-threshold", threshold])
    elif threshold_lower.endswith("mjy"):
        threshold_val = float(threshold_lower[:-3]) / 1000.0  # Convert to Jy
        if threshold_val > 0:
            cmd.extend(["-abs-threshold", f"{threshold_val:.6f}Jy"])

    # Primary beam correction
    if pbcor:
        cmd.append("-apply-primary-beam")

    # UV range filtering
    if uvrange:
        # Parse ">1klambda" format
        import re

        match = re.match(r"([<>]?)(\d+(?:\.\d+)?)(?:\.)?(k?lambda)", uvrange.lower())
        if match:
            op, val, unit = match.groups()
            val_float = float(val)
            if unit == "klambda":
                val_float *= 1000.0
            if op == ">":
                cmd.extend(["-minuv-l", str(int(val_float))])
            elif op == "<":
                cmd.extend(["-maxuv-l", str(int(val_float))])

    # Primary beam limit
    if pblimit > 0:
        cmd.extend(["-primary-beam-limit", str(pblimit)])

    # Wide-field gridding (wproject equivalent)
    # WGridder is WSClean's optimized wide-field gridding algorithm
    # Enable when wproject is requested OR for large images
    if gridder == "wproject" or imsize > 1024:
        cmd.append("-use-wgridder")
        # Note: wprojplanes parameter is not directly supported by WSClean's WGridder
        # WGridder automatically optimizes the number of planes based on image size and frequency
        LOG.debug("Enabled wide-field gridding (WGridder)")

    # Reordering (required for multi-spw, but can be slow - only if needed)
    # CRITICAL: Always reorder data - required for correct multi-SPW processing
    # Reorder ensures proper channel ordering across subbands
    cmd.append("-reorder")

    # Mask file (if provided)
    if mask_path:
        cmd.extend(["-fits-mask", mask_path])
        LOG.info("Using mask file: %s", mask_path)

    # Auto-masking (helps with convergence)
    # Note: Auto-masking can be combined with user-provided mask
    # WSClean will use the user mask as initial constraint and auto-expand if needed
    cmd.extend(["-auto-mask", "3"])
    cmd.extend(["-auto-threshold", "0.5"])
    cmd.extend(["-mgain", "0.8"])

    # Threading: use all available CPU cores (critical for performance!)
    import multiprocessing

    num_threads = os.getenv("WSCLEAN_THREADS", str(multiprocessing.cpu_count()))
    cmd.extend(["-j", num_threads])
    LOG.debug(f"Using {num_threads} threads for WSClean")

    # Memory limit (optimized for performance)
    # Development tier: Use more memory for faster gridding/FFT (16GB default)
    # Production mode: Scale with image size (16-32GB)
    if quality_tier == "development":
        # Development tier: Allow more memory for speed (10-30% faster gridding)
        abs_mem = os.getenv("WSCLEAN_ABS_MEM", "16")
    else:
        # Production mode: Scale with image size
        abs_mem = os.getenv("WSCLEAN_ABS_MEM", "32" if imsize > 2048 else "16")
    cmd.extend(["-abs-mem", abs_mem])
    LOG.debug(f"WSClean memory allocation: {abs_mem}GB")

    # Polarity
    cmd.extend(["-pol", "I"])

    # Input MS (use same path for Docker since volumes are mounted)
    cmd.append(ms_path)

    # Log command
    cmd_str = " ".join(cmd)
    LOG.info("Running WSClean: %s", cmd_str)

    # Execute
    t0 = time.perf_counter()
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True,
        )
        LOG.info("WSClean completed in %.2fs", time.perf_counter() - t0)
    except subprocess.CalledProcessError as e:
        LOG.error("WSClean failed with exit code %d", e.returncode)
        raise RuntimeError(f"WSClean execution failed: {e}") from e
    except FileNotFoundError:
        suggestions = [
            "Check WSClean installation",
            "Verify WSClean is in PATH",
            "Use --wsclean-path to specify WSClean location",
            "Install WSClean: https://gitlab.com/aroffringa/wsclean",
        ]
        error_msg = format_ms_error_with_suggestions(
            FileNotFoundError(f"WSClean executable not found: {wsclean_cmd}"),
            ms_path,
            "WSClean execution",
            suggestions,
        )
        raise RuntimeError(error_msg) from None
    except Exception as e:
        suggestions = [
            "Check WSClean logs for detailed error information",
            "Verify MS path and file permissions",
            "Check disk space for output images",
            "Review WSClean parameters and configuration",
        ]
        error_msg = format_ms_error_with_suggestions(e, ms_path, "WSClean execution", suggestions)
        raise RuntimeError(error_msg) from e


@track_performance("imaging", log_result=True)
@require_casa6_python
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
    use_nvss_mask: bool = True,
    mask_path: Optional[str] = None,
    mask_radius_arcsec: float = 60.0,
    target_mask: Optional[str] = None,
    galvin_clip_mask: Optional[str] = None,
    erode_beam_shape: bool = False,
) -> None:
    """Main imaging function for Measurement Sets.

    Supports both CASA tclean and WSClean backends. WSClean is the default.
    Automatically selects CORRECTED_DATA when present, otherwise uses DATA.

    Quality Tiers:
        - development: 4x coarser cell size, max 300 iterations, NVSS threshold 10 mJy.
          NON-SCIENCE QUALITY - for code testing only. Data is always reordered.
        - standard: Full quality imaging (recommended for science).
        - high_precision: Enhanced settings with 2000+ iterations, NVSS threshold 5 mJy.

    NVSS Seeding:
        When pbcor=True, NVSS sources are limited to the primary beam extent
        (based on pblimit) to avoid including sources beyond the corrected region.
        The seeding radius is calculated from the primary beam FWHM and pblimit.

    Masking:
        When use_nvss_mask=True and nvss_min_mjy is provided, generates a FITS mask
        from NVSS sources for WSClean. This provides 2-4x faster imaging by restricting
        cleaning to known source locations. Masking is only supported for WSClean backend.
    """
    from dsa110_contimg.utils.validation import validate_corrected_data_quality

    # Validate MS using shared validation module
    try:
        validate_ms(
            ms_path,
            check_empty=True,
            check_columns=["DATA", "ANTENNA1", "ANTENNA2", "TIME", "UVW"],
        )
    except ValidationError as e:
        suggestions = [
            "Check MS path is correct and file exists",
            "Verify file permissions",
            "Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>",
            "Check MS structure and integrity",
        ]
        error_msg = format_ms_error_with_suggestions(e, ms_path, "MS validation", suggestions)
        raise RuntimeError(error_msg) from e

    # Validate CORRECTED_DATA quality if present - FAIL if calibration appears unapplied
    warnings = validate_corrected_data_quality(ms_path)
    if warnings:
        # Distinguish between unpopulated data warnings and validation errors
        unpopulated_warnings = [
            w
            for w in warnings
            if "appears unpopulated" in w.lower()
            or "zero rows" in w.lower()
            or "all sampled data is flagged" in w.lower()
        ]
        validation_errors = [
            w for w in warnings if w.startswith("Error validating CORRECTED_DATA:")
        ]

        if unpopulated_warnings:
            # CORRECTED_DATA exists but is unpopulated - calibration failed
            suggestions = [
                "Re-run calibration on this MS",
                "Check calibration logs for errors",
                "Verify calibration tables were applied correctly",
                "Use --datacolumn=DATA to image uncalibrated data (not recommended)",
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("CORRECTED_DATA column exists but appears unpopulated"),
                ms_path,
                "calibration validation",
                suggestions,
            )
            error_msg += f"\nDetails: {'; '.join(unpopulated_warnings)}"
            LOG.error(error_msg)
            raise RuntimeError(error_msg)
        elif validation_errors:
            # Validation error (e.g., permission denied, file access issue)
            suggestions = [
                "Check file permissions on MS directory",
                "Verify MS file is not corrupted",
                "Check disk space and file system",
                "Review detailed error logs",
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("Failed to validate CORRECTED_DATA"),
                ms_path,
                "MS validation",
                suggestions,
            )
            error_msg += f"\nDetails: {'; '.join(validation_errors)}"
            LOG.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            # Other warnings (shouldn't happen, but handle gracefully)
            suggestions = [
                "Review calibration validation warnings",
                "Check MS structure and integrity",
                "Verify calibration was applied correctly",
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("Calibration validation warnings"),
                ms_path,
                "calibration validation",
                suggestions,
            )
            error_msg += f"\nDetails: {'; '.join(warnings)}"
            LOG.error(error_msg)
            raise RuntimeError(error_msg)

    # PRECONDITION CHECK: Verify sufficient disk space for images
    # This ensures we follow "measure twice, cut once" - verify resources upfront
    # before expensive imaging operations.
    try:
        output_dir = os.path.dirname(os.path.abspath(imagename))
        os.makedirs(output_dir, exist_ok=True)

        # Estimate image size: rough estimate based on imsize and number of images
        # Each image is approximately: imsize^2 * 4 bytes (float32) * number of images
        # We create: .image, .model, .residual, .pb, .pbcor = 5 images
        # Plus weights, etc. Use 10x safety margin for overhead
        bytes_per_pixel = 4  # float32
        # Conservative estimate (.image, .model, .residual, .pb, .pbcor, weights, etc.)
        num_images = 10
        image_size_estimate = (
            imsize * imsize * bytes_per_pixel * num_images * 10
        )  # 10x safety margin

        # CRITICAL: Check disk space (fatal check for imaging operations)
        from dsa110_contimg.mosaic.error_handling import check_disk_space

        has_space, space_msg = check_disk_space(
            imagename,
            required_bytes=image_size_estimate,
            operation=f"imaging of {ms_path}",
            fatal=True,  # Fail fast if insufficient space
        )
        LOG.info(space_msg)
    except RuntimeError:
        # Re-raise RuntimeError from fatal disk space check
        raise
    except Exception as e:
        # Other exceptions: log warning but don't fail (may be permission issues, etc.)
        LOG.warning(f"Failed to check disk space: {e}")

    # Prepare temp dirs and working directory to keep TempLattice* off the repo
    try:
        if prepare_temp_environment is not None:
            out_dir = os.path.dirname(os.path.abspath(imagename))
            root = os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg"
            prepare_temp_environment(root, cwd_to=out_dir)
    except Exception:
        # Best-effort; continue even if temp prep fails
        pass
    datacolumn = detect_datacolumn(ms_path)
    if cell_arcsec is None:
        cell_arcsec = default_cell_arcsec(ms_path)

    # Enforce 3.5° x 3.5° image extent
    desired_extent_arcsec = FIXED_IMAGE_EXTENT_DEG * 3600.0  # 12600 arcsec

    # Store original imsize for warning if user overrode it
    user_imsize = imsize

    # Calculate imsize to maintain 3.5° extent
    # If user specified both imsize and cell_arcsec, use cell_arcsec and recalculate imsize
    calculated_imsize = int(np.ceil(desired_extent_arcsec / cell_arcsec))
    # Ensure even number (CASA requirement)
    if calculated_imsize % 2 != 0:
        calculated_imsize += 1

    # Warn if user specified imsize but we're overriding it
    if user_imsize != 1024:  # 1024 is the default, so only warn if user explicitly set it
        if calculated_imsize != user_imsize:
            LOG.warning(
                "User-specified imsize=%d overridden to maintain 3.5° extent: "
                "calculated imsize=%d from cell_arcsec=%.3f arcsec",
                user_imsize,
                calculated_imsize,
                cell_arcsec,
            )

    imsize = calculated_imsize
    cell = f"{cell_arcsec:.3f}arcsec"

    # Apply quality tier settings
    if quality_tier == "development":
        # ⚠️  NON-SCIENCE QUALITY - For code testing only
        LOG.warning(
            "=" * 80 + "\n"
            "⚠️  DEVELOPMENT TIER: NON-SCIENCE QUALITY\n"
            "   This tier uses coarser resolution and fewer iterations.\n"
            "   NEVER use for actual science observations or ESE detection.\n"
            "   Results will have reduced angular resolution and deconvolution quality.\n"
            "=" * 80
        )
        # Coarser resolution (4x default cell size)
        default_cell = default_cell_arcsec(ms_path)
        if abs(cell_arcsec - default_cell) < 0.01:  # Only adjust if using default cell size
            cell_arcsec = cell_arcsec * 4.0
            # Recalculate imsize for new cell size
            calculated_imsize = int(np.ceil(desired_extent_arcsec / cell_arcsec))
            if calculated_imsize % 2 != 0:
                calculated_imsize += 1
            imsize = calculated_imsize
            cell = f"{cell_arcsec:.3f}arcsec"
            LOG.info(
                "Development tier: using coarser cell size (%.3f arcsec) - NON-SCIENCE QUALITY",
                cell_arcsec,
            )
        niter = min(niter, 300)  # Fewer iterations
        # Lower NVSS seeding threshold for faster convergence
        if nvss_min_mjy is None:
            nvss_min_mjy = 10.0
            LOG.info(
                "Development tier: NVSS seeding threshold set to %s mJy (NON-SCIENCE)",
                nvss_min_mjy,
            )

    elif quality_tier == "standard":
        # Recommended for all science observations - no compromises
        LOG.info("Standard tier: full quality imaging (recommended for science)")
        # Use default settings optimized for science quality

    elif quality_tier == "high_precision":
        # Enhanced quality for critical observations
        LOG.info("High precision tier: enhanced quality settings (slower)")
        niter = max(niter, 2000)  # More iterations for better deconvolution
        if nvss_min_mjy is None:
            nvss_min_mjy = 5.0  # Lower threshold for cleaner sky model
            LOG.info(
                "High precision tier: NVSS seeding threshold set to %s mJy",
                nvss_min_mjy,
            )
    LOG.info("Imaging %s -> %s", ms_path, imagename)
    LOG.info(
        "datacolumn=%s cell=%s imsize=%d quality_tier=%s",
        datacolumn,
        cell,
        imsize,
        quality_tier,
    )

    # Build common kwargs for tclean, adding optional params only when needed
    kwargs = dict(
        vis=ms_path,
        imagename=imagename,
        datacolumn=datacolumn,
        field=field,
        spw=spw,
        imsize=[imsize, imsize],
        cell=[cell, cell],
        weighting=weighting,
        robust=robust,
        specmode=specmode,
        deconvolver=deconvolver,
        nterms=nterms,
        niter=niter,
        threshold=threshold,
        gridder=gridder,
        wprojplanes=wprojplanes,
        stokes="I",
        restoringbeam="",
        pbcor=pbcor,
        phasecenter=phasecenter if phasecenter else "",
        interactive=False,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    if pblimit is not None:
        kwargs["pblimit"] = pblimit
    if psfcutoff is not None:
        kwargs["psfcutoff"] = psfcutoff
    if vptable:
        kwargs["vptable"] = vptable
    if wbawp is not None:
        kwargs["wbawp"] = bool(wbawp)
    if cfcache:
        kwargs["cfcache"] = cfcache

    # Avoid overwriting any seeded MODEL_DATA during tclean
    kwargs["savemodel"] = "none"

    # Compute approximate FoV radius from image geometry
    import math as _math

    fov_x = (cell_arcsec * imsize) / 3600.0
    fov_y = (cell_arcsec * imsize) / 3600.0
    radius_deg = 0.5 * float(_math.hypot(fov_x, fov_y))

    # Get phase center from MS (needed for mask generation and NVSS seeding)
    ra0_deg = dec0_deg = None
    with casatables.table(f"{ms_path}::FIELD", readonly=True) as fld:
        try:
            ph = fld.getcol("PHASE_DIR")[0]
            ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
            dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
        except Exception:
            pass
    if ra0_deg is None or dec0_deg is None:
        LOG.warning("Could not determine phase center from MS FIELD table")

    # Optional: seed a single-component calibrator model if provided and in FoV
    did_seed = False
    if (
        calib_ra_deg is not None
        and calib_dec_deg is not None
        and calib_flux_jy is not None
        and calib_flux_jy > 0
    ):
        try:
            with casatables.table(f"{ms_path}::FIELD", readonly=True) as fld:
                ph = fld.getcol("PHASE_DIR")[0]
                ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
            # crude small-angle separation in deg
            d_ra = (float(calib_ra_deg) - ra0_deg) * np.cos(np.deg2rad(dec0_deg))
            d_dec = float(calib_dec_deg) - dec0_deg
            sep_deg = float(_math.hypot(d_ra, d_dec))
            if sep_deg <= radius_deg * 1.05:
                from dsa110_contimg.calibration.skymodels import (  # type: ignore
                    ft_from_cl,
                    make_point_cl,
                )

                cl_path = f"{imagename}.calibrator_{calib_flux_jy:.3f}Jy.cl"
                make_point_cl(
                    name="calibrator",
                    ra_deg=float(calib_ra_deg),
                    dec_deg=float(calib_dec_deg),
                    flux_jy=float(calib_flux_jy),
                    freq_ghz=1.4,
                    out_path=cl_path,
                )
                ft_from_cl(ms_path, cl_path, field=field or "0", usescratch=True)
                LOG.info(
                    "Seeded MODEL_DATA with calibrator point model (flux=%.3f Jy)",
                    calib_flux_jy,
                )
                did_seed = True
        except Exception as exc:
            LOG.debug("Calibrator seeding skipped: %s", exc)

    # Optional: seed a sky model from NVSS (> nvss_min_mjy mJy) via ft(), if no calibrator seed
    if (not did_seed) and (nvss_min_mjy is not None):
        try:
            from dsa110_contimg.calibration.skymodels import (  # type: ignore
                ft_from_cl,
                make_nvss_component_cl,
            )

            # Use phase center already determined above
            if ra0_deg is None or dec0_deg is None:
                raise RuntimeError("FIELD::PHASE_DIR not available")

            # Limit NVSS seeding radius to primary beam extent when pbcor is enabled
            # Primary beam FWHM at 1.4 GHz: ~3.2 degrees (1.22 * lambda / D)
            # Use pblimit to determine effective radius (typically 20% of peak = ~1.6 deg radius)
            # Mean observing frequency and bandwidth
            freq_ghz = 1.4
            bandwidth_hz = 250e6  # Default 250 MHz
            try:
                with casatables.table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                    ch = spw.getcol("CHAN_FREQ")[0]
                    freq_ghz = float(np.nanmean(ch)) / 1e9
                    if len(ch) > 1:
                        bandwidth_hz = float(np.max(ch) - np.min(ch) + abs(ch[1] - ch[0]))
                    else:
                        bandwidth_hz = float(spw.getcol("TOTAL_BANDWIDTH")[0])
            except Exception:
                pass

            # Calculate primary beam radius based on pblimit
            # Primary beam FWHM = 1.22 * lambda / D
            # For DSA-110: D = 4.7 m, lambda = c / (freq_ghz * 1e9)
            # At pblimit=0.2, effective radius is approximately FWHM * sqrt(-ln(0.2)) / sqrt(-ln(0.5))
            import math

            c_mps = 299792458.0
            dish_dia_m = 4.7
            lambda_m = c_mps / (freq_ghz * 1e9)
            fwhm_rad = 1.22 * lambda_m / dish_dia_m
            fwhm_deg = math.degrees(fwhm_rad)

            # Calculate radius at pblimit (Airy pattern: PB = (2*J1(x)/x)^2, solve for PB = pblimit)
            # Approximate: radius at pblimit ≈ FWHM * sqrt(-ln(pblimit)) / sqrt(-ln(0.5))
            if pbcor and pblimit > 0:
                pb_radius_deg = fwhm_deg * math.sqrt(-math.log(pblimit)) / math.sqrt(-math.log(0.5))
                # Use the smaller of image radius or primary beam radius
                nvss_radius_deg = min(radius_deg, pb_radius_deg)
                LOG.info(
                    "Limiting NVSS seeding to primary beam extent: %.2f deg (pblimit=%.2f, FWHM=%.2f deg)",
                    nvss_radius_deg,
                    pblimit,
                    fwhm_deg,
                )
            else:
                nvss_radius_deg = radius_deg

            # Note: wsclean -predict with -model-list is not supported by the installed wsclean version.
            # We use a 2-step process: -draw-model then -predict.
            if backend == "wsclean":
                # Use wsclean -predict (faster, multi-threaded)
                txt_path = f"{imagename}.unified_{float(nvss_min_mjy):g}mJy.txt"
                LOG.info(
                    "Creating Unified source list (FIRST+RACS+NVSS) (>%s mJy, radius %.2f deg) for wsclean -predict",
                    nvss_min_mjy,
                    nvss_radius_deg,
                )
                try:
                    from dsa110_contimg.calibration.skymodels import make_unified_wsclean_list

                    make_unified_wsclean_list(
                        ra0_deg,
                        dec0_deg,
                        nvss_radius_deg,
                        min_mjy=float(nvss_min_mjy),
                        freq_ghz=freq_ghz,
                        out_path=txt_path,
                    )

                    # Determine wsclean executable
                    import shutil
                    import subprocess

                    wsclean_exec = wsclean_path
                    if not wsclean_exec:
                        wsclean_exec = shutil.which("wsclean")

                    # If not found locally, check for Docker
                    use_docker = False
                    if not wsclean_exec:
                        if shutil.which("docker"):
                            use_docker = True
                        else:
                            raise RuntimeError("wsclean executable not found for prediction")

                    if use_docker:
                        # Docker command construction
                        # We need to map volumes. Assumes simple paths (no complex relative paths)
                        ms_dir = os.path.dirname(os.path.abspath(ms_path))
                        ms_name = os.path.basename(ms_path)
                        txt_dir = os.path.dirname(os.path.abspath(txt_path))
                        txt_name = os.path.basename(txt_path)

                        # Convert decimal degrees to h:m:s and d:m:s format
                        # WSClean requires this format for -draw-centre
                        ra_hours = ra0_deg / 15.0
                        ra_h = int(ra_hours)
                        ra_m = int((ra_hours - ra_h) * 60)
                        ra_s = ((ra_hours - ra_h) * 60 - ra_m) * 60
                        ra_str = f"{ra_h}h{ra_m}m{ra_s:.3f}s"

                        dec_sign = "+" if dec0_deg >= 0 else "-"
                        dec_abs = abs(dec0_deg)
                        dec_d = int(dec_abs)
                        dec_m = int((dec_abs - dec_d) * 60)
                        dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
                        dec_str = f"{dec_sign}{dec_d}d{dec_m}m{dec_s:.3f}s"

                        # Step 1: Render model image from text list
                        # Output will be /data_txt/nvss_model-term-0.fits
                        cmd_draw = [
                            "docker",
                            "run",
                            "--rm",
                            "-v",
                            f"{ms_dir}:/data_ms",
                            "-v",
                            f"{txt_dir}:/data_txt",
                            "wsclean-everybeam-0.7.4",
                            "wsclean",
                            "-draw-model",
                            f"/data_txt/{txt_name}",
                            "-name",
                            "/data_txt/nvss_model",
                            "-draw-frequencies",
                            f"{freq_ghz*1e9}",
                            f"{bandwidth_hz}",
                            "-draw-spectral-terms",
                            "2",
                            "-size",
                            str(imsize),
                            str(imsize),
                            "-scale",
                            f"{cell_arcsec}arcsec",
                            "-draw-centre",
                            ra_str,
                            dec_str,
                        ]

                        LOG.info("Running wsclean -draw-model: %s", " ".join(cmd_draw))
                        subprocess.run(cmd_draw, check=True)

                        # Step 1.5: Rename output file for prediction
                        # WSClean -draw-model creates prefix-term-0.fits
                        # WSClean -predict expects prefix-model.fits
                        term_file = os.path.join(txt_dir, "nvss_model-term-0.fits")
                        model_file = os.path.join(txt_dir, "nvss_model-model.fits")
                        if os.path.exists(term_file):
                            shutil.move(term_file, model_file)
                            LOG.info(f"Renamed {term_file} -> {model_file}")
                        else:
                            LOG.warning(f"Expected output file not found: {term_file}")

                        # Step 2: Predict from rendered image
                        cmd_predict = [
                            "docker",
                            "run",
                            "--rm",
                            "-v",
                            f"{ms_dir}:/data_ms",
                            "-v",
                            f"{txt_dir}:/data_txt",
                            "wsclean-everybeam-0.7.4",
                            "wsclean",
                            "-predict",
                            "-reorder",  # Required for multi-SPW MS
                            "-name",
                            "/data_txt/nvss_model",
                            f"/data_ms/{ms_name}",
                        ]

                        LOG.info("Running wsclean -predict: %s", " ".join(cmd_predict))
                        subprocess.run(cmd_predict, check=True)

                    else:
                        # Native WSClean execution
                        # Convert decimal degrees to h:m:s and d:m:s format
                        ra_hours = ra0_deg / 15.0
                        ra_h = int(ra_hours)
                        ra_m = int((ra_hours - ra_h) * 60)
                        ra_s = ((ra_hours - ra_h) * 60 - ra_m) * 60
                        ra_str = f"{ra_h}h{ra_m}m{ra_s:.3f}s"

                        dec_sign = "+" if dec0_deg >= 0 else "-"
                        dec_abs = abs(dec0_deg)
                        dec_d = int(dec_abs)
                        dec_m = int((dec_abs - dec_d) * 60)
                        dec_s = ((dec_abs - dec_d) * 60 - dec_m) * 60
                        dec_str = f"{dec_sign}{dec_d}d{dec_m}m{dec_s:.3f}s"

                        # Step 1: Render model
                        cmd_draw = [
                            wsclean_exec,
                            "-draw-model",
                            txt_path,
                            "-name",
                            f"{imagename}.nvss_model",
                            "-draw-frequencies",
                            f"{freq_ghz*1e9}",
                            f"{bandwidth_hz}",
                            "-draw-spectral-terms",
                            "2",
                            "-size",
                            str(imsize),
                            str(imsize),
                            "-scale",
                            f"{cell_arcsec}arcsec",
                            "-draw-centre",
                            ra_str,
                            dec_str,
                        ]
                        LOG.info("Running wsclean -draw-model: %s", " ".join(cmd_draw))
                        subprocess.run(cmd_draw, check=True)

                        # Step 1.5: Rename output file for prediction
                        term_file = f"{imagename}.nvss_model-term-0.fits"
                        model_file = f"{imagename}.nvss_model-model.fits"
                        if os.path.exists(term_file):
                            shutil.move(term_file, model_file)
                            LOG.info(f"Renamed {term_file} -> {model_file}")
                        else:
                            LOG.warning(f"Expected output file not found: {term_file}")

                        # Step 2: Predict
                        cmd_predict = [
                            wsclean_exec,
                            "-predict",
                            "-reorder",  # Required for multi-SPW MS
                            "-name",
                            f"{imagename}.nvss_model",
                            ms_path,
                        ]
                        LOG.info("Running wsclean -predict: %s", " ".join(cmd_predict))
                        subprocess.run(cmd_predict, check=True)

                    LOG.info("Seeded MODEL_DATA with wsclean -predict")

                except ImportError:
                    LOG.warning("pyradiosky not installed; falling back to CASA ft()")
                    # Fallback to ft() if pyradiosky missing (shouldn't happen in prod)
                    backend = (
                        "tclean"  # Hack to trigger else block? No, just copy-paste or refactor.
                    )
                    # Better to just let it fail or ensure dependencies.
                    raise

            else:
                # Use CASA ft() (standard/tclean)
                cl_path = f"{imagename}.nvss_{float(nvss_min_mjy):g}mJy.cl"
                LOG.info(
                    "Creating NVSS componentlist (>%s mJy, radius %.2f deg, center RA=%.6f° Dec=%.6f°)",
                    nvss_min_mjy,
                    nvss_radius_deg,
                    ra0_deg,
                    dec0_deg,
                )
                make_nvss_component_cl(
                    ra0_deg,
                    dec0_deg,
                    nvss_radius_deg,
                    min_mjy=float(nvss_min_mjy),
                    freq_ghz=freq_ghz,
                    out_path=cl_path,
                )
                # Verify componentlist was created
                if not os.path.exists(cl_path):
                    raise RuntimeError(f"NVSS componentlist was not created: {cl_path}")
                LOG.info("NVSS componentlist created: %s", cl_path)
                ft_from_cl(ms_path, cl_path, field=field or "0", usescratch=True)
                LOG.info(
                    "Seeded MODEL_DATA with NVSS skymodel (>%s mJy, radius %.2f deg)",
                    nvss_min_mjy,
                    nvss_radius_deg,
                )

            # Export MODEL_DATA as FITS image if requested
            if export_model_image:
                try:
                    from dsa110_contimg.calibration.model import export_model_as_fits

                    output_path = f"{imagename}.nvss_model"
                    LOG.info(f"Exporting NVSS model image to {output_path}.fits...")
                    export_model_as_fits(
                        ms_path,
                        output_path,
                        field=field or "0",
                        imsize=512,
                        cell_arcsec=1.0,
                    )
                except Exception as e:
                    LOG.warning(f"Failed to export NVSS model image: {e}")
        except Exception as exc:
            LOG.warning("NVSS skymodel seeding skipped: %s", exc)
            import traceback

            LOG.debug("NVSS seeding traceback: %s", traceback.format_exc())

    # If a VP table is supplied, proactively register it as user default for the
    # telescope reported by the MS (and for DSA_110) to satisfy AWProject.
    if vptable and _vpmanager is not None and _msmd is not None:
        try:
            telname = None
            md = _msmd()
            md.open(ms_path)
            try:
                telname = md.telescope()
            finally:
                md.close()
            vp = _vpmanager()
            vp.loadfromtable(vptable)
            for tname in filter(None, [telname, "DSA_110"]):
                try:
                    vp.setuserdefault(telescope=tname)
                except Exception:
                    pass
            LOG.debug(
                "Registered VP table %s for telescope(s): %s",
                vptable,
                [telname, "DSA_110"],
            )
        except Exception as exc:
            LOG.debug("VP preload skipped: %s", exc)

    # Generate mask if requested (before imaging)
    if mask_path is None and use_nvss_mask and nvss_min_mjy is not None and backend == "wsclean":
        if ra0_deg is not None and dec0_deg is not None:
            try:
                from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

                mask_path = create_nvss_fits_mask(
                    imagename=imagename,
                    imsize=imsize,
                    cell_arcsec=cell_arcsec,
                    ra0_deg=ra0_deg,
                    dec0_deg=dec0_deg,
                    nvss_min_mjy=nvss_min_mjy,
                    radius_arcsec=mask_radius_arcsec,
                )
                LOG.info(
                    "Generated NVSS mask: %s (radius=%.1f arcsec, sources >= %.1f mJy)",
                    mask_path,
                    mask_radius_arcsec,
                    nvss_min_mjy,
                )
            except Exception as exc:
                LOG.warning("Failed to generate NVSS mask, continuing without mask: %s", exc)
                import traceback

                LOG.debug("Mask generation traceback: %s", traceback.format_exc())
                mask_path = None
        else:
            LOG.warning("Cannot generate mask: phase center not available")

    # Route to appropriate backend
    if backend == "wsclean":
        run_wsclean(
            ms_path=ms_path,
            imagename=imagename,
            datacolumn=datacolumn,
            field=field,
            imsize=imsize,
            cell_arcsec=cell_arcsec,
            weighting=weighting,
            robust=robust,
            specmode=specmode,
            deconvolver=deconvolver,
            nterms=nterms,
            niter=niter,
            threshold=threshold,
            pbcor=pbcor,
            uvrange=uvrange,
            pblimit=pblimit,
            quality_tier=quality_tier,
            wsclean_path=wsclean_path,
            gridder=gridder,
            mask_path=mask_path,
            target_mask=target_mask,
            galvin_clip_mask=galvin_clip_mask,
            erode_beam_shape=erode_beam_shape,
        )
    else:
        # Prepare mask if needed for tclean
        if mask_path or target_mask or galvin_clip_mask or erode_beam_shape:
            from dsa110_contimg.imaging.cli_utils import prepare_cleaning_mask

            if mask_path:
                try:
                    prepared_mask = prepare_cleaning_mask(
                        fits_mask=mask_path,
                        target_mask=target_mask,
                        galvin_clip_mask=galvin_clip_mask,
                        erode_beam_shape=erode_beam_shape,
                    )
                    if prepared_mask:
                        mask_path = str(prepared_mask)
                        kwargs["mask"] = mask_path
                        kwargs["usemask"] = "user"
                        LOG.info("Using prepared mask for tclean: %s", mask_path)
                except Exception as e:
                    LOG.warning(
                        f"Failed to prepare advanced mask for tclean: {e}. Proceeding with default mask behavior."
                    )
            elif target_mask:
                # If only target_mask is provided, we could use it as the mask?
                # For now, only support modifying an existing mask_path.
                LOG.warning("Target mask provided without base mask_path for tclean. Ignoring.")

        # CASA tclean doesn't support FITS masks directly, BUT if we prepared it via prepare_cleaning_mask
        # it is still a FITS file. tclean's 'mask' parameter accepts an image name or a list of regions.
        # If it's a FITS file, tclean might accept it if it's in the right format or needs import.
        # However, `dstools` was using WSClean which takes FITS.
        # CASA tclean usually prefers CASA images or region files.
        # If `mask_path` is a FITS file, tclean *can* sometimes read it, but it's safer to import it.
        # Or let the user rely on 'auto-multithresh' if no mask.

        if mask_path and mask_path.endswith(".fits") and backend == "tclean":
            # Convert FITS mask to CASA image mask if needed?
            # Actually, tclean documentation says 'mask' can be an image name.
            # FITS might work if CASA can read it on the fly, but importfits is safer.
            try:
                from casatasks import importfits

                casa_mask = mask_path.replace(".fits", ".mask.image")
                if not os.path.exists(casa_mask):
                    importfits(fitsimage=mask_path, imagename=casa_mask, overwrite=True)
                kwargs["mask"] = casa_mask
                kwargs["usemask"] = "user"
            except Exception as e:
                LOG.warning(f"Failed to convert FITS mask to CASA image: {e}")

        if mask_path and not kwargs.get("mask"):
            LOG.warning(
                "Masking not supported or failed for CASA tclean backend with provided file."
            )

        t0 = time.perf_counter()
        tclean(**kwargs)
        LOG.info("tclean completed in %.2fs", time.perf_counter() - t0)

    # QA validation of image products
    try:
        from dsa110_contimg.qa.pipeline_quality import check_image_quality

        if backend == "wsclean":
            # WSClean outputs FITS directly
            image_path = imagename + "-image.fits"
            if os.path.isfile(image_path):
                check_image_quality(image_path, alert_on_issues=True)
        else:
            image_path = imagename + ".image"
            if os.path.isdir(image_path):
                check_image_quality(image_path, alert_on_issues=True)
    except Exception as e:
        LOG.warning("QA validation failed: %s", e)

    # Export FITS products if present (only for tclean backend)
    if backend == "tclean" and not skip_fits:
        for suffix in (".image", ".pb", ".pbcor", ".residual", ".model"):
            img = imagename + suffix
            if os.path.isdir(img):
                fits = imagename + suffix + ".fits"
                try:
                    exportfits(imagename=img, fitsimage=fits, overwrite=True)
                except Exception as exc:
                    LOG.debug("exportfits failed for %s: %s", img, exc)
