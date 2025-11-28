from dsa110_contimg.utils.constants import OVRO_LOCATION
from astropy.coordinates import EarthLocation, AltAz
import numpy as np

def phase_to_meridian(uvdata):
    """
    Phases the visibility data to the meridian.

    Parameters:
    uvdata : pyuvdata.UVData
        The UVData object containing visibility data.

    Returns:
    None
    """
    # OVRO_LOCATION is already an EarthLocation object
    location = OVRO_LOCATION

    # Use pyuvdata's phase_to_meridian method
    uvdata.phase_to_meridian()

def get_meridian_time(uvdata):
    """
    Gets the time at which the source is at the meridian.

    Parameters:
    uvdata : pyuvdata.UVData
        The UVData object containing visibility data.

    Returns:
    float
        The time at which the source is at the meridian.
    """
    # Placeholder for actual implementation
    return np.mean(uvdata.time_array)  # Example: return the mean time as a placeholder