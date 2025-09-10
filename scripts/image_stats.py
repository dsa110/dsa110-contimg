#!/usr/bin/env python3
import numpy as np
from pathlib import Path
from astropy.io import fits
from astropy.stats import sigma_clipped_stats


def load_image(fits_path: str) -> np.ndarray:
    with fits.open(fits_path, memmap=True) as hdul:
        data = np.squeeze(hdul[0].data)
    return data


def main() -> int:
    fits_path = 'images/quick_dirty.fits'
    if not Path(fits_path).exists():
        print(f'FITS not found: {fits_path}')
        return 2

    img = load_image(fits_path)
    # Compute robust stats on full image (simple baseline). For more rigor, mask central bright pixels.
    mean, median, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
    peak = float(np.nanmax(img))
    rms = float(std)
    minval = float(np.nanmin(img))

    print(f'File: {fits_path}')
    print(f'Image shape: {img.shape}')
    print(f'Peak: {peak:.6g} Jy/beam')
    print(f'RMS (sigma-clipped): {rms:.6g} Jy/beam')
    print(f'Median: {float(median):.6g} Jy/beam')
    print(f'Min: {minval:.6g} Jy/beam')
    if rms > 0:
        print(f'Dynamic range (peak/rms): {peak/rms:.1f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


