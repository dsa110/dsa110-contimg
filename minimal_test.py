# Minimal test script
import os
os.environ['CASACORE_TABLE_PATH'] = '/data/jfaber/dsa110-contimg/tmp/casatables_test' # Use a distinct path
os.makedirs(os.environ['CASACORE_TABLE_PATH'], exist_ok=True)

import numpy as np
from pyuvdata import UVData
from astropy.time import Time

uv = UVData()
uv.Nants_data = 2
uv.Nbls = 1
uv.Nblts = 1
uv.Nfreqs = 1
uv.Npols = 1
uv.Nspws = 1
uv.Ntimes = 1
uv.ant_1_array = np.array([0])
uv.ant_2_array = np.array([1])
uv.antenna_names = ['ant1', 'ant2']
uv.antenna_numbers = np.array([1, 2])
uv.antenna_positions = np.zeros((2, 3)) # Simplified
uv.baseline_array = np.array([257]) # (256 * ant2) + ant1 + 2**16 if ant1 > 255 or ant2 > 255
uv.channel_width = [1e4]
uv.data_array = np.ones((1, 1, 1), dtype=np.complex64)
uv._flex_spw_id_array = np.ones((1, 1, 1), dtype=np.complex64)
uv.flag_array = np.zeros_like(uv.data_array, dtype=bool)
uv.freq_array = np.array([1.4e9])
uv.history = 'Test MS'
uv.instrument = 'Test'
uv.integration_time = np.array([10.0])
uv.known_telescopes = ['Test']
uv.lst_array = np.array([0.0])
uv.nsample_array = np.ones_like(uv.data_array, dtype=float)
uv.phase_center_catalog = {} # Add a basic phase center
pc_id = uv._add_phase_center(cat_name='test_center', cat_type='sidereal', cat_frame='itrs', cat_lon=0.0, cat_lat=0.0)
uv.phase_center_id_array = np.array([pc_id])

uv.polarization_array = np.array([-5]) # XX
uv.spw_array = np.array([1])
uv.telescope_location = (0,0,0) # Simplified
uv.telescope_name = 'Test'
uv.time_array = np.array([Time('2024-01-01T00:00:00').jd])
uv.uvw_array = np.zeros((1, 3))
uv.vis_units = 'Jy'

try:
    print("Checking UVData object...")
    uv.check()
    print("Writing test MS...")
    uv.write_ms('test_minimal.ms', force_phase=True, clobber=False)
    print("Successfully wrote test_minimal.ms")
except Exception as e:
    print(f"Error in minimal test: {e}")