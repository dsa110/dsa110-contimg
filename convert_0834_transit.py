#!/opt/miniforge/envs/casa6/bin/python
from pathlib import Path

from astropy.time import Time

from dsa110_contimg.conversion import CalibratorMSGenerator

result = CalibratorMSGenerator(
    input_dir=Path("/data/incoming"),
    output_dir=Path("/stage/dsa110-contimg/ms"),
    products_db=Path("/data/dsa110-contimg/state/products.sqlite3"),
    catalogs=[Path("/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3")],
).generate_from_transit("0834+555", Time("2025-10-18T14:35:15"), window_minutes=5)

print(f"MS created: {result.ms_path}")
