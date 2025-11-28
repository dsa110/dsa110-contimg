from dsa110_contimg.database.hdf5_index import query_subband_groups
from dsa110_contimg.conversion.strategies.writers import get_writer
from dsa110_contimg.utils.antpos_local import get_itrf
from dsa110_contimg.utils import FastMeta
import os
import numpy as np
import pyuvdata

def convert_subband_groups_to_ms(input_dir, output_dir, start_time, end_time, tolerance_s=60.0):
    """
    Orchestrates the conversion of HDF5 subband files to Measurement Sets.

    Parameters:
    - input_dir: Directory containing the HDF5 subband files.
    - output_dir: Directory where the Measurement Sets will be saved.
    - start_time: Start time for the conversion window.
    - end_time: End time for the conversion window.
    - tolerance_s: Time tolerance for grouping subbands (default: 60 seconds).
    """
    # Query subband groups based on the provided time window
    hdf5_db = os.path.join(input_dir, 'hdf5_file_index.sqlite3')
    groups = query_subband_groups(hdf5_db, start_time, end_time, tolerance_s=tolerance_s)

    for group in groups:
        # Combine subbands using pyuvdata
        uvdata = pyuvdata.UVData()
        for subband_file in group:
            with FastMeta(subband_file) as meta:
                uvdata.read(subband_file)

        # Get antenna positions
        antpos = get_itrf()

        # Prepare output path for Measurement Set
        output_path = os.path.join(output_dir, f"{group[0].split('_')[0]}.ms")

        # Get writer class and write the Measurement Set
        writer_cls = get_writer('parallel-subband')
        writer_instance = writer_cls(uvdata, output_path)
        writer_instance.write()

    print("Conversion completed successfully.")