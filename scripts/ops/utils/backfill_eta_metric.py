#!/opt/miniforge/envs/casa6/bin/python
"""
Backfill eta_metric column in variability_stats table.

This script calculates and populates the η metric (weighted variance) for all
sources in the variability_stats table that have photometry measurements.

Usage:
    python scripts/backfill_eta_metric.py [--db-path PATH] [--dry-run] [--verbose]
"""
import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.photometry.variability import calculate_eta_metric


def backfill_eta_metric(
    db_path: Path,
    dry_run: bool = False,
    verbose: bool = True
) -> int:
    """
    Backfill eta_metric for all sources in variability_stats table.
    
    Args:
        db_path: Path to products database
        dry_run: If True, only show what would be updated without making changes
        verbose: Print progress messages
    
    Returns:
        Number of sources updated
    """
    if not db_path.exists():
        print(f"Error: Database not found: {db_path}")
        return 0
    
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check if tables exist
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        
        if 'variability_stats' not in tables:
            print("Error: variability_stats table not found")
            return 0
        
        # Check if eta_metric column exists
        columns = {
            row[1] for row in conn.execute(
                "PRAGMA table_info(variability_stats)"
            ).fetchall()
        }
        
        if 'eta_metric' not in columns:
            print("Error: eta_metric column not found. Run schema evolution first.")
            print("  python -m dsa110_contimg.database.schema_evolution")
            return 0
        
        # Get all sources from variability_stats
        sources = conn.execute(
            "SELECT source_id FROM variability_stats"
        ).fetchall()
        
        if not sources:
            print("No sources found in variability_stats table")
            return 0
        
        if verbose:
            print(f"Found {len(sources)} sources to process")
        
        updated_count = 0
        skipped_count = 0
        
        # Process each source
        for source_row in sources:
            source_id = source_row['source_id']
            
            # Get photometry measurements for this source
            # Try photometry_timeseries first
            if 'photometry_timeseries' in tables:
                query = """
                    SELECT normalized_flux_jy, normalized_flux_err_jy
                    FROM photometry_timeseries
                    WHERE source_id = ?
                    ORDER BY mjd ASC
                """
                df = pd.read_sql_query(query, conn, params=(source_id,))
                
                if df.empty or len(df) < 2:
                    skipped_count += 1
                    if verbose and skipped_count <= 5:
                        print(f"  Skipping {source_id}: insufficient measurements")
                    continue
                
                # Calculate eta metric
                try:
                    eta = calculate_eta_metric(
                        df,
                        flux_col='normalized_flux_jy',
                        err_col='normalized_flux_err_jy'
                    )
                except Exception as e:
                    if verbose:
                        print(f"  Error calculating η for {source_id}: {e}")
                    skipped_count += 1
                    continue
            
            # Fallback to photometry table
            elif 'photometry' in tables:
                query = """
                    SELECT peak_jyb as normalized_flux_jy, peak_err_jyb as normalized_flux_err_jy
                    FROM photometry
                    WHERE source_id = ?
                    ORDER BY mjd ASC
                """
                df = pd.read_sql_query(query, conn, params=(source_id,))
                
                if df.empty or len(df) < 2:
                    skipped_count += 1
                    continue
                
                try:
                    eta = calculate_eta_metric(
                        df,
                        flux_col='normalized_flux_jy',
                        err_col='normalized_flux_err_jy'
                    )
                except Exception as e:
                    if verbose:
                        print(f"  Error calculating η for {source_id}: {e}")
                    skipped_count += 1
                    continue
            else:
                skipped_count += 1
                continue
            
            # Update variability_stats
            if not dry_run:
                conn.execute(
                    "UPDATE variability_stats SET eta_metric = ? WHERE source_id = ?",
                    (eta, source_id)
                )
            
            updated_count += 1
            
            if verbose and updated_count % 100 == 0:
                print(f"  Processed {updated_count} sources...")
        
        if not dry_run:
            conn.commit()
        
        if verbose:
            print(f"\nSummary:")
            print(f"  Updated: {updated_count}")
            print(f"  Skipped: {skipped_count}")
            if dry_run:
                print(f"  (DRY RUN - no changes made)")
        
        return updated_count
        
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        return 0
    finally:
        conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backfill eta_metric column in variability_stats table"
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Path("/data/dsa110-contimg/state/db/products.sqlite3"),
        help="Path to products database"
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        default=True,
        help="Print progress messages"
    )
    
    args = parser.parse_args()
    
    updated = backfill_eta_metric(
        db_path=args.db_path,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    sys.exit(0 if updated > 0 else 1)


if __name__ == "__main__":
    main()

