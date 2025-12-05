"""
Default values for CLI arguments and configuration.

This module provides backwards-compatible accessors for configuration defaults.
All configuration is now centralized in dsa110_contimg.config with Pydantic validation.

For new code, prefer importing directly from config:
    from dsa110_contimg.config import settings
    minsnr = settings.calibration.bp_minsnr

This module is retained for backwards compatibility with existing CLI code.
"""

from dsa110_contimg.config import settings

# ============================================================================
# Calibration Defaults - delegating to settings.calibration
# ============================================================================

# Bandpass calibration defaults
CAL_BP_MINSNR = settings.calibration.bp_minsnr
CAL_BP_SOLINT = "inf"  # Entire scan (not in central config yet)
CAL_BP_SMOOTH_TYPE = "none"  # No smoothing by default
CAL_BP_SMOOTH_WINDOW = None  # No smoothing window by default

# Gain calibration defaults
CAL_GAIN_MINSNR = settings.calibration.gain_minsnr
CAL_GAIN_SOLINT = settings.calibration.gain_solint
CAL_GAIN_CALMODE = "ap"  # Amplitude+phase (phase-only for fast mode)

# Pre-bandpass phase solve defaults
CAL_PREBP_SOLINT = "30s"  # 30-second intervals for time-variable phase
CAL_PREBP_MINSNR = settings.calibration.bp_minsnr
CAL_PREBP_UVRANGE = ""  # No UV range cut by default

# K-calibration defaults (delay calibration)
CAL_K_MINSNR = 5.0  # Higher threshold for delay solutions
CAL_K_COMBINE_SPW = False  # Process SPWs separately by default

# Flagging defaults
CAL_FLAGGING_MODE = "zeros"  # Flag zero-value data by default
CAL_FLAG_AUTOCORR = True  # Flag autocorrelations by default

# Model source defaults
CAL_MODEL_SOURCE = "catalog"  # Catalog model (manual calculation) by default
CAL_MODEL_SETJY_STANDARD = "Perley-Butler 2017"  # Flux standard for setjy

# Field selection defaults
CAL_BP_WINDOW = 3  # Number of fields around peak to include
CAL_BP_MIN_PB = None  # No primary beam threshold by default
CAL_SEARCH_RADIUS_DEG = 1.0  # Search radius for catalog matching

# Subset creation defaults (for fast mode)
CAL_FAST_TIMEBIN = "30s"  # Time averaging for fast subset
CAL_FAST_CHANBIN = 4  # Channel binning for fast subset
CAL_FAST_UVRANGE = ">1klambda"  # UV range cut for fast solves

# Minimal mode defaults
CAL_MINIMAL_TIMEBIN = "inf"  # Single time integration
CAL_MINIMAL_CHANBIN = 16  # Aggressive channel binning


# ============================================================================
# Imaging Defaults - delegating to settings.imaging
# ============================================================================

IMG_IMSIZE = settings.imaging.imsize
IMG_CELL_ARCSEC = None  # Auto-calculated by default
IMG_WEIGHTING = "briggs"  # Briggs weighting
IMG_ROBUST = settings.imaging.robust
IMG_NITER = settings.imaging.niter
IMG_THRESHOLD = None  # Auto-calculated by default
IMG_DECONVOLVER = "hogbom"  # Hogbom deconvolution (default for point sources)


# ============================================================================
# Conversion Defaults - delegating to settings.conversion
# ============================================================================

CONV_WRITER_STRATEGY = "auto"  # Auto-select writer strategy
CONV_STAGE_TO_TMPFS = settings.paths.stage_to_tmpfs
CONV_MAX_WORKERS = settings.conversion.max_workers


# ============================================================================
# Accessor Functions (for backwards compatibility)
# All now delegate to the centralized settings
# ============================================================================


def get_cal_bp_minsnr() -> float:
    """Get BP minimum SNR from settings."""
    return settings.calibration.bp_minsnr


def get_cal_gain_minsnr() -> float:
    """Get gain minimum SNR from settings."""
    return settings.calibration.gain_minsnr


def get_cal_gain_solint() -> str:
    """Get gain solution interval from settings."""
    return settings.calibration.gain_solint


def get_img_imsize() -> int:
    """Get image size from settings."""
    return settings.imaging.imsize


def get_img_robust() -> float:
    """Get robust parameter from settings."""
    return settings.imaging.robust


def get_img_niter() -> int:
    """Get number of iterations from settings."""
    return settings.imaging.niter


def get_conv_max_workers() -> int:
    """Get max workers from settings."""
    return settings.conversion.max_workers


# ============================================================================
# Default Validation
# ============================================================================


def validate_defaults() -> list[str]:
    """
    Validate default values are reasonable.

    Returns:
        List of warning messages (empty if all defaults are valid)
    """
    warnings = []

    if settings.calibration.bp_minsnr < 2.0:
        msg = "bp_minsnr < 2.0 may produce unreliable solutions"
        warnings.append(msg)

    if settings.calibration.gain_minsnr < 2.0:
        msg = "gain_minsnr < 2.0 may produce unreliable solutions"
        warnings.append(msg)

    if settings.imaging.imsize < 256:
        warnings.append("imsize < 256 may have poor resolution")

    if settings.imaging.imsize > 8192:
        warnings.append("imsize > 8192 may be very slow")

    if settings.imaging.robust < -2.0 or settings.imaging.robust > 2.0:
        msg = "robust should be between -2.0 and 2.0"
        warnings.append(msg)

    return warnings
