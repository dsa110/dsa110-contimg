from pyuvdata import UVData
import numpy as np

fname = '/data/incoming_test/2025-09-05T03:18:05_sb05.hdf5'  # adjust as needed

uv = UVData()
uv.read(fname, file_type='uvh5',
        run_check=False, run_check_acceptability=False,
        strict_uvw_antpos_check=False, check_extra=False)

freq = uv.freq_array.squeeze()
diff = np.diff(freq)

print('freq shape:', uv.freq_array.shape)
print('diff min:', diff.min(), 'diff max:', diff.max())
print('non-negative diffs count:', np.count_nonzero(diff >= 0))
print('first 5 diffs:', diff[:5])
print('last 5 diffs:', diff[-5:])
