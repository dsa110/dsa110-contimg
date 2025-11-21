import matplotlib.pyplot as plt
import numpy as np
from casatools import table

ms_path = "/stage/dsa110-contimg/ms/science/2025-10-02/2025-10-02T01:08:33.ms"

tb = table()
tb.open(ms_path)
times = tb.getcol("TIME")
tb.close()

# Normalize to start time = 0
t0 = np.min(times)
rel_times = times - t0

print(f"Total data points: {len(times)}")
print(f"Time span: {np.max(rel_times):.2f} seconds")
print(f"Min time: {np.min(rel_times):.2f}")
print(f"Max time: {np.max(rel_times):.2f}")

# Check for gaps > 2 seconds (since integration is likely ~1s or less)
sorted_times = np.unique(rel_times)
diffs = np.diff(sorted_times)
gaps = diffs[diffs > 2.0]

if len(gaps) > 0:
    print(f"\nFound {len(gaps)} gaps larger than 2.0s!")
    print(f"Largest gap: {np.max(gaps):.2f}s")
    print(f"Average gap: {np.mean(gaps):.2f}s")
else:
    print("\nNo significant time gaps found.")

# Histogram to show density
hist, bins = np.histogram(rel_times, bins=30)
print("\nData density per 10s bin (approx):")
print(hist)
