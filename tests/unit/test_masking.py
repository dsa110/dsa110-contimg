#!/usr/bin/env python3
"""
Unit tests for NVSS masking functionality.

Tests cover:
- FITS mask generation (create_nvss_fits_mask)
- Mask integration in imaging pipeline
- Configuration parameter handling
- Error handling and fallback behavior

Run with: pytest tests/unit/test_masking.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
import astropy.units as u

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.unit
class TestCreateNVSSFitsMask:
    """Test create_nvss_fits_mask function."""

    def test_mask_creation_basic(self, temp_work_dir):
        """Test basic mask creation with valid parameters."""
        from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

        imagename = str(temp_work_dir / "test.img")
        imsize = 512
        cell_arcsec = 2.0
        ra0_deg = 120.0
        dec0_deg = 45.0
        nvss_min_mjy = 10.0
        radius_arcsec = 60.0

        # Mock NVSS catalog to return sources
        mock_nvss_df = MagicMock()

        def _series(values):
            s = MagicMock()
            s.values = np.asarray(values)
            return s

        mock_nvss_df.__getitem__ = Mock(
            side_effect=lambda key: {
                "ra": _series([120.0, 120.1, 120.2]),
                "dec": _series([45.0, 45.1, 45.2]),
                "flux_20_cm": _series([50.0, 30.0, 15.0]),  # All above 10 mJy
            }[key]
        )
        # Pandas-like .loc indexer that returns a subset via __getitem__
        mock_nvss_df.loc = MagicMock()
        mock_nvss_df.loc.__getitem__ = Mock(return_value=mock_nvss_df)
        mock_nvss_df.iterrows = Mock(
            return_value=[
                (0, {"ra": 120.0, "dec": 45.0, "flux_20_cm": 50.0}),
                (1, {"ra": 120.1, "dec": 45.1, "flux_20_cm": 30.0}),
                (2, {"ra": 120.2, "dec": 45.2, "flux_20_cm": 15.0}),
            ]
        )
        mock_nvss_df.__len__ = Mock(return_value=3)

        with patch(
            "dsa110_contimg.calibration.catalogs.read_nvss_catalog",
            return_value=mock_nvss_df,
        ):
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                ra0_deg=ra0_deg,
                dec0_deg=dec0_deg,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=radius_arcsec,
            )

        # Verify mask file was created
        assert os.path.exists(mask_path)
        assert mask_path.endswith(".nvss_mask.fits")

        # Verify mask file is valid FITS
        with fits.open(mask_path) as hdul:
            assert len(hdul) > 0
            mask_data = hdul[0].data
            assert mask_data.shape == (imsize, imsize)
            # FITS may read as big-endian float32 (">f4"); accept any float32
            assert (
                np.issubdtype(mask_data.dtype, np.floating)
                and mask_data.dtype.itemsize == 4
            )

            # Verify WCS header
            header = hdul[0].header
            assert "CRVAL1" in header
            assert "CRVAL2" in header
            assert abs(header["CRVAL1"] - ra0_deg) < 0.01
            assert abs(header["CRVAL2"] - dec0_deg) < 0.01

    def test_mask_no_sources(self, temp_work_dir):
        """Test mask creation when no sources found."""
        from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

        imagename = str(temp_work_dir / "test.img")
        imsize = 512
        cell_arcsec = 2.0
        ra0_deg = 120.0
        dec0_deg = 45.0
        nvss_min_mjy = 1000.0  # Very high threshold - no sources
        radius_arcsec = 60.0

        # Mock NVSS catalog with no matching sources
        mock_nvss_df = MagicMock()

        def _series(values):
            s = MagicMock()
            s.values = np.asarray(values)
            return s

        mock_nvss_df.__getitem__ = Mock(
            side_effect=lambda key: {
                "ra": _series([120.0]),
                "dec": _series([45.0]),
                "flux_20_cm": _series([5.0]),  # Below threshold
            }[key]
        )
        empty_sel = MagicMock()
        empty_sel.__len__ = Mock(return_value=0)
        mock_nvss_df.loc = MagicMock()
        mock_nvss_df.loc.__getitem__ = Mock(return_value=empty_sel)

        with patch(
            "dsa110_contimg.calibration.catalogs.read_nvss_catalog",
            return_value=mock_nvss_df,
        ):
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                ra0_deg=ra0_deg,
                dec0_deg=dec0_deg,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=radius_arcsec,
            )

        # Verify empty mask was created
        assert os.path.exists(mask_path)
        with fits.open(mask_path) as hdul:
            mask_data = hdul[0].data
            # All zeros (no sources)
            assert np.all(mask_data == 0.0)

    def test_mask_radius_calculation(self, temp_work_dir):
        """Test that mask radius is correctly applied."""
        from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

        imagename = str(temp_work_dir / "test.img")
        imsize = 512
        cell_arcsec = 2.0
        ra0_deg = 120.0
        dec0_deg = 45.0
        nvss_min_mjy = 10.0
        radius_arcsec = 60.0

        # Mock NVSS catalog with one source at image center
        mock_nvss_df = MagicMock()

        def _series(values):
            s = MagicMock()
            s.values = np.asarray(values)
            return s

        mock_nvss_df.__getitem__ = Mock(
            side_effect=lambda key: {
                "ra": _series([ra0_deg]),
                "dec": _series([dec0_deg]),
                "flux_20_cm": _series([50.0]),
            }[key]
        )
        mock_nvss_df.loc = MagicMock()
        mock_nvss_df.loc.__getitem__ = Mock(return_value=mock_nvss_df)
        mock_nvss_df.iterrows = Mock(
            return_value=[
                (0, {"ra": ra0_deg, "dec": dec0_deg, "flux_20_cm": 50.0}),
            ]
        )
        mock_nvss_df.__len__ = Mock(return_value=1)

        with patch(
            "dsa110_contimg.calibration.catalogs.read_nvss_catalog",
            return_value=mock_nvss_df,
        ):
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                ra0_deg=ra0_deg,
                dec0_deg=dec0_deg,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=radius_arcsec,
            )

        # Verify mask has circular region
        with fits.open(mask_path) as hdul:
            mask_data = hdul[0].data
            center_x, center_y = imsize // 2, imsize // 2

            # Check that center region is masked (non-zero)
            assert mask_data[center_y, center_x] > 0.0

            # Check that mask radius is approximately correct
            radius_pixels = radius_arcsec / cell_arcsec
            y, x = np.ogrid[:imsize, :imsize]
            dist_from_center = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

            # Points within radius should be masked
            masked_region = mask_data[dist_from_center <= radius_pixels]
            assert np.any(masked_region > 0.0)

            # Points far from center should not be masked
            far_region = mask_data[dist_from_center > radius_pixels * 1.5]
            assert np.all(far_region == 0.0)

    def test_mask_custom_output_path(self, temp_work_dir):
        """Test mask creation with custom output path."""
        from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

        imagename = str(temp_work_dir / "test.img")
        custom_path = str(temp_work_dir / "custom_mask.fits")
        imsize = 512
        cell_arcsec = 2.0
        ra0_deg = 120.0
        dec0_deg = 45.0
        nvss_min_mjy = 10.0
        radius_arcsec = 60.0

        # Mock empty catalog
        mock_nvss_df = MagicMock()

        def _series(values):
            s = MagicMock()
            s.values = np.asarray(values)
            return s

        mock_nvss_df.__getitem__ = Mock(
            side_effect=lambda key: {
                "ra": _series([]),
                "dec": _series([]),
                "flux_20_cm": _series([]),
            }[key]
        )
        empty_sel = MagicMock()
        empty_sel.__len__ = Mock(return_value=0)
        mock_nvss_df.loc = MagicMock()
        mock_nvss_df.loc.__getitem__ = Mock(return_value=empty_sel)

        with patch(
            "dsa110_contimg.calibration.catalogs.read_nvss_catalog",
            return_value=mock_nvss_df,
        ):
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                ra0_deg=ra0_deg,
                dec0_deg=dec0_deg,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=radius_arcsec,
                out_path=custom_path,
            )

        assert mask_path == custom_path
        assert os.path.exists(custom_path)


@pytest.mark.unit
class TestMaskingIntegration:
    """Test masking integration in imaging pipeline."""

    def test_image_ms_with_masking_enabled(self, mock_table_factory, temp_work_dir):
        """Test image_ms generates mask when use_nvss_mask=True."""
        from dsa110_contimg.imaging.cli_imaging import image_ms

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        # Track if mask generation was called
        mask_generated = []

        def mock_create_mask(*args, **kwargs):
            mask_generated.append(True)
            return str(temp_work_dir / "test.img.nvss_mask.fits")

        with patch("casacore.tables.table", side_effect=mock_table_factory), patch(
            "dsa110_contimg.imaging.cli_utils.table", side_effect=mock_table_factory
        ), patch(
            "dsa110_contimg.imaging.cli_utils.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_utils.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.run_wsclean"
        ) as mock_wsclean, patch(
            "dsa110_contimg.imaging.cli_imaging.validate_ms", return_value=None
        ), patch(
            "dsa110_contimg.utils.validation.validate_corrected_data_quality",
            return_value=[],
        ), patch(
            "dsa110_contimg.imaging.nvss_tools.create_nvss_fits_mask",
            side_effect=mock_create_mask,
        ):

            image_ms(
                ms_path,
                imagename=imagename,
                use_nvss_mask=True,
                nvss_min_mjy=10.0,
                backend="wsclean",
            )

        # Verify mask was generated
        assert len(mask_generated) > 0

        # Verify WSClean was called with mask_path
        assert mock_wsclean.called
        call_kwargs = mock_wsclean.call_args[1]
        assert "mask_path" in call_kwargs
        assert call_kwargs["mask_path"] is not None

    def test_image_ms_with_masking_disabled(self, mock_table_factory, temp_work_dir):
        """Test image_ms skips mask when use_nvss_mask=False."""
        from dsa110_contimg.imaging.cli_imaging import image_ms

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        with patch("casacore.tables.table", side_effect=mock_table_factory), patch(
            "dsa110_contimg.imaging.cli_utils.table", side_effect=mock_table_factory
        ), patch(
            "dsa110_contimg.imaging.cli_utils.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_utils.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.run_wsclean"
        ) as mock_wsclean, patch(
            "dsa110_contimg.imaging.cli_imaging.validate_ms", return_value=None
        ), patch(
            "dsa110_contimg.utils.validation.validate_corrected_data_quality",
            return_value=[],
        ), patch(
            "dsa110_contimg.imaging.nvss_tools.create_nvss_fits_mask"
        ) as mock_create_mask:

            image_ms(
                ms_path,
                imagename=imagename,
                use_nvss_mask=False,
                nvss_min_mjy=10.0,
                backend="wsclean",
            )

        # Verify mask generation was not called
        assert not mock_create_mask.called

        # Verify WSClean was called without mask_path
        assert mock_wsclean.called
        call_kwargs = mock_wsclean.call_args[1]
        assert call_kwargs.get("mask_path") is None

    def test_image_ms_mask_generation_failure_fallback(
        self, mock_table_factory, temp_work_dir
    ):
        """Test image_ms continues without mask if generation fails."""
        from dsa110_contimg.imaging.cli_imaging import image_ms

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        with patch("casacore.tables.table", side_effect=mock_table_factory), patch(
            "dsa110_contimg.imaging.cli_utils.table", side_effect=mock_table_factory
        ), patch(
            "dsa110_contimg.imaging.cli_utils.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.default_cell_arcsec", return_value=2.0
        ), patch(
            "dsa110_contimg.imaging.cli_utils.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.detect_datacolumn", return_value="data"
        ), patch(
            "dsa110_contimg.imaging.cli_imaging.run_wsclean"
        ) as mock_wsclean, patch(
            "dsa110_contimg.imaging.cli_imaging.validate_ms", return_value=None
        ), patch(
            "dsa110_contimg.utils.validation.validate_corrected_data_quality",
            return_value=[],
        ), patch(
            "dsa110_contimg.imaging.nvss_tools.create_nvss_fits_mask",
            side_effect=Exception("Mask generation failed"),
        ):

            # Should not raise exception
            image_ms(
                ms_path,
                imagename=imagename,
                use_nvss_mask=True,
                nvss_min_mjy=10.0,
                backend="wsclean",
            )

        # Verify WSClean was called without mask (fallback)
        assert mock_wsclean.called
        call_kwargs = mock_wsclean.call_args[1]
        assert call_kwargs.get("mask_path") is None

    def test_run_wsclean_with_mask(self, temp_work_dir):
        """Test run_wsclean includes -fits-mask when mask_path provided."""
        from dsa110_contimg.imaging.cli_imaging import run_wsclean

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        mask_path = str(temp_work_dir / "test_mask.fits")
        Path(ms_path).mkdir(parents=True, exist_ok=True)
        Path(mask_path).touch()

        captured_cmd = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            captured_cmd.extend(cmd)
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = b"Success"
            mock_result.stderr = b""
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "shutil.which", return_value="/usr/bin/wsclean"
        ):

            run_wsclean(
                ms_path=ms_path,
                imagename=imagename,
                datacolumn="data",
                field="",
                imsize=512,
                cell_arcsec=2.0,
                weighting="briggs",
                robust=0.0,
                specmode="mfs",
                deconvolver="hogbom",
                nterms=1,
                niter=1000,
                threshold="0.0Jy",
                pbcor=True,
                uvrange="",
                pblimit=0.2,
                quality_tier="standard",
                mask_path=mask_path,
            )

        # Verify -fits-mask parameter was included
        assert "-fits-mask" in captured_cmd
        mask_idx = captured_cmd.index("-fits-mask")
        assert captured_cmd[mask_idx + 1] == mask_path

    def test_run_wsclean_without_mask(self, temp_work_dir):
        """Test run_wsclean does not include -fits-mask when mask_path is None."""
        from dsa110_contimg.imaging.cli_imaging import run_wsclean

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        captured_cmd = []

        def mock_subprocess_run(cmd, *args, **kwargs):
            captured_cmd.extend(cmd)
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = b"Success"
            mock_result.stderr = b""
            return mock_result

        with patch("subprocess.run", side_effect=mock_subprocess_run), patch(
            "shutil.which", return_value="/usr/bin/wsclean"
        ):

            run_wsclean(
                ms_path=ms_path,
                imagename=imagename,
                datacolumn="data",
                field="",
                imsize=512,
                cell_arcsec=2.0,
                weighting="briggs",
                robust=0.0,
                specmode="mfs",
                deconvolver="hogbom",
                nterms=1,
                niter=1000,
                threshold="0.0Jy",
                pbcor=True,
                uvrange="",
                pblimit=0.2,
                quality_tier="standard",
                mask_path=None,
            )

        # Verify -fits-mask parameter was not included
        assert "-fits-mask" not in captured_cmd


@pytest.mark.unit
class TestMaskingConfiguration:
    """Test masking configuration parameter handling."""

    def test_imaging_config_defaults(self):
        """Test ImagingConfig defaults for masking."""
        from dsa110_contimg.pipeline.config import ImagingConfig

        config = ImagingConfig()
        assert config.use_nvss_mask is True
        assert config.mask_radius_arcsec == 60.0

    def test_imaging_config_custom_values(self):
        """Test ImagingConfig with custom masking values."""
        from dsa110_contimg.pipeline.config import ImagingConfig

        config = ImagingConfig(
            use_nvss_mask=False,
            mask_radius_arcsec=120.0,
        )
        assert config.use_nvss_mask is False
        assert config.mask_radius_arcsec == 120.0

    def test_imaging_config_radius_validation(self):
        """Test ImagingConfig radius validation."""
        from dsa110_contimg.pipeline.config import ImagingConfig
        from pydantic import ValidationError

        # Test minimum bound
        with pytest.raises(ValidationError):
            ImagingConfig(mask_radius_arcsec=5.0)  # Below 10.0

        # Test maximum bound
        with pytest.raises(ValidationError):
            ImagingConfig(mask_radius_arcsec=400.0)  # Above 300.0

        # Test valid values
        config1 = ImagingConfig(mask_radius_arcsec=10.0)
        assert config1.mask_radius_arcsec == 10.0

        config2 = ImagingConfig(mask_radius_arcsec=300.0)
        assert config2.mask_radius_arcsec == 300.0

    def test_pipeline_config_from_dict_with_masking(self):
        """Test PipelineConfig.from_dict extracts masking parameters."""
        from dsa110_contimg.pipeline.config import PipelineConfig, PathsConfig

        # Test with masking parameters at top level
        params = {
            "paths": {
                "input_dir": "/test/input",
                "output_dir": "/test/output",
            },
            "use_nvss_mask": False,
            "mask_radius_arcsec": 120.0,
        }

        config = PipelineConfig.from_dict(params)
        assert config.imaging.use_nvss_mask is False
        assert config.imaging.mask_radius_arcsec == 120.0

    def test_pipeline_config_from_dict_nested_imaging(self):
        """Test PipelineConfig.from_dict with nested imaging config."""
        from dsa110_contimg.pipeline.config import PipelineConfig

        params = {
            "paths": {
                "input_dir": "/test/input",
                "output_dir": "/test/output",
            },
            "imaging": {
                "use_nvss_mask": False,
                "mask_radius_arcsec": 120.0,
            },
        }

        config = PipelineConfig.from_dict(params)
        assert config.imaging.use_nvss_mask is False
        assert config.imaging.mask_radius_arcsec == 120.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
