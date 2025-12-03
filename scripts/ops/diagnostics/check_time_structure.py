import matplotlib.pyplot as plt
import numpy as np

# --- CASA log directory setup ---
# Ensure CASA logs go to centralized directory, not CWD
import os as _os
try:
    from pathlib import Path as _Path
    _REPO_ROOT = _Path(__file__).resolve().parents[3]
    _sys_path_entry = str(_REPO_ROOT / 'backend' / 'src')
    import sys as _sys
    if _sys_path_entry not in _sys.path:
        _sys.path.insert(0, _sys_path_entry)
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    _casa_log_dir = derive_casa_log_dir()
    _os.makedirs(str(_casa_log_dir), exist_ok=True)
    _os.chdir(str(_casa_log_dir))
except (ImportError, OSError):
    pass  # Best effort - CASA logs may go to CWD
# --- End CASA log directory setup ---

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
