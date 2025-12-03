"""
Tests for the visualization module.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from dsa110_contimg.visualization import (
    FigureConfig,
    PlotStyle,
    ReportMetadata,
    ReportSection,
    generate_html_report,
)
from dsa110_contimg.visualization.config import FigureConfig


class TestFigureConfig:
    """Tests for FigureConfig."""
    
    def test_default_config(self):
        """Default config should have sensible values."""
        config = FigureConfig()
        # Default is quicklook style with these values
        assert config.dpi == 140  # Quicklook DPI
        assert config.figsize == (6, 5)  # Quicklook figsize
        assert config.style == PlotStyle.QUICKLOOK
    
    def test_quicklook_preset(self):
        """Quicklook style should have moderate DPI."""
        config = FigureConfig(style=PlotStyle.QUICKLOOK)
        assert config.dpi == 140
        assert config.figsize == (6, 5)
    
    def test_publication_preset(self):
        """Publication style should have higher DPI."""
        config = FigureConfig(style=PlotStyle.PUBLICATION)
        # Publication preset sets 300 DPI
        assert config.dpi == 300
        # Font scale should be appropriate
        assert config.font_size >= 12
    
    def test_effective_properties(self):
        """Effective properties should compute derived values."""
        config = FigureConfig(font_size=10)
        # Effective sizes should be based on font_size
        assert config.effective_tick_size == int(10 * 0.9)  # 9
        assert config.effective_label_size == 10
        assert config.effective_title_size == int(10 * 1.2)  # 12


class TestReportGeneration:
    """Tests for HTML/PDF report generation."""
    
    def test_report_metadata_defaults(self):
        """ReportMetadata should have sensible defaults."""
        meta = ReportMetadata()
        assert meta.title == "DSA-110 Pipeline Report"
        assert meta.author == "DSA-110 Continuum Imaging Pipeline"
    
    def test_report_metadata_custom(self):
        """ReportMetadata should accept custom values."""
        meta = ReportMetadata(
            title="Custom Report",
            observation_id="test123"
        )
        assert meta.title == "Custom Report"
        assert meta.observation_id == "test123"
    
    def test_generate_html_report(self, tmp_path):
        """generate_html_report should create valid HTML."""
        sections = [
            ReportSection(
                title="Test Section",
                content="This is a test section with some content."
            )
        ]
        
        output_path = tmp_path / "test_report.html"
        result = generate_html_report(sections, output_path)
        
        assert result.exists()
        html_content = result.read_text()
        assert "<html" in html_content
        assert "Test Section" in html_content
        assert "test section with some content" in html_content
    
    def test_report_with_tables(self, tmp_path):
        """Reports should render tables correctly."""
        sections = [
            ReportSection(
                title="Data Section",
                tables=[{
                    "Parameter A": 1.234,
                    "Parameter B": "value",
                }],
                table_captions=["Test Parameters"]
            )
        ]
        
        output_path = tmp_path / "table_report.html"
        result = generate_html_report(sections, output_path)
        
        html_content = result.read_text()
        assert "<table" in html_content
        assert "Parameter A" in html_content
        assert "1.234" in html_content


class TestPlotFunctions:
    """Tests for plotting functions."""
    
    def test_plot_lightcurve_basic(self, tmp_path):
        """plot_lightcurve should work with basic inputs."""
        from astropy.time import Time
        from dsa110_contimg.visualization.source_plots import plot_lightcurve
        
        flux = np.array([1.0, 1.1, 0.9, 1.2])
        # Use proper astropy Time objects with MJD format
        times = Time([60000.0, 60000.1, 60000.2, 60000.3], format="mjd")
        
        output = tmp_path / "lightcurve.png"
        fig = plot_lightcurve(flux, times, output=output)
        assert fig is not None
        assert output.exists()
    
    def test_plot_spectrum_basic(self, tmp_path):
        """plot_spectrum should work with basic inputs."""
        from dsa110_contimg.visualization.source_plots import plot_spectrum
        
        flux = np.array([1.0, 0.9, 0.8, 0.7])
        freq_ghz = np.array([1.0, 1.2, 1.4, 1.6])
        
        output = tmp_path / "spectrum.png"
        fig = plot_spectrum(flux, freq_ghz, output=output)
        assert fig is not None
        assert output.exists()
    
    def test_plot_source_comparison_basic(self, tmp_path):
        """plot_source_comparison should work with basic inputs."""
        from dsa110_contimg.visualization.source_plots import plot_source_comparison
        
        measured = np.array([1.0, 2.0, 3.0, 4.0])
        reference = np.array([1.1, 1.9, 3.2, 3.8])
        
        output = tmp_path / "comparison.png"
        fig = plot_source_comparison(measured, reference, output=output, show_ratio=False)
        assert fig is not None
        assert output.exists()


class TestTileGrid:
    """Tests for mosaic tile visualization."""
    
    @pytest.fixture
    def synthetic_tiles(self, tmp_path):
        """Create synthetic tile FITS files."""
        from astropy.io import fits
        
        tiles = []
        for i in range(4):
            data = np.random.randn(100, 100)
            hdu = fits.PrimaryHDU(data)
            tile_path = tmp_path / f"tile_{i}.fits"
            hdu.writeto(tile_path)
            tiles.append(tile_path)
        return tiles
    
    def test_plot_tile_grid(self, synthetic_tiles, tmp_path):
        """plot_tile_grid should create a grid of thumbnails."""
        from dsa110_contimg.visualization.mosaic_plots import plot_tile_grid
        
        output_path = tmp_path / "tile_grid.png"
        fig = plot_tile_grid(synthetic_tiles, output=output_path, ncols=2)
        
        assert output_path.exists()
        assert fig is not None
