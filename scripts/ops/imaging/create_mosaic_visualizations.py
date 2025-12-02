#!/opt/miniforge/envs/casa6/bin/python
"""
Create FITS and PNG visualizations for mosaic and individual tiles.

This script:
1. Converts mosaic CASA image to FITS
2. Creates PNG with WCS coordinates and zscale coloring for mosaic
3. Creates PNG with WCS coordinates and zscale coloring for each tile
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.visualization import ZScaleInterval
from astropy.wcs import WCS

# Add backend/src to path
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "backend" / "src"))

import os

from casatasks import exportfits


def create_png_with_wcs(fits_path, output_png, title=""):
    """Create PNG with WCS coordinates and zscale normalization."""
    print(f"  Creating PNG: {output_png}")
    
    hdul = fits.open(fits_path)
    
    # Find HDU with image data
    for hdu in hdul:
        if hdu.data is not None and len(hdu.data.shape) >= 2:
            data = hdu.data
            header = hdu.header
            
            # Handle multi-dimensional data
            if len(data.shape) == 4:
                data = data[0, 0, :, :]  # Take first stokes, first freq
            elif len(data.shape) == 3:
                data = data[0, :, :]  # Take first plane
            
            # Create WCS
            wcs = WCS(header)
            
            # Z-scale normalization
            zscale = ZScaleInterval()
            valid_data = data[~np.isnan(data)]
            if len(valid_data) > 0:
                vmin, vmax = zscale.get_limits(valid_data)
            else:
                vmin, vmax = np.nanmin(data), np.nanmax(data)
            
            # Create figure with WCS projection
            fig = plt.figure(figsize=(12, 12))
            ax = plt.subplot(projection=wcs)
            
            # Plot with zscale normalization
            im = ax.imshow(data, origin='lower', cmap='gray',
                          vmin=vmin, vmax=vmax, interpolation='nearest')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, label='Flux (Jy/beam)')
            
            # Add grid
            ax.coords.grid(True, color='white', ls='--', alpha=0.5)
            ax.coords[0].set_axislabel('Right Ascension')
            ax.coords[1].set_axislabel('Declination')
            
            if title:
                plt.title(title)
            else:
                plt.title(Path(fits_path).stem)
            
            plt.tight_layout()
            plt.savefig(str(output_png), dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"    :check: PNG created")
            break
    
    hdul.close()

def main():
    mosaic_path = "/stage/dsa110-contimg/tmp/mosaic_test"
    output_dir = Path("/stage/dsa110-contimg/tmp")
    
    # Check if CASA image exists
    casa_image = mosaic_path
    if os.path.exists(f"{mosaic_path}.image"):
        casa_image = f"{mosaic_path}.image"
    elif not os.path.exists(mosaic_path):
        print(f"ERROR: Mosaic not found at {mosaic_path}")
        print("Waiting for mosaic build to complete...")
        return 1
    
    # Convert CASA image to FITS
    fits_path = f"{mosaic_path}.fits"
    if not os.path.exists(fits_path):
        print(f"Converting CASA image to FITS: {fits_path}")
        try:
            exportfits(imagename=casa_image, fitsimage=fits_path, overwrite=True)
            print(f":check: FITS exported: {fits_path}")
        except Exception as e:
            print(f"ERROR: Failed to export FITS: {e}")
            return 1
    else:
        print(f":check: FITS already exists: {fits_path}")
    
    # Create PNG for mosaic
    mosaic_png = output_dir / "mosaic_test.png"
    print(f"\nCreating PNG for mosaic...")
    create_png_with_wcs(fits_path, mosaic_png, title="Mosaic (zscale)")
    
    # Get tile paths
    from dsa110_contimg.mosaic.cli import _fetch_tiles
    products_db = Path("/data/dsa110-contimg/state/db/products.sqlite3")
    all_tiles = _fetch_tiles(products_db, since=None, until=None, pbcor_only=True)
    stage_tiles = [t for t in all_tiles if t.startswith('/stage/')]
    test_tiles = stage_tiles[:3]
    
    # Create PNG for each tile
    print(f"\nCreating PNGs for {len(test_tiles)} tiles...")
    for i, tile_path in enumerate(test_tiles, 1):
        tile_name = Path(tile_path).stem
        tile_png = output_dir / f"{tile_name}.png"
        
        if not Path(tile_path).exists():
            print(f"  :cross: Tile {i} not found: {tile_path}")
            continue
        
        print(f"  Tile {i}: {tile_name}")
        create_png_with_wcs(tile_path, tile_png, title=f"Tile {i}: {tile_name} (zscale)")
    
    print(f"\n:check: All visualizations created in: {output_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())

