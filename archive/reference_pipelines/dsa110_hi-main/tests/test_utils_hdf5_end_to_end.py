import os
from shutil import rmtree
from dsa110hi.utils_hdf5 import uvh5_to_ms

def test_uvh5_to_ms():

    files = [f'/data/pipeline/package_test_data/h5/test_sb{i:02}.hdf5' for i in range(16)]
    msname = uvh5_to_ms(files[0], '/data/pipeline/package_test_data/scratch/test_ms', protect_files=False)

    assert msname == '/data/pipeline/package_test_data/scratch/test_ms.ms'
    assert os.path.exists('/data/pipeline/package_test_data/scratch/test_ms.ms')

    rmtree('/data/pipeline/package_test_data/scratch/test_ms.ms')

def test_uvh5_to_ms_big_dataset():

    files = [f'/data/pipeline/package_test_data/h5/test_sb{i:02}.hdf5' for i in range(16)]
    msname = uvh5_to_ms(files, '/data/pipeline/package_test_data/scratch/test_ms', protect_files=False)

    assert msname == '/data/pipeline/package_test_data/scratch/test_ms.ms'
    assert os.path.exists('/data/pipeline/package_test_data/scratch/test_ms.ms')

    rmtree('/data/pipeline/package_test_data/scratch/test_ms.ms')
