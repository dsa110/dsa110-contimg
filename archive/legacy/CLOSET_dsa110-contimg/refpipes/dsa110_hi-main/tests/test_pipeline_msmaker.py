import os
from shutil import rmtree
from dsa110hi.pipeline_msmaker import convert_to_ms

def test_msmaker():
    h5path = '/data/pipeline/package_test_data/h5/test_3c48/'
    mspath = '/data/pipeline/package_test_data/ms/'
    tstamp = '2024-11-02T06:43:34'

    # Just make sure the thing runs - no calibrator step
    if not os.path.exists(mspath):
        os.mkdir(mspath)
    clear_files = [mspath+tstamp+'_ra024.9_dec+33.0.ms', mspath+tstamp+'_ra024.9_dec+33.0.ms.flagversions', mspath+'3c48_'+tstamp+'.ms', mspath+'3c48_'+tstamp+'.ms.flagversions']
    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)
 
    convert_to_ms(incoming_file_path=h5path,
                incoming_file_names=[f'{tstamp}_sb{i:02d}.hdf5' for i in range(2)],
                output_antennas=['pad1','pad2','pad3'], # Just a few antennas to make it run faster
                tmin=None, tmax=None,
                same_timestamp_tolerance=30.0,
                output_file_path=mspath,
                cal_do_search=False, cal_search_radius=1.0, cal_catalog=None,
                cal_output_file_path=mspath,
                post_handle='none'
                )

    print()
    assert os.path.exists(mspath+tstamp+'_ra024.9_dec+33.0.ms')
    assert not os.path.exists(mspath+'3c48_'+tstamp+'.ms')

    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)

def test_msmaker_with_cal():
    h5path = '/data/pipeline/package_test_data/h5/test_3c48/'
    mspath = '/data/pipeline/package_test_data/ms/'
    tstamp = '2024-11-02T06:43:34'

    # Just make sure the thing runs - no calibrator step
    if not os.path.exists(mspath):
        os.mkdir(mspath)
    clear_files = [mspath+tstamp+'_ra024.9_dec+33.0.ms', mspath+tstamp+'_ra024.9_dec+33.0.ms.flagversions', mspath+'3c48_'+tstamp+'.ms', mspath+'3c48_'+tstamp+'.ms.flagversions']
    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)
 
    convert_to_ms(incoming_file_path=h5path,
                incoming_file_names=[f'{tstamp}_sb{i:02d}.hdf5' for i in range(2)],
                output_antennas=['pad1','pad2','pad3'], # Just a few antennas to make it run faster
                tmin=None, tmax=None,
                same_timestamp_tolerance=30.0,
                output_file_path=mspath,
                cal_do_search=True, cal_search_radius=1.0, cal_catalog=None,
                cal_output_file_path=mspath,
                post_handle='none'
                )

    assert os.path.exists(mspath+tstamp+'_ra024.9_dec+33.0.ms')
    assert os.path.exists(mspath+'3c48_'+tstamp+'.ms')

    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)

def test_msmaker_spl():
    h5path = '/data/pipeline/package_test_data/h5/test_3c48/'
    mspath = '/data/pipeline/package_test_data/ms_spl/'
    tstamp = '2024-11-02T06:43:37'

    # Just make sure the thing runs - no calibrator step
    if not os.path.exists(mspath):
        os.mkdir(mspath)
    clear_files = [mspath+tstamp+'_ra024.9_dec+33.0.ms', mspath+tstamp+'_ra024.9_dec+33.0.ms.flagversions', mspath+'3c48_'+tstamp+'.ms', mspath+'3c48_'+tstamp+'.ms.flagversions']
    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)
 
    convert_to_ms(incoming_file_path=h5path,
                incoming_file_names=[f'{tstamp}_sb07_spl.hdf5'],
                spw=['sb07_spl'],
                output_antennas=['pad1','pad2','pad3'], # Just a few antennas to make it run faster
                tmin=None, tmax=None,
                same_timestamp_tolerance=30.0,
                output_file_path=mspath,
                cal_do_search=True, cal_search_radius=1.0, cal_catalog=None,
                cal_output_file_path=mspath,
                post_handle='none'
                )

    assert os.path.exists(mspath+tstamp+'_ra024.9_dec+33.0.ms')
    assert os.path.exists(mspath+'3c48_'+tstamp+'.ms')

    for f in clear_files:
        if os.path.exists(f):
            rmtree(f)

