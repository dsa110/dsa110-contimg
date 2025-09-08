# core/telescope/beam_models.py
"""
Primary beam models for DSA-110 telescope.

This module provides primary beam response calculations for the DSA-110
telescope array.
"""

import numpy as np
from .dsa110 import diam_dsa110


def pb_dsa110(dist, freq, diameter=diam_dsa110):
    """
    Calculate the primary beam response for DSA-110.
    
    Returns the response in an array of shape (N_distances, 1, N_frequencies, 1),
    which is what is needed for the MS maker.
    
    Assumes a simple Gaussian beam with a 1.2 λ/D FWHM.
    
    Parameters
    ----------
    dist : ndarray
        Array of angular offsets from the pointing direction of the telescope, in radians
    freq : ndarray
        Array of frequencies at which to calculate the beam response, in GHz
    diameter : float
        Dish diameter in meters
        
    Returns
    -------
    ndarray
        Primary beam response with shape (N_distances, 1, N_frequencies, 1)
    """
    # Convert frequency to wavelength
    wl = 0.299792458 / freq  # wavelength in meters
    
    # Calculate FWHM and sigma
    fwhm = 1.2 * wl / diameter  # FWHM in radians
    sigma = fwhm / 2.355  # sigma in radians
    
    # Calculate Gaussian beam response
    # Reshape arrays to ensure proper broadcasting
    dist_reshaped = dist.reshape(-1, 1, 1, 1)
    sigma_reshaped = sigma.reshape(1, 1, -1, 1)
    
    pb = np.exp(-0.5 * (dist_reshaped / sigma_reshaped)**2)
    
    return pb


def pb_dsa110_airy(dist, freq, diameter=diam_dsa110):
    """
    Calculate the primary beam response using Airy disk model.
    
    This provides a more accurate model for the primary beam compared to
    the Gaussian approximation.
    
    Parameters
    ----------
    dist : ndarray
        Array of angular offsets from the pointing direction, in radians
    freq : ndarray
        Array of frequencies at which to calculate the beam response, in GHz
    diameter : float
        Dish diameter in meters
        
    Returns
    -------
    ndarray
        Primary beam response with shape (N_distances, 1, N_frequencies, 1)
    """
    # Convert frequency to wavelength
    wl = 0.299792458 / freq  # wavelength in meters
    
    # Calculate first null position
    first_null = 1.22 * wl / diameter  # in radians
    
    # Reshape arrays for broadcasting
    dist_reshaped = dist.reshape(-1, 1, 1, 1)
    first_null_reshaped = first_null.reshape(1, 1, -1, 1)
    
    # Avoid division by zero
    x = np.where(first_null_reshaped > 0, 
                 np.pi * dist_reshaped / first_null_reshaped, 
                 0)
    
    # Calculate Airy disk response
    # Use approximation for small x to avoid numerical issues
    pb = np.where(x < 1e-10, 1.0, 
                  (2 * np.sin(x) / x)**2)
    
    return pb


def get_beam_model(model_type='gaussian'):
    """
    Get a beam model function.
    
    Parameters
    ----------
    model_type : str
        Type of beam model ('gaussian' or 'airy')
        
    Returns
    -------
    callable
        Beam model function
    """
    if model_type.lower() == 'gaussian':
        return pb_dsa110
    elif model_type.lower() == 'airy':
        return pb_dsa110_airy
    else:
        raise ValueError(f"Unknown beam model type: {model_type}")


def calculate_beam_fwhm(freq, diameter=diam_dsa110, model='gaussian'):
    """
    Calculate the FWHM of the primary beam.
    
    Parameters
    ----------
    freq : float or ndarray
        Frequency in GHz
    diameter : float
        Dish diameter in meters
    model : str
        Beam model type ('gaussian' or 'airy')
        
    Returns
    -------
    float or ndarray
        FWHM in radians
    """
    wl = 0.299792458 / freq  # wavelength in meters
    
    if model.lower() == 'gaussian':
        return 1.2 * wl / diameter
    elif model.lower() == 'airy':
        # For Airy disk, FWHM ≈ 1.02 * λ/D
        return 1.02 * wl / diameter
    else:
        raise ValueError(f"Unknown beam model type: {model}")


def calculate_beam_hpbw(freq, diameter=diam_dsa110, model='gaussian'):
    """
    Calculate the Half Power Beam Width (HPBW) of the primary beam.
    
    Parameters
    ----------
    freq : float or ndarray
        Frequency in GHz
    diameter : float
        Dish diameter in meters
    model : str
        Beam model type ('gaussian' or 'airy')
        
    Returns
    -------
    float or ndarray
        HPBW in radians
    """
    if model.lower() == 'gaussian':
        # For Gaussian, HPBW = FWHM
        return calculate_beam_fwhm(freq, diameter, model)
    elif model.lower() == 'airy':
        # For Airy disk, HPBW ≈ 0.89 * λ/D
        wl = 0.299792458 / freq
        return 0.89 * wl / diameter
    else:
        raise ValueError(f"Unknown beam model type: {model}")


class GaussianBeamModel:
    """Gaussian primary beam model for DSA-110."""
    
    def __init__(self, diameter=4.7, frequency=1.4e9):
        """
        Initialize Gaussian beam model.
        
        Args:
            diameter: Dish diameter in meters
            frequency: Reference frequency in Hz
        """
        self.diameter = diameter
        self.frequency = frequency
    
    def get_fwhm(self, frequency=None):
        """Get FWHM at given frequency."""
        if frequency is None:
            frequency = self.frequency
        return calculate_beam_fwhm(frequency / 1e9, self.diameter, 'gaussian')
    
    def get_hpbw(self, frequency=None):
        """Get HPBW at given frequency."""
        if frequency is None:
            frequency = self.frequency
        return calculate_beam_hpbw(frequency / 1e9, self.diameter, 'gaussian')


class AiryDiskBeamModel:
    """Airy disk primary beam model for DSA-110."""
    
    def __init__(self, diameter=4.7, frequency=1.4e9):
        """
        Initialize Airy disk beam model.
        
        Args:
            diameter: Dish diameter in meters
            frequency: Reference frequency in Hz
        """
        self.diameter = diameter
        self.frequency = frequency
    
    def get_fwhm(self, frequency=None):
        """Get FWHM at given frequency."""
        if frequency is None:
            frequency = self.frequency
        return calculate_beam_fwhm(frequency / 1e9, self.diameter, 'airy')
    
    def get_hpbw(self, frequency=None):
        """Get HPBW at given frequency."""
        if frequency is None:
            frequency = self.frequency
        return calculate_beam_hpbw(frequency / 1e9, self.diameter, 'airy')
