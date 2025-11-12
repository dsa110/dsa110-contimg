"""Test aa_simulation plotting routines."""

import pylab as plt
import pytest
from astropy.time import Time
from astropy.units import Quantity

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data

##############
## FIXTURES ##
##############


@pytest.fixture
def fixture_aa_beam_sim():
    """Fixture to create an ApertureArray with simulated beam."""
    t = Time(['2000-01-01T00:00:00'], format='isot', scale='utc')
    aa = ApertureArray(station_id='s8-6', sim_f=Quantity([100], unit='MHz'), sim_t=t)
    pc = aa.coords.get_zenith()
    return aa, pc


@pytest.fixture
def fixture_aa_gsm_sim():
    """Fixture to create an ApertureArray for GSM simulation."""
    uvx = hdf5_to_uvx(
        get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5'),
        telescope_name='aavs2',
    )
    aa = ApertureArray(uvx)
    return aa


#############
## SIM GSM ##
#############


@pytest.mark.mpl_image_compare
def test_gsm_sim_orthview(fixture_aa_gsm_sim):
    """Test plotting routines."""
    aa = fixture_aa_gsm_sim
    aa.simulation.orthview_gsm()
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_gsm_sim_mollview(fixture_aa_gsm_sim):
    """Test plotting routines."""
    aa = fixture_aa_gsm_sim
    aa.simulation.mollview_gsm()
    return plt.gcf()


#############
## SIM VIS ##
#############


def test_gsm_sim(fixture_aa_gsm_sim):
    """Test all-sky visibility GSM simulation."""
    aa = fixture_aa_gsm_sim
    vis = aa.simulation.sim_vis_gsm()
    assert vis.shape == (1, 1, 256, 256, 4)

    # Polarized beam
    vis = aa.simulation.sim_vis_gsm(apply_aep=True)
    assert vis.shape == (1, 1, 256, 256, 4)

    vis = aa.simulation.sim_vis_gsm(as_xarray=False)
    assert vis.shape == (256, 256, 4)

    aa.simulation.sim_vis_gsm(nside=64)
    aa.simulation.sim_vis_gsm(sky_model='lfsm')
    aa.simulation.sim_vis_gsm(mode='stokes')


def test_pointsrc_sim(fixture_aa_gsm_sim):
    """Test simple point source simulation."""
    aa = fixture_aa_gsm_sim
    sky_model = {'SUN': aa.coords.get_sun()}
    vis = aa.simulation.sim_vis_pointsrc(sky_model)
    assert vis.shape == (1, 1, 256, 256, 4)


##############
## SIM BEAM ##
##############


@pytest.mark.mpl_image_compare
def test_beam_cut(fixture_aa_beam_sim):
    """Test beam cut plotting."""
    aa, pc = fixture_aa_beam_sim
    plt.figure()
    aa.simulation.sim_station_beam(phase_center=pc, show=True, plot_type='cut', n_pix=257, db=True)
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_beam_cut_subplots(fixture_aa_beam_sim):
    """Test beam cut plotting with subplots."""
    aa, pc = fixture_aa_beam_sim
    plt.figure(figsize=(8, 4))
    _ = aa.simulation.sim_station_beam(
        phase_center=pc, show=True, plot_type='cut', n_pix=257, reuse_fig=True, db=True
    )

    aa.f[0] = Quantity(250, unit='MHz')
    _ = aa.simulation.sim_station_beam(
        phase_center=pc, show=True, plot_type='cut', n_pix=257, reuse_fig=True, db=True
    )
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_beam_cut_subplots_aep(fixture_aa_beam_sim):
    """Test beam cut plotting with subplots."""
    aa, pc = fixture_aa_beam_sim
    plt.figure(figsize=(8, 4))
    _ = aa.simulation.sim_station_beam(
        phase_center=pc, show=True, plot_type='cut', n_pix=257, reuse_fig=True, db=True, apply_aep=True
    )

    aa.f[0] = Quantity(250, unit='MHz')
    _ = aa.simulation.sim_station_beam(
        phase_center=pc, show=True, plot_type='cut', n_pix=257, reuse_fig=True, db=True, apply_aep=True
    )
    return plt.gcf()


@pytest.mark.mpl_image_compare
def test_orthview_beam(fixture_aa_beam_sim):
    """Test orthview beam plotting."""
    aa, pc = fixture_aa_beam_sim
    plt.figure(figsize=(8, 4))
    aa.simulation.sim_station_beam(
        phase_center=pc,
        show=True,
        plot_type='orthview',
        n_pix=257,
        reuse_fig=True,
        subplot_id=(1, 2, 1),
        db=True,
    )
    aa.simulation.sim_station_beam(
        phase_center=pc,
        show=True,
        plot_type='orthview',
        n_pix=257,
        reuse_fig=True,
        subplot_id=(1, 2, 2),
        db=True,
    )
    return plt.gcf()


def test_sim_station_beam(fixture_aa_beam_sim):
    """Test simulation of beam."""
    aa, pc = fixture_aa_beam_sim
    bp = aa.simulation.sim_station_beam(phase_center=pc, show=False, n_pix=257)
    assert bp.shape == (257, 257)


if __name__ == '__main__':
    test_gsm_sim_mollview()
    test_gsm_sim_orthview()
    test_gsm_sim()
    test_sim_station_beam()
