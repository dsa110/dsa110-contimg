"""
Unit tests for Source class (VAST Tools adoption).

Tests the Source class pattern adopted from VAST Tools for DSA-110.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from astropy.coordinates import SkyCoord
from astropy import units as u

from dsa110_contimg.photometry.source import Source, SourceError
from dsa110_contimg.photometry.variability import (
    calculate_eta_metric,
    calculate_vs_metric,
    calculate_m_metric,
)


class TestSourceClass:
    """Test Source class creation and properties."""
    
    def test_source_creation_with_coords(self):
        """Test Source creation with explicit coordinates."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        assert source.source_id == "TEST001"
        assert source.ra_deg == 123.0
        assert source.dec_deg == 45.0
        assert source.name == "TEST001"
        assert isinstance(source.coord, SkyCoord)
        assert source.coord.ra.deg == 123.0
        assert source.coord.dec.deg == 45.0
    
    def test_source_creation_with_name(self):
        """Test Source creation with custom name."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0,
            name="Test Source"
        )
        assert source.name == "Test Source"
        assert source.source_id == "TEST001"
    
    def test_source_creation_missing_coords(self):
        """Test Source creation fails without coordinates or database."""
        with pytest.raises(SourceError):
            Source(source_id="TEST001")
    
    def test_source_empty_measurements(self):
        """Test Source with empty measurements."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        assert source.n_epochs == 0
        assert source.detections == 0
    
    def test_source_with_measurements(self):
        """Test Source with mock measurements."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        # Add mock measurements
        source.measurements = pd.DataFrame({
            'mjd': [59000.0, 59010.0, 59020.0],
            'normalized_flux_jy': [1.0, 1.1, 0.9],
            'normalized_flux_err_jy': [0.05, 0.05, 0.05],
            'peak_jyb': [1.0, 1.1, 0.9],
            'peak_err_jyb': [0.05, 0.05, 0.05],
            'image_path': ['img1.fits', 'img2.fits', 'img3.fits'],
        })
        
        assert source.n_epochs == 3
        assert source.detections == 3  # All have SNR > 3
    
    def test_source_detections_with_snr(self):
        """Test detections property with SNR column."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'mjd': [59000.0, 59010.0],
            'snr': [10.0, 2.0],  # One detection, one non-detection
            'normalized_flux_jy': [1.0, 0.5],
            'normalized_flux_err_jy': [0.05, 0.25],
        })
        
        assert source.detections == 1  # Only SNR > 5


class TestVariabilityMetrics:
    """Test variability metric calculations."""
    
    def test_eta_metric(self):
        """Test η metric calculation."""
        df = pd.DataFrame({
            'normalized_flux_jy': [1.0, 1.1, 0.9, 1.05],
            'normalized_flux_err_jy': [0.05, 0.05, 0.05, 0.05]
        })
        
        eta = calculate_eta_metric(df)
        assert isinstance(eta, float)
        assert eta >= 0.0
    
    def test_eta_metric_single_point(self):
        """Test η metric with single point returns 0."""
        df = pd.DataFrame({
            'normalized_flux_jy': [1.0],
            'normalized_flux_err_jy': [0.05]
        })
        
        eta = calculate_eta_metric(df)
        assert eta == 0.0
    
    def test_vs_metric(self):
        """Test Vs metric calculation."""
        vs = calculate_vs_metric(
            flux_a=1.0,
            flux_b=1.1,
            flux_err_a=0.05,
            flux_err_b=0.05
        )
        assert isinstance(vs, float)
        # Should be negative since flux_a < flux_b
        assert vs < 0
    
    def test_m_metric(self):
        """Test m metric calculation."""
        m = calculate_m_metric(flux_a=1.0, flux_b=1.1)
        assert isinstance(m, float)
        # Should be negative since flux_a < flux_b
        assert m < 0
    
    def test_m_metric_zero_sum(self):
        """Test m metric with zero sum raises error."""
        with pytest.raises(ValueError):
            calculate_m_metric(flux_a=1.0, flux_b=-1.0)


class TestSourceVariabilityMetrics:
    """Test Source class variability metric methods."""
    
    def test_calc_variability_metrics_empty(self):
        """Test variability metrics with no measurements."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        metrics = source.calc_variability_metrics()
        assert metrics['v'] == 0.0
        assert metrics['eta'] == 0.0
        assert metrics['n_epochs'] == 0
    
    def test_calc_variability_metrics_single_point(self):
        """Test variability metrics with single measurement."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'normalized_flux_jy': [1.0],
            'normalized_flux_err_jy': [0.05],
        })
        
        metrics = source.calc_variability_metrics()
        assert metrics['v'] == 0.0
        assert metrics['eta'] == 0.0
        assert metrics['n_epochs'] == 1
    
    def test_calc_variability_metrics_multiple_points(self):
        """Test variability metrics with multiple measurements."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'normalized_flux_jy': [1.0, 1.1, 0.9, 1.05, 0.95],
            'normalized_flux_err_jy': [0.05, 0.05, 0.05, 0.05, 0.05],
            'mjd': [59000.0, 59010.0, 59020.0, 59030.0, 59040.0],
        })
        
        metrics = source.calc_variability_metrics()
        assert 'v' in metrics
        assert 'eta' in metrics
        assert 'vs_mean' in metrics
        assert 'm_mean' in metrics
        assert metrics['n_epochs'] == 5
        assert metrics['v'] >= 0.0
        assert metrics['eta'] >= 0.0


class TestLightCurvePlotting:
    """Test light curve plotting functionality."""
    
    def test_plot_lightcurve_insufficient_points(self):
        """Test light curve plotting fails with insufficient points."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'normalized_flux_jy': [1.0],
            'normalized_flux_err_jy': [0.05],
        })
        
        with pytest.raises(SourceError):
            source.plot_lightcurve(min_points=2)
    
    def test_plot_lightcurve_success(self):
        """Test light curve plotting succeeds with valid data."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'normalized_flux_jy': [1.0, 1.1, 0.9],
            'normalized_flux_err_jy': [0.05, 0.05, 0.05],
            'mjd': [59000.0, 59010.0, 59020.0],
            'image_path': ['img1.fits', 'img2.fits', 'img3.fits'],
        })
        
        fig = source.plot_lightcurve()
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)
    
    def test_plot_lightcurve_mjd(self):
        """Test light curve plotting with MJD time axis."""
        source = Source(
            source_id="TEST001",
            ra_deg=123.0,
            dec_deg=45.0
        )
        
        source.measurements = pd.DataFrame({
            'normalized_flux_jy': [1.0, 1.1, 0.9],
            'normalized_flux_err_jy': [0.05, 0.05, 0.05],
            'mjd': [59000.0, 59010.0, 59020.0],
        })
        
        fig = source.plot_lightcurve(mjd=True)
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

