import os
import numpy as np
import pytest

from shutil import rmtree

from dsa110hi.utils_hdf5 import load_uvh5_file

# Check that casa loaded properly
def test_pyuvdata_ms():
    from pyuvdata.uvdata.ms import casa_present
    assert casa_present == True

def test_load_uvh5():

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    
    # Make sure stuff has expected shapes - if built using a newer version of pyuvdata
    # this may not hold, which might break assumptions elsewhere.
    assert uvdata.data_array.shape == (111744, 1, 48, 2)
    assert uvdata.data_array.dtype == np.complex64

    assert uvdata.data_array.shape[2] == len(uvdata.freq_array.flatten())
    assert uvdata.data_array.shape[0] == len(uvdata.time_array.flatten())

def test_load_uvh5_ant_selection():

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    antenna_list = ['pad1','pad2','pad3','pad4','pad6']
    uvdata = load_uvh5_file(file,antenna_list=antenna_list)
    
    # Make sure stuff has expected antennas and numbering
    assert np.all(np.sort(uvdata.antenna_names) == np.sort(antenna_list))
    assert np.all(np.sort(uvdata.antenna_numbers) == np.sort([int(n.strip('pad'))-1 for n in antenna_list]).astype(int))

    assert uvdata.data_array.shape[2] == len(uvdata.freq_array.flatten())
    assert uvdata.data_array.shape[0] == len(uvdata.time_array.flatten())

    nbl = int(len(antenna_list)*(len(antenna_list)-1)/2 + len(antenna_list))    
    assert uvdata.data_array.shape == (len(np.unique(uvdata.time_array.flatten()))*nbl, 1, 48, 2)

def test_load_uvh5_single_in_list():
    # Same as previous, but passing a single file in a list - checking for an edge case

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file([file])
    
    assert uvdata.data_array.shape == (111744, 1, 48, 2)
    assert uvdata.data_array.dtype == np.complex64

    assert uvdata.data_array.shape[2] == len(uvdata.freq_array.flatten())
    assert uvdata.data_array.shape[0] == len(uvdata.time_array.flatten())

def test_load_uvh5_multiple():
    # Load 16 
    files = [f'/data/pipeline/package_test_data/h5/test_sb{i:02}.hdf5' for i in range(16)]

    uvdata = load_uvh5_file(files)
    assert uvdata.data_array.shape == (111744, 1, 16*48, 2)
    assert uvdata.data_array.dtype == np.complex64

    assert uvdata.data_array.shape[2] == len(uvdata.freq_array.flatten())
    assert uvdata.data_array.shape[0] == len(uvdata.time_array.flatten())

    # Make sure frequency spacing is correct
    assert len(np.unique(np.diff(uvdata.freq_array)))==1

    # Make sure frequencies are sorted in ascending order
    assert np.all(np.unique(np.diff(uvdata.freq_array))>0)

def test_load_uvh5_repeat_freq():
    # Load last file twice - should raise an error because of repeated frequencies
    files = ['/data/pipeline/package_test_data/h5/test_sb00.hdf5',
             '/data/pipeline/package_test_data/h5/test_sb01.hdf5',
             '/data/pipeline/package_test_data/h5/test_sb01.hdf5',]

    with pytest.raises(ValueError):
        uvdata = load_uvh5_file(files)

def test_load_uvh5_incompatible_times():
    # Load last file twice - should raise an error because of repeated frequencies
    files = ['/data/pipeline/package_test_data/h5/test_sb00.hdf5',
             '/data/pipeline/package_test_data/h5/test_sb01.hdf5',
             '/data/pipeline/package_test_data/h5/test_sb00_second_timestamp.hdf5',]

    with pytest.raises(ValueError):
        uvdata = load_uvh5_file(files)

def test_load_uvh5_telname():
    # Test that the telescope is renamed
    from dsa110hi.utils_dsa110 import loc_dsa110
    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file, telescope_pos=loc_dsa110)
    
    assert uvdata.telescope_name == loc_dsa110.info.name

def test_load_uvh5_telpos():
    # Check that we don't need to manually update telescope positions
    # (ie check that the incoming headers are correct)
    from dsa110hi.utils_antpos import set_antenna_positions
    from dsa110hi.utils_dsa110 import loc_dsa110

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    
    tel = np.copy(uvdata.telescope_location)
    pos = np.copy(uvdata.antenna_positions)
    uvdata = set_antenna_positions(uvdata, telescope_pos=loc_dsa110)

    assert np.allclose(tel, uvdata.telescope_location)
    assert np.allclose(pos, uvdata.antenna_positions)
