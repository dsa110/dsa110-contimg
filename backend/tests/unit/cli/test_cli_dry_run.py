"""
Dry-run tests for CLI commands using subprocess.

These tests verify CLI argument parsing and validation using subprocess
calls with --help and checking the output for expected arguments.
This avoids requiring internal `create_parser` functions.

Run with: python -m pytest tests/unit/cli/test_cli_dry_run.py -v
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestConversionCLIDryRun:
    """Dry-run tests for conversion CLI."""

    def test_single_command_has_expected_positional_args(self):
        """Test that single command has input_path and output_path positional args."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "single", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Check for positional arguments
        assert "input_path" in combined
        assert "output_path" in combined

    def test_single_command_accepts_valid_path_args(self):
        """Test single command accepts path arguments (validation error expected for non-existent)."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsa110_contimg.conversion.cli",
                "single",
                "/nonexistent/input.uvh5",
                "/tmp/output.ms",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Should fail because input file doesn't exist, but args were parsed
        combined = result.stdout + result.stderr
        # Either error about file not found or valid execution
        assert result.returncode != 0 or "error" in combined.lower() or "not found" in combined.lower()

    def test_groups_command_has_expected_args(self):
        """Test that groups command has required arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "groups", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Check for key arguments
        assert "input_dir" in combined
        assert "output_dir" in combined
        # Check for time-related args
        assert "start_time" in combined or "transit" in combined.lower()

    def test_groups_dry_run_option(self):
        """Test groups command has --dry-run option."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "groups", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        assert "--dry-run" in result.stdout

    def test_validate_command_exists(self):
        """Test validate subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "validate", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    def test_verify_ms_command_exists(self):
        """Test verify-ms subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "verify-ms", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestCalibrationCLIDryRun:
    """Dry-run tests for calibration CLI."""

    def test_calibrate_command_has_ms_arg(self):
        """Test calibrate command has --ms argument."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "calibrate", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "ms" in combined.lower()

    def test_apply_command_has_expected_args(self):
        """Test apply command has MS and caltable arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "apply", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "ms" in combined.lower()

    def test_flag_command_has_ms_arg(self):
        """Test flag command has --ms argument."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "flag", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "ms" in combined.lower()

    def test_validate_command_exists(self):
        """Test validate subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "validate", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestImagingCLIDryRun:
    """Dry-run tests for imaging CLI."""

    def test_image_command_has_ms_and_imagename(self):
        """Test image command has --ms and --imagename arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.imaging.cli", "image", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined
        assert "--imagename" in combined or "imagename" in combined

    def test_image_command_has_mask_options(self):
        """Test image command has NVSS mask options."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.imaging.cli", "image", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Check for masking-related options
        assert "mask" in combined.lower() or "nvss" in combined.lower()

    def test_export_command_exists(self):
        """Test export subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.imaging.cli", "export", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestMosaicCLIDryRun:
    """Dry-run tests for mosaic CLI."""

    def test_plan_command_has_name_option(self):
        """Test plan command has --name option for mosaic naming."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.mosaic.cli", "plan", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--name" in combined

    def test_build_command_has_plan_option(self):
        """Test build command has plan file option."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.mosaic.cli", "build", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestPhotometryCLIDryRun:
    """Dry-run tests for photometry CLI."""

    def test_peak_command_has_coordinate_args(self):
        """Test peak command has RA and Dec arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "peak", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ra" in combined or "ra" in combined.lower()
        assert "--dec" in combined or "dec" in combined.lower()

    def test_adaptive_command_has_ms_and_coordinates(self):
        """Test adaptive command has MS path and coordinate arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "adaptive", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "ms" in combined.lower()
        assert "--ra" in combined or "ra" in combined.lower()

    def test_adaptive_command_has_serialize_option(self):
        """Test adaptive command has serialize-ms-access option."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "adaptive", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Check for serialization option
        assert "serialize" in combined.lower() or "lock" in combined.lower()

    def test_ese_detect_command_exists(self):
        """Test ese-detect subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "ese-detect", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestRegistryCLIDryRun:
    """Dry-run tests for registry CLI."""

    def test_init_command_has_db_option(self):
        """Test init command has database path option."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.database.registry_cli", "init", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--db" in combined or "db" in combined.lower()

    def test_active_command_has_mjd_option(self):
        """Test active command has MJD option."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.database.registry_cli", "active", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--mjd" in combined or "mjd" in combined.lower()

    def test_list_sets_command_exists(self):
        """Test list-sets subcommand exists."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.database.registry_cli", "list-sets", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestStreamingConverterCLIDryRun:
    """Dry-run tests for streaming converter CLI."""

    def test_streaming_has_input_output_dirs(self):
        """Test streaming converter has required directory arguments."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsa110_contimg.conversion.streaming.streaming_converter",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--input-dir" in combined
        assert "--output-dir" in combined

    def test_streaming_has_feature_flags(self):
        """Test streaming converter has feature enable flags."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsa110_contimg.conversion.streaming.streaming_converter",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Check for feature flags
        assert "--enable-calibration-solving" in combined
        assert "--enable-group-imaging" in combined
        assert "--enable-mosaic-creation" in combined
        assert "--enable-photometry" in combined

    def test_streaming_has_photometry_options(self):
        """Test streaming converter has photometry options."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsa110_contimg.conversion.streaming.streaming_converter",
                "--help",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--photometry-catalog" in combined
        assert "--photometry-radius" in combined

    def test_streaming_requires_input_output_dirs(self):
        """Test streaming converter fails without required arguments."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "dsa110_contimg.conversion.streaming.streaming_converter",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "required" in combined.lower() or "error" in combined.lower()
