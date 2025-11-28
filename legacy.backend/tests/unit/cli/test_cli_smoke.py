"""
Smoke tests for all CLI entry points.

These tests verify that CLI commands:
1. Can be imported without errors
2. Show help text correctly (--help works)
3. Handle missing/invalid arguments gracefully
4. Have all declared subcommands available

Run with: python -m pytest tests/unit/cli/test_cli_smoke.py -v
"""

import subprocess
import sys
from typing import List, Tuple

import pytest


# CLI modules and their expected subcommands
CLI_MODULES = [
    ("dsa110_contimg.conversion.cli", ["single", "groups", "validate", "verify-ms", "smoke-test"]),
    ("dsa110_contimg.calibration.cli", ["calibrate", "apply", "flag", "validate"]),
    ("dsa110_contimg.imaging.cli", ["image", "export"]),
    ("dsa110_contimg.mosaic.cli", ["plan", "build"]),
    ("dsa110_contimg.photometry.cli", ["peak", "adaptive", "ese-detect"]),
    ("dsa110_contimg.database.registry_cli", ["init", "active", "list-sets"]),
    (
        "dsa110_contimg.conversion.streaming.streaming_converter",
        [],  # No subcommands, just options
    ),
]


def run_cli_help(module: str) -> Tuple[int, str, str]:
    """Run CLI module with --help and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", module, "--help"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, result.stdout, result.stderr


class TestCLIImports:
    """Test that all CLI modules can be imported."""

    @pytest.mark.parametrize("module,_", CLI_MODULES)
    def test_module_imports(self, module: str, _):
        """Test that CLI module can be imported without errors."""
        # Import the module to check for import errors
        import importlib

        try:
            importlib.import_module(module)
        except Exception as e:
            pytest.fail(f"Failed to import {module}: {e}")


class TestCLIHelp:
    """Test that all CLI modules respond to --help."""

    @pytest.mark.smoke
    @pytest.mark.parametrize("module,expected_subcommands", CLI_MODULES)
    def test_help_works(self, module: str, expected_subcommands: List[str]):
        """Test that --help returns successfully and shows expected content."""
        returncode, stdout, stderr = run_cli_help(module)

        # Should exit with 0 for help
        assert returncode == 0, f"{module} --help failed with: {stderr}"

        # Should have some help text
        assert len(stdout) > 50, f"{module} --help returned empty output"

        # Should contain "usage:" or "Usage:"
        combined = stdout + stderr
        assert "usage" in combined.lower(), f"{module} --help missing usage info"

        # Check expected subcommands are present
        for subcmd in expected_subcommands:
            assert subcmd in combined, f"{module} missing subcommand: {subcmd}"


class TestConversionCLI:
    """Test conversion CLI specific functionality."""

    @pytest.mark.smoke
    def test_conversion_single_help(self):
        """Test conversion single subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "single", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Uses positional args: input_path output_path
        assert "input_path" in combined or "output_path" in combined

    @pytest.mark.smoke
    def test_conversion_groups_help(self):
        """Test conversion groups subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "groups", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        # Uses positional arg: input_dir
        assert "input_dir" in combined or "output_dir" in combined

    @pytest.mark.smoke
    def test_conversion_missing_args(self):
        """Test conversion fails gracefully with missing arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.cli", "single"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Should fail with non-zero exit code
        assert result.returncode != 0
        # Should mention required argument
        combined = result.stdout + result.stderr
        assert "required" in combined.lower() or "error" in combined.lower()


class TestCalibrationCLI:
    """Test calibration CLI specific functionality."""

    @pytest.mark.smoke
    def test_calibration_calibrate_help(self):
        """Test calibration calibrate subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "calibrate", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "ms" in combined.lower()

    @pytest.mark.smoke
    def test_calibration_apply_help(self):
        """Test calibration apply subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.calibration.cli", "apply", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestImagingCLI:
    """Test imaging CLI specific functionality."""

    @pytest.mark.smoke
    def test_imaging_image_help(self):
        """Test imaging image subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.imaging.cli", "image", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ms" in combined or "MS" in combined

    @pytest.mark.smoke
    def test_imaging_export_help(self):
        """Test imaging export subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.imaging.cli", "export", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestMosaicCLI:
    """Test mosaic CLI specific functionality."""

    @pytest.mark.smoke
    def test_mosaic_plan_help(self):
        """Test mosaic plan subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.mosaic.cli", "plan", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    @pytest.mark.smoke
    def test_mosaic_build_help(self):
        """Test mosaic build subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.mosaic.cli", "build", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestPhotometryCLI:
    """Test photometry CLI specific functionality."""

    @pytest.mark.smoke
    def test_photometry_peak_help(self):
        """Test photometry peak subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "peak", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0
        combined = result.stdout + result.stderr
        assert "--ra" in combined or "ra" in combined.lower()

    @pytest.mark.smoke
    def test_photometry_adaptive_help(self):
        """Test photometry adaptive subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "adaptive", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    @pytest.mark.smoke
    def test_photometry_ese_detect_help(self):
        """Test photometry ese-detect subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.photometry.cli", "ese-detect", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestRegistryCLI:
    """Test registry CLI specific functionality."""

    @pytest.mark.smoke
    def test_registry_init_help(self):
        """Test registry init subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.database.registry_cli", "init", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0

    @pytest.mark.smoke
    def test_registry_list_sets_help(self):
        """Test registry list-sets subcommand help."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.database.registry_cli", "list-sets", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0


class TestStreamingCLI:
    """Test streaming converter CLI specific functionality."""

    @pytest.mark.smoke
    def test_streaming_help(self):
        """Test streaming converter help."""
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

    @pytest.mark.smoke
    def test_streaming_missing_required_args(self):
        """Test streaming fails with missing required arguments."""
        result = subprocess.run(
            [sys.executable, "-m", "dsa110_contimg.conversion.streaming.streaming_converter"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Should fail
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "required" in combined.lower() or "error" in combined.lower()
