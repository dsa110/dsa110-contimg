import os

import numpy as np
from astropy.io import fits

try:
    with fits.open("sandbox/test_model-term-0.fits") as hdul:
        data = hdul[0].data
        header = hdul[0].header
        print(f"Shape: {data.shape}")
        print(f"Max value: {np.nanmax(data)}")
        print(
            f"Center pixel value: {data[0, 0, 50, 50]}"
        )  # 4D: Stokes, Freq, Dec, Ra. 100x100 image -> center at 50,50
        print(f"CRVAL1: {header['CRVAL1']}")
        print(f"CRVAL2: {header['CRVAL2']}")
except Exception as e:
    print(f"Error: {e}")
