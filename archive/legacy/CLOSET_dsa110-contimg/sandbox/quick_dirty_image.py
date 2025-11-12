#!/usr/bin/env python3
"""
Create a quick dirty image (no deconvolution) from an MS.
This is useful for quickly checking if sources are present in the data.
"""

import sys
import os
from casatasks import tclean
from casatools import image

def make_dirty_image(ms_path, output_dir, imsize=512, cell='5arcsec'):
    """
    Create a dirty image (niter=0) from an MS.
    
    Args:
        ms_path: Path to Measurement Set
        output_dir: Output directory for image products
        imsize: Image size in pixels
        cell: Cell size (pixel scale)
    """
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    imagename = os.path.join(output_dir, 'dirty_image')
    
    print("=" * 70)
    print("Creating Dirty Image")
    print("=" * 70)
    print(f"MS: {ms_path}")
    print(f"Output: {imagename}")
    print(f"Image size: {imsize} x {imsize} pixels")
    print(f"Cell size: {cell}")
    print()
    
    # Run tclean with niter=0 to create dirty image
    print("Running tclean (niter=0 for dirty image)...")
    tclean(
        vis=ms_path,
        imagename=imagename,
        imsize=imsize,
        cell=cell,
        stokes='I',
        weighting='briggs',
        robust=0.5,
        niter=0,  # No deconvolution - just dirty image
        gridder='standard',
        deconvolver='hogbom',
        specmode='mfs',  # Multi-frequency synthesis
        nterms=1,
        savemodel='none'
    )
    
    print("\n✓ Dirty image created")
    
    # Get image statistics
    print("\n" + "=" * 70)
    print("Image Statistics")
    print("=" * 70)
    
    ia = image()
    ia.open(imagename + '.image')
    
    stats = ia.statistics()
    
    print(f"Min:  {stats['min'][0]:.6f} Jy/beam")
    print(f"Max:  {stats['max'][0]:.6f} Jy/beam")
    print(f"Mean: {stats['mean'][0]:.6f} Jy/beam")
    print(f"RMS:  {stats['rms'][0]:.6f} Jy/beam")
    
    if stats['rms'][0] > 0:
        dynamic_range = abs(stats['max'][0] / stats['rms'][0])
        print(f"Peak/RMS: {dynamic_range:.1f}")
    
    # Find peak location
    maxpos = ia.coordsys().toworld(stats['maxpos'])['numeric']
    print(f"\nPeak location:")
    print(f"   RA:  {maxpos[0] * 180/3.14159:.4f}°")
    print(f"   Dec: {maxpos[1] * 180/3.14159:.4f}°")
    
    ia.close()
    
    # Export to FITS
    fits_file = imagename + '.fits'
    print(f"\nExporting to FITS: {fits_file}")
    ia.open(imagename + '.image')
    ia.tofits(fits_file, overwrite=True)
    ia.close()
    
    print("\n" + "=" * 70)
    print("✓ Dirty image complete!")
    print("=" * 70)
    print(f"\nOutput files:")
    print(f"   CASA image: {imagename}.image")
    print(f"   FITS file:  {fits_file}")
    print()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python quick_dirty_image.py <ms> <output_dir> [imsize] [cell]")
        sys.exit(1)
    
    ms_path = sys.argv[1]
    output_dir = sys.argv[2]
    imsize = int(sys.argv[3]) if len(sys.argv) > 3 else 512
    cell = sys.argv[4] if len(sys.argv) > 4 else '5arcsec'
    
    make_dirty_image(ms_path, output_dir, imsize, cell)
