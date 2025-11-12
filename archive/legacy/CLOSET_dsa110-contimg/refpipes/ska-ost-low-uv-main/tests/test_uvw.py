"""test_uvw: Test UVW calculations."""

import numpy as np
from pyuvdata import utils as uvutils

from ska_ost_low_uv.io import hdf5_to_pyuvdata, hdf5_to_uvx
from ska_ost_low_uv.utils import get_test_data
from ska_ost_low_uv.uvw_utils import calc_uvw


def test_uvw():
    """Test UVW calcs."""
    fn = get_test_data('aavs2_2x500ms/correlation_burst_204_20230927_35116_0.hdf5')
    uv = hdf5_to_uvx(fn, telescope_name='aavs2')

    uvd = hdf5_to_pyuvdata(fn, telescope_name='aavs2')
    uv = hdf5_to_uvx(fn, telescope_name='aavs2')

    # Checks comparing internal calls within calc_uvw
    n_bl = len(uv.data.baseline)
    n_ts = len(uv.timestamps)

    # Get LST in radians
    lst_rad = (uv.data.time.lst / 12 * np.pi).values

    # Compute apparent RA and DECs
    app_ras, app_decs = uvutils.phasing.transform_icrs_to_app(
        time_array=uv.timestamps,
        ra=uv.phase_center.ra.to('rad').value,
        dec=uv.phase_center.dec.to('rad').value,
        telescope_loc=uv.origin,
        telescope_frame='itrs',
        ellipsoid='SPHERE',
        astrometry_library=None,
    )

    # Now compute position angle
    frame_pos_angle = uvutils.phasing.calc_frame_pos_angle(
        time_array=uv.timestamps.jd,
        app_ra=app_ras,
        app_dec=app_decs,
        ref_frame='icrs',
        telescope_loc=uv.origin,
    )

    # And now we can compute UVWs
    uvw = uvutils.phasing.calc_uvw(
        app_ra=np.repeat(app_ras, n_bl),
        app_dec=np.repeat(app_decs, n_bl),
        lst_array=np.repeat(lst_rad, n_bl),
        use_ant_pos=True,
        frame_pa=np.repeat(frame_pos_angle, n_bl),
        antenna_positions=uv.antennas.ecef.values,
        antenna_numbers=uv.antennas.coords['antenna'].values,
        ant_1_array=np.tile(uv.data.ant1.values, n_ts),
        ant_2_array=np.tile(uv.data.ant2.values, n_ts),
        telescope_lat=uv.origin.to_geodetic().lat.to('rad').value,
        telescope_lon=uv.origin.to_geodetic().lon.to('rad').value,
    )

    # Check apparent RA and DEC match
    assert np.allclose(uvd.phase_center_app_ra, np.repeat(app_ras, n_bl))
    assert np.allclose(uvd.phase_center_app_dec, np.repeat(app_decs, n_bl))

    # Check LST arrays match
    assert np.allclose(uvd.lst_array, np.repeat(lst_rad, n_bl))

    # Check frame position angles match
    assert np.allclose(uvd.phase_center_frame_pa, np.repeat(frame_pos_angle, n_bl))

    # Check antenna positions match
    assert np.allclose(uvd.telescope.antenna_positions, uv.antennas.ecef.values)
    assert np.allclose(uvd.ant_1_array, np.tile(uv.data.ant1.values, n_ts))
    assert np.allclose(uvd.ant_2_array, np.tile(uv.data.ant2.values, n_ts))
    assert np.allclose(uvd.telescope.antenna_numbers, uv.antennas.coords['antenna'].values)

    # Check telescope positions match
    assert np.isclose(
        uvd.telescope.location.to_geodetic().lat.to('rad').value,
        uv.origin.to_geodetic().lat.to('rad').value,
    )
    assert np.isclose(
        uvd.telescope.location.to_geodetic().lon.to('rad').value,
        uv.origin.to_geodetic().lon.to('rad').value,
    )

    # Finally, check UVW positions match
    assert np.allclose(uvd.uvw_array, uvw, atol=1e-7)

    # And now call and check the actual in-built calc_uvw method
    uvw_ = calc_uvw(uv)
    assert np.allclose(uvw.reshape((n_ts, n_bl, 3)), uvw_)


if __name__ == '__main__':
    test_uvw()
