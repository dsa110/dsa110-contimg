"""peel: Basic source peeling routines."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    from astropy.coordinates import SkyCoord

    from ..aperture_array import ApertureArray

import numpy as np

from ..sky_model import RadioSource


def peel(aa: ApertureArray, src: SkyCoord):
    """Basic source peeling routine."""
    m0 = RadioSource(src.ra, src.dec, mag=1.0)
    idx0 = aa.viewer.get_pixel(src)

    # Simulate point source with mag=1
    aa.simulation.sim_vis_pointsrc({'src0': m0})
    img_m0 = aa.make_image(vis='model')
    mag_m0 = img_m0[idx0]

    # Get magnitude of point source in data
    v_d = aa.generate_vis_matrix('data')
    img_d = aa.make_image(vis='data')
    mag_d = img_d[idx0]
    mag_d_avg = np.nanmedian(img_d)

    # We can now scale model magnitude to data and subtract
    src_mag = np.sqrt((mag_d[0] - mag_d_avg) / mag_m0[0])
    m_src = RadioSource(src.ra, src.dec, mag=src_mag)
    v_m = aa.simulation.sim_vis_pointsrc({'src0': m_src})

    # Apply peeling

    v_peel = v_d - v_m
    return v_peel
