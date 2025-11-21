"""Utility functions for imaging CLI."""

import logging
from pathlib import Path
from typing import NamedTuple, Optional

import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

import casacore.tables as casatables

table = casatables.table  # noqa: N816

LOG = logging.getLogger(__name__)


def detect_datacolumn(ms_path: str) -> str:
    """Choose datacolumn for tclean.

    Preference order:
    - Use CORRECTED_DATA if present and contains any non-zero values.
    - Otherwise fall back to DATA.

    **CRITICAL SAFEGUARD**: If CORRECTED_DATA column exists but is unpopulated
    (all zeros), this indicates calibration was attempted but failed. In this case,
    we FAIL rather than silently falling back to DATA to prevent imaging uncalibrated
    data when calibration was expected.

    This avoids the common pitfall where applycal didn't populate
    CORRECTED_DATA (all zeros) and tclean would produce blank images.
    """
    try:
        with table(ms_path, readonly=True) as t:
            cols = set(t.colnames())
            if "CORRECTED_DATA" in cols:
                try:
                    total = t.nrows()
                    if total <= 0:
                        # Empty MS - can't determine, but CORRECTED_DATA exists
                        # so calibration was attempted, fail to be safe
                        raise RuntimeError(
                            f"CORRECTED_DATA column exists but MS has zero rows: {ms_path}. "
                            f"Calibration appears to have been attempted but failed. "
                            f"Cannot proceed with imaging."
                        )
                    # Sample up to 8 evenly spaced windows of up to 2048 rows
                    windows = 8
                    block = 2048
                    indices = []
                    for i in range(windows):
                        start_idx = int(i * total / max(1, windows))
                        indices.append(max(0, start_idx - block // 2))

                    found_nonzero = False
                    for start in indices:
                        n = min(block, total - start)
                        if n <= 0:
                            continue
                        cd = t.getcol("CORRECTED_DATA", start, n)
                        flags = t.getcol("FLAG", start, n)
                        # Check unflagged data
                        unflagged = cd[~flags]
                        if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) > 0:
                            found_nonzero = True
                            break

                    if found_nonzero:
                        return "corrected"
                    else:
                        # CORRECTED_DATA exists but is all zeros - calibration failed
                        raise RuntimeError(
                            f"CORRECTED_DATA column exists but appears unpopulated in {ms_path}. "
                            f"Calibration appears to have been attempted but failed (all zeros). "
                            f"Cannot proceed with imaging uncalibrated data. "
                            f"Please verify calibration was applied successfully using: "
                            f"python -m dsa110_contimg.calibration.cli apply --ms {ms_path}"
                        )
                except RuntimeError:
                    raise  # Re-raise our errors
                except Exception as e:
                    # Other exceptions - be safe and fail
                    raise RuntimeError(
                        f"Error checking CORRECTED_DATA in {ms_path}: {e}. "
                        f"Cannot determine if calibration was applied. Cannot proceed."
                    ) from e
            # CORRECTED_DATA doesn't exist - calibration never attempted, fall back to DATA
            return "data"
    except RuntimeError:
        raise  # Re-raise our errors
    except Exception as e:
        # Other exceptions - be safe and fail
        raise RuntimeError(
            f"Error accessing MS {ms_path}: {e}. Cannot determine calibration status. Cannot proceed."
        ) from e


def default_cell_arcsec(ms_path: str) -> float:
    """Estimate cell size (arcsec) as a fraction of synthesized beam.

    Uses uv extents as proxy: theta ~ 0.5 * lambda / umax (radians).
    Returns 1/5 of theta in arcsec, clipped to [0.1, 60].
    """
    try:
        from daskms import xds_from_ms  # type: ignore[import]

        dsets = xds_from_ms(ms_path, columns=["UVW", "DATA"], chunks={})
        umax = 0.0
        freq_list: list[float] = []
        for ds in dsets:
            uvw = np.asarray(ds.UVW.data.compute())
            umax = max(umax, float(np.nanmax(np.abs(uvw[:, 0]))))
            # derive mean freq per ddid
            with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd:
                spw_map = dd.getcol("SPECTRAL_WINDOW_ID")
                spw_id = int(spw_map[ds.attrs["DATA_DESC_ID"]])
            with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")[spw_id]
            freq_list.append(float(np.nanmean(chan)))
        if umax <= 0 or not freq_list:
            raise RuntimeError("bad umax or freq")
        c = 299_792_458.0
        lam = c / float(np.nanmean(freq_list))
        theta_rad = 0.5 * lam / umax
        cell = max(0.1, min(60.0, np.degrees(theta_rad) * 3600.0 / 5.0))
        return float(cell)
    except Exception:
        # CASA-only fallback using casacore tables if daskms missing
        try:
            with table(f"{ms_path}::MAIN", readonly=True) as main_tbl:
                uvw0 = main_tbl.getcol("UVW", 0, min(10000, main_tbl.nrows()))
                umax = float(np.nanmax(np.abs(uvw0[:, 0])))
            with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")
                if hasattr(chan, "__array__"):
                    freq_scalar = float(np.nanmean(chan))
                else:
                    freq_scalar = float(np.nanmean(np.asarray(chan)))
            if umax <= 0 or not np.isfinite(freq_scalar):
                return 2.0
            c = 299_792_458.0
            lam = c / freq_scalar
            theta_rad = 0.5 * lam / umax
            cell = max(0.1, min(60.0, np.degrees(theta_rad) * 3600.0 / 5.0))
            return float(cell)
        except Exception:
            return 2.0


# Masking Utilities


class SkewResult(NamedTuple):
    positive_pixel_frac: np.ndarray
    """The fraction of positive pixels in a boxcar function"""
    skew_mask: np.ndarray
    """Mask of pixel positions indicating which positions failed the skew test"""
    box_size: int
    """Size of the boxcar window applies"""
    skew_delta: float
    """The test threshold for skew"""


def create_boxcar_skew_mask(
    image: np.ndarray,
    skew_delta: float,
    box_size: int,
) -> SkewResult:
    from scipy.signal import fftconvolve

    assert 0.0 < skew_delta < 0.5, f"{skew_delta=}, but should be 0.0 to 0.5"
    assert len(image.shape) == 2, f"Expected two dimensions, got image shape of {image.shape}"

    LOG.debug(f"Computing boxcar skew with {box_size=} and {skew_delta=}")
    positive_pixels = (image > 0.0).astype(np.float32)

    # Counting positive pixel fraction here.
    window_shape = (box_size, box_size)
    positive_pixel_fraction = fftconvolve(
        in1=positive_pixels,
        in2=np.ones(window_shape, dtype=np.float32),
        mode="same",
    ) / np.prod(window_shape)
    positive_pixel_fraction = np.clip(
        positive_pixel_fraction,
        0.0,
        1.0,
    )  # trust nothing

    skew_mask = positive_pixel_fraction > (0.5 + skew_delta)
    LOG.debug(f"{np.sum(skew_mask)} pixels above {skew_delta=} with {box_size=}")

    return SkewResult(
        positive_pixel_frac=positive_pixel_fraction,
        skew_mask=skew_mask,
        skew_delta=skew_delta,
        box_size=box_size,
    )


def _minimum_absolute_clip(
    image: np.ndarray,
    increase_factor: float = 2.0,
    box_size: int = 100,
) -> np.ndarray:
    """Given an input image or signal array, construct a simple image mask by applying a
    rolling boxcar minimum filter, and then selecting pixels above a cut of
    the absolute value value scaled by `increase_factor`. This is a pixel-wise operation.
    """
    from scipy.ndimage import minimum_filter

    LOG.debug(f"Minimum absolute clip, {increase_factor=} {box_size=}")
    rolling_box_min = minimum_filter(image, box_size)

    image_mask = image > (increase_factor * np.abs(rolling_box_min))

    return image_mask


def _adaptive_minimum_absolute_clip(
    image: np.ndarray,
    increase_factor: float = 2.0,
    box_size: int = 100,
    adaptive_max_depth: int = 3,
    adaptive_box_step: float = 2.0,
    adaptive_skew_delta: float = 0.2,
) -> np.ndarray:
    from scipy.ndimage import minimum_filter

    LOG.debug(f"Using adaptive minimum absolute clip with {box_size=} {adaptive_skew_delta=}")
    min_value = minimum_filter(image, size=box_size)

    for box_round in range(adaptive_max_depth, 0, -1):
        skew_results = create_boxcar_skew_mask(
            image=image,
            skew_delta=adaptive_skew_delta,
            box_size=box_size,
        )
        if np.all(~skew_results.skew_mask):
            LOG.info("No skewed islands detected")
            break
        if any([box_size > dim for dim in image.shape]):
            LOG.info(f"{box_size=} larger than a dimension in {image.shape=}")
            break

        LOG.debug(f"({box_round}) Growing {box_size=} {adaptive_box_step=}")
        box_size = int(box_size * adaptive_box_step)
        minval = minimum_filter(image, box_size)
        LOG.debug("Slicing minimum values into place")

        min_value[skew_results.skew_mask] = minval[skew_results.skew_mask]

    mask = image > (np.abs(min_value) * increase_factor)

    return mask


def minimum_absolute_clip(
    image: np.ndarray,
    increase_factor: float = 2.0,
    box_size: int = 100,
    adaptive_max_depth: Optional[int] = None,
    adaptive_box_step: float = 2.0,
    adaptive_skew_delta: float = 0.2,
) -> np.ndarray:
    """Adaptive minimum absolute clip.

    Implements minimum absolute clip method. A minimum filter of a particular
    boxc size is applied to the input image. The absolute of the output is taken
    and increased by a guard factor, which forms the clipping level used to construct
    a clean mask.
    """

    if adaptive_max_depth is None:
        return _minimum_absolute_clip(
            image=image,
            box_size=box_size,
            increase_factor=increase_factor,
        )

    adaptive_max_depth = int(adaptive_max_depth)

    return _adaptive_minimum_absolute_clip(
        image=image,
        increase_factor=increase_factor,
        box_size=box_size,
        adaptive_max_depth=adaptive_max_depth,
        adaptive_box_step=adaptive_box_step,
        adaptive_skew_delta=adaptive_skew_delta,
    )


def create_beam_mask_kernel(
    fits_header,
    kernel_size=100,
    minimum_response: float = 0.6,
) -> np.ndarray:
    """Make a mask using the shape of a beam in a FITS Header object.

    Uses BMAJ, BMIN, BPA from header to generate a Gaussian kernel using Astropy.
    """
    from astropy.convolution import Gaussian2DKernel
    from astropy.stats import gaussian_fwhm_to_sigma

    assert (
        0.0 < minimum_response < 1.0
    ), f"{minimum_response=}, should be between 0 to 1 (exclusive)"

    if not all(key in fits_header for key in ["BMAJ", "BMIN", "BPA"]):
        raise KeyError("BMAJ, BMIN, BPA must be present in FITS header")

    if "CDELT1" in fits_header:
        pixel_scale = abs(fits_header["CDELT1"])
    elif "CD1_1" in fits_header:
        pixel_scale = abs(fits_header["CD1_1"])
    else:
        raise KeyError("Pixel scale (CDELT1 or CD1_1) missing from FITS header")

    # Beam parameters in degrees
    bmaj = fits_header["BMAJ"]
    bmin = fits_header["BMIN"]
    bpa = fits_header["BPA"]

    # Convert to pixels (sigma)
    # FWHM to Sigma: FWHM = 2.355 * sigma
    sigma_major = (bmaj / pixel_scale) * gaussian_fwhm_to_sigma
    sigma_minor = (bmin / pixel_scale) * gaussian_fwhm_to_sigma
    theta = np.radians(bpa)

    # Create 2D Gaussian Kernel
    kernel = Gaussian2DKernel(
        x_stddev=sigma_major,
        y_stddev=sigma_minor,
        theta=theta,
        x_size=kernel_size,
        y_size=kernel_size,
    )

    # Normalize kernel to peak at 1.0 for thresholding
    kernel_array = kernel.array / kernel.array.max()

    return kernel_array > minimum_response


def beam_shape_erode(
    mask: np.ndarray,
    fits_header,
    minimum_response: float = 0.6,
) -> np.ndarray:
    """Construct a kernel representing the shape of the restoring beam at
    a particular level, and use it as the basis of a binary erosion of the
    input mask.
    """
    from scipy.ndimage import binary_erosion

    if not all([key in fits_header for key in ["BMAJ", "BMIN", "BPA"]]):
        LOG.warning("Beam parameters missing. Not performing the beam shape erosion. ")
        return mask

    LOG.debug(f"Eroding the mask using the beam shape with {minimum_response=}")

    try:
        beam_mask_kernel = create_beam_mask_kernel(
            fits_header=fits_header,
            minimum_response=minimum_response,
        )

        # This handles any unsqueezed dimensions
        beam_mask_kernel = beam_mask_kernel.reshape(mask.shape[:-2] + beam_mask_kernel.shape)

        erode_mask = binary_erosion(
            input=mask,
            iterations=1,
            structure=beam_mask_kernel,
        )

        return erode_mask.astype(mask.dtype)
    except Exception as e:
        LOG.warning(f"Failed to create beam mask kernel: {e}. Skipping erosion.")
        return mask


def prepare_cleaning_mask(
    fits_mask: Optional[Path],
    target_mask: Optional[Path] = None,
    galvin_clip_mask: Optional[Path] = None,
    erode_beam_shape: bool = False,
) -> Optional[Path]:
    """Prepare a cleaning mask by combining optional target mask, adaptive clip mask,
    and beam erosion.

    Args:
        fits_mask: Path to input FITS mask (modified in place or copied).
        target_mask: Optional path to mask to intersect with (AND).
        galvin_clip_mask: Optional path to image for adaptive clipping (minimum_absolute_clip).
        erode_beam_shape: Whether to erode mask by beam shape.

    Returns:
        Path to the final prepared mask (same as fits_mask input).
    """
    from astropy.io import fits

    if fits_mask is None:
        return None

    # Use str conversion for Path compatibility
    mask_path = Path(fits_mask).absolute()
    if not mask_path.exists():
        LOG.warning(f"Mask file not found: {mask_path}")
        return None

    try:
        # Load mask
        with fits.open(mask_path) as hdul:
            header = hdul[0].header
            mask_data = hdul[0].data
            # Handle dimensions
            if mask_data.ndim == 4:
                mask_array = mask_data[0, 0, :, :]
            elif mask_data.ndim == 3:
                mask_array = mask_data[0, :, :]
            else:
                mask_array = mask_data

        # Adaptive clipping
        if galvin_clip_mask is not None:
            clip_path = Path(galvin_clip_mask).absolute()
            if clip_path.exists():
                try:
                    with fits.open(clip_path) as hdul_clip:
                        clip_data = hdul_clip[0].data
                        if clip_data.ndim == 4:
                            clip_array = clip_data[0, 0, :, :]
                        elif clip_data.ndim == 3:
                            clip_array = clip_data[0, :, :]
                        else:
                            clip_array = clip_data

                    # Apply Galvin clip
                    # Use adaptive defaults: box_size=100, adaptive_max_depth=3
                    mask_array = minimum_absolute_clip(
                        clip_array,
                        box_size=100,
                        adaptive_max_depth=3,
                    )
                    LOG.info(f"Applied Galvin adaptive clip using {clip_path}")
                except Exception as e:
                    LOG.warning(f"Failed to apply Galvin clip from {clip_path}: {e}")
            else:
                LOG.warning(f"Galvin clip mask file not found: {clip_path}")

        # Erode the beam shape
        if erode_beam_shape:
            mask_array = beam_shape_erode(
                mask=mask_array,
                fits_header=header,
            )

        # Remove user-specified region from mask by selecting pixels
        # that are in mask_array but not in target_mask (Intersection)
        if target_mask is not None:
            target_path = Path(target_mask).absolute()
            if target_path.exists():
                with fits.open(target_path) as hdul_target:
                    target_data = hdul_target[0].data
                    if target_data.ndim == 4:
                        target_array = target_data[0, 0, :, :]
                    elif target_data.ndim == 3:
                        target_array = target_data[0, :, :]
                    else:
                        target_array = target_data

                # Ensure shapes match
                if target_array.shape == mask_array.shape:
                    mask_array = np.logical_and(mask_array, target_array)
                else:
                    LOG.warning(
                        f"Target mask shape {target_array.shape} mismatch with mask {mask_array.shape}"
                    )

        # Save updated mask (in place update)
        with fits.open(mask_path, mode="update") as hdul:
            # Update data while preserving dimensions
            if hdul[0].data.ndim == 4:
                hdul[0].data[0, 0, :, :] = mask_array.astype(hdul[0].data.dtype)
            elif hdul[0].data.ndim == 3:
                hdul[0].data[0, :, :] = mask_array.astype(hdul[0].data.dtype)
            else:
                hdul[0].data = mask_array.astype(hdul[0].data.dtype)

            hdul.flush()

        return mask_path

    except Exception as e:
        LOG.error(f"Failed to prepare cleaning mask: {e}")
        return None
