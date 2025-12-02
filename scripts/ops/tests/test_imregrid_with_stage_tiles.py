#!/opt/miniforge/envs/casa6/bin/python
"""
Test imregrid functionality using tiles from /stage/.

This script tests the mosaic building process using tiles from /stage/
to verify imregrid works correctly.
"""
import os
import sys
from pathlib import Path

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import sqlite3
import tempfile

from dsa110_contimg.mosaic.cli import (_build_weighted_mosaic_linearmosaic,
                                       _fetch_tiles)
from dsa110_contimg.mosaic.validation import TileQualityMetrics


def test_imregrid_with_stage_tiles():
    """Test imregrid using tiles from /stage/."""
    products_db = Path("/data/dsa110-contimg/state/db/products.sqlite3")
    
    if not products_db.exists():
        print(f"ERROR: Products database not found: {products_db}")
        return 1
    
    # Fetch tiles from /stage/ specifically
    print("Fetching tiles from /stage/...")
    all_tiles = _fetch_tiles(products_db, since=None, until=None, pbcor_only=True)
    
    # Filter to only /stage/ tiles
    stage_tiles = [t for t in all_tiles if t.startswith('/stage/')]
    
    if not stage_tiles:
        print("ERROR: No tiles found in /stage/")
        print(f"Total tiles found: {len(all_tiles)}")
        if all_tiles:
            print("Sample paths:")
            for t in all_tiles[:5]:
                print(f"  {t}")
        return 1
    
    print(f"Found {len(stage_tiles)} tiles in /stage/")
    print(f"First tile (will be template): {Path(stage_tiles[0]).name}")
    print()
    
    # Verify tiles exist
    missing = [t for t in stage_tiles if not os.path.exists(t)]
    if missing:
        print(f"WARNING: {len(missing)} tiles don't exist:")
        for t in missing[:5]:
            print(f"  {t}")
        stage_tiles = [t for t in stage_tiles if os.path.exists(t)]
        print(f"Proceeding with {len(stage_tiles)} existing tiles")
    
    if not stage_tiles:
        print("ERROR: No existing tiles found")
        return 1
    
    # Create metrics dict
    metrics_dict = {t: TileQualityMetrics(tile_path=t) for t in stage_tiles}
    
    # Test with a small subset first
    test_tiles = stage_tiles[:3]  # Use first 3 tiles for testing
    print(f"\nTesting with {len(test_tiles)} tiles:")
    for i, t in enumerate(test_tiles):
        print(f"  {i+1}. {Path(t).name}")
    
    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = os.path.join(temp_dir, "test_mosaic")
        
        try:
            print(f"\nBuilding mosaic to: {output_path}")
            print("This will test imregrid functionality...")
            
            _build_weighted_mosaic_linearmosaic(
                tiles=test_tiles,
                metrics_dict={t: metrics_dict[t] for t in test_tiles},
                output_path=output_path
            )
            
            print("\nSUCCESS: Mosaic built successfully!")
            print(f"Output: {output_path}")
            return 0
            
        except Exception as e:
            print(f"\nERROR: Mosaic building failed: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(test_imregrid_with_stage_tiles())

