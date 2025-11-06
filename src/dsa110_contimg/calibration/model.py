from typing import Optional
import os

import astropy.units as u
from astropy.coordinates import SkyCoord
from casacore.tables import addImagingColumns
import casacore.tables as tb
import numpy as np

# Import cached MS metadata helper
try:
    from dsa110_contimg.utils.ms_helpers import get_ms_metadata
except ImportError:
    # Fallback if helper not available
    get_ms_metadata = None


def _ensure_imaging_columns(ms_path: str) -> None:
    try:
        addImagingColumns(ms_path)
    except Exception:
        pass


def _initialize_corrected_from_data(ms_path: str) -> None:
    try:
        with tb.table(ms_path, readonly=False) as t:
            if "DATA" in t.colnames() and "CORRECTED_DATA" in t.colnames():
                t.putcol("CORRECTED_DATA", t.getcol("DATA"))
    except Exception:
        pass


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
    """
    from casacore.tables import table as casa_table
    
    _ensure_imaging_columns(ms_path)
    
    # Parse field selection to get list of field indices
    field_indices = None
    if field is not None:
        if '~' in str(field):
            # Field range: "0~15"
            try:
                parts = str(field).split('~')
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
    if get_ms_metadata is not None:
        try:
            metadata = get_ms_metadata(ms_path)
            phase_dir = metadata.get('phase_dir')
            chan_freq = metadata.get('chan_freq')
            if phase_dir is not None and chan_freq is not None:
                nfields = len(phase_dir)
                nspw = len(chan_freq)
                # Use cached metadata
            else:
                # Fallback to direct read if cache doesn't have required fields
                raise ValueError("Cached metadata incomplete")
        except Exception:
            # Fallback to direct read if cache fails
            get_ms_metadata = None
    
    if get_ms_metadata is None:
        # Fallback: Read MS phase center from PHASE_DIR for all fields
        # PHASE_DIR matches the actual phase center used for DATA column phasing
        # (updated by phaseshift). This ensures MODEL_DATA matches DATA column phase structure.
        with casa_table(f"{ms_path}::FIELD", readonly=True) as field_tb:
            if "PHASE_DIR" in field_tb.colnames():
                phase_dir = field_tb.getcol("PHASE_DIR")  # Shape: (nfields, 1, 2)
            else:
                # Fallback to REFERENCE_DIR if PHASE_DIR not available
                phase_dir = field_tb.getcol("REFERENCE_DIR")  # Shape: (nfields, 1, 2)
            nfields = len(phase_dir)
        
        # Read spectral window information for frequencies
        with casa_table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            chan_freq = spw_tb.getcol("CHAN_FREQ")  # Shape: (nspw, nchan)
            nspw = len(chan_freq)
    
    # Read main table data
    with casa_table(ms_path, readonly=False) as main_tb:
        nrows = main_tb.nrows()
        
        # Read UVW coordinates
        uvw = main_tb.getcol("UVW")  # Shape: (nrows, 3)
        u = uvw[:, 0]
        v = uvw[:, 1]
        
        # Read SPECTRAL_WINDOW_ID to map rows to spectral windows
        spw_id = main_tb.getcol("DATA_DESC_ID")  # Shape: (nrows,)
        
        # Read FIELD_ID to apply field selection and get per-field phase centers
        field_id = main_tb.getcol("FIELD_ID")  # Shape: (nrows,)
        
        # Apply field selection if specified
        if field_indices is not None:
            field_mask = np.isin(field_id, field_indices)
        else:
            field_mask = np.ones(nrows, dtype=bool)
        
        # Read DATA shape to create MODEL_DATA with matching shape
        data_sample = main_tb.getcell("DATA", 0)
        data_shape = data_sample.shape  # In CASA: (nchan, npol)
        nchan, npol = data_shape[0], data_shape[1]
        
        # Initialize MODEL_DATA array with correct shape (nrows, nchan, npol)
        model_data = np.zeros((nrows, nchan, npol), dtype=np.complex64)
        
        # Calculate MODEL_DATA for each row using that row's field's PHASE_DIR
        for row_idx in range(nrows):
            if not field_mask[row_idx]:
                continue  # Skip rows not in selected field
            
            # Get the field index for this row
            row_field_idx = field_id[row_idx]
            if row_field_idx >= nfields:
                continue  # Skip invalid field indices
            
            # Use this field's PHASE_DIR (matches DATA column phasing, updated by phaseshift)
            phase_center_ra_rad = phase_dir[row_field_idx][0][0]
            phase_center_dec_rad = phase_dir[row_field_idx][0][1]
            phase_center_ra_deg = phase_center_ra_rad * 180.0 / np.pi
            phase_center_dec_deg = phase_center_dec_rad * 180.0 / np.pi
            
            # Calculate offset from this field's phase center to component
            offset_ra_rad = (ra_deg - phase_center_ra_deg) * np.pi / 180.0 * np.cos(phase_center_dec_rad)
            offset_dec_rad = (dec_deg - phase_center_dec_deg) * np.pi / 180.0
            
            spw_idx = spw_id[row_idx]
            if spw_idx >= nspw:
                continue  # Skip invalid spectral window
            
            # Get frequencies for this spectral window
            freqs = chan_freq[spw_idx]  # Shape: (nchan,)
            wavelengths = 3e8 / freqs  # Shape: (nchan,)
            
            # Calculate phase for each channel using this field's phase center
            # phase = 2π * (u*ΔRA + v*ΔDec) / λ
            phase = 2 * np.pi * (u[row_idx] * offset_ra_rad + v[row_idx] * offset_dec_rad) / wavelengths
            phase = np.mod(phase + np.pi, 2*np.pi) - np.pi  # Wrap to [-π, π]
            
            # Amplitude is constant (flux_jy)
            amplitude = float(flux_jy)
            
            # Create complex model: amplitude * exp(i*phase)
            # Shape: (nchan,)
            model_complex = amplitude * (np.cos(phase) + 1j * np.sin(phase))
            
            # Broadcast to all polarizations: (nchan,) -> (nchan, npol)
            # Use broadcasting: model_complex[:, np.newaxis] creates (nchan, 1) which broadcasts to (nchan, npol)
            model_data[row_idx, :, :] = model_complex[:, np.newaxis]
        
        # Write MODEL_DATA column
        main_tb.putcol("MODEL_DATA", model_data)
    
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
        _calculate_manual_model_data(ms_path, ra_deg, dec_deg, flux_jy, field=field)
        return
    
    from casatools import componentlist as cltool
    from casatasks import ft

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
        shape="point")
    if spectral_index is not None:
        try:
            cl.setspectrum(
                which=0,
                type="spectral index",
                index=[
                    float(spectral_index)],
                reffreq=f"{reffreq_hz}Hz")
        except Exception:
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
            RuntimeWarning
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
        stacklevel=2
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
        stacklevel=2
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
    from casatasks import tclean, exportfits
    from casatools import image as imtool
    import logging
    
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
        
        LOG.info(f"✓ Model image exported to {fits_path}")
        
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
        stacklevel=2
    )
    from casatasks import setjy

    _ensure_imaging_columns(ms_path)
    setjy(
        vis=ms_path,
        field=str(field),
        spw=spw,
        standard=standard,
        usescratch=usescratch)
    _initialize_corrected_from_data(ms_path)
