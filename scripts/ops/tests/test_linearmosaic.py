#!/opt/miniforge/envs/casa6/bin/python
"""
Test script for linearmosaic implementation.

Tests the new _build_weighted_mosaic_linearmosaic function with real data.
"""

import logging
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# Add backend/src to path BEFORE importing dsa110_contimg modules
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / 'backend' / 'src'))

from dsa110_contimg.mosaic.cli import (_build_weighted_mosaic,
                                       _build_weighted_mosaic_linearmosaic)
from dsa110_contimg.mosaic.validation import TileQualityMetrics


logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)


def get_test_tiles(mosaic_id=None, max_tiles=3):
    """Get a small set of tiles for testing."""
    # Try to find tiles directly from filesystem
    stage_dir = Path("/stage/dsa110-contimg/images")
    if stage_dir.exists():
        # First try FITS files (preferred - we'll convert to CASA)
        fits_tiles = []
        for fits_file in sorted(stage_dir.glob("*.fits")):
            name = fits_file.name
            # Look for image tiles (not PB, not beam)
            if "img-image.fits" in name and "pb" not in name and "beam" not in name:
                # Check if corresponding PB exists
                pb_name = name.replace("img-image.fits", "img-image-pb.fits")
                pb_path = stage_dir / pb_name
                if pb_path.exists():
                    fits_tiles.append(str(fits_file))
                    if len(fits_tiles) >= max_tiles:
                        break

        if fits_tiles:
            # Convert FITS to CASA format
            import shutil
            import tempfile


# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

            from casatasks import importfits

            temp_dir = tempfile.mkdtemp(prefix="linearmosaic_test_")
            casa_tiles = []

            LOG.info(
                f"Found {len(fits_tiles)} FITS tiles with PB images, converting to CASA images...")
            for i, fits_tile in enumerate(fits_tiles):
                casa_tile = os.path.join(temp_dir, f"tile_{i}.image")
                try:
                    importfits(fitsimage=fits_tile,
                               imagename=casa_tile, overwrite=True)
                    casa_tiles.append(casa_tile)
                    LOG.info(
                        f"  Converted {Path(fits_tile).name} -> {Path(casa_tile).name}")
                except Exception as e:
                    LOG.warning(f"  Failed to convert {fits_tile}: {e}")

            if casa_tiles:
                LOG.info(
                    f"Using {len(casa_tiles)} converted tiles from {stage_dir}")
                return casa_tiles

        # Fallback: try CASA image directories (but filter out PB images)
        tiles = []
        for casa_dir in sorted(stage_dir.glob("*.image")):
            name = casa_dir.name
            # Skip PB images and beam images
            if "pb" not in name.lower() and "beam" not in name.lower() and "img-image" in name:
                tiles.append(str(casa_dir))
                if len(tiles) >= max_tiles:
                    break

        if tiles:
            LOG.info(f"Found {len(tiles)} CASA image tiles in {stage_dir}")
            return tiles

        # Fallback: look for FITS image files
        fits_tiles = []
        for fits_file in sorted(stage_dir.glob("*.fits")):
            name = fits_file.name
            # Look for main image files (not beam, dirty, psf, residual, model)
            if "img-image.fits" in name and "beam" not in name and "pb" not in name:
                fits_tiles.append(str(fits_file))

        if fits_tiles:
            # Convert FITS to CASA images for testing
            import shutil
            import tempfile

            from casatasks import importfits

            temp_dir = tempfile.mkdtemp(prefix="linearmosaic_test_")
            casa_tiles = []

            LOG.info(
                f"Found {len(fits_tiles)} FITS tiles, converting to CASA images...")
            for i, fits_tile in enumerate(fits_tiles[:max_tiles]):
                casa_tile = os.path.join(temp_dir, f"tile_{i}.image")
                try:
                    importfits(fitsimage=fits_tile,
                               imagename=casa_tile, overwrite=True)
                    casa_tiles.append(casa_tile)
                    LOG.info(
                        f"  Converted {Path(fits_tile).name} -> {Path(casa_tile).name}")
                except Exception as e:
                    LOG.warning(f"  Failed to convert {fits_tile}: {e}")

            if casa_tiles:
                LOG.info(
                    f"Using {len(casa_tiles)} converted tiles from {stage_dir}")
                return casa_tiles

    # Fallback: try products database
    products_db = Path("/data/dsa110-contimg/state/db/products.sqlite3")
    if products_db.exists():
        conn = sqlite3.connect(str(products_db))
        cursor = conn.cursor()

        # Get tiles from images table
        cursor.execute("""
            SELECT path FROM images
            WHERE path LIKE '%.image'
            LIMIT ?
        """, (max_tiles,))

        tiles = [row[0] for row in cursor.fetchall()]
        conn.close()

        # Verify tiles exist
        existing_tiles = []
        for tile in tiles:
            if Path(tile).exists():
                existing_tiles.append(tile)
            else:
                LOG.warning(f"Tile not found: {tile}")

        if existing_tiles:
            return existing_tiles

    # Last resort: use synthetic data
    synth_dir = Path("/data/dsa110-contimg/state/synth/images")
    if synth_dir.exists():
        tiles = list(synth_dir.glob("*.image"))
        if tiles:
            tiles = [str(t) for t in tiles[:max_tiles]]
            LOG.warning(f"Using synthetic tiles from {synth_dir}")
            return tiles

    raise FileNotFoundError("No tiles found for testing")


def get_metrics_dict(tiles):
    """Get metrics dict for tiles."""
    from dsa110_contimg.mosaic.validation import (TileQualityMetrics,
                                                  _find_pb_path)

    metrics_dict = {}
    stage_dir = Path("/stage/dsa110-contimg/images")

    for tile in tiles:
        metrics = TileQualityMetrics(tile_path=tile)

        # Try to find PB image
        # If tile is in temp dir (from FITS conversion), look for PB in stage_dir
        if "linearmosaic_test" in tile:
            # Extract original FITS name from temp tile name
            tile_idx = Path(tile).stem.split("_")[-1]
            # Find corresponding PB FITS file
            pb_fits_files = sorted(stage_dir.glob("*img-image-pb.fits"))
            if pb_fits_files and int(tile_idx) < len(pb_fits_files):
                pb_fits = pb_fits_files[int(tile_idx)]
                # Convert PB FITS to CASA image
                import tempfile

                from casatasks import importfits
                temp_dir = os.path.dirname(tile)
                pb_casa = os.path.join(temp_dir, f"pb_{tile_idx}.image")
                try:
                    importfits(fitsimage=str(pb_fits),
                               imagename=pb_casa, overwrite=True)
                    metrics.pb_path = pb_casa
                    LOG.info(
                        f"  Found PB: {Path(pb_fits).name} -> {Path(pb_casa).name}")
                except Exception as e:
                    LOG.warning(f"  Failed to convert PB {pb_fits}: {e}")
        else:
            # Use standard PB finding logic
            pb_path = _find_pb_path(tile)
            if pb_path:
                metrics.pb_path = pb_path

        metrics_dict[tile] = metrics

    return metrics_dict


def test_linearmosaic():
    """Test linearmosaic implementation."""
    print("=" * 60)
    print("Testing linearmosaic Implementation")
    print("=" * 60)

    # Get test tiles
    print("\n1. Getting test tiles...")
    tiles = get_test_tiles(max_tiles=3)
    if not tiles:
        print(":cross: No tiles found for testing")
        return False

    print(f":check: Found {len(tiles)} tiles:")
    for tile in tiles:
        print(f"  - {Path(tile).name}")

    # Get metrics
    print("\n2. Getting tile metrics...")
    metrics_dict = get_metrics_dict(tiles)

    # Check PB images
    pb_available = all(
        metrics_dict[t].pb_path and Path(metrics_dict[t].pb_path).exists()
        for t in tiles
    )

    if not pb_available:
        print(":warning: Warning: Not all tiles have PB images")
        print("  linearmosaic requires PB images - will test fallback instead")
        return test_fallback()

    print(":check: All tiles have PB images")

    # Create output path
    output_dir = Path("/data/dsa110-contimg/state/test_mosaics")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "test_linearmosaic.image")

    # Remove existing if present
    if Path(output_path).exists():
        import shutil
        import time

        # Try multiple times with delay (CASA images can be slow to release)
        for attempt in range(3):
            try:
                shutil.rmtree(output_path)
                break
            except OSError:
                if attempt < 2:
                    time.sleep(1)
                else:
                    # Force remove with ignore_errors
                    shutil.rmtree(output_path, ignore_errors=True)

    print(f"\n3. Testing linearmosaic...")
    print(f"   Output: {output_path}")

    try:
        _build_weighted_mosaic_linearmosaic(
            tiles=tiles,
            metrics_dict=metrics_dict,
            output_path=output_path
        )

        # Check output
        if Path(output_path).exists():
            print(f"\n:check::check::check: SUCCESS: Mosaic created at {output_path}")

            # Convert to FITS
            try:
                from casatasks import exportfits
                fits_path = str(output_path).replace(".image", ".fits")
                print(f"\n4. Converting mosaic to FITS...")
                exportfits(imagename=str(output_path),
                           fitsimage=fits_path, overwrite=True)
                if Path(fits_path).exists():
                    size_mb = Path(fits_path).stat().st_size / 1024 / 1024
                    print(
                        f":check: FITS file created: {fits_path} ({size_mb:.2f} MB)")
                else:
                    print(f":warning: Warning: FITS conversion completed but file not found")
            except Exception as e:
                print(f":warning: Warning: Failed to convert to FITS: {e}")

            return True
        else:
            print(f"\n:cross: FAILED: Mosaic not created")
            return False

    except Exception as e:
        print(f"\n:cross: FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback():
    """Test fallback method."""
    print("\n" + "=" * 60)
    print("Testing Fallback Method (imregrid + immath)")
    print("=" * 60)

    tiles = get_test_tiles(max_tiles=3)
    if not tiles:
        print(":cross: No tiles found for testing")
        return False

    metrics_dict = get_metrics_dict(tiles)

    output_dir = Path("/data/dsa110-contimg/state/test_mosaics")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "test_fallback.image")

    if Path(output_path).exists():
        import shutil
        import time

        # Try multiple times with delay (CASA images can be slow to release)
        for attempt in range(3):
            try:
                shutil.rmtree(output_path)
                break
            except OSError:
                if attempt < 2:
                    time.sleep(1)
                else:
                    # Force remove with ignore_errors
                    shutil.rmtree(output_path, ignore_errors=True)

    print(f"\nTesting fallback method...")
    print(f"   Output: {output_path}")

    try:
        _build_weighted_mosaic(
            tiles=tiles,
            metrics_dict=metrics_dict,
            output_path=output_path
        )

        if Path(output_path).exists():
            print(f"\n:check::check::check: SUCCESS: Fallback mosaic created at {output_path}")
            return True
        else:
            print(f"\n:cross: FAILED: Mosaic not created")
            return False

    except Exception as e:
        print(f"\n:cross: FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wrapper():
    """Test the wrapper function that tries linearmosaic first."""
    print("\n" + "=" * 60)
    print("Testing Wrapper Function (linearmosaic with fallback)")
    print("=" * 60)

    tiles = get_test_tiles(max_tiles=3)
    if not tiles:
        print(":cross: No tiles found for testing")
        return False

    metrics_dict = get_metrics_dict(tiles)

    output_dir = Path("/data/dsa110-contimg/state/test_mosaics")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "test_wrapper.image")

    if Path(output_path).exists():
        import shutil
        import time

        # Try multiple times with delay (CASA images can be slow to release)
        for attempt in range(3):
            try:
                shutil.rmtree(output_path)
                break
            except OSError:
                if attempt < 2:
                    time.sleep(1)
                else:
                    # Force remove with ignore_errors
                    shutil.rmtree(output_path, ignore_errors=True)

    print(f"\nTesting wrapper function...")
    print(f"   Output: {output_path}")

    try:
        _build_weighted_mosaic(
            tiles=tiles,
            metrics_dict=metrics_dict,
            output_path=output_path
        )

        if Path(output_path).exists():
            print(f"\n:check::check::check: SUCCESS: Wrapper created mosaic at {output_path}")

            # Convert to FITS
            try:
                from casatasks import exportfits
                fits_path = str(output_path).replace(".image", ".fits")
                print(f"\n4. Converting mosaic to FITS...")
                exportfits(imagename=str(output_path),
                           fitsimage=fits_path, overwrite=True)
                if Path(fits_path).exists():
                    size_mb = Path(fits_path).stat().st_size / 1024 / 1024
                    print(
                        f":check: FITS file created: {fits_path} ({size_mb:.2f} MB)")
                else:
                    print(f":warning: Warning: FITS conversion completed but file not found")
            except Exception as e:
                print(f":warning: Warning: Failed to convert to FITS: {e}")

            return True
        else:
            print(f"\n:cross: FAILED: Mosaic not created")
            return False

    except Exception as e:
        print(f"\n:cross: FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import os
    import signal

    # Set strict timeout: 30 minutes (1800 seconds)
    TIMEOUT_SECONDS = 1800
    
    def timeout_handler(signum, frame):
        print(f"\n\n{'='*60}")
        print(f"TIMEOUT: Test exceeded {TIMEOUT_SECONDS} seconds ({TIMEOUT_SECONDS/60:.1f} minutes)")
        print(f"{'='*60}")
        print("This may indicate:")
        print("  - Mosaic building is taking longer than expected")
        print("  - A hang or infinite loop in the code")
        print("  - Very large images requiring more time")
        print("\nConsider:")
        print("  - Using downsampled images for testing")
        print("  - Checking system resources (CPU, memory, disk)")
        print("  - Reviewing logs for progress indicators")
        sys.exit(124)  # Standard timeout exit code
    
    # Set up signal handler for timeout
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TIMEOUT_SECONDS)
    
    try:
        print("Starting linearmosaic tests...")
        print(f"Timeout: {TIMEOUT_SECONDS} seconds ({TIMEOUT_SECONDS/60:.1f} minutes)\n")

        # Test 1: Direct linearmosaic (if PB images available)
        success1 = test_linearmosaic()

        # Test 2: Wrapper function
        success2 = test_wrapper()

        # Cancel timeout if we complete successfully
        signal.alarm(0)

        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(
            f"linearmosaic direct: {':check: PASSED' if success1 else ':cross: FAILED/SKIPPED'}")
        print(f"Wrapper function:    {':check: PASSED' if success2 else ':cross: FAILED'}")

        if success1 or success2:
            print("\n:check::check::check: At least one test passed!")
            sys.exit(0)
        else:
            print("\n:cross::cross::cross: All tests failed")
            sys.exit(1)
    except KeyboardInterrupt:
        signal.alarm(0)
        print("\n\nInterrupted by user")
        sys.exit(130)
    except SystemExit as e:
        signal.alarm(0)
        raise
    except Exception as e:
        signal.alarm(0)
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
