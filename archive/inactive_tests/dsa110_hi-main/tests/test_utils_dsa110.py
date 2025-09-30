import numpy as np
from dsa110hi.utils_dsa110 import *

def test_loc_dsa110():

    assert loc_dsa110.info.name == 'CARMA'

    assert np.isclose(loc_dsa110.lon.rad,-2.064427799136453)
    assert np.isclose(loc_dsa110.lat.rad,0.6498455107238486)
    assert np.isclose(loc_dsa110.height.value,1188.0519)

def test_pb_dsa110():
    # Try 5 distances by 10 frequencies
    dist = np.linspace(0,1/180*np.pi,5)
    freq = np.linspace(1.3,1.5,10)

    pb = pb_dsa110(dist, freq)
    assert pb.shape == (5,1,10,1)

    assert np.isclose(diam_dsa110, 4.7)

def test_pb_val():
    dist = np.array([0,1/180*np.pi])
    freq = np.array([1.3])

    width = 1.2 * 0.299792458 / freq / diam_dsa110 / 2.355
    resp = np.exp(-0.5 * (dist/width)**2)

    pb = pb_dsa110(dist, freq)

    assert np.isclose(pb.flatten()[0], 1)
    assert np.isclose(resp[0], 1)
    assert np.isclose(pb.flatten()[0], resp[0])
    assert np.isclose(pb.flatten()[1], resp[1])







def pb_dsa110(dist, freq, diameter=4.7):
    wl = 0.299792458 / freq
    fwhm = 1.2 * wl / diameter
    sigma = fwhm / 2.355
    pb = np.exp(-0.5 * (dist.reshape(-1,1,1,1) / sigma.reshape(1,1,-1,1))**2)
    return pb

