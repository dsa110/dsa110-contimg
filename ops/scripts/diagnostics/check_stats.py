import glob

import numpy as np
from astropy.io import fits
from astropy.stats import mad_std

# Get list of fast images
images = sorted(glob.glob("/data/dsa110-contimg/2025-10-02T01:08:33.ms.fast-t*-image.fits"))
print(f"Found {len(images)} images")

rms_values = []
peak_values = []
min_values = []
max_values = []

for img in images:
    with fits.open(img) as hdul:
        data = hdul[0].data.squeeze()
        # Convert to mJy for readability
        data_mjy = data * 1000

        # Calculate robust statistics (MAD)
        rms = mad_std(data_mjy, ignore_nan=True)
        peak = np.nanmax(data_mjy)

        rms_values.append(rms)
        peak_values.append(peak)
        min_values.append(np.nanmin(data_mjy))
        max_values.append(np.nanmax(data_mjy))

rms_arr = np.array(rms_values)
peak_arr = np.array(peak_values)

print("\n--- Image Statistics (mJy/beam) ---")
print(f"Mean RMS Noise:   {np.mean(rms_arr):.2f} +/- {np.std(rms_arr):.2f} mJy")
print(f"Min RMS:          {np.min(rms_arr):.2f} mJy")
print(f"Max RMS:          {np.max(rms_arr):.2f} mJy")
print(f"Mean Peak Flux:   {np.mean(peak_arr):.2f} mJy")
print(f"Max Peak in set:  {np.max(peak_arr):.2f} mJy")
print("-" * 35)

# Check for any > 6 sigma peaks relative to *local* image RMS
detections = []
for i, (peak, rms) in enumerate(zip(peak_values, rms_values)):
    if peak > 6 * rms:
        detections.append(f"Frame {i}: Peak={peak:.2f} mJy (SNR={peak/rms:.1f})")

if detections:
    print(f"\nPotential Detections (>6 sigma):")
    for d in detections:
        print(d)
else:
    print("\nNo >6 sigma peaks detected in any frame.")
