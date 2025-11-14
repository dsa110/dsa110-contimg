#!/usr/bin/env python3
"""CLI tool for recommending reference antennas for DSA-110 calibration.

This script provides intelligent reference antenna selection for CASA
calibration tasks, with emphasis on using healthy outrigger antennas.

Examples:
    # Get default outrigger chain
    python recommend_refant.py
    
    # Optimize based on previous calibration table
    python recommend_refant.py --caltable /path/to/previous.bcal
    
    # Get detailed analysis
    python recommend_refant.py --caltable /path/to/cal.bcal --verbose
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dsa110_contimg.calibration.refant_selection import (
    get_default_outrigger_refants,
    recommend_refants_from_ms,
    recommend_outrigger_refants,
    analyze_antenna_health_from_caltable,
)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Recommend reference antennas for DSA-110 calibration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--caltable',
        type=str,
        help='Path to calibration table for health analysis (optional)'
    )
    
    parser.add_argument(
        '--ms',
        type=str,
        help='Path to Measurement Set (currently unused, reserved for future)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Print detailed antenna health analysis'
    )
    
    parser.add_argument(
        '--default-only',
        action='store_true',
        help='Only print default chain (ignore caltable if provided)'
    )
    
    parser.add_argument(
        '--format',
        choices=['casa', 'list', 'json'],
        default='casa',
        help='Output format (default: casa comma-separated string)'
    )
    
    args = parser.parse_args()
    
    # Default-only mode
    if args.default_only:
        refant_string = get_default_outrigger_refants()
        if args.format == 'casa':
            print(refant_string)
        elif args.format == 'list':
            print(' '.join(refant_string.split(',')))
        elif args.format == 'json':
            import json
            print(json.dumps(refant_string.split(',')))
        return 0
    
    # With analysis
    if args.caltable:
        try:
            # Analyze antenna health
            antenna_stats = analyze_antenna_health_from_caltable(args.caltable)
            
            # Get recommendations
            recs = recommend_outrigger_refants(antenna_stats)
            
            if args.verbose:
                print("=" * 60)
                print("DSA-110 Outrigger Reference Antenna Recommendations")
                print("=" * 60)
                print(f"\nCalibration table: {args.caltable}")
                print(f"\nOutrigger antennas: {recs['outrigger_antennas']}")
                print(f"\nDefault priority: {recs['default_refant_list']}")
                
                if 'healthy_outriggers' in recs:
                    print("\nHealthy outrigger antennas (<50% flagged):")
                    for ant in recs['healthy_outriggers']:
                        status = ant['health_status']
                        ant_id = ant['antenna_id']
                        frac = ant['flagged_fraction'] * 100
                        print(f"  {ant_id}: {frac:5.1f}% flagged ({status})")
                
                if 'problematic_outriggers' in recs:
                    print("\nProblematic outrigger antennas (>80% flagged):")
                    for ant in recs['problematic_outriggers']:
                        ant_id = ant['antenna_id']
                        frac = ant['flagged_fraction'] * 100
                        print(f"  {ant_id}: {frac:5.1f}% flagged")
                
                print(f"\n{recs.get('note', '')}")
                
                if 'recommended_refant_string' in recs:
                    rec_str = recs['recommended_refant_string']
                    print(f"\nRecommended refant chain: {rec_str}")
                else:
                    def_str = recs['default_refant_string']
                    print(f"\nDefault refant chain: {def_str}")
                
                print("\nUsage in CASA:")
                refant = recs.get(
                    'recommended_refant_string',
                    recs['default_refant_string']
                )
                print(f"  bandpass(vis='obs.ms', refant='{refant}', ...)")
                print("=" * 60)
            else:
                # Non-verbose: just print the refant string
                refant = recs.get(
                    'recommended_refant_string',
                    recs['default_refant_string']
                )
                
                if args.format == 'casa':
                    print(refant)
                elif args.format == 'list':
                    print(' '.join(refant.split(',')))
                elif args.format == 'json':
                    import json
                    print(json.dumps(refant.split(',')))
            
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except ImportError as e:
            print(
                f"Error: {e}\n"
                "casacore.tables is required for caltable analysis.",
                file=sys.stderr
            )
            return 1
        except Exception as e:
            print(f"Error analyzing caltable: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        # No caltable - use defaults
        refant_string = get_default_outrigger_refants()
        
        if args.verbose:
            print("=" * 60)
            print("DSA-110 Default Outrigger Reference Antenna Chain")
            print("=" * 60)
            print("\nNo calibration table provided - using default priority")
            print(f"\nDefault refant chain: {refant_string}")
            print("\nUsage in CASA:")
            print(f"  bandpass(vis='obs.ms', refant='{refant_string}', ...)")
            print("\nNote: Provide --caltable to optimize based on antenna health")
            print("=" * 60)
        else:
            if args.format == 'casa':
                print(refant_string)
            elif args.format == 'list':
                print(' '.join(refant_string.split(',')))
            elif args.format == 'json':
                import json
                print(json.dumps(refant_string.split(',')))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
