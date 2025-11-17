# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, etc.)
"""Utility functions for calibration CLI."""

import casacore.tables as casatables

table = casatables.table  # noqa: N816
import os
import shutil

import numpy as np
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()


def rephase_ms_to_calibrator(
    ms_path: str,
    cal_ra_deg: float,
    cal_dec_deg: float,
    cal_name: str,
    logger,
) -> bool:
    """Rephase MS to calibrator position using phaseshift.

    This rephases ALL fields in the MS to the same phase center (calibrator position),
    which simplifies field selection and allows combining fields for better SNR.

    Args:
        ms_path: Path to Measurement Set
        cal_ra_deg: Calibrator RA in degrees
        cal_dec_deg: Calibrator Dec in degrees
        cal_name: Calibrator name (for logging)
        logger: Logger instance

    Returns:
        True if rephasing succeeded or was not needed, False if failed
    """
    print("\n" + "=" * 70)
    print("REPHASING MS TO CALIBRATOR POSITION")
    print("=" * 70)
    print(f"Calibrator: {cal_name} @ ({cal_ra_deg:.6f}°, {cal_dec_deg:.6f}°)")

    # Check if already phased to calibrator (within 1 arcmin tolerance)
    needs_rephasing = True
    try:
        print("Checking current phase center...")
        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as tf:
            if "REFERENCE_DIR" in tf.colnames():
                ref_dir = tf.getcol("REFERENCE_DIR")
                ms_ra_rad = float(np.array(ref_dir[0]).ravel()[0])
                ms_dec_rad = float(np.array(ref_dir[0]).ravel()[1])
            else:
                phase_dir = tf.getcol("PHASE_DIR")
                ms_ra_rad = float(np.array(phase_dir[0]).ravel()[0])
                ms_dec_rad = float(np.array(phase_dir[0]).ravel()[1])
            ms_ra_deg = np.rad2deg(ms_ra_rad)
            ms_dec_deg = np.rad2deg(ms_dec_rad)

        print(f"Current phase center: RA={ms_ra_deg:.4f}°, Dec={ms_dec_deg:.4f}°")
        ms_coord = SkyCoord(ra=ms_ra_deg * u.deg, dec=ms_dec_deg * u.deg)
        cal_coord = SkyCoord(ra=cal_ra_deg * u.deg, dec=cal_dec_deg * u.deg)
        sep_arcmin = ms_coord.separation(cal_coord).to(u.arcmin).value

        print(f"Separation: {sep_arcmin:.2f} arcmin")
        if sep_arcmin < 1.0:
            print(f"✓ MS already phased to calibrator position (offset: {sep_arcmin:.2f} arcmin)")
            print("=" * 70)
            return True
        else:
            print(f"Rephasing needed: offset {sep_arcmin:.2f} arcmin")
            needs_rephasing = True
    except Exception as e:
        print(f"WARNING: Could not check phase center: {e}. Proceeding with rephasing.")
        logger.warning(f"Could not check phase center: {e}. Proceeding with rephasing.")
        needs_rephasing = True

    if not needs_rephasing:
        return True

    try:
        from casatasks import phaseshift as casa_phaseshift

        # Format phase center string for CASA
        ra_hms = (
            Angle(cal_ra_deg, unit="deg")
            .to_string(unit="hourangle", sep="hms", precision=2, pad=True)
            .replace(" ", "")
        )
        dec_dms = (
            Angle(cal_dec_deg, unit="deg")
            .to_string(unit="deg", sep="dms", precision=2, alwayssign=True, pad=True)
            .replace(" ", "")
        )
        phasecenter_str = f"J2000 {ra_hms} {dec_dms}"
        print(f"Phase center string: {phasecenter_str}")

        # Create temporary MS for rephased data
        ms_abs = os.path.abspath(ms_path.rstrip("/"))
        ms_dir = os.path.dirname(ms_abs)
        ms_base = os.path.basename(ms_abs).rstrip(".ms")
        ms_phased = os.path.join(ms_dir, f"{ms_base}.phased.ms")

        # Clean up any existing temporary files
        if os.path.exists(ms_phased):
            print(f"Removing existing phased MS: {ms_phased}")
            shutil.rmtree(ms_phased, ignore_errors=True)

        # Run phaseshift - this rephases ALL fields to the calibrator position
        print("Running phaseshift (rephasing all fields to calibrator position)...")
        print("This may take a while...")
        casa_phaseshift(
            vis=ms_path,
            outputvis=ms_phased,
            phasecenter=phasecenter_str,
            # No field parameter = rephase ALL fields
        )
        print("✓ phaseshift completed successfully")

        # Update REFERENCE_DIR for all fields to match PHASE_DIR
        try:
            with table(f"{ms_phased}::FIELD", readonly=False, ack=False) as tf:
                if "REFERENCE_DIR" in tf.colnames() and "PHASE_DIR" in tf.colnames():
                    # Shape: (nfields, 1, 2)
                    ref_dir_all = tf.getcol("REFERENCE_DIR")
                    # Shape: (nfields, 1, 2)
                    phase_dir_all = tf.getcol("PHASE_DIR")
                    nfields = len(ref_dir_all)

                    # Check if REFERENCE_DIR matches PHASE_DIR for each field
                    needs_update = False
                    for field_idx in range(nfields):
                        ref_dir = ref_dir_all[field_idx][0]
                        phase_dir = phase_dir_all[field_idx][0]
                        if not np.allclose(ref_dir, phase_dir, atol=2.9e-5):
                            needs_update = True
                            break

                    if needs_update:
                        print(
                            f"Updating REFERENCE_DIR for all {nfields} fields to match PHASE_DIR..."
                        )
                        tf.putcol("REFERENCE_DIR", phase_dir_all)
                        print("✓ REFERENCE_DIR updated for all fields")
                    else:
                        print("✓ REFERENCE_DIR already correct for all fields")
        except Exception as refdir_error:
            print(f"WARNING: Could not verify/update REFERENCE_DIR: {refdir_error}")
            logger.warning(f"Could not verify/update REFERENCE_DIR: {refdir_error}")

        # Verify phase center after rephasing
        try:
            with table(f"{ms_phased}::FIELD", readonly=True, ack=False) as tf:
                if "REFERENCE_DIR" in tf.colnames():
                    ref_dir = tf.getcol("REFERENCE_DIR")[0][0]
                    ref_ra_deg = ref_dir[0] * 180.0 / np.pi
                    ref_dec_deg = ref_dir[1] * 180.0 / np.pi

                    ms_coord = SkyCoord(ra=ref_ra_deg * u.deg, dec=ref_dec_deg * u.deg)
                    cal_coord = SkyCoord(ra=cal_ra_deg * u.deg, dec=cal_dec_deg * u.deg)
                    separation = ms_coord.separation(cal_coord)

                    print(f"Final phase center: RA={ref_ra_deg:.6f}°, Dec={ref_dec_deg:.6f}°")
                    print(f"Separation from calibrator: {separation.to(u.arcmin):.4f}")

                    if separation.to(u.arcmin).value > 1.0:
                        print(
                            f"WARNING: Phase center still offset by {separation.to(u.arcmin):.4f}"
                        )
                    else:
                        print("✓ Phase center correctly aligned")
        except Exception as verify_error:
            print(f"WARNING: Could not verify phase center: {verify_error}")

        # Replace original MS with rephased version
        print("Replacing original MS with rephased version...")
        shutil.rmtree(ms_path, ignore_errors=True)
        shutil.move(ms_phased, ms_path)
        print("✓ MS rephased to calibrator position")
        print("=" * 70)
        return True

    except ImportError:
        error_msg = (
            "phaseshift task not available. Cannot rephase MS to calibrator position. "
            "Please ensure CASA environment is properly set up."
        )
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return False
    except Exception as e:
        error_msg = f"Rephasing failed: {e}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        return False


def clear_all_calibration_artifacts(ms_path: str, logger, restore_field_names: bool = True) -> None:
    """Clear all calibration artifacts from MS and directory.

    Clears:
    - MODEL_DATA column (fills with zeros)
    - CORRECTED_DATA column (fills with zeros)
    - Any calibration tables in MS directory
    - Restores field names to original (meridian_icrs_t*) if restore_field_names=True

    Args:
        ms_path: Path to Measurement Set
        logger: Logger instance
        restore_field_names: If True, restore field 0 name to meridian_icrs_t0
    """
    import glob

    ms_dir = os.path.dirname(os.path.abspath(ms_path))
    ms_name = os.path.basename(ms_path.rstrip("/").rstrip(".ms"))

    cleared_items = []

    # 1. Clear MODEL_DATA
    try:
        with table(ms_path, readonly=False) as tb:
            if "MODEL_DATA" in tb.colnames() and tb.nrows() > 0:
                # Get DATA shape to match MODEL_DATA shape
                if "DATA" in tb.colnames():
                    data_sample = tb.getcell("DATA", 0)
                    data_shape = getattr(data_sample, "shape", None)
                    data_dtype = getattr(data_sample, "dtype", None)
                    if data_shape and data_dtype:
                        zeros = np.zeros((tb.nrows(),) + data_shape, dtype=data_dtype)
                        tb.putcol("MODEL_DATA", zeros)
                        cleared_items.append("MODEL_DATA")
                        print(f"  ✓ Cleared MODEL_DATA ({tb.nrows()} rows)")
    except Exception as e:
        logger.warning(f"Could not clear MODEL_DATA: {e}")

    # 2. Clear CORRECTED_DATA
    try:
        with table(ms_path, readonly=False) as tb:
            if "CORRECTED_DATA" in tb.colnames() and tb.nrows() > 0:
                # Get DATA shape to match CORRECTED_DATA shape
                if "DATA" in tb.colnames():
                    data_sample = tb.getcell("DATA", 0)
                    data_shape = getattr(data_sample, "shape", None)
                    data_dtype = getattr(data_sample, "dtype", None)
                    if data_shape and data_dtype:
                        zeros = np.zeros((tb.nrows(),) + data_shape, dtype=data_dtype)
                        tb.putcol("CORRECTED_DATA", zeros)
                        cleared_items.append("CORRECTED_DATA")
                        print(f"  ✓ Cleared CORRECTED_DATA ({tb.nrows()} rows)")
    except Exception as e:
        logger.warning(f"Could not clear CORRECTED_DATA: {e}")

    # 3. Remove calibration tables in MS directory
    try:
        cal_patterns = [
            os.path.join(ms_dir, "*.cal"),
            os.path.join(ms_dir, "*_kcal"),
            os.path.join(ms_dir, "*_bpcal"),
            os.path.join(ms_dir, "*_gpcal"),
            os.path.join(ms_dir, "*_2gcal"),
            os.path.join(ms_dir, "*_gacal"),
            os.path.join(ms_dir, "*_prebp_phase"),
            os.path.join(ms_dir, f"{ms_name}*_bpcal"),
            os.path.join(ms_dir, f"{ms_name}*_gpcal"),
            os.path.join(ms_dir, f"{ms_name}*_2gcal"),
            os.path.join(ms_dir, f"{ms_name}*_prebp_phase"),
            os.path.join(ms_dir, "cal_component.cl"),
        ]

        removed_tables = []
        for pattern in cal_patterns:
            for cal_table in glob.glob(pattern):
                if os.path.isdir(cal_table):  # CASA tables are directories
                    try:
                        shutil.rmtree(cal_table)
                        removed_tables.append(os.path.basename(cal_table))
                    except Exception as e:
                        logger.warning(f"Could not remove {cal_table}: {e}")
                elif os.path.isfile(cal_table):
                    try:
                        os.remove(cal_table)
                        removed_tables.append(os.path.basename(cal_table))
                    except Exception as e:
                        logger.warning(f"Could not remove {cal_table}: {e}")

        if removed_tables:
            cleared_items.append(f"{len(removed_tables)} calibration table(s)")
            print(
                f"  ✓ Removed {len(removed_tables)} calibration table(s): {', '.join(removed_tables[:5])}"
            )
            if len(removed_tables) > 5:
                print(f"    ... and {len(removed_tables) - 5} more")
        else:
            print("  ✓ No calibration tables found to remove")
    except Exception as e:
        logger.warning(f"Could not remove calibration tables: {e}")

    # 4. Restore field names if requested
    if restore_field_names:
        try:
            with table(f"{ms_path}::FIELD", readonly=False, ack=False) as field_tb:
                field_names = field_tb.getcol("NAME")
                if len(field_names) > 0 and not field_names[0].startswith("meridian_icrs_t"):
                    # Field 0 was renamed to calibrator name, restore to meridian_icrs_t0
                    original_name = field_names[0]
                    field_names[0] = "meridian_icrs_t0"
                    field_tb.putcol("NAME", field_names)
                    cleared_items.append(f"field_0_name (restored from '{original_name}')")
                    print("  ✓ Restored field 0 name to 'meridian_icrs_t0'")
                else:
                    print("  ✓ Field 0 name is already correct")
        except Exception as e:
            logger.warning(f"Could not restore field names: {e}")

    if not cleared_items:
        print("  ℹ No calibration artifacts found to clear")
