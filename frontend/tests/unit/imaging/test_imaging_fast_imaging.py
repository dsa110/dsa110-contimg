#!/usr/bin/env python3
"""
Unit tests for imaging module.

Tests:
- fast_imaging functionality
"""
import os
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from dsa110_contimg.imaging.fast_imaging import (
    FastImagingError,
    analyze_snapshots,
    get_scan_duration,
    run_fast_imaging,
    run_wsclean_snapshots,
)


@pytest.mark.unit
class TestFastImaging:
    """Test class for fast_imaging."""

    @pytest.fixture
    def mock_wsclean(self):
        with patch("dsa110_contimg.imaging.fast_imaging.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/wsclean"
            yield mock_which

    @pytest.fixture
    def mock_subprocess(self):
        with patch("dsa110_contimg.imaging.fast_imaging.subprocess.run") as mock_run:
            yield mock_run

    @pytest.fixture
    def mock_casatools(self):
        with (
            patch("dsa110_contimg.imaging.fast_imaging._msmd", new_callable=Mock) as mock_msmd,
            patch("dsa110_contimg.imaging.fast_imaging._tb", new_callable=Mock) as mock_tb,
        ):

            # Mock msmd behavior
            md_instance = Mock()
            mock_msmd.return_value = md_instance
            md_instance.timerangeforobs.return_value = {
                "begin": {"m0": {"value": 59000.0}},
                "end": {"m0": {"value": 59000.0 + (300.0 / 86400.0)}},  # 300 seconds
            }

            yield mock_msmd, mock_tb

    def test_get_scan_duration(self, mock_casatools):
        """Test scan duration calculation."""
        duration = get_scan_duration("test.ms")
        assert abs(duration - 300.0) < 1e-5

    def test_run_wsclean_snapshots(self, mock_wsclean, mock_subprocess, mock_casatools):
        """Test WSClean command generation and execution."""
        with patch("dsa110_contimg.imaging.fast_imaging.os.listdir") as mock_listdir:
            # Mock output files
            mock_listdir.return_value = ["test.fast-t0000-image.fits", "test.fast-t0001-image.fits"]

            images = run_wsclean_snapshots(
                ms_path="test.ms", output_prefix="test.fast", interval_seconds=30.0, imsize=512
            )

            assert len(images) == 2

            # Verify WSClean call
            mock_subprocess.assert_called_once()
            cmd = mock_subprocess.call_args[0][0]
            assert cmd[0] == "/usr/bin/wsclean"
            assert "-niter" in cmd
            assert "0" in cmd[cmd.index("-niter") + 1]
            assert "-intervals-out" in cmd
            assert "10" in cmd[cmd.index("-intervals-out") + 1]  # 300s / 30s = 10

    def test_analyze_snapshots(self):
        """Test candidate detection logic."""
        with patch("dsa110_contimg.imaging.fast_imaging.fits.open") as mock_fits:
            # Create fake data with a peak
            data = np.random.normal(0, 1, (1, 1, 100, 100))
            # Add a 10-sigma source
            data[0, 0, 50, 50] = 10.0

            hdu = Mock()
            hdu.data = data
            hdu.header = {
                "CRVAL1": 0.0,
                "CRPIX1": 50,
                "CDELT1": -1.0 / 3600,
                "CTYPE1": "RA---SIN",
                "CRVAL2": 0.0,
                "CRPIX2": 50,
                "CDELT2": 1.0 / 3600,
                "CTYPE2": "DEC--SIN",
            }

            mock_fits.return_value.__enter__.return_value = [hdu]

            candidates = analyze_snapshots(["test-t0000-image.fits"], threshold_sigma=5.0)

            assert len(candidates) == 1
            assert candidates[0]["snr"] > 5.0
            assert candidates[0]["peak_mjy"] > 0
            assert candidates[0]["timestamp_idx"] == 0

    def test_run_fast_imaging_end_to_end(self, mock_wsclean, mock_subprocess, mock_casatools):
        """Test full workflow."""
        with (
            patch("dsa110_contimg.imaging.fast_imaging.os.listdir") as mock_listdir,
            patch("dsa110_contimg.imaging.fast_imaging.fits.open") as mock_fits,
        ):

            mock_listdir.return_value = ["test.ms.fast-t0000-image.fits"]

            # Fake data
            data = np.zeros((1, 1, 100, 100))
            data[0, 0, 50, 50] = 10.0  # Peak
            hdu = Mock()
            hdu.data = data
            hdu.header = {
                "CRVAL1": 0.0,
                "CRPIX1": 50,
                "CDELT1": -1.0,
                "CTYPE1": "RA---SIN",
                "CRVAL2": 0.0,
                "CRPIX2": 50,
                "CDELT2": 1.0,
                "CTYPE2": "DEC--SIN",
            }
            mock_fits.return_value.__enter__.return_value = [hdu]

            candidates = run_fast_imaging(
                ms_path="test.ms", interval_seconds=30.0, threshold_sigma=5.0
            )

            assert len(candidates) == 1
