"""
Default values for CLI arguments and configuration.

This module centralizes all default values used throughout the pipeline,
making it easier to manage, document, and validate defaults.
"""

import os


# ============================================================================
# Calibration Defaults
# ============================================================================

# Bandpass calibration defaults
# NOTE: For streaming mode, bandpass calibration should be performed
# once every 24 hours. Bandpass solutions are relatively stable and
# can be reused for extended periods.
CAL_BP_MINSNR = 3.0
CAL_BP_SOLINT = "inf"  # Entire scan
CAL_BP_SMOOTH_TYPE = "none"  # No smoothing by default
CAL_BP_SMOOTH_WINDOW = None  # No smoothing window by default

# Gain calibration defaults
# NOTE: For streaming mode, gain calibration should be performed
# every hour. Gain solutions vary with time and atmospheric
# conditions, requiring more frequent updates.
CAL_GAIN_MINSNR = 3.0
CAL_GAIN_SOLINT = "inf"  # Entire scan (per-integration for production)
CAL_GAIN_CALMODE = "ap"  # Amplitude+phase (phase-only for fast mode)

# Pre-bandpass phase solve defaults
CAL_PREBP_SOLINT = "30s"  # 30-second intervals for time-variable phase
CAL_PREBP_MINSNR = 3.0
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
# Imaging Defaults
# ============================================================================

IMG_IMSIZE = 1024  # Image size in pixels
IMG_CELL_ARCSEC = None  # Auto-calculated by default
IMG_WEIGHTING = "briggs"  # Briggs weighting
IMG_ROBUST = 0.0  # Robust parameter (0.0 = uniform weighting, 0.5 = natural)
IMG_NITER = 1000  # Number of deconvolution iterations
IMG_THRESHOLD = None  # Auto-calculated by default
IMG_DECONVOLVER = "hogbom"  # Hogbom deconvolution (default for point sources)


# ============================================================================
# Conversion Defaults
# ============================================================================

CONV_WRITER_STRATEGY = "auto"  # Auto-select writer strategy
CONV_STAGE_TO_TMPFS = True  # Use tmpfs staging by default
CONV_MAX_WORKERS = 4  # Number of parallel workers


# ============================================================================
# Environment Variable Overrides
# ============================================================================

def get_cal_bp_minsnr() -> float:
    """Get BP minimum SNR from environment or default."""
    return float(os.getenv("CONTIMG_CAL_BP_MINSNR", str(CAL_BP_MINSNR)))


def get_cal_gain_minsnr() -> float:
    """Get gain minimum SNR from environment or default."""
    return float(os.getenv("CONTIMG_CAL_GAIN_MINSNR", str(CAL_GAIN_MINSNR)))


def get_cal_gain_solint() -> str:
    """Get gain solution interval from environment or default."""
    return os.getenv("CONTIMG_CAL_GAIN_SOLINT", CAL_GAIN_SOLINT)


def get_img_imsize() -> int:
    """Get image size from environment or default."""
    return int(os.getenv("IMG_IMSIZE", str(IMG_IMSIZE)))


def get_img_robust() -> float:
    """Get robust parameter from environment or default."""
    return float(os.getenv("IMG_ROBUST", str(IMG_ROBUST)))


def get_img_niter() -> int:
    """Get number of iterations from environment or default."""
    return int(os.getenv("IMG_NITER", str(IMG_NITER)))


def get_conv_max_workers() -> int:
    """Get max workers from environment or default."""
    return int(os.getenv("CONTIMG_MAX_WORKERS", str(CONV_MAX_WORKERS)))


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

    if CAL_BP_MINSNR < 2.0:
        msg = "CAL_BP_MINSNR < 2.0 may produce unreliable solutions"
        warnings.append(msg)

    if CAL_GAIN_MINSNR < 2.0:
        msg = "CAL_GAIN_MINSNR < 2.0 may produce unreliable solutions"
        warnings.append(msg)

    if IMG_IMSIZE < 256:
        warnings.append("IMG_IMSIZE < 256 may have poor resolution")

    if IMG_IMSIZE > 8192:
        warnings.append("IMG_IMSIZE > 8192 may be very slow")

    if IMG_ROBUST < -2.0 or IMG_ROBUST > 2.0:
        msg = "IMG_ROBUST should be between -2.0 and 2.0"
        warnings.append(msg)

    return warnings
