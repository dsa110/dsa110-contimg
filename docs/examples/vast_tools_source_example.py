"""
Example usage of Source class (VAST Tools adoption).

Demonstrates how to use the Source class for ESE candidate analysis.
"""
from pathlib import Path
from dsa110_contimg.photometry.source import Source

# Example 1: Create Source from database
products_db = Path("state/products.sqlite3")
source_id = "NVSS J123456+420312"

source = Source(
    source_id=source_id,
    products_db=products_db
)

# Access properties
print(f"Source: {source.name}")
print(f"Coordinates: {source.coord}")
print(f"Number of epochs: {source.n_epochs}")
print(f"Number of detections: {source.detections}")

# Example 2: Calculate variability metrics
metrics = source.calc_variability_metrics()
print(f"\nVariability Metrics:")
print(f"  V (coefficient of variation): {metrics['v']:.4f}")
print(f"  η (weighted variance): {metrics['eta']:.4f}")
print(f"  Vs mean (two-epoch t-statistic): {metrics['vs_mean']:.4f}")
print(f"  m mean (modulation index): {metrics['m_mean']:.4f}")

# Example 3: Plot light curve
fig = source.plot_lightcurve(
    use_normalized=True,
    highlight_baseline=True,
    highlight_ese_period=True,
    grid=True
)
fig.savefig(f"{source_id.replace(' ', '_')}_lightcurve.png")

# Example 4: Plot light curve with MJD time axis
fig_mjd = source.plot_lightcurve(
    mjd=True,
    highlight_baseline=True,
    highlight_ese_period=True
)
fig_mjd.savefig(f"{source_id.replace(' ', '_')}_lightcurve_mjd.png")

# Example 5: Create Source with explicit coordinates (no database)
source2 = Source(
    source_id="TEST001",
    ra_deg=123.456,
    dec_deg=42.0312,
    name="Test Source"
)

# Add measurements manually
import pandas as pd
import numpy as np
from astropy.time import Time

source2.measurements = pd.DataFrame({
    'mjd': [59000.0, 59010.0, 59020.0, 59030.0],
    'normalized_flux_jy': [1.0, 1.1, 0.9, 1.05],
    'normalized_flux_err_jy': [0.05, 0.05, 0.05, 0.05],
    'image_path': ['img1.fits', 'img2.fits', 'img3.fits', 'img4.fits'],
})

# Calculate metrics
metrics2 = source2.calc_variability_metrics()
print(f"\nTest Source Metrics:")
print(f"  V: {metrics2['v']:.4f}")
print(f"  η: {metrics2['eta']:.4f}")

# Plot light curve
fig2 = source2.plot_lightcurve()
fig2.savefig("test_source_lightcurve.png")

