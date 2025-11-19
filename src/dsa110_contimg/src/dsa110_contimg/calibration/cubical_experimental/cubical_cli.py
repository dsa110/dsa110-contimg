"""
Standalone CLI for CubiCal calibration testing.

This CLI is completely independent of the existing CASA-based pipeline.
It can be used to test CubiCal performance and compare results.
"""

import argparse
import logging
from pathlib import Path

# Note: These imports will fail until CubiCal is installed
# That's intentional - this is experimental code
try:
    from .cubical_calibrate import solve_bandpass_cubical, solve_gains_cubical
    from .format_converter import cubical_to_casa_table

    CUBICAL_AVAILABLE = True
except ImportError:
    CUBICAL_AVAILABLE = False
    logging.warning("CubiCal not installed. This is experimental code.")


def main():
    """Standalone CubiCal calibration CLI."""
    parser = argparse.ArgumentParser(
        description="Experimental CubiCal calibration (standalone, does not modify existing pipeline)"
    )
    parser.add_argument("--ms", required=True, help="Measurement Set path")
    parser.add_argument(
        "--auto-fields",
        action="store_true",
        help="Auto-select calibrator fields (uses existing catalog logic)",
    )
    parser.add_argument("--field", help="Manual field selection (e.g., '0' or '0~1')")
    parser.add_argument("--refant", default="103", help="Reference antenna")
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for calibration tables"
    )
    parser.add_argument(
        "--convert-to-casa",
        action="store_true",
        help="Convert CubiCal results to CASA table format for comparison",
    )

    args = parser.parse_args()

    if not CUBICAL_AVAILABLE:
        print("ERROR: CubiCal is not installed.")
        print(
            "Install with: pip install 'cubical[lsm-support]@git+https://github.com/ratt-ru/CubiCal.git@1.4.0'"
        )
        return 1

    ms_path = Path(args.ms)
    if not ms_path.exists():
        print(f"ERROR: MS file not found: {ms_path}")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("CUBICAL EXPERIMENTAL CALIBRATION")
    print("=" * 70)
    print(f"MS: {ms_path}")
    print(f"Output: {output_dir}")
    print()

    # Field selection (reuse existing logic if needed, or implement CubiCal-specific)
    if args.auto_fields:
        # TODO: Implement auto-field selection for CubiCal
        # Could reuse existing catalog logic from calibration/selection.py
        print("Auto-field selection not yet implemented for CubiCal")
        print("Please use --field for now")
        return 1

    if not args.field:
        print("ERROR: Either --auto-fields or --field must be specified")
        return 1

    cal_field = args.field

    try:
        # Step 1: Bandpass calibration
        print("[1/2] Solving bandpass with CubiCal...")
        bp_solution = solve_bandpass_cubical(
            ms_path=str(ms_path), cal_field=cal_field, refant=args.refant
        )

        bp_output = output_dir / "bandpass_cubical.h5"
        bp_solution.save(str(bp_output))
        print(f"✓ Bandpass solution saved: {bp_output}")

        # Step 2: Gain calibration
        print("[2/2] Solving gains with CubiCal...")
        gain_solution = solve_gains_cubical(
            ms_path=str(ms_path),
            cal_field=cal_field,
            refant=args.refant,
            bptable=str(bp_output),
        )

        gain_output = output_dir / "gains_cubical.h5"
        gain_solution.save(str(gain_output))
        print(f"✓ Gain solution saved: {gain_output}")

        # Optional: Convert to CASA format for comparison
        if args.convert_to_casa:
            print("Converting to CASA format...")
            casa_bp = output_dir / "bandpass_cubical.cal"
            casa_gain = output_dir / "gains_cubical.cal"

            cubical_to_casa_table(bp_solution, str(ms_path), str(casa_bp))
            cubical_to_casa_table(gain_solution, str(ms_path), str(casa_gain))

            print("✓ CASA format tables created:")
            print(f"  - {casa_bp}")
            print(f"  - {casa_gain}")

        print()
        print("=" * 70)
        print("CALIBRATION COMPLETE")
        print("=" * 70)
        print(f"Results saved to: {output_dir}")
        print()
        print("To compare with CASA results, run:")
        print("  python -m dsa110_contimg.calibration.cli calibrate \\")
        print(f"    --ms {ms_path} --field {cal_field} --preset standard")

        return 0

    except Exception as e:
        print(f"ERROR: Calibration failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
