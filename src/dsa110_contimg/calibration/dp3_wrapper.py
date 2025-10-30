"""
DP3 wrappers for sky model seeding and calibration application.

DP3 is faster than CASA for visibility operations:
- Predict: Sky model seeding (MODEL_DATA)
- ApplyCal: Calibration application (CORRECTED_DATA)

Usage:
    from dsa110_contimg.calibration.dp3_wrapper import (
        predict_from_skymodel_dp3,
        apply_calibration_dp3,
    )
    
    # Seed MODEL_DATA
    predict_from_skymodel_dp3(
        ms_path='/path/to/ms',
        sky_model_path='/path/to/sky_model.skymodel',
    )
    
    # Apply calibration
    apply_calibration_dp3(
        ms_path='/path/to/ms',
        cal_tables=['/path/to/kcal', '/path/to/bpcal'],
    )
"""

import os
import subprocess
import logging
from typing import List, Optional
from pathlib import Path

LOG = logging.getLogger(__name__)


def _find_dp3_executable() -> Optional[str]:
    """Find DP3 executable in PATH or Docker."""
    import shutil
    
    # Check PATH first
    dp3_cmd = shutil.which("DP3")
    if dp3_cmd:
        return dp3_cmd
    
    # Try Docker
    docker_cmd = shutil.which("docker")
    if docker_cmd:
        # Check if DP3 Docker image exists
        try:
            result = subprocess.run(
                [docker_cmd, "images", "-q", "dp3:latest"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                return f"{docker_cmd} run --rm -v /scratch:/scratch -v /data:/data dp3:latest DP3"
        except Exception:
            pass
    
    return None


def convert_nvss_to_dp3_skymodel(
    center_ra_deg: float,
    center_dec_deg: float,
    radius_deg: float,
    *,
    min_mjy: float = 10.0,
    freq_ghz: float = 1.4,
    out_path: str,
) -> str:
    """Convert NVSS catalog to DP3 sky model format (.skymodel).
    
    DP3 sky model format:
        Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, ReferenceFrequency='1400000000.0', MajorAxis, MinorAxis, Orientation
        s0c0,POINT,07:02:53.6790,+44:31:11.940,2.4,[-0.7],false,1400000000.0,,,
    """
    from dsa110_contimg.calibration.catalogs import read_nvss_catalog
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    import numpy as np
    
    df = read_nvss_catalog()
    sc_all = SkyCoord(df["ra"].to_numpy() * u.deg, df["dec"].to_numpy() * u.deg, frame="icrs")
    ctr = SkyCoord(center_ra_deg * u.deg, center_dec_deg * u.deg, frame="icrs")
    sep = sc_all.separation(ctr).deg
    flux_mjy = np.asarray(df["flux_20_cm"].to_numpy(), float)
    keep = (sep <= float(radius_deg)) & (flux_mjy >= float(min_mjy))
    
    # Format RA/Dec as HH:MM:SS.sss and DD:MM:SS.sss
    from astropy.coordinates import Angle
    
    ref_freq_hz = float(freq_ghz) * 1e9
    
    out_file = Path(out_path)
    with open(out_file, "w") as f:
        # Write header
        f.write(
            f"Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, "
            f"ReferenceFrequency='{ref_freq_hz:.1f}', MajorAxis, MinorAxis, Orientation\n"
        )
        
        # Write sources
        for idx, (ra, dec, flux) in enumerate(zip(
            df.loc[keep, "ra"].to_numpy(),
            df.loc[keep, "dec"].to_numpy(),
            flux_mjy[keep],
        )):
            ra_angle = Angle(ra, unit="deg")
            dec_angle = Angle(dec, unit="deg")
            
            ra_str = ra_angle.to_string(unit="hour", sep=":", precision=3, pad=True)
            dec_str = dec_angle.to_string(unit="deg", sep=":", precision=3, pad=True, alwayssign=True)
            
            flux_jy = float(flux) / 1000.0
            
            # Point source, no spectral index (can be extended later)
            f.write(
                f"s{idx}c0,POINT,{ra_str},{dec_str},{flux_jy:.6f},[0.0],false,"
                f"{ref_freq_hz:.1f},,,\n"
            )
    
    LOG.info(
        "Created DP3 sky model with %d sources (>%.1f mJy, radius %.2f deg)",
        keep.sum(),
        min_mjy,
        radius_deg,
    )
    return os.fspath(out_file)


def convert_calibrator_to_dp3_skymodel(
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    freq_ghz: float = 1.4,
    out_path: str,
) -> str:
    """Create DP3 sky model for a single calibrator point source."""
    from astropy.coordinates import Angle
    
    ref_freq_hz = float(freq_ghz) * 1e9
    
    ra_angle = Angle(ra_deg, unit="deg")
    dec_angle = Angle(dec_deg, unit="deg")
    
    ra_str = ra_angle.to_string(unit="hour", sep=":", precision=3, pad=True)
    dec_str = dec_angle.to_string(unit="deg", sep=":", precision=3, pad=True, alwayssign=True)
    
    out_file = Path(out_path)
    with open(out_file, "w") as f:
        f.write(
            f"Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, "
            f"ReferenceFrequency='{ref_freq_hz:.1f}', MajorAxis, MinorAxis, Orientation\n"
        )
        f.write(
            f"calibrator,POINT,{ra_str},{dec_str},{flux_jy:.6f},[0.0],false,"
            f"{ref_freq_hz:.1f},,,\n"
        )
    
    LOG.info(
        "Created DP3 sky model for calibrator at RA=%s, Dec=%s, flux=%.3f Jy",
        ra_str,
        dec_str,
        flux_jy,
    )
    return os.fspath(out_file)


def predict_from_skymodel_dp3(
    ms_path: str,
    sky_model_path: str,
    *,
    field: str = "",
    use_beam: bool = False,
    operation: str = "replace",
) -> None:
    """Use DP3 Predict step to seed MODEL_DATA from sky model.
    
    Args:
        ms_path: Path to Measurement Set
        sky_model_path: Path to DP3 sky model file (.skymodel)
        field: Field selection (empty string = all fields)
        use_beam: Whether to apply primary beam model during prediction
        operation: 'replace' (default), 'add', or 'subtract'
    """
    dp3_cmd = _find_dp3_executable()
    if not dp3_cmd:
        raise RuntimeError(
            "DP3 not found. Install DP3 or ensure Docker is available with DP3 image."
        )
    
    # Build DP3 parset
    cmd = dp3_cmd.split() if "docker" in dp3_cmd else [dp3_cmd]
    
    cmd.extend([
        f"msin={ms_path}",
        "msout=.",
        "msout.datacolumn=MODEL_DATA",
        "steps=[predict]",
        f"predict.sourcedb={sky_model_path}",
        f"predict.usebeammodel={'true' if use_beam else 'false'}",
        f"predict.operation={operation}",
    ])
    
    if field:
        cmd.extend([f"msin.field={field}"])
    
    LOG.info("Running DP3 Predict: %s", " ".join(cmd))
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        LOG.info("DP3 Predict completed successfully")
        if result.stderr:
            LOG.debug("DP3 stderr: %s", result.stderr)
    except subprocess.CalledProcessError as e:
        LOG.error("DP3 Predict failed: %s", e.stderr)
        raise RuntimeError(f"DP3 Predict failed: {e}") from e


def apply_calibration_dp3(
    ms_path: str,
    cal_tables: List[str],
    *,
    field: str = "",
    output_column: str = "CORRECTED_DATA",
    update_weights: bool = True,
) -> None:
    """Use DP3 ApplyCal step to apply calibration tables.
    
    IMPORTANT: DP3 ApplyCal expects ParmDB format, not CASA calibration tables.
    CASA tables (K, BP, G tables) are in a different format and cannot be used
    directly with DP3 ApplyCal. Conversion from CASA to ParmDB is complex.
    
    For now, this function falls back to CASA applycal. Future work could:
    1. Convert CASA tables to ParmDB format
    2. Use DP3 GainCal to generate ParmDB tables directly
    
    Args:
        ms_path: Path to Measurement Set
        cal_tables: List of calibration table paths (CASA format - will use CASA)
        field: Field selection (empty string = all fields)
        output_column: Data column to write corrected data to
        update_weights: Whether to update weights during calibration
    """
    # DP3 ApplyCal requires ParmDB format, not CASA tables
    # For now, use CASA applycal as fallback
    LOG.info(
        "DP3 ApplyCal requires ParmDB format; CASA tables not supported. "
        "Using CASA applycal instead."
    )
    from dsa110_contimg.calibration.applycal import apply_to_target
    apply_to_target(ms_path, field, cal_tables)

