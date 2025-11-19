import os
import shutil

import numpy as np
from casacore.tables import table

ms_path = "/stage/dsa110-contimg/2025-10-02T16:02:12/2025-10-02T16:02:12.sb03.ms"
test_ms_path = "/data/dsa110-contimg/test_data/test_masking.ms"

if not os.path.exists("/data/dsa110-contimg/test_data"):
    os.makedirs("/data/dsa110-contimg/test_data")

if os.path.exists(test_ms_path):
    shutil.rmtree(test_ms_path)

print(f"Copying {ms_path} to {test_ms_path}...")
shutil.copytree(ms_path, test_ms_path)

# Mock calibration by populating CORRECTED_DATA with DATA
print("Mocking calibration by copying DATA to CORRECTED_DATA...")
with table(test_ms_path, readonly=False, ack=False) as t:
    data = t.getcol("DATA")
    # Ensure CORRECTED_DATA column exists
    if "CORRECTED_DATA" not in t.colnames():
        from casacore.tables import makedesc, makesca

        # Add column definition
        desc = t.getcoldesc("DATA")
        desc["name"] = "CORRECTED_DATA"
        t.addcols(desc)

    t.putcol("CORRECTED_DATA", data)
    print("CORRECTED_DATA populated.")

# Verify
with table(test_ms_path, readonly=True, ack=False) as t:
    cols = t.colnames()
    print(f"Columns in test MS: {cols}")
    if "CORRECTED_DATA" in cols:
        cd = t.getcol("CORRECTED_DATA", 0, 10)
        print(f"CORRECTED_DATA sample: {np.abs(cd).mean()}")
