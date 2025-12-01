# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, etc.)
import logging
import os
import time
from typing import Optional

import astropy.units as u
import casacore.tables as tb
import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

from astropy.coordinates import SkyCoord
from casacore.tables import addImagingColumns

# Set up logger
logger = logging.getLogger(__name__)

# Import cached MS metadata helper
try:
    from dsa110_contimg.utils.ms_helpers import get_ms_metadata
except ImportError:
    # Fallback if helper not available
    get_ms_metadata = None


def _ensure_imaging_columns(ms_path: str) -> None:
    """Ensure imaging columns (MODEL_DATA, CORRECTED_DATA) exist in MS.

    Args:
        ms_path: Path to Measurement Set
    """
    try:
        addImagingColumns(ms_path)
    except Exception as e:
        logger.debug(f"Could not add imaging columns to {ms_path}: {e}")
        # Non-fatal, continue


def _initialize_corrected_from_data(ms_path: str) -> None:
    """Initialize CORRECTED_DATA column from DATA column.

    Args:
        ms_path: Path to Measurement Set
    """
    try:
        with tb.table(ms_path, readonly=False) as t:
            if "DATA" in t.colnames() and "CORRECTED_DATA" in t.colnames():
                t.putcol("CORRECTED_DATA", t.getcol("DATA"))
    except Exception as e:
        logger.debug(f"Could not initialize CORRECTED_DATA from DATA in {ms_path}: {e}")
        # Non-fatal, continue


def _calculate_manual_model_data(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    field: Optional[str] = None,
) -> None:
    """Manually calculate MODEL_DATA phase structure using correct phase center.

    This function calculates MODEL_DATA directly using the formula:
        phase = 2π * (u*ΔRA + v*ΔDec) / λ

    This bypasses ft() which may use incorrect phase center information.

    **CRITICAL**: Uses each field's own PHASE_DIR (falls back to REFERENCE_DIR if unavailable)
    to ensure correct phase structure. PHASE_DIR matches the DATA column phasing (updated by
    phaseshift), ensuring MODEL_DATA phase structure matches DATA column exactly.

    Args:
        ms_path: Path to Measurement Set
        ra_deg: Right ascension in degrees (component position)
        dec_deg: Declination in degrees (component position)
        flux_jy: Flux in Jy
        field: Optional field selection (default: all fields). Can be:
              - Single field index: "0"
              - Field range: "0~15"
              - Field name: "MyField"
              If None, writes to all fields.
    """
    import casacore.tables as casatables

    casa_table = casatables.table  # noqa: N816

    _ensure_imaging_columns(ms_path)

    # Parse field selection to get list of field indices
    field_indices = None
    if field is not None:
        if "~" in str(field):
            # Field range: "0~15"
            try:
                parts = str(field).split("~")
                start_idx = int(parts[0])
                end_idx = int(parts[1])
                field_indices = list(range(start_idx, end_idx + 1))
            except (ValueError, IndexError):
                field_indices = None
        elif field.isdigit():
            # Single field index: "0"
            field_indices = [int(field)]
        # If field is a name or invalid, field_indices stays None (use all fields)

    # OPTIMIZATION: Use cached MS metadata if available to avoid redundant table reads
    # This is especially beneficial when MODEL_DATA is calculated multiple times
    # for the same MS (e.g., during calibration iteration).
    use_cached_metadata = False
    if get_ms_metadata is not None:
        try:
            metadata = get_ms_metadata(ms_path)
            phase_dir = metadata.get("phase_dir")
            chan_freq = metadata.get("chan_freq")
            if phase_dir is not None and chan_freq is not None:
                nfields = len(phase_dir)
                nspw = len(chan_freq)
                # Check if cached metadata is actually valid (non-empty)
                if nfields > 0 and nspw > 0:
                    use_cached_metadata = True
                    logger.debug(
                        f"Using cached MS metadata for {ms_path} ({nfields} fields, {nspw} SPWs)"
                    )
                else:
                    # Cached metadata is empty/invalid, fall back to direct read
                    raise ValueError("Cached metadata incomplete")
            else:
                # Fallback to direct read if cache doesn't have required fields
                raise ValueError("Cached metadata incomplete")
        except Exception as e:
            # Fallback to direct read if cache fails
            logger.debug(
                f"Metadata cache lookup failed for {ms_path}: {e}. Falling back to direct read."
            )
            use_cached_metadata = False

    if not use_cached_metadata:
        # Fallback: Read MS phase center from PHASE_DIR for all fields
        # PHASE_DIR matches the actual phase center used for DATA column phasing
        # (updated by phaseshift). This ensures MODEL_DATA matches DATA column phase structure.
        logger.debug(f"Reading MS metadata directly from tables for {ms_path}")
        with casa_table(f"{ms_path}::FIELD", readonly=True) as field_tb:
            if "PHASE_DIR" in field_tb.colnames():
                phase_dir = field_tb.getcol("PHASE_DIR")  # Shape: (nfields, 1, 2)
                logger.debug("Using PHASE_DIR for phase centers")
            else:
                # Fallback to REFERENCE_DIR if PHASE_DIR not available
                phase_dir = field_tb.getcol("REFERENCE_DIR")  # Shape: (nfields, 1, 2)
                logger.debug("PHASE_DIR not available, using REFERENCE_DIR")
            nfields = len(phase_dir)

        # Read spectral window information for frequencies
        with casa_table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            chan_freq = spw_tb.getcol("CHAN_FREQ")  # Shape: (nspw, nchan)
            nspw = len(chan_freq)

    # Log field selection
    if field_indices is not None:
        logger.debug(f"Field selection: {field_indices} ({len(field_indices)} fields)")
    else:
        logger.debug("No field selection: processing all fields")

    # Read main table data
    start_time = time.time()
    with casa_table(ms_path, readonly=False) as main_tb:
        nrows = main_tb.nrows()
        logger.info(
            f"Calculating MODEL_DATA for {ms_path} (field={field}, flux={flux_jy:.2f} Jy, {nrows:,} rows)"
        )

        # Read UVW coordinates
        uvw = main_tb.getcol("UVW")  # Shape: (nrows, 3)
        u = uvw[:, 0]
        v = uvw[:, 1]

        # Read DATA_DESC_ID and map to SPECTRAL_WINDOW_ID
        # DATA_DESC_ID indexes the DATA_DESCRIPTION table, not SPECTRAL_WINDOW directly
        data_desc_id = main_tb.getcol("DATA_DESC_ID")  # Shape: (nrows,)

        # Read DATA_DESCRIPTION table to get SPECTRAL_WINDOW_ID mapping
        with casa_table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd_tb:
            dd_spw_id = dd_tb.getcol("SPECTRAL_WINDOW_ID")  # Shape: (ndd,)
            # Map DATA_DESC_ID -> SPECTRAL_WINDOW_ID
            spw_id = dd_spw_id[data_desc_id]  # Shape: (nrows,)

        # Read FIELD_ID to apply field selection and get per-field phase centers
        field_id = main_tb.getcol("FIELD_ID")  # Shape: (nrows,)

        # Apply field selection if specified
        if field_indices is not None:
            field_mask = np.isin(field_id, field_indices)
        else:
            field_mask = np.ones(nrows, dtype=bool)

        nselected = np.sum(field_mask)
        logger.debug(f"Processing {nselected:,} rows ({nselected / nrows * 100:.1f}% of total)")

        # Read DATA shape to create MODEL_DATA with matching shape
        data_sample = main_tb.getcell("DATA", 0)
        data_shape = data_sample.shape  # In CASA: (nchan, npol)
        nchan, npol = data_shape[0], data_shape[1]
        logger.debug(f"Data shape: {nchan} channels, {npol} polarizations")

        # Initialize MODEL_DATA array with correct shape (nrows, nchan, npol)
        model_data = np.zeros((nrows, nchan, npol), dtype=np.complex64)
        logger.debug(f"Allocated MODEL_DATA array: {model_data.nbytes / 1e9:.2f} GB")

        # VECTORIZED CALCULATION: Process all rows at once using NumPy broadcasting
        # This replaces the row-by-row loop for 10-100x speedup

        # Filter to selected rows only
        selected_indices = np.where(field_mask)[0]
        if len(selected_indices) == 0:
            logger.warning("No rows match field selection criteria")
            main_tb.putcol("MODEL_DATA", model_data)
            main_tb.flush()
            return

        # Get field and SPW indices for selected rows
        selected_field_id = field_id[selected_indices]  # (nselected,)
        selected_spw_id = spw_id[selected_indices]  # (nselected,)
        selected_u = u[selected_indices]  # (nselected,)
        selected_v = v[selected_indices]  # (nselected,)

        # Validate field and SPW indices
        valid_field_mask = (selected_field_id >= 0) & (selected_field_id < nfields)
        valid_spw_mask = (selected_spw_id >= 0) & (selected_spw_id < nspw)
        valid_mask = valid_field_mask & valid_spw_mask

        if not np.all(valid_mask):
            n_invalid = np.sum(~valid_mask)
            logger.warning(f"Skipping {n_invalid} rows with invalid field/SPW indices")
            selected_indices = selected_indices[valid_mask]
            selected_field_id = selected_field_id[valid_mask]
            selected_spw_id = selected_spw_id[valid_mask]
            selected_u = selected_u[valid_mask]
            selected_v = selected_v[valid_mask]

        nselected = len(selected_indices)
        if nselected == 0:
            logger.warning("No valid rows after filtering")
            main_tb.putcol("MODEL_DATA", model_data)
            main_tb.flush()
            return

        # Get phase centers for all selected rows (one per field)
        # phase_dir shape: (nfields, 1, 2) -> extract (ra_rad, dec_rad) for each field
        phase_centers_ra_rad = phase_dir[selected_field_id, 0, 0]  # (nselected,)
        phase_centers_dec_rad = phase_dir[selected_field_id, 0, 1]  # (nselected,)

        # Convert to degrees
        phase_centers_ra_deg = np.degrees(phase_centers_ra_rad)  # (nselected,)
        phase_centers_dec_deg = np.degrees(phase_centers_dec_rad)  # (nselected,)

        # Calculate offsets from phase centers to component (vectorized)
        # Offset in RA: account for cos(dec) factor
        offset_ra_rad = np.radians(ra_deg - phase_centers_ra_deg) * np.cos(
            phase_centers_dec_rad
        )  # (nselected,)
        offset_dec_rad = np.radians(dec_deg - phase_centers_dec_deg)  # (nselected,)

        # Get frequencies for all selected rows
        # chan_freq shape: (nspw, nchan)
        # selected_spw_id contains SPECTRAL_WINDOW_ID values (mapped from DATA_DESC_ID)
        # We index: chan_freq[selected_spw_id] -> (nselected, nchan)
        selected_freqs = chan_freq[selected_spw_id]  # (nselected, nchan)
        selected_wavelengths = 3e8 / selected_freqs  # (nselected, nchan)

        # Vectorize phase calculation using broadcasting
        # u, v: (nselected,) -> (nselected, 1) for broadcasting
        # offset_ra_rad, offset_dec_rad: (nselected,) -> (nselected, 1)
        # wavelengths: (nselected, nchan)
        # Result: (nselected, nchan)
        u_broadcast = selected_u[:, np.newaxis]  # (nselected, 1)
        v_broadcast = selected_v[:, np.newaxis]  # (nselected, 1)
        offset_ra_broadcast = offset_ra_rad[:, np.newaxis]  # (nselected, 1)
        offset_dec_broadcast = offset_dec_rad[:, np.newaxis]  # (nselected, 1)

        # Phase calculation: 2π * (u*ΔRA + v*ΔDec) / λ
        phase = (
            2
            * np.pi
            * (u_broadcast * offset_ra_broadcast + v_broadcast * offset_dec_broadcast)
            / selected_wavelengths
        )
        phase = np.mod(phase + np.pi, 2 * np.pi) - np.pi  # Wrap to [-π, π]

        # Create complex model: amplitude * exp(i*phase)
        # Shape: (nselected, nchan)
        amplitude = float(flux_jy)
        model_complex = amplitude * (np.cos(phase) + 1j * np.sin(phase))  # (nselected, nchan)

        # Broadcast to all polarizations: (nselected, nchan) -> (nselected, nchan, npol)
        model_complex_pol = model_complex[:, :, np.newaxis]  # (nselected, nchan, 1)
        model_data[selected_indices, :, :] = (
            model_complex_pol  # Broadcasts to (nselected, nchan, npol)
        )

        calc_time = time.time() - start_time
        logger.info(
            f"MODEL_DATA calculation completed in {calc_time:.2f}s ({nselected:,} rows, {calc_time / nselected * 1e6:.2f} μs/row)"
        )

        # Write MODEL_DATA column
        write_start = time.time()
        main_tb.putcol("MODEL_DATA", model_data)
        main_tb.flush()  # Ensure data is written to disk
        write_time = time.time() - write_start
        logger.debug(f"MODEL_DATA written to disk in {write_time:.2f}s")

        total_time = time.time() - start_time
        logger.info(f":check: MODEL_DATA populated for {ms_path} (total: {total_time:.2f}s)")

    _initialize_corrected_from_data(ms_path)


def write_point_model_with_ft(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    reffreq_hz: float = 1.4e9,
    spectral_index: Optional[float] = None,
    field: Optional[str] = None,
    use_manual: bool = True,
) -> None:
    """Write a physically-correct complex point-source model into MODEL_DATA.

    By default, uses manual calculation which handles per-field phase centers correctly.
    If use_manual=False, uses CASA ft() task, which reads phase center from FIELD parameters
    but uses ONE phase center for ALL fields. This causes phase errors when fields have
    different phase centers (e.g., each field phased to its own meridian). ft() works correctly
    when all fields share the same phase center (after rephasing), but manual calculation
    is more robust and handles per-field phase centers correctly in all scenarios.

    Args:
        ms_path: Path to Measurement Set
        ra_deg: Right ascension in degrees
        dec_deg: Declination in degrees
        flux_jy: Flux in Jy
        reffreq_hz: Reference frequency in Hz (default: 1.4 GHz)
        spectral_index: Optional spectral index for frequency-dependent flux
        field: Optional field selection (default: all fields). If specified, MODEL_DATA
              will only be written to the selected field(s).
        use_manual: If True (default), use manual calculation (recommended).
                   If False, use ft() which uses one phase center for all fields.
                   Use False only when all fields share the same phase center.
    """
    if use_manual:
        # Use manual calculation to bypass ft() phase center issues
        logger.info(
            "Writing point model using manual calculation (bypasses ft() phase center issues)"
        )
        _calculate_manual_model_data(ms_path, ra_deg, dec_deg, flux_jy, field=field)
        return

    from casatasks import ft
    from casatools import componentlist as cltool

    logger.info(
        "Writing point model using ft() (use_manual=False). "
        "WARNING: ft() uses one phase center for all fields. "
        "Use use_manual=True for per-field phase centers."
    )
    _ensure_imaging_columns(ms_path)

    comp_path = os.path.join(os.path.dirname(ms_path), "cal_component.cl")
    # Remove existing component list if it exists (cl.rename() will fail if it exists)
    if os.path.exists(comp_path):
        import shutil

        shutil.rmtree(comp_path, ignore_errors=True)
    cl = cltool()
    sc = SkyCoord(ra_deg * u.deg, dec_deg * u.deg, frame="icrs")
    dir_dict = {
        "refer": "J2000",
        "type": "direction",
        "long": f"{sc.ra.deg}deg",
        "lat": f"{sc.dec.deg}deg",
    }
    cl.addcomponent(
        dir=dir_dict,
        flux=float(flux_jy),
        fluxunit="Jy",
        freq=f"{reffreq_hz}Hz",
        shape="point",
    )
    if spectral_index is not None:
        try:
            cl.setspectrum(
                which=0,
                type="spectral index",
                index=[float(spectral_index)],
            )
            cl.setfreq(which=0, value=reffreq_hz, unit="Hz")
        except (RuntimeError, ValueError):
            pass
    cl.rename(comp_path)
    cl.close()

    # CRITICAL: Explicitly clear MODEL_DATA with zeros before calling ft()
    # This matches the approach in ft_from_cl() and ensures MODEL_DATA is properly cleared
    # clearcal() may not fully clear MODEL_DATA, especially after rephasing
    try:
        import numpy as np

        t = tb.table(ms_path, readonly=False)
        if "MODEL_DATA" in t.colnames() and t.nrows() > 0:
            # Get DATA shape to match MODEL_DATA shape
            if "DATA" in t.colnames():
                data_sample = t.getcell("DATA", 0)
                data_shape = getattr(data_sample, "shape", None)
                data_dtype = getattr(data_sample, "dtype", None)
                if data_shape and data_dtype:
                    # Clear MODEL_DATA with zeros matching DATA shape
                    zeros = np.zeros((t.nrows(),) + data_shape, dtype=data_dtype)
                    t.putcol("MODEL_DATA", zeros)
        t.close()
    except Exception as e:
        # Non-fatal: log warning but continue
        import warnings

        warnings.warn(
            f"Failed to explicitly clear MODEL_DATA before ft(): {e}. "
            "Continuing with ft() call, but MODEL_DATA may not be properly cleared.",
            RuntimeWarning,
        )

    # Pass field parameter to ensure MODEL_DATA is written to the correct field
    # NOTE: ft() reads phase center from FIELD parameters, but uses ONE phase center for ALL fields.
    # If fields have different phase centers (e.g., each field phased to its own meridian),
    # ft() will use the phase center from one field (typically field 0) for all fields,
    # causing phase errors for fields with different phase centers.
    # Manual calculation (use_manual=True) handles per-field phase centers correctly.
    ft_kwargs = {"vis": ms_path, "complist": comp_path, "usescratch": True}
    if field is not None:
        ft_kwargs["field"] = field
    ft(**ft_kwargs)
    _initialize_corrected_from_data(ms_path)


# NOTE: write_point_model_quick() has been archived to archive/legacy/calibration/model_quick.py
# This function was testing-only and not used in production. It did not calculate
# phase structure (amplitude-only), making it unsuitable for calibration workflows.
# Use write_point_model_with_ft(use_manual=True) instead.


def write_component_model_with_ft(ms_path: str, component_path: str) -> None:
    """Apply an existing CASA component list (.cl) into MODEL_DATA using ft.

    .. deprecated:: 2025-11-05
        This function uses ft() which has known phase center bugs.
        For point sources, use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.

        Known Issues:
        - Uses ft() which does not use PHASE_DIR correctly after rephasing
        - May cause phase scatter when MS is rephased

        This function is kept for component list support (no manual alternative available).
        Use with caution and only when component list is required.

    Args:
        ms_path: Path to Measurement Set
        component_path: Path to CASA component list (.cl)
    """
    import warnings

    warnings.warn(
        "write_component_model_with_ft() uses ft() which has known phase center bugs. "
        "For point sources, use write_point_model_with_ft(use_manual=True) instead. "
        "See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2,
    )
    from casatasks import ft

    if not os.path.exists(component_path):
        raise FileNotFoundError(f"Component list not found: {component_path}")

    _ensure_imaging_columns(ms_path)
    ft(vis=ms_path, complist=component_path, usescratch=True)
    _initialize_corrected_from_data(ms_path)


def write_image_model_with_ft(ms_path: str, image_path: str) -> None:
    """Apply a CASA image model into MODEL_DATA using ft.

    .. deprecated:: 2025-11-05
        This function uses ft() which has known phase center bugs.
        For point sources, use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.

        Known Issues:
        - Uses ft() which does not use PHASE_DIR correctly after rephasing
        - May cause phase scatter when MS is rephased

        This function is kept for image model support (no manual alternative available).
        Use with caution and only when image model is required.

    Args:
        ms_path: Path to Measurement Set
        image_path: Path to CASA image model
    """
    import warnings

    warnings.warn(
        "write_image_model_with_ft() uses ft() which has known phase center bugs. "
        "For point sources, use write_point_model_with_ft(use_manual=True) instead. "
        "See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2,
    )
    from casatasks import ft

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Model image not found: {image_path}")

    _ensure_imaging_columns(ms_path)
    ft(vis=ms_path, model=image_path, usescratch=True)
    _initialize_corrected_from_data(ms_path)


def export_model_as_fits(
    ms_path: str,
    output_path: str,
    field: Optional[str] = None,
    imsize: int = 512,
    cell_arcsec: float = 1.0,
) -> None:
    """Export MODEL_DATA as a FITS image.

    Creates a CASA image from MODEL_DATA column and exports it to FITS format.
    This is useful for visualizing the sky model used during calibration (NVSS sources
    or calibrator model) and for debugging calibration issues.

    Args:
        ms_path: Path to Measurement Set
        output_path: Output FITS file path (without .fits extension)
        field: Optional field selection (default: all fields)
        imsize: Image size in pixels (default: 512)
        cell_arcsec: Cell size in arcseconds (default: 1.0)
    """
    import logging

    from casatasks import exportfits, tclean

    LOG = logging.getLogger(__name__)

    # Ensure imaging columns exist
    _ensure_imaging_columns(ms_path)

    # Create image name (CASA will add .image suffix)
    image_name = f"{output_path}.model"

    try:
        # Use tclean to create image from MODEL_DATA
        # Use niter=0 to just grid without deconvolution
        tclean_kwargs = {
            "vis": ms_path,
            "imagename": image_name,
            "datacolumn": "model",
            "imsize": [imsize, imsize],
            "cell": [f"{cell_arcsec}arcsec", f"{cell_arcsec}arcsec"],
            "specmode": "mfs",
            "niter": 0,  # No deconvolution, just grid the model
            "weighting": "natural",
            "stokes": "I",
        }
        if field is not None:
            tclean_kwargs["field"] = field

        LOG.info(f"Creating model image from {ms_path} MODEL_DATA...")
        tclean(**tclean_kwargs)

        # Export to FITS
        fits_path = f"{output_path}.fits"
        LOG.info(f"Exporting model image to {fits_path}...")
        exportfits(imagename=f"{image_name}.image", fitsimage=fits_path, overwrite=True)

        LOG.info(f":check: Model image exported to {fits_path}")

    except Exception as e:
        LOG.error(f"Failed to export model image: {e}")
        raise


def write_setjy_model(
    ms_path: str,
    field: str,
    *,
    standard: str = "Perley-Butler 2017",
    spw: str = "",
    usescratch: bool = True,
) -> None:
    """Populate MODEL_DATA via casatasks.setjy for standard calibrators.

    .. deprecated:: 2025-11-05
        This function has known phase center bugs when used with rephased MS.
        Use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.

        Known Issues:
        - Uses setjy() which internally calls ft() with phase center bugs
        - Causes 100°+ phase scatter when MS is rephased
        - Does not use PHASE_DIR correctly after rephasing

        The CLI now prevents problematic usage, but this function is deprecated
        for new code.

    Args:
        ms_path: Path to Measurement Set
        field: Field selection
        standard: Flux standard name (default: "Perley-Butler 2017")
        spw: SPW selection
        usescratch: Whether to use scratch column
    """
    import warnings

    warnings.warn(
        "write_setjy_model() is deprecated. Use write_point_model_with_ft(use_manual=True) instead. "
        "This function has known phase center bugs. See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2,
    )
    from casatasks import setjy

    _ensure_imaging_columns(ms_path)
    setjy(vis=ms_path, field=str(field), spw=spw, standard=standard, usescratch=usescratch)
    _initialize_corrected_from_data(ms_path)


def populate_model_from_catalog(
    ms_path: str,
    *,
    field: Optional[str] = None,
    calibrator_name: Optional[str] = None,
    cal_ra_deg: Optional[float] = None,
    cal_dec_deg: Optional[float] = None,
    cal_flux_jy: Optional[float] = None,
) -> None:
    """Populate MODEL_DATA from catalog source.

    Looks up calibrator coordinates and flux from catalog, then writes
    MODEL_DATA using manual calculation (bypasses ft() phase center bugs).

    Args:
        ms_path: Path to Measurement Set
        field: Field selection (default: "0" or first field)
        calibrator_name: Calibrator name (e.g., "0834+555"). If not provided,
                        attempts to auto-detect from MS field names.
        cal_ra_deg: Optional explicit RA in degrees (overrides catalog lookup)
        cal_dec_deg: Optional explicit Dec in degrees (overrides catalog lookup)
        cal_flux_jy: Optional explicit flux in Jy (default: 2.5 Jy if not in catalog)

    Raises:
        ValueError: If calibrator cannot be found or coordinates are invalid
        RuntimeError: If MODEL_DATA population fails
    """
    from dsa110_contimg.calibration.catalogs import (
        get_calibrator_radec,
        load_vla_catalog,
    )

    # Default field to "0" if not provided
    if field is None:
        field = "0"

    # Determine calibrator coordinates
    if cal_ra_deg is not None and cal_dec_deg is not None:
        # Use explicit coordinates
        ra_deg = float(cal_ra_deg)
        dec_deg = float(cal_dec_deg)
        flux_jy = float(cal_flux_jy) if cal_flux_jy is not None else 2.5
        name = calibrator_name or f"manual_{ra_deg:.2f}_{dec_deg:.2f}"
        logger.info(
            f"Using explicit calibrator coordinates: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°), {flux_jy:.2f} Jy"
        )
    elif calibrator_name:
        # Look up from catalog
        try:
            catalog = load_vla_catalog()
            ra_deg, dec_deg = get_calibrator_radec(catalog, calibrator_name)
            # Try to get flux from catalog, default to 2.5 Jy
            flux_jy = float(cal_flux_jy) if cal_flux_jy is not None else 2.5
            name = calibrator_name
            logger.info(
                f"Found calibrator in catalog: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°), {flux_jy:.2f} Jy"
            )
        except Exception as e:
            raise ValueError(
                f"Could not find calibrator '{calibrator_name}' in catalog: {e}. "
                "Provide explicit coordinates with cal_ra_deg and cal_dec_deg."
            ) from e
    else:
        # Try to auto-detect from MS field names
        try:
            with tb.table(ms_path + "::FIELD", readonly=True) as field_tb:
                if "NAME" in field_tb.colnames() and field_tb.nrows() > 0:
                    field_names = field_tb.getcol("NAME")
                    # Look for common calibrator names in field names
                    common_calibrators = ["0834+555", "3C286", "3C48", "3C147", "3C138"]
                    for cal_name in common_calibrators:
                        if any(cal_name.lower() in str(name).lower() for name in field_names):
                            catalog = load_vla_catalog()
                            ra_deg, dec_deg = get_calibrator_radec(catalog, cal_name)
                            flux_jy = float(cal_flux_jy) if cal_flux_jy is not None else 2.5
                            name = cal_name
                            logger.info(
                                f"Auto-detected calibrator from field names: {name} @ ({ra_deg:.4f}°, {dec_deg:.4f}°), {flux_jy:.2f} Jy"
                            )
                            break
                    else:
                        raise ValueError(
                            "Could not auto-detect calibrator from MS field names. "
                            "Provide calibrator_name or explicit coordinates."
                        )
                else:
                    raise ValueError(
                        "Could not read field names from MS. "
                        "Provide calibrator_name or explicit coordinates."
                    )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(
                f"Could not auto-detect calibrator: {e}. "
                "Provide calibrator_name or explicit coordinates."
            ) from e

    # Clear existing MODEL_DATA before writing
    try:
        from casatasks import clearcal

        clearcal(vis=ms_path, addmodel=True)
        logger.debug("Cleared existing MODEL_DATA before writing new model")
    except Exception as e:
        logger.warning(f"Could not clear MODEL_DATA before writing: {e}")

    # Write MODEL_DATA using manual calculation (bypasses ft() phase center bugs)
    logger.info(f"Populating MODEL_DATA for {name} using manual calculation...")
    write_point_model_with_ft(
        ms_path,
        ra_deg,
        dec_deg,
        flux_jy,
        field=field,
        use_manual=True,  # Critical: bypasses ft() phase center bugs
    )
    logger.info(f":check: MODEL_DATA populated for {name}")


def populate_model_from_image(
    ms_path: str,
    *,
    field: Optional[str] = None,
    model_image: str,
) -> None:
    """Populate MODEL_DATA from image file.

    Args:
        ms_path: Path to Measurement Set
        field: Field selection (default: "0")
        model_image: Path to model image file

    Raises:
        FileNotFoundError: If model image does not exist
        RuntimeError: If MODEL_DATA population fails
    """
    if field is None:
        field = "0"

    if not os.path.exists(model_image):
        raise FileNotFoundError(f"Model image not found: {model_image}")

    logger.info(f"Populating MODEL_DATA from image: {model_image}")
    write_image_model_with_ft(ms_path, model_image)
    logger.info(":check: MODEL_DATA populated from image")
