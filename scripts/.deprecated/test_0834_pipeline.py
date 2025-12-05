#!/usr/bin/env python3
"""
Small-scale test: Process a single 16-subband group containing 0834+555 transit.

This test exercises the complete pipeline from HDF5 → MS → calibration:
1. Convert 16 subbands to a single Measurement Set
2. Identify 0834+555 in the field table
3. (Optional) Run bandpass calibration

Usage:
    conda activate casa6
    python scripts/test_0834_pipeline.py [--calibrate]

Test Data:
    Timestamp: 2025-10-21T14:23:19
    Declination: +54.57°
    Calibrator: 0834+555 (RA=8.582h, Dec=+55.57°)
    LST range: 8.52-8.61h (calibrator at RA 8.58h transits mid-observation)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("test_0834")

# Test parameters
TEST_TIMESTAMP = "2025-10-21T14:23:19"
CALIBRATOR_NAME = "0834+555"
CALIBRATOR_RA_DEG = 128.728767
CALIBRATOR_DEC_DEG = 55.5725
INPUT_DIR = Path("/data/incoming")
OUTPUT_DIR = Path("/stage/dsa110-contimg/ms")


def step_1_convert_to_ms() -> Path:
    """Step 1: Convert 16 subbands to Measurement Set."""
    logger.info("=" * 70)
    logger.info("STEP 1: Convert HDF5 subbands to Measurement Set")
    logger.info("=" * 70)
    
    from dsa110_contimg.conversion.hdf5_orchestrator import (
        convert_subband_groups_to_ms,
    )
    
    # Define time window (just this one group)
    start_time = TEST_TIMESTAMP
    # Add 1 second to ensure we capture this exact timestamp
    end_time = TEST_TIMESTAMP.replace("49", "50")
    
    logger.info(f"Input directory: {INPUT_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Time window: {start_time} to {end_time}")
    
    # Run conversion
    result = convert_subband_groups_to_ms(
        input_dir=str(INPUT_DIR),
        output_dir=str(OUTPUT_DIR),
        start_time=start_time,
        end_time=end_time,
    )
    
    # Expected output path
    ms_path = OUTPUT_DIR / f"{TEST_TIMESTAMP}.ms"
    
    if not ms_path.exists():
        raise RuntimeError(f"Conversion failed: {ms_path} not created")
    
    # Validate MS
    from casacore.tables import table
    with table(str(ms_path), ack=False) as tb:
        nrows = tb.nrows()
        logger.info(f"✓ Created MS with {nrows:,} rows")
    
    return ms_path


def step_2_identify_calibrator(ms_path: Path) -> tuple[int, float]:
    """Step 2: Identify which field contains 0834+555."""
    logger.info("=" * 70)
    logger.info("STEP 2: Identify calibrator field")
    logger.info("=" * 70)
    
    from dsa110_contimg.calibration.selection import select_bandpass_from_catalog
    import numpy as np
    
    logger.info(f"Searching for {CALIBRATOR_NAME} in MS fields...")
    
    result = select_bandpass_from_catalog(str(ms_path), search_radius_deg=2.0)
    
    if result is None:
        raise RuntimeError(f"No calibrator found within 2° of any field")
    
    sel_str, field_indices, weighted_flux, cal_info, peak_idx = result
    name, ra_deg, dec_deg, flux_jy = cal_info
    
    logger.info(f"✓ Found calibrator: {name}")
    logger.info(f"  RA: {ra_deg:.4f}° ({ra_deg/15:.4f}h)")
    logger.info(f"  Dec: {dec_deg:+.4f}°")
    logger.info(f"  Peak field: {peak_idx}")
    logger.info(f"  Peak weighted flux: {np.max(weighted_flux):.4f}")
    logger.info(f"  Field selection string: {sel_str}")
    
    # Verify it's 0834+555
    if "0834" not in name:
        logger.warning(f"Found {name} instead of {CALIBRATOR_NAME}")
    
    return peak_idx, np.max(weighted_flux)


def step_3_analyze_ms_structure(ms_path: Path):
    """Step 3: Analyze MS structure for calibration readiness."""
    logger.info("=" * 70)
    logger.info("STEP 3: Analyze MS structure")
    logger.info("=" * 70)
    
    from casacore.tables import table
    import numpy as np
    
    # Check spectral windows
    with table(f"{ms_path}::SPECTRAL_WINDOW", ack=False) as tspw:
        n_spw = tspw.nrows()
        num_chan = tspw.getcol("NUM_CHAN")
        ref_freq = tspw.getcol("REF_FREQUENCY")
        logger.info(f"Spectral windows: {n_spw}")
        logger.info(f"Channels per SPW: {num_chan[0]}")
        logger.info(f"Frequency range: {ref_freq[0]/1e9:.4f} - {ref_freq[-1]/1e9:.4f} GHz")
    
    # Check field structure
    with table(f"{ms_path}::FIELD", ack=False) as tf:
        n_fields = tf.nrows()
        names = tf.getcol("NAME")
        logger.info(f"Fields: {n_fields}")
        logger.info(f"Field names: {names[0]} ... {names[-1]}")
    
    # Check data columns
    with table(str(ms_path), ack=False) as tb:
        cols = tb.colnames()
        logger.info(f"DATA column: {'DATA' in cols}")
        logger.info(f"MODEL_DATA column: {'MODEL_DATA' in cols}")
        logger.info(f"CORRECTED_DATA column: {'CORRECTED_DATA' in cols}")
        
        # Check flagging percentage
        flags = tb.getcol("FLAG")
        flag_pct = np.mean(flags) * 100
        logger.info(f"Flagged data: {flag_pct:.2f}%")


def step_4_run_calibration(ms_path: Path, field_idx: int):
    """Step 4: Run bandpass calibration (optional)."""
    logger.info("=" * 70)
    logger.info("STEP 4: Bandpass calibration")
    logger.info("=" * 70)
    
    from dsa110_contimg.calibration.cli import run_calibrator
    
    logger.info(f"Running bandpass calibration on field {field_idx}...")
    logger.info(f"Calibrator: {CALIBRATOR_NAME}")
    
    # Run calibration
    try:
        result = run_calibrator(
            ms_path=str(ms_path),
            calibrator_name=CALIBRATOR_NAME,
            field=str(field_idx),
        )
        
        if result:
            logger.info("✓ Bandpass calibration completed")
            logger.info(f"  Caltable: {result.get('caltable', 'N/A')}")
            logger.info(f"  Flagged: {result.get('flagged_pct', 'N/A')}%")
        else:
            logger.warning("Calibration returned no result")
            
    except Exception as e:
        logger.error(f"Calibration failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Test 0834+555 calibrator pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run bandpass calibration after MS creation",
    )
    parser.add_argument(
        "--skip-conversion",
        action="store_true",
        help="Skip conversion if MS already exists",
    )
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("DSA-110 Pipeline Test: 0834+555 Calibrator")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {TEST_TIMESTAMP}")
    logger.info(f"Calibrator: {CALIBRATOR_NAME}")
    logger.info(f"  RA: {CALIBRATOR_RA_DEG:.4f}° ({CALIBRATOR_RA_DEG/15:.4f}h)")
    logger.info(f"  Dec: {CALIBRATOR_DEC_DEG:+.4f}°")
    logger.info("")
    
    start_time = datetime.now()
    
    # Step 1: Convert to MS
    ms_path = OUTPUT_DIR / f"{TEST_TIMESTAMP}.ms"
    if args.skip_conversion and ms_path.exists():
        logger.info(f"Skipping conversion: {ms_path} already exists")
    else:
        ms_path = step_1_convert_to_ms()
    
    # Step 2: Identify calibrator
    field_idx, peak_flux = step_2_identify_calibrator(ms_path)
    
    # Step 3: Analyze MS structure
    step_3_analyze_ms_structure(ms_path)
    
    # Step 4: Optional calibration
    if args.calibrate:
        step_4_run_calibration(ms_path, field_idx)
    else:
        logger.info("")
        logger.info("Skipping calibration (use --calibrate to enable)")
    
    elapsed = datetime.now() - start_time
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"Test completed in {elapsed.total_seconds():.1f} seconds")
    logger.info("=" * 70)
    logger.info(f"Output MS: {ms_path}")


if __name__ == "__main__":
    main()
