"""Unit tests for PhotometryManager and PhotometryConfig."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import numpy as np
import pytest

from dsa110_contimg.photometry.manager import (
    PhotometryConfig,
    PhotometryManager,
    PhotometryResult,
)


@pytest.mark.unit
class TestPhotometryConfig:
    """Test PhotometryConfig class."""

    def test_default_initialization(self):
        """Test default configuration values."""
        config = PhotometryConfig()
        assert config.catalog == "nvss"
        assert config.radius_deg is None
        assert config.ra_radius_deg is None
        assert config.dec_radius_deg is None
        assert config.min_flux_mjy is None
        assert config.max_sources is None
        assert config.method == "peak"
        assert config.normalize is False
        assert config.detect_ese is False
        assert config.catalog_path is None
        assert config.auto_compute_extent is True

    def test_explicit_radius(self):
        """Test configuration with explicit radius."""
        config = PhotometryConfig(radius_deg=1.0)
        assert config.radius_deg == 1.0

    def test_explicit_ra_dec_radii(self):
        """Test configuration with explicit RA/Dec radii."""
        config = PhotometryConfig(ra_radius_deg=1.0, dec_radius_deg=0.5)
        assert config.ra_radius_deg == 1.0
        assert config.dec_radius_deg == 0.5

    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "catalog": "first",
            "radius_deg": 0.75,
            "method": "adaptive",
            "normalize": True,
        }
        config = PhotometryConfig.from_dict(config_dict)
        assert config.catalog == "first"
        assert config.radius_deg == 0.75
        assert config.method == "adaptive"
        assert config.normalize is True

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = PhotometryConfig(
            catalog="nvss",
            radius_deg=0.5,
            ra_radius_deg=1.0,
            dec_radius_deg=0.25,
        )
        config_dict = config.to_dict()
        assert config_dict["catalog"] == "nvss"
        assert config_dict["radius_deg"] == 0.5
        assert config_dict["ra_radius_deg"] == 1.0
        assert config_dict["dec_radius_deg"] == 0.25


@pytest.mark.unit
class TestPhotometryResult:
    """Test PhotometryResult class."""

    def test_result_initialization(self):
        """Test result initialization."""
        result = PhotometryResult(
            fits_path=Path("test.fits"),
            sources_queried=10,
            measurements_successful=8,
            measurements_total=10,
        )
        assert result.fits_path == Path("test.fits")
        assert result.sources_queried == 10
        assert result.measurements_successful == 8
        assert result.measurements_total == 10
        assert result.success_rate == 0.8

    def test_success_rate_zero_total(self):
        """Test success rate calculation with zero total."""
        result = PhotometryResult(
            fits_path=Path("test.fits"),
            sources_queried=0,
            measurements_successful=0,
            measurements_total=0,
        )
        assert result.success_rate == 0.0

    def test_result_with_batch_job_id(self):
        """Test result with batch job ID."""
        result = PhotometryResult(
            fits_path=Path("test.fits"),
            sources_queried=5,
            measurements_successful=0,
            measurements_total=5,
            batch_job_id=123,
        )
        assert result.batch_job_id == 123


@pytest.mark.unit
class TestPhotometryManagerInitialization:
    """Test PhotometryManager initialization."""

    def test_default_initialization(self, tmp_path):
        """Test manager initialization with defaults."""
        products_db = tmp_path / "products.sqlite3"
        manager = PhotometryManager(products_db_path=products_db)
        assert manager.products_db_path == products_db
        assert manager.data_registry_db_path is None
        assert manager.default_config.catalog == "nvss"

    def test_with_data_registry(self, tmp_path):
        """Test manager initialization with data registry."""
        products_db = tmp_path / "products.sqlite3"
        registry_db = tmp_path / "registry.sqlite3"
        manager = PhotometryManager(
            products_db_path=products_db,
            data_registry_db_path=registry_db,
        )
        assert manager.data_registry_db_path == registry_db

    def test_with_custom_config(self, tmp_path):
        """Test manager initialization with custom config."""
        products_db = tmp_path / "products.sqlite3"
        config = PhotometryConfig(catalog="first", radius_deg=1.0)
        manager = PhotometryManager(
            products_db_path=products_db,
            default_config=config,
        )
        assert manager.default_config.catalog == "first"
        assert manager.default_config.radius_deg == 1.0


@pytest.mark.unit
class TestGetSearchRadii:
    """Test _get_search_radii method."""

    def test_explicit_ra_dec_radii(self, tmp_path):
        """Test with explicit RA/Dec radii."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        config = PhotometryConfig(ra_radius_deg=1.0, dec_radius_deg=0.5)
        fits_path = tmp_path / "test.fits"

        ra_radius, dec_radius = manager._get_search_radii(fits_path, config)
        assert ra_radius == 1.0
        assert dec_radius == 0.5

    def test_explicit_radius_deg(self, tmp_path):
        """Test with explicit radius_deg (circular)."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        config = PhotometryConfig(radius_deg=0.75)
        fits_path = tmp_path / "test.fits"

        ra_radius, dec_radius = manager._get_search_radii(fits_path, config)
        assert ra_radius == 0.75
        assert dec_radius == 0.75

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_auto_compute_extent_success(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test auto-computing extent from FITS header."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        config = PhotometryConfig(auto_compute_extent=True)
        fits_path = tmp_path / "test.fits"

        # Setup mock FITS header
        mock_hdr = Mock()
        mock_hdr.get.side_effect = lambda key, default: {
            "NAXIS1": 2000,
            "NAXIS2": 500,
        }.get(key, default)

        mock_wcs = Mock()
        mock_wcs.has_celestial = True
        # Simulate elongated mosaic: 2° RA × 0.5° Dec
        corners_world = np.array(
            [
                [179.0, 34.75],  # Bottom-left
                [181.0, 34.75],  # Bottom-right
                [181.0, 35.25],  # Top-right
                [179.0, 35.25],  # Top-left
            ]
        )
        mock_wcs.all_pix2world.return_value = corners_world
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        ra_radius, dec_radius = manager._get_search_radii(fits_path, config)

        # Should be extent/2 * 1.1 (10% buffer)
        # RA extent: 2.0°, so radius = 1.0° * 1.1 = 1.1°
        # Dec extent: 0.5°, so radius = 0.25° * 1.1 = 0.275°
        assert abs(ra_radius - 1.1) < 0.01
        assert abs(dec_radius - 0.275) < 0.01

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_auto_compute_extent_failure_fallback(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test fallback when auto-compute fails."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        config = PhotometryConfig(auto_compute_extent=True)
        fits_path = tmp_path / "test.fits"

        # Mock WCS to raise error
        mock_wcs_class.side_effect = ValueError("WCS error")

        ra_radius, dec_radius = manager._get_search_radii(fits_path, config)

        # Should fallback to default 0.5°
        assert ra_radius == 0.5
        assert dec_radius == 0.5

    def test_fallback_to_default(self, tmp_path):
        """Test fallback to default when nothing is specified."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        config = PhotometryConfig(
            radius_deg=None,
            auto_compute_extent=False,
        )
        fits_path = tmp_path / "test.fits"

        ra_radius, dec_radius = manager._get_search_radii(fits_path, config)

        assert ra_radius == 0.5
        assert dec_radius == 0.5


@pytest.mark.unit
class TestComputeFieldExtent:
    """Test _compute_field_extent method."""

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_compute_extent_success(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test successful extent computation."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"

        # Setup mock
        mock_hdr = Mock()
        mock_hdr.get.side_effect = lambda key, default: {
            "NAXIS1": 1000,
            "NAXIS2": 500,
        }.get(key, default)

        mock_wcs = Mock()
        mock_wcs.has_celestial = True
        # Simulate 1° RA × 0.5° Dec mosaic
        corners_world = np.array(
            [
                [179.5, 34.75],
                [180.5, 34.75],
                [180.5, 35.25],
                [179.5, 35.25],
            ]
        )
        mock_wcs.all_pix2world.return_value = corners_world
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        ra_extent, dec_extent = manager._compute_field_extent(fits_path)

        assert abs(ra_extent - 1.0) < 0.01
        assert abs(dec_extent - 0.5) < 0.01

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_compute_extent_ra_wrap_around(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test extent computation with RA wrap-around."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"

        mock_hdr = Mock()
        mock_hdr.get.side_effect = lambda key, default: {
            "NAXIS1": 1000,
            "NAXIS2": 500,
        }.get(key, default)

        mock_wcs = Mock()
        mock_wcs.has_celestial = True
        # Simulate RA crossing 0/360 boundary
        corners_world = np.array(
            [
                [359.5, 34.75],  # Near 360°
                [0.5, 34.75],  # Crosses to 0°
                [0.5, 35.25],
                [359.5, 35.25],
            ]
        )
        mock_wcs.all_pix2world.return_value = corners_world
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        ra_extent, dec_extent = manager._compute_field_extent(fits_path)

        # Should handle wrap-around correctly
        assert ra_extent > 0
        assert dec_extent > 0

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_compute_extent_no_celestial(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test error when WCS has no celestial coordinates."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"

        mock_hdr = Mock()
        mock_wcs = Mock()
        mock_wcs.has_celestial = False
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        with pytest.raises(ValueError, match="no celestial WCS"):
            manager._compute_field_extent(fits_path)

    @patch("dsa110_contimg.photometry.manager.fits.open")
    @patch("dsa110_contimg.photometry.manager.WCS")
    def test_compute_extent_invalid_dimensions(self, mock_wcs_class, mock_fits_open, tmp_path):
        """Test error with invalid image dimensions."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"

        # Use actual FITS Header for WCS compatibility
        from astropy.io import fits as astropy_fits

        mock_hdr = astropy_fits.Header()
        mock_hdr["NAXIS1"] = 0
        mock_hdr["NAXIS2"] = 0

        mock_wcs = Mock()
        mock_wcs.has_celestial = True
        mock_wcs_class.return_value = mock_wcs

        mock_hdul = Mock()
        mock_hdul.__enter__ = Mock(return_value=[Mock(header=mock_hdr)])
        mock_hdul.__exit__ = Mock(return_value=None)
        mock_fits_open.return_value = mock_hdul

        with pytest.raises(ValueError, match="Invalid image dimensions"):
            manager._compute_field_extent(fits_path)


@pytest.mark.unit
class TestMeasureForFits:
    """Test measure_for_fits method."""

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    @patch("dsa110_contimg.photometry.manager.ensure_products_db")
    def test_measure_for_fits_batch_job_success(
        self, mock_ensure_db, mock_create_job, mock_query_sources, tmp_path
    ):
        """Test successful batch job creation."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"
        fits_path.touch()  # Create file

        # Mock sources
        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
            {"ra_deg": 180.1, "dec_deg": 35.1},
        ]

        # Mock database
        mock_conn = Mock()
        mock_ensure_db.return_value = mock_conn
        mock_create_job.return_value = 123

        result = manager.measure_for_fits(
            fits_path=fits_path,
            create_batch_job=True,
            data_id="test_data",
        )

        assert result is not None
        assert result.batch_job_id == 123
        assert result.sources_queried == 2
        mock_create_job.assert_called_once()

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    def test_measure_for_fits_no_sources(self, mock_query_sources, tmp_path):
        """Test when no sources are found."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"
        fits_path.touch()

        mock_query_sources.return_value = []

        result = manager.measure_for_fits(fits_path=fits_path)

        assert result is not None
        assert result.sources_queried == 0
        assert result.measurements_total == 0

    def test_measure_for_fits_file_not_found(self, tmp_path):
        """Test when FITS file doesn't exist."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "nonexistent.fits"

        result = manager.measure_for_fits(fits_path=fits_path)

        assert result is None

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    @patch("dsa110_contimg.photometry.manager.measure_many")
    def test_measure_for_fits_synchronous(self, mock_measure_many, mock_query_sources, tmp_path):
        """Test synchronous execution (no batch job)."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"
        fits_path.touch()

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        # Mock measurement results
        mock_result = Mock()
        mock_result.success = True
        mock_measure_many.return_value = [mock_result]

        result = manager.measure_for_fits(
            fits_path=fits_path,
            create_batch_job=False,
        )

        assert result is not None
        assert result.measurements_successful == 1
        assert result.measurements_total == 1
        assert result.results is not None
        mock_measure_many.assert_called_once()


@pytest.mark.unit
class TestMeasureForMosaic:
    """Test measure_for_mosaic method."""

    @patch("dsa110_contimg.photometry.manager.query_sources_for_mosaic")
    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    @patch("dsa110_contimg.photometry.manager.ensure_products_db")
    def test_measure_for_mosaic_success(
        self, mock_ensure_db, mock_create_job, mock_query_sources, tmp_path
    ):
        """Test successful mosaic photometry."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        mosaic_path = tmp_path / "mosaic.fits"
        mosaic_path.touch()

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        mock_conn = Mock()
        mock_ensure_db.return_value = mock_conn
        mock_create_job.return_value = 456

        result = manager.measure_for_mosaic(
            mosaic_path=mosaic_path,
            create_batch_job=True,
        )

        assert result is not None
        assert result.batch_job_id == 456
        mock_query_sources.assert_called_once()


@pytest.mark.unit
class TestCreateBatchJob:
    """Test _create_batch_job method."""

    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    @patch("dsa110_contimg.photometry.manager.ensure_products_db")
    def test_create_batch_job_success(self, mock_ensure_db, mock_create_job, tmp_path):
        """Test successful batch job creation."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        mock_conn = Mock()
        mock_ensure_db.return_value = mock_conn
        mock_create_job.return_value = 789

        fits_paths = [tmp_path / "test1.fits", tmp_path / "test2.fits"]
        coordinates = [{"ra_deg": 180.0, "dec_deg": 35.0}]
        config = PhotometryConfig(method="peak", normalize=False)

        job_id = manager._create_batch_job(
            fits_paths=fits_paths,
            coordinates=coordinates,
            config=config,
            data_id="test_data",
        )

        assert job_id == 789
        mock_create_job.assert_called_once()
        call_args = mock_create_job.call_args
        assert call_args[1]["job_type"] == "batch_photometry"
        assert call_args[1]["data_id"] == "test_data"

    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    @patch("dsa110_contimg.photometry.manager.ensure_products_db")
    def test_create_batch_job_failure(self, mock_ensure_db, mock_create_job, tmp_path):
        """Test batch job creation failure."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        mock_conn = Mock()
        mock_ensure_db.return_value = mock_conn
        mock_create_job.side_effect = Exception("Database error")

        fits_paths = [tmp_path / "test.fits"]
        coordinates = [{"ra_deg": 180.0, "dec_deg": 35.0}]
        config = PhotometryConfig()

        job_id = manager._create_batch_job(
            fits_paths=fits_paths,
            coordinates=coordinates,
            config=config,
        )

        assert job_id is None


@pytest.mark.unit
class TestDryRun:
    """Test dry-run functionality."""

    @patch("dsa110_contimg.photometry.manager.query_sources_for_fits")
    def test_measure_for_fits_dry_run(self, mock_query_sources, tmp_path):
        """Test dry-run mode for measure_for_fits."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        fits_path = tmp_path / "test.fits"
        fits_path.touch()

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
            {"ra_deg": 180.1, "dec_deg": 35.1},
        ]

        result = manager.measure_for_fits(
            fits_path=fits_path,
            dry_run=True,
        )

        assert result is not None
        assert result.sources_queried == 2
        assert result.measurements_total == 2
        assert result.batch_job_id is None
        # Should not create batch job
        mock_query_sources.assert_called_once()

    @patch("dsa110_contimg.photometry.manager.query_sources_for_mosaic")
    def test_measure_for_mosaic_dry_run(self, mock_query_sources, tmp_path):
        """Test dry-run mode for measure_for_mosaic."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")
        mosaic_path = tmp_path / "mosaic.fits"
        mosaic_path.touch()

        mock_query_sources.return_value = [
            {"ra_deg": 180.0, "dec_deg": 35.0},
        ]

        result = manager.measure_for_mosaic(
            mosaic_path=mosaic_path,
            dry_run=True,
        )

        assert result is not None
        assert result.sources_queried == 1
        assert result.batch_job_id is None

    @patch("dsa110_contimg.photometry.manager.create_batch_photometry_job")
    @patch("dsa110_contimg.photometry.manager.ensure_products_db")
    def test_create_batch_job_dry_run(self, mock_ensure_db, mock_create_job, tmp_path):
        """Test dry-run mode for batch job creation."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        fits_paths = [tmp_path / "test.fits"]
        coordinates = [{"ra_deg": 180.0, "dec_deg": 35.0}]
        config = PhotometryConfig()

        job_id = manager._create_batch_job(
            fits_paths=fits_paths,
            coordinates=coordinates,
            config=config,
            dry_run=True,
        )

        assert job_id is None
        # Should not call create_batch_photometry_job
        mock_create_job.assert_not_called()


@pytest.mark.unit
class TestLinkToDataRegistry:
    """Test _link_to_data_registry method."""

    @patch("dsa110_contimg.photometry.manager.link_photometry_to_data")
    @patch("dsa110_contimg.photometry.manager.ensure_data_registry_db")
    def test_link_success(self, mock_ensure_registry, mock_link, tmp_path):
        """Test successful linking to data registry."""
        registry_db = tmp_path / "registry.sqlite3"
        manager = PhotometryManager(
            products_db_path=tmp_path / "products.sqlite3",
            data_registry_db_path=registry_db,
        )

        mock_conn = Mock()
        mock_ensure_registry.return_value = mock_conn
        mock_link.return_value = True

        success = manager._link_to_data_registry("data_123", "job_456")

        assert success is True
        mock_link.assert_called_once_with(mock_conn, "data_123", "job_456")

    def test_link_no_registry_db(self, tmp_path):
        """Test linking when no registry DB is configured."""
        manager = PhotometryManager(products_db_path=tmp_path / "products.sqlite3")

        success = manager._link_to_data_registry("data_123", "job_456")

        assert success is False

    @patch("dsa110_contimg.photometry.manager.link_photometry_to_data")
    @patch("dsa110_contimg.photometry.manager.ensure_data_registry_db")
    def test_link_failure(self, mock_ensure_registry, mock_link, tmp_path):
        """Test linking failure."""
        registry_db = tmp_path / "registry.sqlite3"
        manager = PhotometryManager(
            products_db_path=tmp_path / "products.sqlite3",
            data_registry_db_path=registry_db,
        )

        mock_conn = Mock()
        mock_ensure_registry.return_value = mock_conn
        mock_link.side_effect = Exception("Link error")

        success = manager._link_to_data_registry("data_123", "job_456")

        assert success is False
