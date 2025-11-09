#!/usr/bin/env python3
"""Test complete pipeline stages on 1-minute MS (excluding mosaicking)."""

import sys
import os
from pathlib import Path
import logging

# Force unbuffered output for real-time visibility
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("=" * 70, flush=True)
print("Starting pipeline test script", flush=True)
print("=" * 70, flush=True)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
print(f"Added src to path: {Path(__file__).parent / 'src'}", flush=True)

# Set up environment before CASA imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ.get("DISPLAY"):
    os.environ.pop("DISPLAY", None)

from dsa110_contimg.utils.cli_helpers import setup_casa_environment, configure_logging_from_args
from dsa110_contimg.utils.tempdirs import prepare_temp_environment

# Set CASA environment BEFORE any CASA imports
print("Setting up CASA environment...", flush=True)
setup_casa_environment()
print("CASA environment configured", flush=True)

# Set up logging
print("Configuring logging...", flush=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True  # Force reconfiguration
)
LOG = logging.getLogger(__name__)
print("Logging configured", flush=True)

# Import pipeline modules
from dsa110_contimg.conversion.ms_utils import configure_ms_for_imaging
from dsa110_contimg.calibration.flagging import reset_flags, flag_zeros, flag_rfi
from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.selection import select_bandpass_fields
from dsa110_contimg.imaging.cli import image_ms
from dsa110_contimg.utils.validation import validate_ms


def get_ms_metadata(ms_path):
    """Extract phase center and frequency from MS in a single pass (optimized).
    
    Args:
        ms_path: Path to Measurement Set
        
    Returns:
        Tuple of (ra0_deg, dec0_deg, freq_ghz)
    """
    from casacore.tables import table
    import numpy as np
    
    # Get phase center from FIELD table
    with table(f"{ms_path}::FIELD", readonly=True) as fld:
        ph = fld.getcol("PHASE_DIR")[0]
        ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
        dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
    
    # Get observing frequency from SPECTRAL_WINDOW table
    with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
        ch = spw.getcol("CHAN_FREQ")[0]
        freq_ghz = float(np.nanmean(ch)) / 1e9
    
    return ra0_deg, dec0_deg, freq_ghz


def test_pipeline_stages(ms_path, output_dir, skip_calibration=False):
    """Run all pipeline stages on the 1-minute MS."""
    
    ms_path = Path(ms_path).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not ms_path.exists():
        LOG.error(f"MS not found: {ms_path}")
        return False
    
    LOG.info("="*70)
    LOG.info("Pipeline Test: 1-Minute MS")
    LOG.info("="*70)
    LOG.info(f"Input MS:  {ms_path}")
    LOG.info(f"Output dir: {output_dir}")
    LOG.info("")
    
    # Prepare temp environment
    try:
        scratch_dir = os.getenv("CONTIMG_SCRATCH_DIR") or "/stage/dsa110-contimg"
        prepare_temp_environment(scratch_dir, cwd_to=str(output_dir))
    except Exception as e:
        LOG.warning(f"Temp environment prep failed: {e}")
    
    success_stages = []
    failed_stages = []
    
    # Stage 1: Validate and Configure MS for Imaging
    LOG.info("="*70)
    LOG.info("Stage 1: MS Validation & Configuration")
    LOG.info("="*70)
    try:
        validate_ms(str(ms_path), check_empty=True)
        LOG.info("✓ MS validation passed")
        
        configure_ms_for_imaging(str(ms_path))
        LOG.info("✓ MS configured for imaging")
        success_stages.append("validation")
    except Exception as e:
        LOG.error(f"✗ Stage 1 failed: {e}")
        failed_stages.append("validation")
        return False
    
    # Stage 2: RFI Flagging
    LOG.info("")
    LOG.info("="*70)
    LOG.info("Stage 2: RFI Flagging")
    LOG.info("="*70)
    try:
        reset_flags(str(ms_path))
        LOG.info("✓ Flags reset")
        
        flag_zeros(str(ms_path), datacolumn='data')
        LOG.info("✓ Zero values flagged")
        
        flag_rfi(str(ms_path), datacolumn='data')
        LOG.info("✓ RFI flagged")
        success_stages.append("flagging")
    except Exception as e:
        LOG.error(f"✗ Stage 2 failed: {e}")
        failed_stages.append("flagging")
        import traceback
        traceback.print_exc()
    
    # Stage 3: Calibration (optional - skip if requested or if no calibrator field)
    caltables = []
    if not skip_calibration:
        LOG.info("")
        LOG.info("="*70)
        LOG.info("Stage 3: Calibration (Fast Mode)")
        LOG.info("="*70)
        try:
            # CRITICAL: Populate MODEL_DATA before calibration
            # Calibration requires MODEL_DATA to know what signal to calibrate against
            LOG.info("Populating MODEL_DATA with NVSS sources...")
            try:
                from dsa110_contimg.calibration.skymodels import (
                    make_nvss_component_cl,
                    ft_from_cl,
                )
                
                # Get MS metadata in single optimized pass (faster than separate reads)
                ra0_deg, dec0_deg, freq_ghz = get_ms_metadata(str(ms_path))
                
                # Create NVSS component list (10 mJy minimum, 0.2 deg radius)
                cl_path = str(output_dir / "cal_model_10mJy.cl")
                make_nvss_component_cl(
                    ra0_deg,
                    dec0_deg,
                    radius_deg=0.2,
                    min_mjy=10.0,
                    freq_ghz=freq_ghz,
                    out_path=cl_path,
                )
                LOG.info(f"✓ NVSS component list created: {cl_path}")
                
                # Apply to MODEL_DATA via ft()
                ft_from_cl(str(ms_path), cl_path, field="0")
                LOG.info("✓ MODEL_DATA populated with NVSS sources")
                
            except Exception as e:
                LOG.warning(f"Failed to populate MODEL_DATA with NVSS: {e}")
                LOG.warning("Calibration will likely fail without MODEL_DATA")
                raise
            
            # Try to find a calibrator field or use field 0
            # For 1-minute data, we'll use fast mode with minimal calibration
            cal_field = "0"  # Use first field
            refant = "103"   # Default reference antenna
            
            LOG.info(f"Attempting calibration on field {cal_field} with refant {refant}")
            LOG.info("Using fast mode (phase-only gains, uvrange cut)")
            
            # Note: K-calibration skipped by default for DSA-110
            # BP calibration with fast mode
            bp_table = str(output_dir / "test_1min.bpcal")
            LOG.info("Solving bandpass...")
            bp_tabs = solve_bandpass(
                str(ms_path),
                cal_field,
                refant,
                ktable=None,  # No K-table
                uvrange=">1klambda",  # Fast mode: exclude short baselines
            )
            
            if bp_tabs:
                LOG.info(f"✓ Bandpass calibration: {bp_tabs[0]}")
                caltables.extend(bp_tabs)
            
            # G calibration with phase-only (fast mode)
            if bp_tabs:
                LOG.info("Solving gains (phase-only)...")
                g_tabs = solve_gains(
                    str(ms_path),
                    cal_field,
                    refant,
                    ktable=None,
                    bptables=bp_tabs,
                    phase_only=True,  # Fast mode
                )
                if g_tabs:
                    LOG.info(f"✓ Gain calibration: {g_tabs[0]}")
                    caltables.extend(g_tabs)
            
            if caltables:
                LOG.info(f"✓ Calibration complete: {len(caltables)} tables")
                success_stages.append("calibration")
            else:
                LOG.warning("No calibration tables generated")
                failed_stages.append("calibration")
        except Exception as e:
            LOG.warning(f"Calibration failed (continuing anyway): {e}")
            failed_stages.append("calibration")
            import traceback
            traceback.print_exc()
    else:
        LOG.info("")
        LOG.info("="*70)
        LOG.info("Stage 3: Calibration (SKIPPED)")
        LOG.info("="*70)
        LOG.info("Skipping calibration as requested")
    
    # Stage 4: Apply Calibration
    LOG.info("")
    LOG.info("="*70)
    LOG.info("Stage 4: Apply Calibration")
    LOG.info("="*70)
    try:
        if caltables:
            LOG.info(f"Applying {len(caltables)} calibration tables...")
            apply_to_target(
                str(ms_path),
                field='',
                gaintables=caltables,
                calwt=True,
            )
            
            # Verify CORRECTED_DATA was populated
            from casacore.tables import table
            with table(str(ms_path), readonly=True) as t:
                corrected = t.getcol('CORRECTED_DATA')
            if corrected is not None and not (corrected == 0).all():
                LOG.info("✓ Calibration applied (CORRECTED_DATA populated)")
                success_stages.append("applycal")
            else:
                LOG.warning("CORRECTED_DATA appears all zeros")
                failed_stages.append("applycal")
        else:
            LOG.info("No calibration tables to apply (using DATA column)")
            success_stages.append("applycal")  # Not a failure if no caltables
    except Exception as e:
        LOG.error(f"✗ Stage 4 failed: {e}")
        failed_stages.append("applycal")
        import traceback
        traceback.print_exc()
    
    # Stage 5: Imaging with WSClean
    LOG.info("")
    LOG.info("="*70)
    LOG.info("Stage 5: Imaging with WSClean (Quick Mode)")
    LOG.info("="*70)
    try:
        imagename = str(output_dir / "test_1min_wsclean")
        
        LOG.info(f"Imaging to: {imagename}")
        LOG.info("Using WSClean backend (quick mode: reduced imsize, fewer iterations)")
        LOG.info("Note: MODEL_DATA already populated during calibration stage")
        
        image_ms(
            str(ms_path),
            imagename=imagename,
            imsize=512,  # Quick mode: smaller image
            niter=300,  # Quick mode: fewer iterations
            threshold="0.0Jy",
            pbcor=True,
            quick=True,  # Quick mode
            skip_fits=False,  # Keep FITS for WSClean (it outputs FITS directly)
            backend="wsclean",  # Use WSClean instead of tclean
            wsclean_path="docker",  # Use Docker container
            # datacolumn is auto-detected (will use CORRECTED_DATA if available)
        )
        
        # Check if images were created (WSClean outputs FITS files)
        image_files = list(output_dir.glob("test_1min_wsclean-MFS-*.fits"))
        if not image_files:
            # Also check for CASA-style images in case it fell back
            image_files = list(output_dir.glob("test_1min_wsclean.image*"))
        
        if image_files:
            LOG.info(f"✓ Imaging complete: {len(image_files)} image files created")
            success_stages.append("imaging")
        else:
            LOG.warning("No image files found")
            failed_stages.append("imaging")
    except Exception as e:
        LOG.error(f"✗ Stage 5 failed: {e}")
        failed_stages.append("imaging")
        import traceback
        traceback.print_exc()
    
    # Summary
    LOG.info("")
    LOG.info("="*70)
    LOG.info("Pipeline Test Summary")
    LOG.info("="*70)
    LOG.info(f"Successful stages: {len(success_stages)}/{5}")
    for stage in success_stages:
        LOG.info(f"  ✓ {stage}")
    if failed_stages:
        LOG.info(f"Failed stages: {len(failed_stages)}")
        for stage in failed_stages:
            LOG.info(f"  ✗ {stage}")
    
    LOG.info("")
    LOG.info(f"Output directory: {output_dir}")
    LOG.info(f"Calibration tables: {len(caltables)}")
    
    return len(failed_stages) == 0


if __name__ == "__main__":
    print("=" * 70, flush=True)
    print("MAIN: Parsing arguments", flush=True)
    print("=" * 70, flush=True)
    
    if len(sys.argv) < 2:
        print("Usage: python test_pipeline_1min.py <ms_path> [output_dir] [--skip-cal]", flush=True)
        print("\nExample:", flush=True)
        print("  python test_pipeline_1min.py /data/dsa110-contimg/ms/2025-11-02T13:40:03_1min.ms /tmp/pipeline_test", flush=True)
        sys.exit(1)
    
    ms_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/pipeline_test_1min"
    skip_cal = "--skip-cal" in sys.argv
    
    print(f"MS path: {ms_path}", flush=True)
    print(f"Output dir: {output_dir}", flush=True)
    print(f"Skip calibration: {skip_cal}", flush=True)
    print("=" * 70, flush=True)
    print("Calling test_pipeline_stages...", flush=True)
    print("=" * 70, flush=True)
    
    success = test_pipeline_stages(ms_path, output_dir, skip_calibration=skip_cal)
    
    print("=" * 70, flush=True)
    print(f"Pipeline test completed: {'SUCCESS' if success else 'FAILED'}", flush=True)
    print("=" * 70, flush=True)
    
    sys.exit(0 if success else 1)

