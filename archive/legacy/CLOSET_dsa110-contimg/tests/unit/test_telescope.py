# tests/unit/test_telescope.py
"""
Unit tests for telescope-specific modules.

This module contains unit tests for DSA-110 telescope constants,
utilities, and beam models.
"""

import pytest
import numpy as np
from astropy.coordinates import EarthLocation
import astropy.units as u

from dsa110.telescope.dsa110 import (
    get_valid_antennas, get_valid_antenna_names, is_valid_antenna,
    get_telescope_location, get_dish_diameter,
    ant_inds_to_names_dsa110, ant_names_to_inds_dsa110
)
from dsa110.telescope.beam_models import (
    pb_dsa110, pb_dsa110_airy, get_beam_model,
    calculate_beam_fwhm, calculate_beam_hpbw
)


class TestDSA110Constants:
    """Test cases for DSA-110 telescope constants."""
    
    def test_get_valid_antennas(self):
        """Test getting valid antenna indices."""
        antennas = get_valid_antennas()
        
        assert isinstance(antennas, np.ndarray)
        assert len(antennas) > 0
        assert np.all(antennas >= 0)
        assert np.all(antennas <= 116)
    
    def test_get_valid_antenna_names(self):
        """Test getting valid antenna names."""
        names = get_valid_antenna_names()
        
        assert isinstance(names, np.ndarray)
        assert len(names) > 0
        assert all(name.startswith('pad') for name in names)
        assert all(name[3:].isdigit() for name in names)
    
    def test_is_valid_antenna(self):
        """Test antenna validation."""
        # Test valid antenna
        assert is_valid_antenna(0) is True
        assert is_valid_antenna(1) is True
        
        # Test invalid antenna
        assert is_valid_antenna(200) is False
        assert is_valid_antenna(-1) is False
    
    def test_get_telescope_location(self):
        """Test getting telescope location."""
        location = get_telescope_location()
        
        assert isinstance(location, EarthLocation)
        assert location.info.name == 'CARMA'
        assert location.lat.unit == u.rad
        assert location.lon.unit == u.rad
        assert location.height.unit == u.m
    
    def test_get_dish_diameter(self):
        """Test getting dish diameter."""
        diameter = get_dish_diameter()
        
        assert isinstance(diameter, float)
        assert diameter > 0
        assert diameter == 4.7  # Expected value
    
    def test_ant_inds_to_names(self):
        """Test converting antenna indices to names."""
        # Test single index
        name = ant_inds_to_names_dsa110([0])
        assert name[0] == 'pad1'
        
        # Test multiple indices
        names = ant_inds_to_names_dsa110([0, 1, 2])
        expected = ['pad1', 'pad2', 'pad3']
        assert np.array_equal(names, expected)
        
        # Test invalid index
        with pytest.raises(ValueError, match="Index too high/low"):
            ant_inds_to_names_dsa110([200])
    
    def test_ant_names_to_inds(self):
        """Test converting antenna names to indices."""
        # Test single name
        ind = ant_names_to_inds_dsa110(['pad1'])
        assert ind[0] == 0
        
        # Test multiple names
        inds = ant_names_to_inds_dsa110(['pad1', 'pad2', 'pad3'])
        expected = [0, 1, 2]
        assert np.array_equal(inds, expected)
        
        # Test invalid name
        with pytest.raises(ValueError, match="Name not recognized"):
            ant_names_to_inds_dsa110(['invalid'])


class TestBeamModels:
    """Test cases for beam models."""
    
    def test_pb_dsa110_gaussian(self):
        """Test Gaussian primary beam model."""
        # Test parameters
        dist = np.array([0.0, 0.1, 0.2])  # radians
        freq = np.array([1.4e9, 1.5e9, 1.6e9])  # Hz
        
        # Calculate beam response
        pb = pb_dsa110(dist, freq)
        
        # Check output shape
        assert pb.shape == (3, 1, 3, 1)
        
        # Check that response is maximum at center
        assert pb[0, 0, :, 0].max() == 1.0
        
        # Check that response decreases with distance
        for i in range(len(freq)):
            assert pb[0, 0, i, 0] > pb[1, 0, i, 0] > pb[2, 0, i, 0]
    
    def test_pb_dsa110_airy(self):
        """Test Airy disk primary beam model."""
        # Test parameters
        dist = np.array([0.0, 0.1, 0.2])  # radians
        freq = np.array([1.4e9, 1.5e9, 1.6e9])  # Hz
        
        # Calculate beam response
        pb = pb_dsa110_airy(dist, freq)
        
        # Check output shape
        assert pb.shape == (3, 1, 3, 1)
        
        # Check that response is maximum at center
        assert pb[0, 0, :, 0].max() == 1.0
        
        # Check that response decreases with distance
        for i in range(len(freq)):
            assert pb[0, 0, i, 0] > pb[1, 0, i, 0] > pb[2, 0, i, 0]
    
    def test_get_beam_model(self):
        """Test getting beam model functions."""
        # Test Gaussian model
        gaussian_model = get_beam_model('gaussian')
        assert gaussian_model == pb_dsa110
        
        # Test Airy model
        airy_model = get_beam_model('airy')
        assert airy_model == pb_dsa110_airy
        
        # Test invalid model
        with pytest.raises(ValueError, match="Unknown beam model type"):
            get_beam_model('invalid')
    
    def test_calculate_beam_fwhm(self):
        """Test calculating beam FWHM."""
        # Test single frequency
        freq = 1.5e9  # Hz
        fwhm_gaussian = calculate_beam_fwhm(freq, model='gaussian')
        fwhm_airy = calculate_beam_fwhm(freq, model='airy')
        
        assert fwhm_gaussian > 0
        assert fwhm_airy > 0
        assert fwhm_gaussian != fwhm_airy  # Different models should give different results
        
        # Test frequency array
        freqs = np.array([1.4e9, 1.5e9, 1.6e9])
        fwhm_array = calculate_beam_fwhm(freqs, model='gaussian')
        
        assert len(fwhm_array) == len(freqs)
        assert np.all(fwhm_array > 0)
        
        # Test invalid model
        with pytest.raises(ValueError, match="Unknown beam model type"):
            calculate_beam_fwhm(freq, model='invalid')
    
    def test_calculate_beam_hpbw(self):
        """Test calculating beam HPBW."""
        # Test single frequency
        freq = 1.5e9  # Hz
        hpbw_gaussian = calculate_beam_hpbw(freq, model='gaussian')
        hpbw_airy = calculate_beam_hpbw(freq, model='airy')
        
        assert hpbw_gaussian > 0
        assert hpbw_airy > 0
        assert hpbw_gaussian != hpbw_airy  # Different models should give different results
        
        # Test frequency array
        freqs = np.array([1.4e9, 1.5e9, 1.6e9])
        hpbw_array = calculate_beam_hpbw(freqs, model='gaussian')
        
        assert len(hpbw_array) == len(freqs)
        assert np.all(hpbw_array > 0)
        
        # Test invalid model
        with pytest.raises(ValueError, match="Unknown beam model type"):
            calculate_beam_hpbw(freq, model='invalid')
    
    def test_beam_frequency_dependence(self):
        """Test that beam size depends on frequency."""
        # Test that higher frequencies give smaller beams
        freq_low = 1.4e9
        freq_high = 1.6e9
        
        fwhm_low = calculate_beam_fwhm(freq_low, model='gaussian')
        fwhm_high = calculate_beam_fwhm(freq_high, model='gaussian')
        
        assert fwhm_low > fwhm_high  # Lower frequency should give larger beam
        
        hpbw_low = calculate_beam_hpbw(freq_low, model='gaussian')
        hpbw_high = calculate_beam_hpbw(freq_high, model='gaussian')
        
        assert hpbw_low > hpbw_high  # Lower frequency should give larger beam
    
    def test_beam_model_consistency(self):
        """Test consistency between different beam model functions."""
        # Test parameters
        dist = np.array([0.0, 0.1, 0.2])
        freq = np.array([1.5e9])
        
        # Calculate using direct function
        pb_direct = pb_dsa110(dist, freq)
        
        # Calculate using get_beam_model
        model_func = get_beam_model('gaussian')
        pb_model = model_func(dist, freq)
        
        # Results should be identical
        assert np.allclose(pb_direct, pb_model)
