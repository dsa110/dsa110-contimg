"""test_postx_calibration: test routines in postx.calibration."""

import matplotlib.pyplot as plt
import numpy as np
import pytest
from astropy.coordinates import get_sun

from ska_ost_low_uv.io import hdf5_to_uvx
from ska_ost_low_uv.postx import ApertureArray
from ska_ost_low_uv.postx.simulation.simple_sim import simulate_visibilities_pointsrc
from ska_ost_low_uv.postx.sky_model import generate_skycat
from ska_ost_low_uv.postx.viewer.aa_viewer import AllSkyViewer
from ska_ost_low_uv.utils import get_aa_config, get_test_data

FN_RAW = get_test_data('aavs2_1x1000ms/correlation_burst_204_20230823_21356_0.hdf5')
YAML_RAW = get_aa_config('aavs2')


@pytest.mark.mpl_image_compare
def test_calibration():
    """Test calibration.

    TODO: Get stefcal working.
    """
    vis = hdf5_to_uvx(FN_RAW, yaml_config=YAML_RAW)

    aa = ApertureArray(vis)
    asv = AllSkyViewer(aa)
    sc = generate_skycat(aa)
    asv.load_labels(sc)

    # Uncalibrated
    img_raw = aa.imaging.make_image(128)

    # Generate model visibilities (Sun)
    sky_model = {'sun': get_sun(aa.t[0])}
    v_model = simulate_visibilities_pointsrc(aa, sky_model=sky_model)
    aa.simulation.model.visibilities = v_model

    # Image model visibilities
    img_model = aa.imaging.make_image(128, vis='model')

    # Run stefcal and make calibrated image
    aa.calibration.holography.set_cal_src(aa.coords.get_sun())
    cal = aa.calibration.holography.run_phasecal()

    aa.set_cal(cal)
    img_c = aa.imaging.make_image(vis='cal')

    # plt.plot(g)
    # plt.show()

    plt.figure(figsize=(10, 4))
    asv.orthview(
        np.log(img_raw),
        overlay_srcs=True,
        reuse_fig=True,
        subplot_id=(1, 3, 1),
        title='data',
        colorbar=True,
    )

    asv.orthview(
        np.log(img_c), overlay_srcs=True, subplot_id=(1, 3, 2), reuse_fig=True, title='cal', colorbar=True
    )

    asv.orthview(
        np.log(img_model),
        overlay_srcs=True,
        reuse_fig=True,
        subplot_id=(1, 3, 3),
        title='model',
        colorbar=True,
    )
    return plt.gcf()


if __name__ == '__main__':
    test_calibration()
