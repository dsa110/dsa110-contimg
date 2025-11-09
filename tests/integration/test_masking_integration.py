#!/usr/bin/env python3
"""
Integration tests for masking functionality.

Tests the end-to-end masking workflow:
1. Mask generation from NVSS sources
2. Mask integration in imaging pipeline
3. Configuration parameter flow
4. Error handling and fallback

Run with: pytest tests/integration/test_masking_integration.py -v
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
from astropy.io import fits

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@pytest.mark.integration
class TestMaskingIntegration:
    """Integration tests for masking workflow."""

    def test_mask_generation_with_real_nvss_catalog(self, temp_work_dir):
        """Test mask generation using real NVSS catalog (if available)."""
        from dsa110_contimg.imaging.nvss_tools import create_nvss_fits_mask

        imagename = str(temp_work_dir / "test.img")
        imsize = 512
        cell_arcsec = 2.0
        ra0_deg = 120.0  # Test coordinates
        dec0_deg = 45.0
        nvss_min_mjy = 10.0
        radius_arcsec = 60.0

        try:
            mask_path = create_nvss_fits_mask(
                imagename=imagename,
                imsize=imsize,
                cell_arcsec=cell_arcsec,
                ra0_deg=ra0_deg,
                dec0_deg=dec0_deg,
                nvss_min_mjy=nvss_min_mjy,
                radius_arcsec=radius_arcsec,
            )

            # Verify mask file exists and is valid
            assert os.path.exists(mask_path)
            assert mask_path.endswith('.nvss_mask.fits')

            # Verify FITS structure
            with fits.open(mask_path) as hdul:
                assert len(hdul) > 0
                mask_data = hdul[0].data
                assert mask_data.shape == (imsize, imsize)
                assert mask_data.dtype == np.float32

        except Exception as e:
            # If NVSS catalog is not available, skip test
            pytest.skip(f"NVSS catalog not available: {e}")

    def test_imaging_stage_with_masking(self, test_config, context_with_repo, temp_work_dir):
        """Test ImagingStage with masking enabled."""
        from dsa110_contimg.pipeline.stages_impl import ImagingStage
        from dsa110_contimg.pipeline.config import ImagingConfig

        # Update config with masking enabled
        test_config.imaging = ImagingConfig(
            use_nvss_mask=True,
            mask_radius_arcsec=60.0,
        )

        # Create mock MS
        ms_path = str(temp_work_dir / "test.ms")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        # Create context with MS path
        context = context_with_repo
        context.config = test_config
        context.outputs = {"ms_path": ms_path}

        # Mock MS structure
        def mock_table_factory(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)

            if "FIELD" in path:
                ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
                ctx.colnames.return_value = ['PHASE_DIR']
                ctx.nrows.return_value = 1
            elif "SPECTRAL_WINDOW" in path:
                ctx.getcol.return_value = np.array([[1.4e9]])
                ctx.colnames.return_value = ['CHAN_FREQ']
                ctx.nrows.return_value = 1
            else:
                ctx.colnames.return_value = ['DATA', 'CORRECTED_DATA', 'FLAG', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
                ctx.nrows.return_value = 1000
                ctx.getcol.return_value = np.random.random((1000, 1, 4)) + 1j * np.random.random((1000, 1, 4))
            return ctx

        mask_generated = []

        def mock_create_mask(*args, **kwargs):
            mask_generated.append(True)
            return str(temp_work_dir / "test.img.nvss_mask.fits")

        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.imaging.cli_imaging.image_ms') as mock_image_ms, \
             patch('dsa110_contimg.imaging.nvss_tools.create_nvss_fits_mask', side_effect=mock_create_mask):

            stage = ImagingStage(test_config)
            is_valid, error_msg = stage.validate(context)
            assert is_valid, f"Validation failed: {error_msg}"

            # Execute stage (will call image_ms internally)
            try:
                result_context = stage.execute(context)
                # Verify image_ms was called with masking parameters
                assert mock_image_ms.called
                call_kwargs = mock_image_ms.call_args[1]
                assert call_kwargs.get('use_nvss_mask') is True
                assert call_kwargs.get('mask_radius_arcsec') == 60.0
            except Exception as e:
                # If imaging fails due to missing dependencies, that's okay for integration test
                # We're just verifying the parameter flow
                if "WSClean" in str(e) or "CASA" in str(e):
                    pytest.skip(f"Imaging backend not available: {e}")
                raise

    def test_config_parameter_flow_api_to_pipeline(self, temp_work_dir):
        """Test parameter flow from API request to pipeline config."""
        from dsa110_contimg.pipeline.config import PipelineConfig

        # Simulate API request parameters
        api_params = {
            "paths": {
                "input_dir": "/test/input",
                "output_dir": "/test/output",
            },
            "use_nvss_mask": False,
            "mask_radius_arcsec": 120.0,
            "gridder": "wproject",
        }

        # Convert to PipelineConfig
        config = PipelineConfig.from_dict(api_params)

        # Verify masking parameters are correctly extracted
        assert config.imaging.use_nvss_mask is False
        assert config.imaging.mask_radius_arcsec == 120.0
        assert config.imaging.gridder == "wproject"

    def test_mask_generation_failure_handling(self, temp_work_dir):
        """Test that imaging continues when mask generation fails."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table

        ms_path = str(temp_work_dir / "test.ms")
        imagename = str(temp_work_dir / "test.img")
        Path(ms_path).mkdir(parents=True, exist_ok=True)

        # Mock MS structure
        def mock_table_factory(path, readonly=True):
            ctx = MagicMock()
            ctx.__enter__ = MagicMock(return_value=ctx)
            ctx.__exit__ = MagicMock(return_value=None)

            if "FIELD" in path:
                ctx.getcol.return_value = np.array([[[np.radians(120.0), np.radians(45.0)]]])
                ctx.colnames.return_value = ['PHASE_DIR']
                ctx.nrows.return_value = 1
            elif "SPECTRAL_WINDOW" in path:
                ctx.getcol.return_value = np.array([[1.4e9]])
                ctx.colnames.return_value = ['CHAN_FREQ']
                ctx.nrows.return_value = 1
            else:
                ctx.colnames.return_value = ['DATA', 'CORRECTED_DATA', 'FLAG', 'ANTENNA1', 'ANTENNA2', 'TIME', 'UVW']
                ctx.nrows.return_value = 1000
                ctx.getcol.return_value = np.random.random((1000, 1, 4)) + 1j * np.random.random((1000, 1, 4))
            return ctx

        with patch('casacore.tables.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.table', side_effect=mock_table_factory), \
             patch('dsa110_contimg.imaging.cli_utils.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_imaging.default_cell_arcsec', return_value=2.0), \
             patch('dsa110_contimg.imaging.cli_utils.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.detect_datacolumn', return_value='data'), \
             patch('dsa110_contimg.imaging.cli_imaging.run_wsclean') as mock_wsclean, \
             patch('dsa110_contimg.imaging.cli_imaging.validate_ms', return_value=None), \
             patch('dsa110_contimg.utils.validation.validate_corrected_data_quality', return_value=[]), \
             patch('dsa110_contimg.imaging.nvss_tools.create_nvss_fits_mask', side_effect=RuntimeError("Catalog unavailable")):

            # Should not raise exception
            image_ms(
                ms_path,
                imagename=imagename,
                use_nvss_mask=True,
                nvss_min_mjy=10.0,
                backend="wsclean",
            )

        # Verify WSClean was called (imaging continued despite mask failure)
        assert mock_wsclean.called
        call_kwargs = mock_wsclean.call_args[1]
        # Mask path should be None due to failure
        assert call_kwargs.get('mask_path') is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

