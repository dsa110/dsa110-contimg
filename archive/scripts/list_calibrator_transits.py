#!/usr/bin/env python3
"""
List all available transits for a calibrator that have data in /data/incoming.

Example:
    python scripts/list_calibrator_transits.py --name 0834+555
    python scripts/list_calibrator_transits.py --name 0834+555 --max-days-back 60
"""
import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.conversion.calibrator_ms_service import CalibratorMSGenerator
from dsa110_contimg.conversion.config import CalibratorMSConfig


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List all available transits for a calibrator with data in /data/incoming"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Calibrator name (e.g., '0834+555')"
    )
    parser.add_argument(
        "--input-dir",
        default="/data/incoming",
        type=Path,
        help="Input directory to search (default: /data/incoming)"
    )
    parser.add_argument(
        "--max-days-back",
        type=int,
        default=30,
        help="Maximum days to search back (default: 30)"
    )
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=60,
        help="Search window around each transit in minutes (default: 60)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Use custom config file (default: use environment variables)"
    )
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        # TODO: Support config file loading
        config = CalibratorMSConfig.from_env()
    else:
        config = CalibratorMSConfig.from_env()
    
    # Override input directory if specified
    if args.input_dir != Path("/data/incoming"):
        config.input_dir = args.input_dir
    
    # Create service
    service = CalibratorMSGenerator.from_config(config)
    
    # List available transits
    try:
        transits = service.list_available_transits(
            args.name,
            max_days_back=args.max_days_back,
            window_minutes=args.window_minutes
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    if not transits:
        print(f"No transits found for {args.name} in the last {args.max_days_back} days", file=sys.stderr)
        return 1
    
    if args.json:
        # Convert Path objects to strings for JSON serialization
        output = []
        for t in transits:
            t_copy = t.copy()
            # Convert any Path objects to strings
            for key, value in t_copy.items():
                if isinstance(value, Path):
                    t_copy[key] = str(value)
            output.append(t_copy)
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output
        print(f"\nFound {len(transits)} available transit(s) for {args.name}:\n")
        for i, t in enumerate(transits, 1):
            print(f"{i}. Transit: {t['transit_iso']}")
            print(f"   Group ID: {t['group_id']}")
            print(f"   Group mid: {t['group_mid_iso']}")
            print(f"   Δ from transit: {t['delta_minutes']:.1f} minutes")
            print(f"   Subbands: {t['subband_count']}")
            print(f"   Days ago: {t['days_ago']:.1f}")
            print(f"   Has MS: {'✓' if t['has_ms'] else '✗'}")
            print()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

