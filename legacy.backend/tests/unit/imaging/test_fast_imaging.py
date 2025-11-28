"""Unit tests for fast imaging module."""

import os
import shutil
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from astropy.io import fits

from dsa110_contimg.imaging.fast_imaging import (
    FastImagingError,
    analyze_snapshots,
    extract_timestamp_index,
    get_scan_duration,
    run_fast_imaging,
    run_wsclean_snapshots,
)


@pytest.fixture
def mock_ms_path(tmp_path):
    """Create a dummy MS directory."""
    ms_dir = tmp_path / "test.ms"
    ms_dir.mkdir()
    return str(ms_dir)


@pytest.fixture
def mock_image_files(tmp_path):
    """Create dummy FITS images for analysis testing."""
    files = []
    # Create 3 dummy images
    for i in range(3):
        fname = tmp_path / f"test-t{i:04d}-image.fits"

        # Create synthetic data: Gaussian noise + one peak in the middle image
        data = np.random.normal(0, 1, (1, 1, 100, 100)).astype(np.float32)

        if i == 1:  # Inject source in second image
            data[0, 0, 50, 50] = 20.0  # 20 sigma peak

        hdu = fits.PrimaryHDU(data)
        # Add minimal WCS header
        hdu.header["CRVAL1"] = 180.0
        hdu.header["CRVAL2"] = 45.0
        hdu.header["CRPIX1"] = 50.0
        hdu.header["CRPIX2"] = 50.0
        hdu.header["CDELT1"] = -0.001
        hdu.header["CDELT2"] = 0.001
        hdu.header["CTYPE1"] = "RA---SIN"
        hdu.header["CTYPE2"] = "DEC--SIN"

        hdu.writeto(fname)
        files.append(str(fname))

    return files


def test_extract_timestamp_index():
    """Test timestamp extraction from filenames."""
    assert extract_timestamp_index("image-t0001.fits") == 1
    assert extract_timestamp_index("test-t1234-dirty.fits") == 1234
    assert extract_timestamp_index("no-timestamp.fits") == -1


@patch("dsa110_contimg.imaging.fast_imaging._msmd")
@patch("dsa110_contimg.imaging.fast_imaging._tb")
def test_get_scan_duration(mock_tb, mock_msmd, mock_ms_path):
    """Test scan duration calculation."""
    # Test metadata path
    mock_md_instance = MagicMock()
    mock_msmd.return_value = mock_md_instance
    mock_md_instance.timerangeforobs.return_value = {
        "begin": {"m0": {"value": 1000.0}},
        "end": {"m0": {"value": 1060.0}},
    }

    duration = get_scan_duration(mock_ms_path)
    assert duration == 60.0 * 86400.0  # days to seconds

    # Test table fallback
    mock_msmd.return_value = None  # Force fallback
    mock_tb_instance = MagicMock()
    mock_tb.return_value = mock_tb_instance
    mock_tb_instance.getcell.side_effect = [1000.0, 1060.0]  # start, end

    duration = get_scan_duration(mock_ms_path)
    assert duration == 60.0


@patch("shutil.which")
@patch("subprocess.run")
@patch("dsa110_contimg.imaging.fast_imaging.get_scan_duration")
def test_run_wsclean_snapshots(mock_duration, mock_run, mock_which, mock_ms_path, tmp_path):
    """Test WSClean command generation."""
    mock_duration.return_value = 300.0  # 5 minutes
    mock_which.return_value = "/usr/bin/wsclean"

    # Create dummy output file to simulate WSClean running
    output_prefix = str(tmp_path / "test_output")
    dummy_output = tmp_path / "test_output-t0000-image.fits"
    dummy_output.touch()

    images = run_wsclean_snapshots(
        ms_path=mock_ms_path, output_prefix=output_prefix, interval_seconds=30.0
    )

    # Check arguments
    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "-intervals-out" in args
    assert "10" in args  # 300 / 30 = 10 intervals
    assert "-niter" in args
    assert "0" in args

    assert len(images) == 1
    assert images[0] == str(dummy_output)


@patch("shutil.which")
@patch("subprocess.run")
@patch("dsa110_contimg.imaging.fast_imaging.get_scan_duration")
def test_run_wsclean_snapshots_subtract_model(
    mock_duration, mock_run, mock_which, mock_ms_path, tmp_path
):
    """Test WSClean command generation with model subtraction."""
    mock_duration.return_value = 300.0
    mock_which.return_value = "/usr/bin/wsclean"

    output_prefix = str(tmp_path / "test_output")

    run_wsclean_snapshots(
        ms_path=mock_ms_path,
        output_prefix=output_prefix,
        interval_seconds=30.0,
        subtract_model=True,
    )

    # Check arguments
    assert mock_run.called
    args = mock_run.call_args[0][0]
    assert "-subtract-model" in args


def test_analyze_snapshots(mock_image_files):
    """Test candidate detection."""
    candidates = analyze_snapshots(mock_image_files, threshold_sigma=5.0)

    assert len(candidates) == 1
    c = candidates[0]
    assert c["timestamp_idx"] == 1
    assert c["snr"] > 15.0
    assert abs(c["ra_deg"] - 180.0) < 0.1
    assert abs(c["dec_deg"] - 45.0) < 0.1


@patch("dsa110_contimg.imaging.fast_imaging.run_wsclean_snapshots")
@patch("dsa110_contimg.imaging.fast_imaging.analyze_snapshots")
def test_run_fast_imaging(mock_analyze, mock_run, mock_ms_path, tmp_path):
    """Test main entry point."""
    mock_run.return_value = ["img1.fits", "img2.fits"]
    mock_analyze.return_value = [
        {
            "candidate": "yes",
            "ra_deg": 180.0,
            "dec_deg": 45.0,
            "snr": 20.0,
            "peak_mjy": 100.0,
            "rms_mjy": 5.0,
            "image": "img1.fits",
            "timestamp_idx": 0,
        }
    ]

    results = run_fast_imaging(mock_ms_path, work_dir=str(tmp_path))

    assert len(results) == 1
    assert mock_run.called
    assert mock_analyze.called
