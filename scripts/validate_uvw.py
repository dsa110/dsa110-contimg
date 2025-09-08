#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.utils.uvw_validator import UVWValidator, UVWValidationThresholds


def main() -> int:
    parser = argparse.ArgumentParser(description='Comprehensive UVW geometry validator for MS files')
    parser.add_argument('ms_path', help='Path to Measurement Set (directory)')
    parser.add_argument('--abs-delta', type=float, default=0.02, help='Max allowed absolute |Δuvw| in meters (default: 0.02)')
    parser.add_argument('--rms-delta', type=float, default=0.005, help='Max allowed RMS |Δuvw| in meters (default: 0.005)')
    parser.add_argument('--max-uvw', type=float, default=10000.0, help='Max allowed absolute UVW magnitude in meters (default: 10000)')
    parser.add_argument('--autos-imag-ratio', type=float, default=1e-12, help='Max allowed autos imag/real ratio (default: 1e-12)')
    parser.add_argument('--json', action='store_true', help='Output JSON report')

    args = parser.parse_args()

    thresholds = UVWValidationThresholds(
        max_abs_delta_m=args.abs_delta,
        max_rms_delta_m=args.rms_delta,
        max_uvw_abs_m=args.max_uvw,
        min_autos_imag_ratio=args.autos_imag_ratio,
    )

    validator = UVWValidator(thresholds)
    report = validator.validate_ms(args.ms_path)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print('=== UVW VALIDATION REPORT ===')
        print(f"MS: {args.ms_path}")
        print(f"Success: {report.success}")
        print('\n-- Checks --')
        for k, v in report.checks.items():
            print(f"{k}: {v}")
        if report.warnings:
            print('\n-- Warnings --')
            for w in report.warnings:
                print(f"- {w}")
        if report.errors:
            print('\n-- Errors --')
            for e in report.errors:
                print(f"- {e}")

    return 0 if report.success else 2


if __name__ == '__main__':
    raise SystemExit(main())


