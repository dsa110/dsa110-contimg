"""Core imaging functions for imaging CLI."""
import os
import time
import subprocess
import shutil
import logging
from typing import Optional

import numpy as np
from casacore.tables import table
from casatasks import tclean, exportfits  # type: ignore[import]
try:
    from casatools import vpmanager as _vpmanager  # type: ignore[import]
    from casatools import msmetadata as _msmd  # type: ignore[import]
except Exception:  # pragma: no cover
    _vpmanager = None
    _msmd = None

from dsa110_contimg.utils.validation import validate_ms, ValidationError
from dsa110_contimg.imaging.cli_utils import detect_datacolumn, default_cell_arcsec
from dsa110_contimg.utils.performance import track_performance
from dsa110_contimg.utils.error_context import format_ms_error_with_suggestions

LOG = logging.getLogger(__name__)

# Fixed image extent: all images should be 3.5° x 3.5° regardless of resolution
FIXED_IMAGE_EXTENT_DEG = 3.5

try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment, derive_default_scratch_root
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
    quick: bool,
    wsclean_path: Optional[str] = None,
    gridder: str = "standard",
) -> None:
    """Run WSClean with parameters mapped from tclean equivalents.
    
    This function builds a WSClean command-line that matches the tclean
    parameters as closely as possible. MODEL_DATA seeding should be done
    before calling this function via CASA ft().
    """
    # Find WSClean executable
    # Priority: Prefer native WSClean over Docker for better performance (2-5x faster)
    use_docker = False
    if wsclean_path:
        if wsclean_path == "docker":
            # Check for native WSClean first (faster than Docker)
            native_wsclean = shutil.which("wsclean")
            if native_wsclean:
                LOG.info("Using native WSClean (faster than Docker)")
                wsclean_cmd = [native_wsclean]
                use_docker = False
            else:
                # Fall back to Docker if native not available
                docker_cmd = shutil.which("docker")
                if not docker_cmd:
                    raise RuntimeError("Docker not found but --wsclean-path=docker was specified")
                use_docker = True
                wsclean_cmd = [docker_cmd, "run", "--rm", "-v", "/scratch:/scratch", "-v", "/data:/data",
                              "wsclean-everybeam-0.7.4", "wsclean"]
        else:
            wsclean_cmd = [wsclean_path]
    else:
        # Check for native WSClean first (preferred)
        wsclean_cmd = shutil.which("wsclean")
        if not wsclean_cmd:
            # Fall back to Docker container if native not available
            docker_cmd = shutil.which("docker")
            if docker_cmd:
                use_docker = True
                wsclean_cmd = [docker_cmd, "run", "--rm", "-v", "/scratch:/scratch", "-v", "/data:/data",
                              "wsclean-everybeam-0.7.4", "wsclean"]
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
    # For single-spw or already-ordered MS, skip to save time
    if quick:
        # In quick mode, skip reorder if not absolutely necessary (faster)
        # Reorder is only needed if MS has multiple SPWs with different channel ordering
        # For most cases, we can skip it for speed
        pass  # Skip reorder in quick mode
    else:
        cmd.append("-reorder")
    
    # Auto-masking (helps with convergence)
    cmd.extend(["-auto-mask", "3"])
    cmd.extend(["-auto-threshold", "0.5"])
    cmd.extend(["-mgain", "0.8"])
    
    # Threading: use all available CPU cores (critical for performance!)
    import multiprocessing
    num_threads = os.getenv("WSCLEAN_THREADS", str(multiprocessing.cpu_count()))
    cmd.extend(["-j", num_threads])
    LOG.debug(f"Using {num_threads} threads for WSClean")
    
    # Memory limit (optimized for performance)
    # Quick mode: Use more memory for faster gridding/FFT (16GB default)
    # Production mode: Scale with image size (16-32GB)
    if quick:
        # Quick mode: Allow more memory for speed (10-30% faster gridding)
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
        result = subprocess.run(
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
            "Install WSClean: https://gitlab.com/aroffringa/wsclean"
        ]
        error_msg = format_ms_error_with_suggestions(
            FileNotFoundError(f"WSClean executable not found: {wsclean_cmd}"),
            ms_path, "WSClean execution", suggestions
        )
        raise RuntimeError(error_msg) from None
    except Exception as e:
        suggestions = [
            "Check WSClean logs for detailed error information",
            "Verify MS path and file permissions",
            "Check disk space for output images",
            "Review WSClean parameters and configuration"
        ]
        error_msg = format_ms_error_with_suggestions(
            e, ms_path, "WSClean execution", suggestions
        )
        raise RuntimeError(error_msg) from e


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
    quick: bool = False,
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
) -> None:
    """Main imaging function for Measurement Sets.
    
    Supports both CASA tclean and WSClean backends. WSClean is the default.
    Automatically selects CORRECTED_DATA when present, otherwise uses DATA.
    """
    from dsa110_contimg.utils.validation import validate_corrected_data_quality
    
    # Validate MS using shared validation module
    try:
        validate_ms(ms_path, check_empty=True,
                   check_columns=['DATA', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW'])
    except ValidationError as e:
        suggestions = [
            "Check MS path is correct and file exists",
            "Verify file permissions",
            "Run validation: python -m dsa110_contimg.calibration.cli validate --ms <path>",
            "Check MS structure and integrity"
        ]
        error_msg = format_ms_error_with_suggestions(
            e, ms_path, "MS validation", suggestions
        )
        raise RuntimeError(error_msg) from e
    
    # Validate CORRECTED_DATA quality if present - FAIL if calibration appears unapplied
    warnings = validate_corrected_data_quality(ms_path)
    if warnings:
        # Distinguish between unpopulated data warnings and validation errors
        unpopulated_warnings = [
            w for w in warnings 
            if "appears unpopulated" in w.lower() or "zero rows" in w.lower() 
            or "all sampled data is flagged" in w.lower()
        ]
        validation_errors = [
            w for w in warnings 
            if w.startswith("Error validating CORRECTED_DATA:")
        ]
        
        if unpopulated_warnings:
            # CORRECTED_DATA exists but is unpopulated - calibration failed
            suggestions = [
                "Re-run calibration on this MS",
                "Check calibration logs for errors",
                "Verify calibration tables were applied correctly",
                "Use --datacolumn=DATA to image uncalibrated data (not recommended)"
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("CORRECTED_DATA column exists but appears unpopulated"),
                ms_path, "calibration validation", suggestions
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
                "Review detailed error logs"
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("Failed to validate CORRECTED_DATA"),
                ms_path, "MS validation", suggestions
            )
            error_msg += f"\nDetails: {'; '.join(validation_errors)}"
            LOG.error(error_msg)
            raise RuntimeError(error_msg)
        else:
            # Other warnings (shouldn't happen, but handle gracefully)
            suggestions = [
                "Review calibration validation warnings",
                "Check MS structure and integrity",
                "Verify calibration was applied correctly"
            ]
            error_msg = format_ms_error_with_suggestions(
                RuntimeError("Calibration validation warnings"),
                ms_path, "calibration validation", suggestions
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
        num_images = 10  # Conservative estimate (.image, .model, .residual, .pb, .pbcor, weights, etc.)
        image_size_estimate = imsize * imsize * bytes_per_pixel * num_images * 10  # 10x safety margin
        
        available_space = shutil.disk_usage(output_dir).free
        
        if available_space < image_size_estimate:
            LOG.warning(
                "Insufficient disk space for images: need ~%.1f GB, available %.1f GB. "
                "Imaging may fail. Consider freeing space or using a different output directory.",
                image_size_estimate / 1e9,
                available_space / 1e9
            )
        else:
            LOG.info(
                "✓ Disk space check passed: %.1f GB available (need ~%.1f GB)",
                available_space / 1e9,
                image_size_estimate / 1e9
            )
    except Exception as e:
        # Non-fatal: log warning but don't fail
        LOG.warning(f"Failed to check disk space: {e}")
    
    # Prepare temp dirs and working directory to keep TempLattice* off the repo
    try:
        if prepare_temp_environment is not None:
            out_dir = os.path.dirname(os.path.abspath(imagename))
            root = os.getenv("CONTIMG_SCRATCH_DIR") or "/scratch/dsa110-contimg"
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
                user_imsize, calculated_imsize, cell_arcsec
            )
    
    imsize = calculated_imsize
    cell = f"{cell_arcsec:.3f}arcsec"
    
    if quick:
        # Quick mode: maintain 3.5° extent but use coarser cell size (2x default)
        # This reduces computational cost while maintaining field of view
        default_cell = default_cell_arcsec(ms_path)
        if abs(cell_arcsec - default_cell) < 0.01:  # Only adjust if using default cell size
            cell_arcsec = cell_arcsec * 2.0
            # Recalculate imsize for new cell size
            calculated_imsize = int(np.ceil(desired_extent_arcsec / cell_arcsec))
            if calculated_imsize % 2 != 0:
                calculated_imsize += 1
            imsize = calculated_imsize
            cell = f"{cell_arcsec:.3f}arcsec"
            LOG.info(
                "Quick mode: using coarser cell size (%.3f arcsec) to maintain 3.5° extent with reduced resolution",
                cell_arcsec
            )
        niter = min(niter, 300)
        threshold = threshold or "0.0Jy"
        weighting = weighting or "briggs"
        robust = robust if robust is not None else 0.0
        # Default NVSS seeding threshold in quick mode when not explicitly provided
        if nvss_min_mjy is None:
            try:
                env_val = os.getenv("CONTIMG_QUICK_NVSS_MIN_MJY")
                nvss_min_mjy = float(env_val) if env_val is not None else 10.0
            except Exception:
                nvss_min_mjy = 10.0
            LOG.info(
                "Quick mode: defaulting NVSS seeding threshold to %s mJy",
                nvss_min_mjy,
            )
    LOG.info("Imaging %s -> %s", ms_path, imagename)
    LOG.info(
        "datacolumn=%s cell=%s imsize=%d quick=%s",
        datacolumn,
        cell,
        imsize,
        quick,
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

    # Optional: seed a single-component calibrator model if provided and in FoV
    did_seed = False
    if (calib_ra_deg is not None and calib_dec_deg is not None and calib_flux_jy is not None and calib_flux_jy > 0):
        try:
            with table(f"{ms_path}::FIELD", readonly=True) as fld:
                ph = fld.getcol("PHASE_DIR")[0]
                ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
            # crude small-angle separation in deg
            d_ra = (float(calib_ra_deg) - ra0_deg) * np.cos(np.deg2rad(dec0_deg))
            d_dec = (float(calib_dec_deg) - dec0_deg)
            sep_deg = float(_math.hypot(d_ra, d_dec))
            if sep_deg <= radius_deg * 1.05:
                from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl  # type: ignore
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
                LOG.info("Seeded MODEL_DATA with calibrator point model (flux=%.3f Jy)", calib_flux_jy)
                did_seed = True
        except Exception as exc:
            LOG.debug("Calibrator seeding skipped: %s", exc)

    # Optional: seed a sky model from NVSS (> nvss_min_mjy mJy) via ft(), if no calibrator seed
    if (not did_seed) and (nvss_min_mjy is not None):
        try:
            from dsa110_contimg.calibration.skymodels import (
                make_nvss_component_cl,
                ft_from_cl,
            )  # type: ignore
            # Determine phase center from FIELD table
            ra0_deg = dec0_deg = None
            with table(f"{ms_path}::FIELD", readonly=True) as fld:
                try:
                    ph = fld.getcol("PHASE_DIR")[0]
                    ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                    dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
                except Exception:
                    pass
            if ra0_deg is None or dec0_deg is None:
                raise RuntimeError("FIELD::PHASE_DIR not available")
            # radius_deg computed above
            # Mean observing frequency
            freq_ghz = 1.4
            try:
                with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                    ch = spw.getcol("CHAN_FREQ")[0]
                    freq_ghz = float(np.nanmean(ch)) / 1e9
            except Exception:
                pass
            cl_path = f"{imagename}.nvss_{float(nvss_min_mjy):g}mJy.cl"
            LOG.info(
                "Creating NVSS componentlist (>%s mJy, radius %.2f deg, center RA=%.6f° Dec=%.6f°)",
                nvss_min_mjy,
                radius_deg,
                ra0_deg,
                dec0_deg,
            )
            make_nvss_component_cl(
                ra0_deg,
                dec0_deg,
                radius_deg,
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
                radius_deg,
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
            LOG.debug("Registered VP table %s for telescope(s): %s", vptable, [telname, "DSA_110"]) 
        except Exception as exc:
            LOG.debug("VP preload skipped: %s", exc)

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
            quick=quick,
            wsclean_path=wsclean_path,
            gridder=gridder,
        )
    else:
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
                    exportfits(
                        imagename=img, fitsimage=fits, overwrite=True
                    )
                except Exception as exc:
                    LOG.debug("exportfits failed for %s: %s", img, exc)

