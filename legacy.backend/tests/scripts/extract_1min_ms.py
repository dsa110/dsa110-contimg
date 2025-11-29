#!/usr/bin/env python3
"""Extract 1 minute from an existing Measurement Set using CASA split."""

import sys
from pathlib import Path

from astropy.time import Time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from casatasks import split  # type: ignore

from dsa110_contimg.database.products import _ms_time_range


def extract_1minute(ms_in, ms_out):
    """Extract the first 1 minute from an MS."""

    ms_in = Path(ms_in).resolve()
    ms_out = Path(ms_out).resolve()

    if not ms_in.exists():
        print(f"Error: Input MS not found: {ms_in}")
        return False

    print(f"Input MS:  {ms_in}")
    print(f"Output MS:  {ms_out}")

    # Extract time range from MS
    print("\nExtracting time range from MS...")
    start_mjd, end_mjd, mid_mjd = _ms_time_range(str(ms_in))

    if start_mjd is None or end_mjd is None:
        print("Error: Could not extract time range from MS")
        return False

    # Calculate duration
    duration_days = end_mjd - start_mjd
    duration_seconds = duration_days * 86400.0
    duration_minutes = duration_seconds / 60.0

    print(f"  Start MJD: {start_mjd:.6f}")
    print(f"  End MJD:   {end_mjd:.6f}")
    print(f"  Duration:  {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")

    if duration_seconds < 60.0:
        print(f"\nWarning: MS contains only {duration_seconds:.1f} seconds (< 1 minute)")
        print("Will extract all available data.")
        extract_end_mjd = end_mjd
    else:
        # Extract first 1 minute
        one_minute_days = 1.0 / 1440.0  # 1 minute in days
        extract_end_mjd = start_mjd + one_minute_days

        # Make sure we don't exceed the available data
        if extract_end_mjd > end_mjd:
            extract_end_mjd = end_mjd
            print("\nWarning: MS is shorter than 1 minute, extracting all available data")

    # Convert to Time objects for formatting
    t_start = Time(start_mjd, format="mjd")
    t_end = Time(extract_end_mjd, format="mjd")

    extract_duration_seconds = (extract_end_mjd - start_mjd) * 86400.0
    print(
        f"\nExtracting: {extract_duration_seconds:.1f} seconds ({extract_duration_seconds / 60.0:.2f} minutes)"
    )
    print(f"  From: {t_start.isot}")
    print(f"  To:   {t_end.isot}")

    # Format for CASA split: YYYY/MM/DD/HH:MM:SS~YYYY/MM/DD/HH:MM:SS
    timerange_str = (
        f"{t_start.datetime.strftime('%Y/%m/%d/%H:%M:%S')}~"
        f"{t_end.datetime.strftime('%Y/%m/%d/%H:%M:%S')}"
    )

    print(f"\nCASA timerange: {timerange_str}")

    # Remove output if exists
    if ms_out.exists():
        print(f"\nRemoving existing output: {ms_out}")
        import shutil

        shutil.rmtree(str(ms_out), ignore_errors=True)

    # Extract using CASA split
    print("\nExtracting 1 minute subset...")
    try:
        split(
            vis=str(ms_in),
            outputvis=str(ms_out),
            timerange=timerange_str,
            keepflags=True,
            datacolumn="DATA",
        )
        print(f"\n:check_mark: Successfully created 1-minute MS: {ms_out}")

        # Verify output
        out_start, out_end, out_mid = _ms_time_range(str(ms_out))
        if out_start is not None and out_end is not None:
            out_duration = (out_end - out_start) * 86400.0
            print("\nOutput MS verification:")
            print(f"  Duration: {out_duration:.1f} seconds ({out_duration / 60.0:.2f} minutes)")
            print(f"  Start: {Time(out_start, format='mjd').isot}")
            print(f"  End:   {Time(out_end, format='mjd').isot}")

        return True

    except Exception as e:
        print(f"\n:ballot_x: Failed to extract 1-minute subset: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python extract_1min_ms.py <input_ms> <output_ms>")
        print("\nExample:")
        print(
            "  python extract_1min_ms.py /data/dsa110-contimg/ms/2025-11-02T13:40:03.ms /tmp/2025-11-02T13:40:03_1min.ms"
        )
        sys.exit(1)

    ms_in = sys.argv[1]
    ms_out = sys.argv[2]

    success = extract_1minute(ms_in, ms_out)
    sys.exit(0 if success else 1)
