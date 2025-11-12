#!/usr/bin/env python3
import sys
from pathlib import Path
import argparse
import os

def export_fits(image_prefix: str) -> str:
    from casatasks import exportfits
    casa_image = f"{image_prefix}.image"
    fits_path = f"{image_prefix}.fits"
    exportfits(imagename=casa_image, fitsimage=fits_path, dropstokes=True, overwrite=True)
    return fits_path

def summarize_beam(image_prefix: str):
    try:
        from casatasks import imhead
    except Exception:
        return None
    h = imhead(imagename=f"{image_prefix}.image", mode='list')
    beam = h.get('restoringbeam') or h.get('perplanebeams')
    return beam

def plot_pdf(fits_path: str, pdf_path: str):
    import numpy as np
    from astropy.io import fits
    import matplotlib.pyplot as plt
    from astropy.wcs import WCS

    with fits.open(fits_path) as hdul:
        hdu = hdul[0]
        data = hdu.data
        header = hdu.header
        img = np.squeeze(data)
        # Build WCS and select last two axes if more than 2D
        w = WCS(header)
        if w.pixel_n_dim > 2:
            # Create a WCS slice that keeps the last two axes
            # Prepend slices of 0 for leading axes
            extra = w.pixel_n_dim - 2
            slices = (0,) * extra + (slice(None), slice(None))
            w2 = w.slice(slices)
        else:
            w2 = w

    vmin, vmax = np.nanpercentile(img, [5, 99.5])
    fig = plt.figure(figsize=(6, 6))
    ax = plt.subplot(projection=w2)
    im = ax.imshow(img, origin='lower', cmap='inferno', vmin=vmin, vmax=vmax)
    ax.set_xlabel('RA')
    ax.set_ylabel('Dec')
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label='Jy/beam')
    plt.tight_layout()
    plt.ylabel('Declination')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close(fig)

def export_and_plot(image_prefix: str):
    """Orchestrates the export and plotting."""
    casa_image = f"{image_prefix}.image"
    if not os.path.exists(casa_image):
        print(f"CASA image not found: {casa_image}")
        return

    beam = summarize_beam(image_prefix)
    if beam:
        print('Beam info:', beam)

    fits_path = export_fits(image_prefix)
    print('Wrote FITS:', fits_path)

    pdf_path = f"{image_prefix}.pdf"
    plot_pdf(fits_path, pdf_path)
    print('Wrote PDF:', pdf_path)

def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description='Export a CASA image to FITS and create a PDF plot.')
    parser.add_argument('--imagename', type=str, default='images/clean_image', help='Path to the input CASA image (without extension)')
    args = parser.parse_args()

    export_and_plot(args.imagename)

if __name__ == '__main__':
    main()


