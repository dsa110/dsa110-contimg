"""Test aa_plotter plotting routines."""

import pylab as plt
import pytest

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.utils import get_test_data

uvx = hdf5_to_uvx(
    get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5'),
    telescope_name='aavs2',
)
aa = ApertureArray(uvx)


@pytest.mark.mpl_image_compare
def test_plot_antennas():
    """Test plotting routines."""
    fig = plt.figure('ANT')
    aa.plotting.plot_antennas()
    aa.plotting.plot_antennas(overlay_names=True)
    return fig


@pytest.mark.mpl_image_compare
def test_corr_matrix():
    """Test plotting routines."""
    fig = plt.figure('CORR')
    aa.plotting.plot_corr_matrix()
    return fig


@pytest.mark.mpl_image_compare
def test_plot_corr_matrix_4x():
    """Test plotting routines."""
    fig = aa.plotting.plot_corr_matrix_4pol()
    return fig


@pytest.mark.mpl_image_compare
def test_plot_uvdist_amp():
    """Test plotting routines."""
    fig = plt.figure('UV DIST')
    aa.plotting.plot_uvdist_amp()
    return fig
