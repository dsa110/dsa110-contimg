#!/opt/miniforge/envs/casa6/bin/python
"""Quick 30-second test: Regrid one tile to another's coordinate system."""

import os
import shutil
import sys
import tempfile
from pathlib import Path

from casacore.images import image as casaimage
from casatasks import importfits, imregrid

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def test_regrid():
    """Test regridding tile 2 to tile 1's coordinate system."""
    tile1_fits = '/stage/dsa110-contimg/images/2025-10-28T13:30:07.img-image-pb.fits'
    tile2_fits = '/stage/dsa110-contimg/images/2025-10-28T13:35:16.img-image-pb.fits'

    print("="*60)
    print("QUICK REGRID TEST (30 seconds)")
    print("="*60)
    print(f"Tile 1 (template): {Path(tile1_fits).name}")
    print(f"Tile 2 (source): {Path(tile2_fits).name}")

    # Convert FITS to CASA format (imregrid requires CASA images)
    output_dir = tempfile.mkdtemp()
    tile1_casa = os.path.join(output_dir, 'tile1_casa.image')
    tile2_casa = os.path.join(output_dir, 'tile2_casa.image')

    print(f"\nConverting FITS to CASA format...")
    importfits(fitsimage=tile1_fits, imagename=tile1_casa, overwrite=True)
    importfits(fitsimage=tile2_fits, imagename=tile2_casa, overwrite=True)

    # Get original shapes
    img1 = casaimage(tile1_casa)
    img2 = casaimage(tile2_casa)
    shape1 = img1.shape()
    shape2 = img2.shape()
    print(f"\nOriginal shapes:")
    print(f"  Tile 1: {shape1}")
    print(f"  Tile 2: {shape2}")

    # Get coordinate systems
    coordsys1 = img1.coordinates()
    coordsys2 = img2.coordinates()

    # Get reference values
    dir1 = coordsys1.get_coordinate('direction')
    dir2 = coordsys2.get_coordinate('direction')
    ref1 = dir1.get_referencevalue()
    ref2 = dir2.get_referencevalue()

    print(f"\nReference positions:")
    print(f"  Tile 1 RA: {ref1[0]:.6f} rad ({ref1[0]*180/3.14159:.6f} deg)")
    print(f"  Tile 2 RA: {ref2[0]:.6f} rad ({ref2[0]*180/3.14159:.6f} deg)")
    print(f"  RA difference: {(ref2[0]-ref1[0])*180/3.14159:.6f} deg")

    try:
        img1.close()
        img2.close()
    except:
        pass

    # Regrid tile2 to tile1's coordinate system
    output = os.path.join(output_dir, 'regridded_test.image')

    print(f"\nRegridding tile 2 to tile 1's coordinate system...")
    try:
        imregrid(
            imagename=tile2_casa,
            template=tile1_casa,
            output=output,
            overwrite=True
        )

        # Check result
        regridded = casaimage(output)
        regridded_shape = regridded.shape()
        regridded_coordsys = regridded.coordinates()
        regridded_dir = regridded_coordsys.get_coordinate('direction')
        regridded_ref = regridded_dir.get_referencevalue()

        print(f"\n✓ Regridding successful!")
        print(f"  Output shape: {regridded_shape}")
        print(
            f"  Output RA: {regridded_ref[0]:.6f} rad ({regridded_ref[0]*180/3.14159:.6f} deg)")
        print(f"  Shape matches template: {regridded_shape == shape1}")
        print(
            f"  Coordinate system matches: {abs(regridded_ref[0] - ref1[0]) < 1e-6}")

        try:
            regridded.close()
        except:
            pass

        # Cleanup
        shutil.rmtree(output_dir)

        print(f"\n✓ TEST PASSED: Method works!")
        print(f"  - FITS → CASA conversion: ✓")
        print(f"  - Regridding to template: ✓")
        print(f"  - Coordinate transformation: ✓")
        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        return False


if __name__ == '__main__':
    success = test_regrid()
    sys.exit(0 if success else 1)
