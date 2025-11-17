#!/opt/miniforge/envs/casa6/bin/python
"""
Generate FITS and PNG images from a sky model.

Usage:
    python generate_skymodel_image.py --sky-model sky.skyh5 --output skymodel
    python generate_skymodel_image.py --nvss --center-ra 165.0 --center-dec 55.5 --output nvss_region
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pyradiosky import SkyModel

from dsa110_contimg.calibration.skymodel_image import write_skymodel_images


def main():
    parser = argparse.ArgumentParser(description="Generate FITS and PNG images from sky model")
    parser.add_argument('--sky-model', type=str, help='Path to sky model file (skyh5, vot, etc.)')
    parser.add_argument('--nvss', action='store_true', help='Use NVSS catalog')
    parser.add_argument('--center-ra', type=float, help='Center RA in degrees (for NVSS)')
    parser.add_argument('--center-dec', type=float, help='Center Dec in degrees (for NVSS)')
    parser.add_argument('--radius', type=float, default=0.2, help='Radius in degrees (for NVSS, default: 0.2)')
    parser.add_argument('--min-flux-mjy', type=float, default=10.0, help='Minimum flux in mJy (for NVSS, default: 10.0)')
    parser.add_argument('--output', type=str, required=True, help='Output base path (will add .fits and .png)')
    parser.add_argument('--image-size', type=int, nargs=2, default=[1024, 1024], help='Image size in pixels (default: 1024 1024)')
    parser.add_argument('--pixel-scale', type=float, default=5.0, help='Pixel scale in arcseconds (default: 5.0)')
    parser.add_argument('--beam-fwhm', type=float, help='Beam FWHM in arcseconds (optional, for convolution)')
    
    args = parser.parse_args()
    
    # Load or create sky model
    if args.sky_model:
        print(f"Loading sky model from: {args.sky_model}")
        sky = SkyModel.from_file(args.sky_model)
    elif args.nvss:
        if args.center_ra is None or args.center_dec is None:
            print("Error: --center-ra and --center-dec required for --nvss")
            return 1
        
        print(f"Creating NVSS sky model (center: {args.center_ra}°, {args.center_dec}°, radius: {args.radius}°)")
        import astropy.units as u
        import numpy as np
        from astropy.coordinates import SkyCoord

        from dsa110_contimg.calibration.catalogs import read_nvss_catalog
        
        df = read_nvss_catalog()
        sc_all = SkyCoord(df["ra"].to_numpy() * u.deg, df["dec"].to_numpy() * u.deg, frame="icrs")
        ctr = SkyCoord(args.center_ra * u.deg, args.center_dec * u.deg, frame="icrs")
        sep = sc_all.separation(ctr).deg
        flux_mjy = np.asarray(df["flux_20_cm"].to_numpy(), float)
        keep = (sep <= args.radius) & (flux_mjy >= args.min_flux_mjy)
        
        if keep.sum() == 0:
            print(f"Error: No NVSS sources found in region")
            return 1
        
        ras = df.loc[keep, "ra"].to_numpy()
        decs = df.loc[keep, "dec"].to_numpy()
        fluxes = flux_mjy[keep] / 1000.0  # Convert to Jy
        
        ra = ras * u.deg
        dec = decs * u.deg
        stokes = np.zeros((4, 1, len(ras))) * u.Jy
        stokes[0, 0, :] = fluxes * u.Jy
        
        skycoord = SkyCoord(ra=ra, dec=dec, frame='icrs')
        
        sky = SkyModel(
            name=[f"nvss_{i}" for i in range(len(ras))],
            skycoord=skycoord,
            stokes=stokes,
            spectral_type='flat',
            component_type='point',
        )
        print(f"Created sky model with {sky.Ncomponents} sources")
    else:
        print("Error: Must specify --sky-model or --nvss")
        return 1
    
    # Generate images
    print(f"\nGenerating images...")
    print(f"  Output base: {args.output}")
    print(f"  Image size: {args.image_size[0]}x{args.image_size[1]} pixels")
    print(f"  Pixel scale: {args.pixel_scale} arcsec/pixel")
    if args.beam_fwhm:
        print(f"  Beam FWHM: {args.beam_fwhm} arcsec")
    
    fits_path, png_path = write_skymodel_images(
        sky,
        args.output,
        image_size=tuple(args.image_size),
        pixel_scale_arcsec=args.pixel_scale,
        center_ra_deg=args.center_ra if args.nvss else None,
        center_dec_deg=args.center_dec if args.nvss else None,
        beam_fwhm_arcsec=args.beam_fwhm,
    )
    
    print(f"\n✓ FITS image: {fits_path}")
    print(f"✓ PNG image: {png_path}")
    print(f"\nPNG saved to: {png_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

