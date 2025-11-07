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
import shutil

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
        # Check if DP3 Docker image exists (try multiple possible names)
        for image_name in ["dp3:latest", "dp3-everybeam-0.7.4:latest", "dp3-everybeam-0.7.4"]:
        try:
            result = subprocess.run(
                    [docker_cmd, "images", "-q", image_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.stdout.strip():
                    # Use the image name that was found
                    # Mount /tmp as well for temporary files
                    return f"{docker_cmd} run --rm -v /scratch:/scratch -v /data:/data -v /tmp:/tmp {image_name} DP3"
        except Exception:
                continue
    
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


def concatenate_fields_in_ms(ms_path: str, output_ms_path: str) -> str:
    """Concatenate all fields in an MS into a single field.
    
    After rephasing all fields to a common phase center, concatenate them
    into a single field so DP3 can process the MS.
    
    Args:
        ms_path: Path to multi-field MS (all fields should have same phase center)
        output_ms_path: Path for output single-field MS
        
    Returns:
        Path to concatenated MS
    """
    from casatasks import concat
    from casacore.tables import table
    
    # Check field count
    field_table = table(ms_path + "/FIELD", readonly=True)
    nfields = field_table.nrows()
    field_table.close()
    
    if nfields == 1:
        LOG.info("MS already has single field, copying to output")
        if os.path.exists(output_ms_path):
            shutil.rmtree(output_ms_path)
        shutil.copytree(ms_path, output_ms_path)
        return output_ms_path
    
    LOG.info(f"Concatenating {nfields} fields into single field")
    
    # Use manual concatenation (CASA concat may not work as expected for this)
    return _concatenate_fields_manual(ms_path, output_ms_path)


def _concatenate_fields_manual(ms_path: str, output_ms_path: str) -> str:
    """Manually concatenate fields by setting all FIELD_ID to 0.
    
    This is simpler than using CASA concat and works for our use case.
    """
    from casacore.tables import table
    import numpy as np
    
    LOG.info("Using manual field concatenation")
    
    # Copy entire MS first
    if os.path.exists(output_ms_path):
        shutil.rmtree(output_ms_path)
    shutil.copytree(ms_path, output_ms_path)
    
    # Open output for writing
    output_table = table(output_ms_path, readonly=False)
    
    # Update all FIELD_ID to 0 (single field)
    field_ids = output_table.getcol("FIELD_ID")
    nrows = output_table.nrows()
    new_field_ids = np.zeros(nrows, dtype=field_ids.dtype)
    output_table.putcol("FIELD_ID", new_field_ids)
    output_table.close()
    
    # Update FIELD table to have single entry
    field_table = table(output_ms_path + "/FIELD", readonly=False)
    if field_table.nrows() > 1:
        # Keep first field entry, remove others
        field_table.removerows(range(1, field_table.nrows()))
        # Update name to indicate concatenated
        if "NAME" in field_table.colnames():
            field_table.putcell("NAME", 0, "CONCATENATED")
    field_table.close()
    
    LOG.info(f"Manually concatenated MS created: {output_ms_path}")
    return output_ms_path


def prepare_ms_for_dp3(
    ms_path: str,
    target_ra_deg: float,
    target_dec_deg: float,
    *,
    output_ms_path: Optional[str] = None,
    keep_copy: bool = True,
) -> str:
    """Prepare multi-field MS for DP3 by rephasing and concatenating.
    
    This function:
    1. Creates a copy of the MS (if keep_copy=True)
    2. Rephases all fields to a common phase center
    3. Concatenates fields into a single field
    4. Returns path to prepared MS ready for DP3
    
    Args:
        ms_path: Path to input MS (may be multi-field)
        target_ra_deg: Target RA in degrees for rephasing
        target_dec_deg: Target Dec in degrees for rephasing
        output_ms_path: Optional output path (default: ms_path + "_dp3_prepared")
        keep_copy: If True, work on copy; if False, modify in place
        
    Returns:
        Path to prepared single-field MS
    """
    from dsa110_contimg.calibration.cli_utils import rephase_ms_to_calibrator
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Determine output path
    if output_ms_path is None:
        if keep_copy:
            output_ms_path = ms_path + "_dp3_prepared"
        else:
            output_ms_path = ms_path
    
    # Step 1: Copy MS if needed
    if keep_copy and output_ms_path != ms_path:
        LOG.info(f"Copying MS for DP3 preparation: {ms_path} -> {output_ms_path}")
        if os.path.exists(output_ms_path):
            shutil.rmtree(output_ms_path)
        shutil.copytree(ms_path, output_ms_path)
        work_ms = output_ms_path
    else:
        work_ms = ms_path
    
    # Step 2: Rephase all fields to common phase center
    LOG.info(f"Rephasing all fields to ({target_ra_deg:.6f}°, {target_dec_deg:.6f}°)")
    rephase_success = rephase_ms_to_calibrator(
        work_ms,
        target_ra_deg,
        target_dec_deg,
        "DP3_target",
        logger,
    )
    
    if not rephase_success:
        LOG.warning("Rephasing may have failed, but continuing...")
    
    # Step 3: Concatenate fields into single field
    concat_ms_path = work_ms + "_concat"
    LOG.info("Concatenating fields into single field")
    concatenate_fields_in_ms(work_ms, concat_ms_path)
    
    # If we created a working copy, clean it up
    if keep_copy and work_ms != ms_path and work_ms != concat_ms_path:
        if os.path.exists(work_ms):
            shutil.rmtree(work_ms)
    
    return concat_ms_path


def convert_skymodel_to_dp3(
    sky: "SkyModel",
    *,
    out_path: str,
    spectral_index: float = -0.7,
) -> str:
    """Convert pyradiosky SkyModel to DP3 sky model format.
    
    Args:
        sky: pyradiosky SkyModel object
        out_path: Path to output DP3 sky model file (.skymodel)
        spectral_index: Default spectral index if not specified in SkyModel
    
    Returns:
        Path to created DP3 sky model file
    
    DP3 format: Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, 
                ReferenceFrequency, MajorAxis, MinorAxis, Orientation
    Example: s0c0,POINT,07:02:53.6790,+44:31:11.940,2.4,[-0.7],false,1400000000.0,,,
    """
    try:
        from pyradiosky import SkyModel
    except ImportError:
        raise ImportError(
            "pyradiosky is required for convert_skymodel_to_dp3(). "
            "Install with: pip install pyradiosky"
        )
    
    from astropy.coordinates import Angle
    import astropy.units as u
    
    with open(out_path, 'w') as f:
        # Write header
        f.write("Format = Name, Type, Ra, Dec, I, SpectralIndex, LogarithmicSI, ReferenceFrequency='1400000000.0', MajorAxis, MinorAxis, Orientation\n")
        
        for i in range(sky.Ncomponents):
            # Get component data
            ra = sky.skycoord[i].ra
            dec = sky.skycoord[i].dec
            flux_jy = sky.stokes[0, 0, i].to('Jy').value  # I stokes, first frequency
            
            # Format RA/Dec
            ra_str = Angle(ra).to_string(unit='hour', precision=3, pad=True)
            dec_str = Angle(dec).to_string(unit='deg', precision=3, alwayssign=True, pad=True)
            
            # Get reference frequency
            if sky.spectral_type == 'spectral_index':
                ref_freq_hz = sky.reference_frequency[i].to('Hz').value
                spec_idx = sky.spectral_index[i]
            else:
                # Use first frequency as reference
                if sky.freq_array is not None and len(sky.freq_array) > 0:
                    ref_freq_hz = sky.freq_array[0].to('Hz').value
                else:
                    ref_freq_hz = 1.4e9  # Default 1.4 GHz
                spec_idx = spectral_index
            
            # Get name
            if sky.name is not None and i < len(sky.name):
                name = sky.name[i]
            else:
                name = f"s{i}c{i}"
            
            # Write DP3 format line
            f.write(f"{name},POINT,{ra_str},{dec_str},{flux_jy:.6f},[{spec_idx:.2f}],false,{ref_freq_hz:.1f},,,\n")
    
    return out_path


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

