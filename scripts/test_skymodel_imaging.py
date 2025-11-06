#!/usr/bin/env python3
"""
Test sky model image generation (FITS and PNG).

This script tests creating images from sky models for visualization.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyradiosky import SkyModel
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np
from dsa110_contimg.calibration.skymodel_image import (
    write_skymodel_images,
    write_skymodel_fits,
    write_skymodel_png,
)
import tempfile
import os

def test_single_source():
    """Test imaging a single point source."""
    print("=" * 60)
    print("Test 1: Single Point Source")
    print("=" * 60)
    
    stokes = np.zeros((4, 1, 1)) * u.Jy
    stokes[0, 0, 0] = 2.3 * u.Jy
    
    sky = SkyModel(
        name=["test_source"],
        skycoord=SkyCoord(ra=165.0*u.deg, dec=55.5*u.deg, frame='icrs'),
        stokes=stokes,
        spectral_type='flat',
        component_type='point',
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, "single_source")
        
        try:
            fits_path, png_path = write_skymodel_images(
                sky,
                base_path,
                image_size=(256, 256),
                pixel_scale_arcsec=20.0,
                beam_fwhm_arcsec=60.0,  # Convolve with 1 arcmin beam
            )
            
            print(f"✓ FITS created: {fits_path} ({os.path.getsize(fits_path)} bytes)")
            print(f"✓ PNG created: {png_path} ({os.path.getsize(png_path)} bytes)")
            return True
        except Exception as e:
            print(f"✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_multiple_sources():
    """Test imaging multiple sources."""
    print("\n" + "=" * 60)
    print("Test 2: Multiple Point Sources")
    print("=" * 60)
    
    # Create 5 sources in a small region
    center_ra = 165.0
    center_dec = 55.5
    n_sources = 5
    
    ra_offsets = np.linspace(-0.05, 0.05, n_sources)  # degrees
    dec_offsets = np.linspace(-0.05, 0.05, n_sources)
    
    ra_values = center_ra + ra_offsets
    dec_values = center_dec + dec_offsets
    flux_values = np.linspace(2.0, 0.5, n_sources)  # Jy, decreasing
    
    ra = ra_values * u.deg
    dec = dec_values * u.deg
    stokes = np.zeros((4, 1, n_sources)) * u.Jy
    stokes[0, 0, :] = flux_values * u.Jy  # I flux
    
    skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
    
    sky = SkyModel(
        name=[f"source_{i}" for i in range(n_sources)],
        skycoord=skycoord,
        stokes=stokes,
        spectral_type='flat',
        component_type='point',
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = os.path.join(tmpdir, "multi_source")
        
        try:
            fits_path, png_path = write_skymodel_images(
                sky,
                base_path,
                image_size=(512, 512),
                pixel_scale_arcsec=10.0,
                center_ra_deg=center_ra,
                center_dec_deg=center_dec,
                beam_fwhm_arcsec=30.0,  # 30 arcsec beam
            )
            
            print(f"✓ FITS created: {fits_path} ({os.path.getsize(fits_path)} bytes)")
            print(f"✓ PNG created: {png_path} ({os.path.getsize(png_path)} bytes)")
            print(f"  Sources: {n_sources}")
            return True
        except Exception as e:
            print(f"✗ Failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_with_nvss_region():
    """Test imaging a region with NVSS sources."""
    print("\n" + "=" * 60)
    print("Test 3: NVSS Region (if catalog available)")
    print("=" * 60)
    
    try:
        from dsa110_contimg.calibration.catalogs import read_nvss_catalog
        from astropy.coordinates import SkyCoord
        import astropy.units as u
        import numpy as np
        
        center_ra = 165.0
        center_dec = 55.5
        radius_deg = 0.2
        
        df = read_nvss_catalog()
        sc_all = SkyCoord(df["ra"].to_numpy() * u.deg, df["dec"].to_numpy() * u.deg, frame="icrs")
        ctr = SkyCoord(center_ra * u.deg, center_dec * u.deg, frame="icrs")
        sep = sc_all.separation(ctr).deg
        flux_mjy = np.asarray(df["flux_20_cm"].to_numpy(), float)
        keep = (sep <= radius_deg) & (flux_mjy >= 10.0)  # >10 mJy
        
        if keep.sum() == 0:
            print("  ⚠ No NVSS sources found in region")
            return False
        
        # Create sky model from NVSS sources
        ras = df.loc[keep, "ra"].to_numpy()
        decs = df.loc[keep, "dec"].to_numpy()
        fluxes = flux_mjy[keep] / 1000.0  # Convert to Jy
        
        ra = ras * u.deg
        dec = decs * u.deg
        stokes = np.zeros((4, 1, len(ras))) * u.Jy
        stokes[0, 0, :] = fluxes
        
        skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
        
        sky = SkyModel(
            name=[f"nvss_{i}" for i in range(len(ras))],
            skycoord=skycoord,
            stokes=stokes,
            spectral_type='flat',
            component_type='point',
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = os.path.join(tmpdir, "nvss_region")
            
            fits_path, png_path = write_skymodel_images(
                sky,
                base_path,
                image_size=(1024, 1024),
                pixel_scale_arcsec=5.0,
                center_ra_deg=center_ra,
                center_dec_deg=center_dec,
                beam_fwhm_arcsec=45.0,  # 45 arcsec beam
            )
            
            print(f"✓ FITS created: {fits_path} ({os.path.getsize(fits_path)} bytes)")
            print(f"✓ PNG created: {png_path} ({os.path.getsize(png_path)} bytes)")
            print(f"  Sources: {len(ras)}")
            return True
    except Exception as e:
        print(f"  ⚠ NVSS test skipped: {e}")
        return False


def main():
    """Run all imaging tests."""
    print("=" * 60)
    print("Sky Model Image Generation Test")
    print("=" * 60)
    print()
    
    results = {}
    
    results['single'] = test_single_source()
    results['multiple'] = test_multiple_sources()
    results['nvss'] = test_with_nvss_region()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Single source: {'✓' if results['single'] else '✗'}")
    print(f"Multiple sources: {'✓' if results['multiple'] else '✗'}")
    print(f"NVSS region: {'✓' if results['nvss'] else '⚠'}")
    
    if results['single'] and results['multiple']:
        print("\n✓ Sky model imaging is working!")
        print("  You can now generate FITS and PNG images from sky models")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

