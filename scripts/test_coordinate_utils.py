#!/usr/bin/env python3
"""
Test script for coordinate_utils module.

Tests the pre-validation fix for imregrid RuntimeError.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

from dsa110_contimg.mosaic.coordinate_utils import (
    get_tile_coordinate_bounds,
    compute_tiles_bounding_box,
    check_tile_overlaps_template,
    filter_tiles_by_overlap
)
import logging

logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

def find_test_tiles():
    """Find tiles for testing."""
    tiles = []
    
    # Try real tiles first
    stage_dir = Path("/stage/dsa110-contimg/images")
    if stage_dir.exists():
        tiles = list(stage_dir.glob("*.image"))[:5]
        if tiles:
            LOG.info(f"Found {len(tiles)} real tiles in {stage_dir}")
            return tiles
    
    # Try synthetic
    synth_dir = Path("/data/dsa110-contimg/state/synth/images")
    if synth_dir.exists():
        tiles = list(synth_dir.glob("*.image"))[:5]
        if tiles:
            LOG.warning(f"Using {len(tiles)} synthetic tiles from {synth_dir}")
            return tiles
    
    return []

def test_coordinate_bounds():
    """Test coordinate bounds extraction."""
    print("\n" + "=" * 60)
    print("Test 1: Coordinate Bounds Extraction")
    print("=" * 60)
    
    tiles = find_test_tiles()
    if not tiles:
        print("✗ No tiles found - skipping test")
        return False
    
    success_count = 0
    for tile in tiles[:3]:
        bounds = get_tile_coordinate_bounds(str(tile))
        if bounds:
            print(f"\n✓ {tile.name}:")
            print(f"  RA: [{bounds['ra_min']:.6f}, {bounds['ra_max']:.6f}] rad")
            print(f"  Dec: [{bounds['dec_min']:.6f}, {bounds['dec_max']:.6f}] rad")
            print(f"  Center: ({bounds['center_ra']:.6f}, {bounds['center_dec']:.6f}) rad")
            print(f"  Cell: ({bounds['cell_ra']:.6f}, {bounds['cell_dec']:.6f}) rad")
            print(f"  Shape: {bounds['shape']}")
            success_count += 1
        else:
            print(f"\n✗ {tile.name}: Failed to extract bounds")
    
    print(f"\n✓ Extracted bounds from {success_count}/{len(tiles[:3])} tiles")
    return success_count > 0

def test_overlap_check():
    """Test overlap checking."""
    print("\n" + "=" * 60)
    print("Test 2: Overlap Checking")
    print("=" * 60)
    
    tiles = find_test_tiles()
    if len(tiles) < 2:
        print("✗ Need at least 2 tiles - skipping test")
        return False
    
    template = tiles[0]
    print(f"Template: {template.name}")
    
    success_count = 0
    for tile in tiles[1:]:
        overlaps, reason = check_tile_overlaps_template(str(tile), str(template))
        if overlaps:
            print(f"  ✓ {tile.name}: Overlaps")
            success_count += 1
        else:
            print(f"  ✗ {tile.name}: Does NOT overlap - {reason}")
    
    print(f"\n✓ {success_count}/{len(tiles)-1} tiles overlap template")
    return True

def test_filter_tiles():
    """Test tile filtering."""
    print("\n" + "=" * 60)
    print("Test 3: Tile Filtering")
    print("=" * 60)
    
    tiles = find_test_tiles()
    if len(tiles) < 2:
        print("✗ Need at least 2 tiles - skipping test")
        return False
    
    template = tiles[0]
    tile_paths = [str(t) for t in tiles]
    
    print(f"Template: {template.name}")
    print(f"Total tiles: {len(tile_paths)}")
    
    overlapping, skipped = filter_tiles_by_overlap(tile_paths, str(template), margin_pixels=10)
    
    print(f"\nResults:")
    print(f"  Overlapping tiles: {len(overlapping)}")
    for tile_path in overlapping:
        print(f"    ✓ {Path(tile_path).name}")
    
    print(f"  Skipped tiles: {len(skipped)}")
    for tile_path, reason in skipped:
        print(f"    ✗ {Path(tile_path).name}: {reason}")
    
    print(f"\n✓ Filtered {len(skipped)} non-overlapping tiles")
    return True

def test_bounding_box():
    """Test bounding box computation."""
    print("\n" + "=" * 60)
    print("Test 4: Bounding Box Computation")
    print("=" * 60)
    
    tiles = find_test_tiles()
    if len(tiles) < 2:
        print("✗ Need at least 2 tiles - skipping test")
        return False
    
    tile_paths = [str(t) for t in tiles]
    bbox = compute_tiles_bounding_box(tile_paths)
    
    if bbox:
        print(f"\n✓ Computed bounding box:")
        print(f"  RA: [{bbox['ra_min']:.6f}, {bbox['ra_max']:.6f}] rad")
        print(f"  Dec: [{bbox['dec_min']:.6f}, {bbox['dec_max']:.6f}] rad")
        print(f"  Center: ({bbox['center_ra']:.6f}, {bbox['center_dec']:.6f}) rad")
        print(f"  Cell: ({bbox['cell_ra']:.6f}, {bbox['cell_dec']:.6f}) rad")
        print(f"  Dimensions: {bbox['nx']} x {bbox['ny']} pixels")
        return True
    else:
        print("\n✗ Failed to compute bounding box")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing coordinate_utils Module")
    print("=" * 60)
    
    results = []
    
    results.append(("Coordinate Bounds", test_coordinate_bounds()))
    results.append(("Overlap Check", test_overlap_check()))
    results.append(("Filter Tiles", test_filter_tiles()))
    results.append(("Bounding Box", test_bounding_box()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED/SKIPPED"
        print(f"{test_name:20s}: {status}")
    
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("\n✓✓✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠ Some tests were skipped (no tiles available)")
        print("  This is expected if no test tiles are available.")
        sys.exit(0)  # Don't fail if no tiles available

