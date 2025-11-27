"""Unit tests for GPU utilities module."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from dsa110_contimg.utils.gpu_utils import (
    GPUBackend,
    GPUConfig,
    GPUInfo,
    _parse_nvidia_smi_output,
    build_docker_command,
    build_wsclean_gpu_args,
    check_nvidia_docker,
    clear_gpu_cache,
    detect_gpus,
    get_gpu_config,
    get_gpu_count,
    get_gpu_env_config,
    is_gpu_available,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear GPU detection cache before and after each test."""
    clear_gpu_cache()
    yield
    clear_gpu_cache()


class TestGPUInfo:
    """Test GPUInfo dataclass."""

    def test_memory_gb_property(self):
        """Test memory_gb property converts correctly."""
        gpu = GPUInfo(
            index=0,
            name="GeForce RTX 2080 Ti",
            memory_mb=11019,
            driver_version="455.23.05",
        )
        assert gpu.memory_gb == pytest.approx(10.76, rel=0.01)


class TestParseNvidiaSmiOutput:
    """Test nvidia-smi output parsing."""

    def test_parse_single_gpu(self):
        """Test parsing single GPU output."""
        output = "GeForce RTX 2080 Ti, 11019, 455.23.05"
        gpus = _parse_nvidia_smi_output(output)
        assert len(gpus) == 1
        assert gpus[0].name == "GeForce RTX 2080 Ti"
        assert gpus[0].memory_mb == 11019
        assert gpus[0].driver_version == "455.23.05"

    def test_parse_multiple_gpus(self):
        """Test parsing multiple GPU output."""
        output = """GeForce RTX 2080 Ti, 11019, 455.23.05
GeForce RTX 2080 Ti, 11019, 455.23.05"""
        gpus = _parse_nvidia_smi_output(output)
        assert len(gpus) == 2
        assert gpus[0].index == 0
        assert gpus[1].index == 1

    def test_parse_empty_output(self):
        """Test parsing empty output."""
        gpus = _parse_nvidia_smi_output("")
        assert len(gpus) == 0

    def test_parse_invalid_output(self):
        """Test parsing invalid output is handled gracefully."""
        output = "invalid, not-a-number, test"
        gpus = _parse_nvidia_smi_output(output)
        assert len(gpus) == 0


class TestGPUConfig:
    """Test GPUConfig dataclass."""

    def test_has_gpu_with_gpus(self):
        """Test has_gpu returns True when GPUs exist."""
        config = GPUConfig(
            enabled=True,
            gpus=[
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ],
        )
        assert config.has_gpu is True

    def test_has_gpu_without_gpus(self):
        """Test has_gpu returns False when no GPUs."""
        config = GPUConfig(enabled=True, gpus=[])
        assert config.has_gpu is False

    def test_total_gpu_memory(self):
        """Test total GPU memory calculation."""
        config = GPUConfig(
            enabled=True,
            gpus=[
                GPUInfo(index=0, name="GPU0", memory_mb=10240, driver_version="1.0"),
                GPUInfo(index=1, name="GPU1", memory_mb=10240, driver_version="1.0"),
            ],
        )
        assert config.total_gpu_memory_gb == pytest.approx(20.0, rel=0.01)

    def test_effective_gridder_with_gpu(self):
        """Test effective gridder with GPU available."""
        config = GPUConfig(
            enabled=True,
            wsclean_gridder="idg",
            gpus=[
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ],
        )
        assert config.effective_gridder == "idg"

    def test_effective_gridder_without_gpu(self):
        """Test effective gridder falls back to wgridder without GPU."""
        config = GPUConfig(enabled=True, wsclean_gridder="idg", gpus=[])
        assert config.effective_gridder == "wgridder"

    def test_effective_idg_mode_with_gpu(self):
        """Test effective IDG mode with GPU."""
        config = GPUConfig(
            enabled=True,
            wsclean_idg_mode="gpu",
            gpus=[
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ],
        )
        assert config.effective_idg_mode == "gpu"

    def test_effective_idg_mode_without_gpu(self):
        """Test effective IDG mode falls back to cpu without GPU."""
        config = GPUConfig(enabled=True, wsclean_idg_mode="gpu", gpus=[])
        assert config.effective_idg_mode == "cpu"


class TestDetectGPUs:
    """Test GPU detection."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_detect_gpus_success(self, mock_run, mock_which):
        """Test successful GPU detection."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="GeForce RTX 2080 Ti, 11019, 455.23.05",
        )

        gpus = detect_gpus()
        assert len(gpus) == 1
        assert gpus[0].name == "GeForce RTX 2080 Ti"

    @patch("shutil.which")
    def test_detect_gpus_no_nvidia_smi(self, mock_which):
        """Test detection when nvidia-smi not found."""
        mock_which.return_value = None
        gpus = detect_gpus()
        assert len(gpus) == 0

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_detect_gpus_nvidia_smi_fails(self, mock_run, mock_which):
        """Test detection when nvidia-smi returns error."""
        mock_which.return_value = "/usr/bin/nvidia-smi"
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        gpus = detect_gpus()
        assert len(gpus) == 0


class TestBuildDockerCommand:
    """Test Docker command building."""

    @patch("shutil.which")
    def test_build_docker_command_with_gpu(self, mock_which):
        """Test building Docker command with GPU."""
        mock_which.return_value = "/usr/bin/docker"
        config = GPUConfig(
            enabled=True,
            docker_gpu_flag="--gpus all",
            gpus=[
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ],
        )

        cmd = build_docker_command(
            image="wsclean:latest",
            command=["wsclean", "--version"],
            gpu_config=config,
        )

        assert "/usr/bin/docker" in cmd
        assert "--gpus" in cmd
        assert "all" in cmd
        assert "wsclean:latest" in cmd
        assert "wsclean" in cmd
        assert "--version" in cmd

    @patch("shutil.which")
    def test_build_docker_command_without_gpu(self, mock_which):
        """Test building Docker command without GPU."""
        mock_which.return_value = "/usr/bin/docker"
        config = GPUConfig(enabled=False, gpus=[])

        cmd = build_docker_command(
            image="wsclean:latest",
            command=["wsclean", "--version"],
            gpu_config=config,
        )

        assert "--gpus" not in cmd
        assert "wsclean:latest" in cmd

    @patch("shutil.which")
    def test_build_docker_command_with_volumes(self, mock_which):
        """Test building Docker command with custom volumes."""
        mock_which.return_value = "/usr/bin/docker"
        config = GPUConfig(enabled=False, gpus=[])

        cmd = build_docker_command(
            image="wsclean:latest",
            command=["wsclean", "--version"],
            gpu_config=config,
            volumes={"/host/path": "/container/path"},
        )

        assert "-v" in cmd
        idx = cmd.index("-v")
        assert cmd[idx + 1] == "/host/path:/container/path"


class TestBuildWSCleanGPUArgs:
    """Test WSClean GPU argument building."""

    def test_gpu_args_with_idg(self):
        """Test GPU args with IDG gridder."""
        config = GPUConfig(
            enabled=True,
            wsclean_gridder="idg",
            wsclean_idg_mode="hybrid",
            gpus=[
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ],
        )

        args = build_wsclean_gpu_args(config)
        assert args == ["-gridder", "idg", "-idg-mode", "hybrid"]

    def test_gpu_args_fallback_to_wgridder(self):
        """Test GPU args fall back to wgridder without GPU."""
        config = GPUConfig(enabled=True, gpus=[])

        args = build_wsclean_gpu_args(config)
        assert args == ["-gridder", "wgridder"]


class TestGetGPUEnvConfig:
    """Test environment-based GPU configuration."""

    def test_env_config_defaults(self):
        """Test env config with default values."""
        # Clear any existing env vars
        for var in ["PIPELINE_GPU_ENABLED", "PIPELINE_GPU_DEVICES",
                    "PIPELINE_GPU_GRIDDER", "PIPELINE_GPU_IDG_MODE"]:
            os.environ.pop(var, None)

        # Mock GPU detection
        with patch("dsa110_contimg.utils.gpu_utils.detect_gpus") as mock_detect:
            mock_detect.return_value = []
            with patch("dsa110_contimg.utils.gpu_utils.check_nvidia_docker") as mock_docker:
                mock_docker.return_value = False
                config = get_gpu_env_config()

        assert config.enabled is False  # No GPUs detected

    @patch.dict(os.environ, {
        "PIPELINE_GPU_ENABLED": "true",
        "PIPELINE_GPU_GRIDDER": "idg",
        "PIPELINE_GPU_IDG_MODE": "gpu",
    })
    def test_env_config_with_values(self):
        """Test env config with explicit values."""
        with patch("dsa110_contimg.utils.gpu_utils.detect_gpus") as mock_detect:
            mock_detect.return_value = [
                GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
            ]
            with patch("dsa110_contimg.utils.gpu_utils.check_nvidia_docker") as mock_docker:
                mock_docker.return_value = True
                config = get_gpu_env_config()

        assert config.enabled is True
        assert config.wsclean_gridder == "idg"
        assert config.wsclean_idg_mode == "gpu"


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    @patch("dsa110_contimg.utils.gpu_utils.detect_gpus")
    @patch("dsa110_contimg.utils.gpu_utils.check_nvidia_docker")
    def test_is_gpu_available(self, mock_docker, mock_detect):
        """Test is_gpu_available convenience function."""
        mock_detect.return_value = [
            GPUInfo(index=0, name="GPU", memory_mb=1024, driver_version="1.0")
        ]
        mock_docker.return_value = True

        assert is_gpu_available() is True

    @patch("dsa110_contimg.utils.gpu_utils.detect_gpus")
    @patch("dsa110_contimg.utils.gpu_utils.check_nvidia_docker")
    def test_get_gpu_count(self, mock_docker, mock_detect):
        """Test get_gpu_count convenience function."""
        mock_detect.return_value = [
            GPUInfo(index=0, name="GPU0", memory_mb=1024, driver_version="1.0"),
            GPUInfo(index=1, name="GPU1", memory_mb=1024, driver_version="1.0"),
        ]
        mock_docker.return_value = True

        assert get_gpu_count() == 2
