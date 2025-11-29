"""
GPU utilities for seamless GPU acceleration across all pipeline modes.

This module provides unified GPU detection, configuration, and Docker command
building that works consistently across CLI, streaming, and ABSURD execution modes.

Example usage:
    from dsa110_contimg.utils.gpu_utils import get_gpu_config, build_docker_command

    # Auto-detect GPU availability
    gpu_config = get_gpu_config()
    
    # Build Docker command with GPU support if available
    cmd = build_docker_command(
        image="wsclean-everybeam:0.7.4",
        command=["wsclean", "-gridder", "idg", "-idg-mode", "gpu", ...],
        gpu_config=gpu_config,
    )
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class GPUBackend(str, Enum):
    """GPU backend types."""

    NONE = "none"  # No GPU acceleration
    CUDA = "cuda"  # NVIDIA CUDA
    # Future: OPENCL = "opencl"  # OpenCL (AMD, Intel)


@dataclass
class GPUInfo:
    """Information about a detected GPU."""

    index: int
    name: str
    memory_mb: int
    driver_version: str
    cuda_version: Optional[str] = None
    compute_capability: Optional[str] = None
    
    @property
    def memory_gb(self) -> float:
        """Memory in GB."""
        return self.memory_mb / 1024.0


@dataclass
class GPUConfig:
    """Unified GPU configuration for pipeline execution.
    
    This configuration is used across all pipeline modes (CLI, streaming, ABSURD)
    to ensure consistent GPU behavior.
    """

    # Core settings
    enabled: bool = True  # Whether to attempt GPU acceleration
    backend: GPUBackend = GPUBackend.CUDA
    device_ids: List[int] = field(default_factory=list)  # Empty = all GPUs
    
    # Docker settings
    docker_gpu_flag: str = "--gpus all"  # Can be "--gpus 0" for specific GPU
    
    # WSClean-specific settings
    wsclean_gridder: str = "idg"  # "idg", "wgridder", or "wstacking"
    wsclean_idg_mode: str = "hybrid"  # "cpu", "gpu", or "hybrid"
    
    # Photometry GPU settings (CuPy)
    photometry_use_gpu: bool = True
    photometry_batch_threshold: int = 100  # Min sources to use GPU
    
    # Memory management
    gpu_memory_fraction: float = 0.9  # Max fraction of GPU memory to use
    
    # Detected GPU info (populated by detect_gpus())
    gpus: List[GPUInfo] = field(default_factory=list)
    
    @property
    def has_gpu(self) -> bool:
        """Check if any GPUs are available."""
        return len(self.gpus) > 0
    
    @property
    def total_gpu_memory_gb(self) -> float:
        """Total GPU memory across all devices."""
        return sum(gpu.memory_gb for gpu in self.gpus)
    
    @property
    def effective_gridder(self) -> str:
        """Get effective gridder based on GPU availability."""
        if self.enabled and self.has_gpu:
            return self.wsclean_gridder
        return "wgridder"  # CPU fallback
    
    @property
    def effective_idg_mode(self) -> str:
        """Get effective IDG mode based on GPU availability."""
        if self.enabled and self.has_gpu:
            return self.wsclean_idg_mode
        return "cpu"


def _parse_nvidia_smi_output(output: str) -> List[GPUInfo]:
    """Parse nvidia-smi query output into GPUInfo list."""
    gpus = []
    lines = output.strip().split("\n")
    
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        parts = line.split(", ")
        if len(parts) >= 3:
            try:
                gpus.append(GPUInfo(
                    index=i,
                    name=parts[0].strip(),
                    memory_mb=int(parts[1].strip().replace(" MiB", "")),
                    driver_version=parts[2].strip(),
                    cuda_version=None,  # Not available via nvidia-smi query
                ))
            except (ValueError, IndexError) as e:
                logger.debug(f"Failed to parse GPU info from line: {line}: {e}")
    
    return gpus


@lru_cache(maxsize=1)
def detect_gpus() -> List[GPUInfo]:
    """Detect available NVIDIA GPUs.
    
    Returns:
        List of GPUInfo for each detected GPU
    """
    gpus: List[GPUInfo] = []
    
    # Try nvidia-smi first (most reliable)
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gpus = _parse_nvidia_smi_output(result.stdout)
                logger.info(f"Detected {len(gpus)} NVIDIA GPU(s) via nvidia-smi")
                for gpu in gpus:
                    logger.debug(f"  GPU {gpu.index}: {gpu.name} ({gpu.memory_gb:.1f} GB)")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.debug(f"nvidia-smi failed: {e}")
    
    return gpus
    if nvidia_smi:
        try:
            result = subprocess.run(
                [
                    nvidia_smi,
                    "--query-gpu=name,memory.total,driver_version,cuda_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                gpus = _parse_nvidia_smi_output(result.stdout)
                logger.info(f"Detected {len(gpus)} NVIDIA GPU(s) via nvidia-smi")
                for gpu in gpus:
                    logger.debug(f"  GPU {gpu.index}: {gpu.name} ({gpu.memory_gb:.1f} GB)")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.debug(f"nvidia-smi failed: {e}")
    
    return gpus


def check_nvidia_docker() -> bool:
    """Check if NVIDIA Docker runtime is available.
    
    Returns:
        True if nvidia-container-toolkit is properly configured
    """
    docker_cmd = shutil.which("docker")
    if not docker_cmd:
        return False
    
    try:
        # Check if nvidia runtime is configured
        result = subprocess.run(
            [docker_cmd, "info", "--format", "{{.Runtimes}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if "nvidia" in result.stdout.lower():
            return True
        
        # Also check for --gpus support (CDI mode)
        result = subprocess.run(
            [docker_cmd, "run", "--rm", "--gpus", "all", "nvidia/cuda:11.1.1-base-ubuntu18.04", "echo", "ok"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.debug(f"NVIDIA Docker check failed: {e}")
        return False


@lru_cache(maxsize=1)
def get_gpu_config(
    enabled: Optional[bool] = None,
    device_ids: Optional[Tuple[int, ...]] = None,
) -> GPUConfig:
    """Get unified GPU configuration with auto-detection.
    
    This is the main entry point for GPU configuration. It auto-detects
    available GPUs and Docker capabilities, returning a configuration
    that works across all pipeline modes.
    
    Args:
        enabled: Override auto-detection (None = auto-detect)
        device_ids: Specific GPU indices to use (None = all)
    
    Returns:
        GPUConfig with detected capabilities
    
    Example:
        >>> config = get_gpu_config()
        >>> if config.has_gpu:
        ...     print(f"Using {len(config.gpus)} GPU(s)")
        >>> else:
        ...     print("CPU-only mode")
    """
    # Detect GPUs
    gpus = detect_gpus()
    
    # Check Docker GPU support
    has_docker_gpu = check_nvidia_docker() if gpus else False
    
    # Determine if GPU should be enabled
    if enabled is None:
        enabled = len(gpus) > 0 and has_docker_gpu
    
    # Build device list
    device_list = list(device_ids) if device_ids else []
    
    # Build GPU flag
    if device_list:
        gpu_flag = f"--gpus '\"device={','.join(str(d) for d in device_list)}\"'"
    else:
        gpu_flag = "--gpus all"
    
    config = GPUConfig(
        enabled=enabled,
        backend=GPUBackend.CUDA if gpus else GPUBackend.NONE,
        device_ids=device_list,
        docker_gpu_flag=gpu_flag,
        gpus=gpus,
        # Use hybrid mode by default (best balance of speed and memory)
        wsclean_idg_mode="hybrid" if gpus else "cpu",
    )
    
    if config.has_gpu:
        logger.info(
            f"GPU acceleration enabled: {len(gpus)} GPU(s), "
            f"{config.total_gpu_memory_gb:.1f} GB total memory"
        )
    else:
        logger.info("GPU acceleration disabled (no GPUs detected or Docker GPU unavailable)")
    
    return config


def build_docker_command(
    image: str,
    command: List[str],
    gpu_config: Optional[GPUConfig] = None,
    volumes: Optional[Dict[str, str]] = None,
    workdir: Optional[str] = None,
    env_vars: Optional[Dict[str, str]] = None,
    extra_flags: Optional[List[str]] = None,
    remove: bool = True,
) -> List[str]:
    """Build Docker command with optional GPU support.
    
    This is the unified way to build Docker commands across the pipeline.
    It handles GPU flags, volume mounts, and other common options.
    
    Args:
        image: Docker image name
        command: Command to run inside container
        gpu_config: GPU configuration (None = auto-detect)
        volumes: Host:container volume mappings
        workdir: Working directory inside container
        env_vars: Environment variables to set
        extra_flags: Additional Docker flags
        remove: Remove container after exit (--rm)
    
    Returns:
        Complete Docker command as list
    
    Example:
        >>> cmd = build_docker_command(
        ...     image="wsclean-everybeam:0.7.4",
        ...     command=["wsclean", "-size", "5040", "5040", ...],
        ...     volumes={"/data": "/data", "/stage": "/stage"},
        ... )
        >>> subprocess.run(cmd)
    """
    if gpu_config is None:
        gpu_config = get_gpu_config()
    
    docker_cmd = shutil.which("docker")
    if not docker_cmd:
        raise RuntimeError("Docker not found in PATH")
    
    cmd = [docker_cmd, "run"]
    
    # Basic flags
    if remove:
        cmd.append("--rm")
    
    # GPU support
    if gpu_config.enabled and gpu_config.has_gpu:
        # Parse gpu_flag (handle quoted format)
        gpu_flag = gpu_config.docker_gpu_flag
        if gpu_flag.startswith("--gpus"):
            parts = gpu_flag.split(None, 1)
            cmd.append(parts[0])  # --gpus
            if len(parts) > 1:
                # Remove surrounding quotes if present
                value = parts[1].strip("'\"")
                cmd.append(value)
    
    # Volumes
    if volumes:
        for host_path, container_path in volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])
    else:
        # Default volume mounts for DSA-110 pipeline
        cmd.extend(["-v", "/scratch:/scratch"])
        cmd.extend(["-v", "/data:/data"])
        cmd.extend(["-v", "/stage:/stage"])
        cmd.extend(["-v", "/dev/shm:/dev/shm"])
    
    # Working directory
    if workdir:
        cmd.extend(["-w", workdir])
    
    # Environment variables
    if env_vars:
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])
    
    # Extra flags
    if extra_flags:
        cmd.extend(extra_flags)
    
    # Image and command
    cmd.append(image)
    cmd.extend(command)
    
    return cmd


def build_wsclean_gpu_args(gpu_config: Optional[GPUConfig] = None) -> List[str]:
    """Build WSClean GPU-specific arguments.
    
    Args:
        gpu_config: GPU configuration (None = auto-detect)
    
    Returns:
        List of WSClean arguments for GPU acceleration
    
    Example:
        >>> args = build_wsclean_gpu_args()
        >>> # Returns ["-gridder", "idg", "-idg-mode", "hybrid"] if GPU available
        >>> # Returns ["-gridder", "wgridder"] if no GPU
    """
    if gpu_config is None:
        gpu_config = get_gpu_config()
    
    args = []
    
    if gpu_config.enabled and gpu_config.has_gpu:
        args.extend(["-gridder", gpu_config.wsclean_gridder])
        if gpu_config.wsclean_gridder == "idg":
            args.extend(["-idg-mode", gpu_config.effective_idg_mode])
        logger.debug(f"WSClean GPU args: {args}")
    else:
        # CPU fallback - use wgridder (still fast, but CPU-only)
        args.extend(["-gridder", "wgridder"])
        logger.debug("WSClean using CPU-only wgridder")
    
    return args


def get_gpu_env_config() -> GPUConfig:
    """Get GPU configuration from environment variables.
    
    Environment variables:
        PIPELINE_GPU_ENABLED: "true" or "false" (default: auto-detect)
        PIPELINE_GPU_DEVICES: Comma-separated device IDs (default: all)
        PIPELINE_GPU_GRIDDER: WSClean gridder (default: "idg")
        PIPELINE_GPU_IDG_MODE: IDG mode (default: "hybrid")
        PIPELINE_GPU_MEMORY_FRACTION: Max memory fraction (default: 0.9)
    
    Returns:
        GPUConfig from environment
    """
    # Get enabled state
    enabled_str = os.getenv("PIPELINE_GPU_ENABLED", "").lower()
    if enabled_str == "true":
        enabled = True
    elif enabled_str == "false":
        enabled = False
    else:
        enabled = None  # Auto-detect
    
    # Get device IDs
    devices_str = os.getenv("PIPELINE_GPU_DEVICES", "")
    device_ids: Optional[Tuple[int, ...]] = None
    if devices_str:
        try:
            device_ids = tuple(int(d.strip()) for d in devices_str.split(","))
        except ValueError:
            logger.warning(f"Invalid PIPELINE_GPU_DEVICES: {devices_str}")
    
    # Get base config with detection
    config = get_gpu_config(enabled=enabled, device_ids=device_ids)
    
    # Override with env vars
    config.wsclean_gridder = os.getenv("PIPELINE_GPU_GRIDDER", config.wsclean_gridder)
    config.wsclean_idg_mode = os.getenv("PIPELINE_GPU_IDG_MODE", config.wsclean_idg_mode)
    
    memory_fraction_str = os.getenv("PIPELINE_GPU_MEMORY_FRACTION", "")
    if memory_fraction_str:
        try:
            config.gpu_memory_fraction = float(memory_fraction_str)
        except ValueError:
            logger.warning(f"Invalid PIPELINE_GPU_MEMORY_FRACTION: {memory_fraction_str}")
    
    return config


# Module-level convenience functions

def is_gpu_available() -> bool:
    """Quick check if GPU acceleration is available."""
    return get_gpu_config().has_gpu


def get_gpu_count() -> int:
    """Get number of available GPUs."""
    return len(get_gpu_config().gpus)


def clear_gpu_cache() -> None:
    """Clear cached GPU detection results.
    
    Call this if GPU configuration changes (e.g., Docker restarted).
    """
    detect_gpus.cache_clear()
    get_gpu_config.cache_clear()
