"""
Utilities for creating test MS files.
"""

from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from casacore.tables import table
from casatasks import split

logger = logging.getLogger(__name__)


def create_test_ms(
    ms_in: str,
    ms_out: str,
    max_baselines: int = 20,
    max_times: int = 100,
    timebin: str = None,
) -> bool:
    """
    Create a smaller test MS from a full MS for testing.

    This function uses CASA `split` to create a subset MS that prioritizes:
    1. Baselines containing the reference antenna (default: 103)
    2. Even sampling across the time range
    3. Preservation of all spectral windows (full bandwidth)

    Args:
        ms_in: Input MS path (full MS)
        ms_out: Output MS path (will be overwritten if exists)
        max_baselines: Maximum number of baselines to include (default: 20)
        max_times: Maximum number of time integrations to include (default: 100)
        timebin: Optional time binning for further reduction (e.g., '30s')

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Creating Test MS for K-Calibration")
    print(f"{'='*70}\n")
    print(f"Input:  {ms_in}")
    print(f"Output: {ms_out}\n")

    # Analyze input MS
    with table(ms_in, readonly=True) as tb:
        n_rows = tb.nrows()
        ant1 = tb.getcol("ANTENNA1")
        ant2 = tb.getcol("ANTENNA2")
        times = tb.getcol("TIME")
        field_ids = tb.getcol("FIELD_ID")

        # Get unique baselines
        baselines = list(set(zip(ant1, ant2)))
        unique_times = sorted(set(times))

        print(f"Input MS:")
        print(f"  Total rows: {n_rows:,}")
        print(f"  Baselines: {len(baselines)}")
        print(f"  Time integrations: {len(unique_times)}")
        print(f"  Fields: {sorted(set(field_ids))}\n")

        # Select subset of baselines (include reference antenna 103)
        refant = 103
        refant_baselines = [bl for bl in baselines if refant in bl]
        other_baselines = [bl for bl in baselines if refant not in bl]

        selected_baselines = refant_baselines[:max_baselines]
        remaining = max_baselines - len(selected_baselines)
        if remaining > 0:
            selected_baselines.extend(other_baselines[:remaining])

        print(f"Selected baselines: {len(selected_baselines)}")
        print(
            f"  (Including {len(refant_baselines[:max_baselines])} with refant {refant})"
        )

        # Build antenna selection string
        ants_in_selected = set()
        for bl in selected_baselines:
            ants_in_selected.add(bl[0])
            ants_in_selected.add(bl[1])
        antenna_str = ",".join(map(str, sorted(ants_in_selected)))

        # Select subset of times
        if len(unique_times) > max_times:
            indices = np.linspace(0, len(unique_times) - 1, max_times, dtype=int)
            selected_times = [unique_times[i] for i in indices]
            time_start = min(selected_times)
            time_end = max(selected_times)
        else:
            selected_times = unique_times
            time_start = min(selected_times)
            time_end = max(selected_times)

        print(f"Selected times: {len(selected_times)}")
        print(f"  Time range: {time_start} to {time_end}")

        # Get SPW info
        with table(f"{ms_in}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
            n_spw = spw_tb.nrows()
            print(f"\nSpectral windows: {n_spw} (keeping all for delay testing)")

    # Remove output if exists
    if os.path.exists(ms_out):
        print(f"\nRemoving existing output: {ms_out}")
        shutil.rmtree(ms_out, ignore_errors=True)

    # Use CASA split to create subset
    print(f"\nCreating subset MS...")

    # Build time selection
    # Use format detection to handle both TIME formats (seconds since MJD 0 vs MJD 51544.0)
    from astropy.time import Time
    from dsa110_contimg.utils.time_utils import detect_casa_time_format

    _, mjd_start = detect_casa_time_format(time_start)
    _, mjd_end = detect_casa_time_format(time_end)
    t_start = Time(mjd_start, format="mjd")
    t_end = Time(mjd_end, format="mjd")

    # Format for CASA: YYYY/MM/DD/HH:MM:SS
    timerange_str = f"{t_start.datetime.strftime('%Y/%m/%d/%H:%M:%S')}~{t_end.datetime.strftime('%Y/%m/%d/%H:%M:%S')}"

    # Split with selections
    split_kwargs = {
        "vis": ms_in,
        "outputvis": ms_out,
        "antenna": antenna_str,
        "timerange": timerange_str,
        "keepflags": True,
        "datacolumn": "DATA",
    }

    if timebin:
        split_kwargs["timebin"] = timebin

    print(f"Split parameters:")
    print(f"  antenna: {antenna_str[:50]}... ({len(ants_in_selected)} antennas)")
    print(f"  timerange: {timerange_str}")
    if timebin:
        print(f"  timebin: {timebin}")

    try:
        split(**split_kwargs)
        print(f"\n✓ Successfully created test MS: {ms_out}")
    except Exception as e:
        print(f"\n✗ Split failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Verify output
    try:
        with table(ms_out, readonly=True) as tb:
            n_rows_out = tb.nrows()
            print(f"\nOutput MS:")
            print(f"  Total rows: {n_rows_out:,}")
            print(f"  Reduction: {n_rows / n_rows_out:.1f}x smaller")

            # Check SPWs preserved
            with table(f"{ms_out}::SPECTRAL_WINDOW", readonly=True) as spw_tb:
                n_spw_out = spw_tb.nrows()
                print(f"  Spectral windows: {n_spw_out} (preserved)")

            # Check baselines
            ant1_out = tb.getcol("ANTENNA1")
            ant2_out = tb.getcol("ANTENNA2")
            baselines_out = len(set(zip(ant1_out, ant2_out)))
            print(f"  Baselines: {baselines_out}")

            # Check times
            times_out = tb.getcol("TIME")
            unique_times_out = len(set(times_out))
            print(f"  Time integrations: {unique_times_out}")

    except Exception as e:
        print(f"⚠ Could not verify output: {e}")

    return True


def create_minimal_test_ms(output_ms: str, cleanup: bool = True) -> bool:
    """
    Create a minimal test MS using synthetic data generation.

    This generates synthetic UVH5 data, converts it to MS, and validates
    the result - all in under 1 minute for quick smoke testing.

    Args:
        output_ms: Output MS path
        cleanup: Whether to clean up temporary synthetic data

    Returns:
        bool: True if successful, False otherwise
    """
    import tempfile
    from pathlib import Path

    logger.info("=" * 70)
    logger.info("Smoke Test: Minimal MS Generation")
    logger.info("=" * 70)
    logger.info(f"Output: {output_ms}\n")

    try:
        # Generate minimal synthetic data
        with tempfile.TemporaryDirectory() as tmpdir:
            synth_dir = Path(tmpdir) / "synthetic"
            synth_dir.mkdir()

            logger.info("1. Generating minimal synthetic UVH5 data...")
            from dsa110_contimg.simulation.make_synthetic_uvh5 import main as make_synth
            import sys

            # Create minimal config inline or use defaults
            synth_args = [
                "--output",
                str(synth_dir),
                "--start-time",
                "2025-10-30T10:00:00",
                "--nsubbands",
                "4",  # Minimal for speed
                "--duration-minutes",
                "1",  # 1 minute only
            ]

            # Call synthetic data generator
            old_argv = sys.argv
            try:
                sys.argv = ["make_synthetic_uvh5"] + synth_args
                make_synth()
            except SystemExit:
                pass
            finally:
                sys.argv = old_argv

            # Find generated files
            synth_files = list(synth_dir.glob("*_sb*.hdf5"))
            if not synth_files:
                logger.error("✗ Synthetic data generation failed")
                return False

            logger.info(f"   Generated {len(synth_files)} subband files")

            # Convert to MS
            logger.info("\n2. Converting synthetic data to MS...")
            from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                convert_subband_groups_to_ms,
            )

            ms_dir = Path(output_ms).parent
            ms_dir.mkdir(parents=True, exist_ok=True)

            convert_subband_groups_to_ms(
                input_dir=str(synth_dir),
                output_dir=str(ms_dir),
                start_time="2025-10-30 10:00:00",
                end_time="2025-10-30 10:01:00",
                writer="pyuvdata",  # Fastest for small data
            )

            # Find generated MS
            ms_files = list(ms_dir.glob("*.ms"))
            if not ms_files:
                logger.error("✗ MS conversion failed")
                return False

            generated_ms = ms_files[0]

            # Rename to desired output if different
            if str(generated_ms) != output_ms:
                if os.path.exists(output_ms):
                    shutil.rmtree(output_ms)
                shutil.move(str(generated_ms), output_ms)

            # Validate MS
            logger.info("\n3. Validating generated MS...")
            from dsa110_contimg.utils.validation import validate_ms

            try:
                validate_ms(
                    output_ms,
                    check_empty=True,
                    check_columns=["DATA", "ANTENNA1", "ANTENNA2", "TIME", "UVW"],
                )

                with table(output_ms, readonly=True) as tb:
                    logger.info(f"   ✓ MS created: {tb.nrows():,} rows")

                logger.info("\n" + "=" * 70)
                logger.info("✓ Smoke test PASSED")
                logger.info("=" * 70)
                logger.info(f"\nTest MS: {output_ms}")
                logger.info("Pipeline is functional!")

                return True

            except Exception as e:
                logger.error(f"✗ MS validation failed: {e}")
                return False

            finally:
                # Cleanup synthetic data if requested
                if cleanup:
                    logger.info("\n4. Cleaning up temporary files...")
                    shutil.rmtree(synth_dir, ignore_errors=True)

    except Exception as e:
        logger.error(f"✗ Smoke test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
