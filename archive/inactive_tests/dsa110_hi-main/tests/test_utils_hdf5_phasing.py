import pytest
import numpy as np
from dsa110hi.utils_hdf5 import load_uvh5_file, compute_pointing, set_phases, make_calib_model, loc_dsa110
from astropy.coordinates import SkyCoord

def test_compute_pointing():
    from astropy.time import Time
    from astropy.coordinates import TETE
    # Hard to come up with robust tests here.
    # Just check that the declinations are right (based
    # on headers) and the array shapes make sense.

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    
    pt = compute_pointing(uvdata, loc_dsa110)

    assert pt.shape == uvdata.time_array.shape

    # Assuming here that the dec in the headers is apparent, not J2000
    # Just make sure it's within an arcsec
    pt_apparent0 = pt[0].transform_to(TETE(location=loc_dsa110,obstime=Time(uvdata.time_array[0],format='jd')))
    pt_apparent1 = pt[-1].transform_to(TETE(location=loc_dsa110,obstime=Time(uvdata.time_array[-1],format='jd')))

    assert np.abs(pt_apparent0.dec.rad-uvdata.extra_keywords['phase_center_dec'])<1/3600*np.pi/180
    assert np.abs(pt_apparent1.dec.rad-uvdata.extra_keywords['phase_center_dec'])<1/3600*np.pi/180


def test_set_phases():

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    
    # First check unphased data is what I expect
    assert np.all(uvdata.phase_center_id_array==0)
    assert uvdata.phase_center_catalog.keys() == {0:None}.keys()
    assert uvdata.phase_center_catalog[0]['cat_type'] == 'unprojected'

    # Now phase and do some checks
    uvdata = set_phases(uvdata, 'test', loc_dsa110, verbose=False)

    assert 0 not in uvdata.phase_center_catalog.keys()

    for k,v in uvdata.phase_center_catalog.items():
        assert v['cat_type'] == 'sidereal'

    ids, n = np.unique(uvdata.phase_center_id_array, return_counts=True)
    assert np.all(n==n[0])

def test_set_phases_uvwcoords():
    # We overwite the UVW coordinates with ones calculated exactly
    # from the antenna positions + pointing direction - this means 
    # our UVW coordinates differ slightly from what the raw data 
    # contain. Here we check that those changes are small

    # The difference appears to be driven by the PA computation, which
    # suggests that the correct PA is about -0.005 (~0.3 deg), rather 
    # than the 0 which is hard-coded into the writer. I'm not sure 
    # if that is correct.

    # The new and old uvw coordinates differ in sqrt(u^2+v^2) by no more
    # than 1 part in 10,000, but differ in u or v by up to 0.3%. The w 
    # coordinates are consistent to 1 part in 10,000.

    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    uvw = np.copy(uvdata.uvw_array)

    # Now phase and do some checks
    uvdata = set_phases(uvdata, 'test', loc_dsa110, verbose=False)

    # Recalculating UVW should give simillar answers to
    # original version, but we allow for small changes 
    
    # Doing for the autocorrs will give inf:
    inds = np.nonzero(uvdata.ant_1_array != uvdata.ant_2_array)
    
    uvsq1 = np.sqrt(uvdata.uvw_array[:,0][inds]**2+uvdata.uvw_array[:,1][inds]**2)
    uvsq2 = np.sqrt(uvw[:,0][inds]**2+uvw[:,1][inds]**2)

    norm_u1 = (uvdata.uvw_array[:,0][inds]/uvsq1)
    norm_v1 = (uvdata.uvw_array[:,1][inds]/uvsq1)
    norm_u2 = (uvw[:,0][inds]/uvsq1)
    norm_v2 = (uvw[:,1][inds]/uvsq1)

    # Radii are all the same
    assert np.max(np.abs(uvsq2-uvsq1)) < 1e-4

    # u/v don't change by much
    assert np.max(np.abs(norm_u1-norm_u2)) < .005
    assert np.max(np.abs(norm_v1-norm_v2)) < .005

    # w is the same
    assert np.max(np.abs(uvdata.uvw_array[:,2]-uvw[:,2])) < 1e-4

    # PA is small
    assert np.max(np.abs(uvdata.phase_center_frame_pa)) < .01
    
    # Autcorrelations have uvw=0
    inds_auto = np.nonzero(uvdata.ant_1_array == uvdata.ant_2_array)
    assert np.allclose(uvw[inds_auto],0)

def test_model():
    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    uvdata = set_phases(uvdata, 'test', loc_dsa110, verbose=False)

    cal_source = SkyCoord(0,0,unit='deg')
    cal_flux = 1
    uvcalib = make_calib_model(uvdata, calib_ra=cal_source.ra, calib_dec=cal_source.dec, calib_flux_jy=cal_flux)

    assert np.all(uvcalib.phase_center_id_array == uvdata.phase_center_id_array)
    assert np.allclose(uvcalib.uvw_array, uvdata.uvw_array)
    assert np.all(np.abs(uvcalib.data_array)<=cal_flux)

def test_model_multiple():
    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    uvdata = set_phases(uvdata, 'test', loc_dsa110, verbose=False)

    cal_source1 = SkyCoord(0,0,unit='deg')
    cal_source2 = SkyCoord(0,0.5,unit='deg')
    cal_flux1 = 1
    cal_flux2 = 1.5

    uvcalib = make_calib_model(uvdata, calib_ra=[cal_source1.ra,cal_source2.ra], calib_dec=[cal_source1.dec,cal_source2.dec], calib_flux_jy=[cal_flux1,cal_flux2])

    assert np.all(uvcalib.phase_center_id_array == uvdata.phase_center_id_array)
    assert np.allclose(uvcalib.uvw_array, uvdata.uvw_array)
    assert np.all(np.abs(uvcalib.data_array)<=cal_flux1+cal_flux2)

def test_model_input_checker():
    file = '/data/pipeline/package_test_data/h5/test_sb00.hdf5'

    uvdata = load_uvh5_file(file)
    uvdata = set_phases(uvdata, 'test', loc_dsa110, verbose=False)

    cal_source1 = SkyCoord(0,0,unit='deg')
    cal_source2 = SkyCoord(0,0.5,unit='deg')

    # Run to make sure the nominal things work
    make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=[0,0],calib_sidx_f0_ghz=[1.4,1.4],calib_epoch='J2000.0')
    make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=[0,None],calib_sidx_f0_ghz=[1.4,None],calib_epoch='J2000.0')
    make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_epoch='J2000.0')
    make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_epoch=['J2000.0','J2000.0'])

    # Run to make sure errors are raised
    with pytest.raises(ValueError, match='All of calib_ra, calib_dec, calib_flux_jy must be specified as either single values or lists'):
        make_calib_model(uvdata,cal_source1.ra,[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=[0,0],calib_sidx_f0_ghz=[1.4,1.4],calib_epoch='J2000.0')
    with pytest.raises(ValueError, match='All of calib_ra, calib_dec, calib_flux_jy must be specified as either single values or lists'):
        make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],cal_source1.dec,[1,1],calib_sidx=[0,0],calib_sidx_f0_ghz=[1.4,1.4],calib_epoch='J2000.0')
    with pytest.raises(ValueError, match='All of calib_ra, calib_dec, calib_flux_jy must be specified as either single values or lists'):
        make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],1,calib_sidx=[0,0],calib_sidx_f0_ghz=[1.4,1.4],calib_epoch='J2000.0')
    with pytest.raises(ValueError, match='Multiple calibrator position/flux and single spectral indices not supported'):
        make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=0,calib_sidx_f0_ghz=[1.4,1.4],calib_epoch='J2000.0')
    with pytest.raises(ValueError, match='Multiple calibrator position/flux and single spectral indices not supported'):
        make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=[0,0],calib_sidx_f0_ghz=1.4,calib_epoch='J2000.0')
    with pytest.raises(ValueError,match='Must specify either single calib_epoch or a list with one value per calibrator source'):
        make_calib_model(uvdata,[cal_source1.ra,cal_source2.ra],[cal_source1.dec,cal_source2.dec],[1,1],calib_sidx=[0,0],calib_sidx_f0_ghz=[1.4,1.4],calib_epoch=['J2000.0'])

test_model_input_checker()