# GPU Acceleration Guide

This guide explains how to use GPU acceleration in the DSA-110 continuum imaging
pipeline.

## Overview

The pipeline supports GPU acceleration for imaging operations using the
[IDG (Image Domain Gridding)](https://gitlab.com/astron-idg/idg) library
integrated into WSClean. The system automatically detects available NVIDIA GPUs
and configures Docker containers to use them.

## Hardware Requirements

- **GPU**: NVIDIA GPU with CUDA compute capability 3.5+ (Pascal, Volta, Turing,
  Ampere architectures)
- **Driver**: NVIDIA driver 455.23.05 or newer
- **Docker**: nvidia-container-toolkit installed and configured
- **Memory**: 8+ GB VRAM recommended for typical DSA-110 images

The current system has:

- 2x GeForce RTX 2080 Ti (11 GB VRAM each, 22 GB total)
- NVIDIA Driver 455.23.05
- CUDA 11.1 (in Docker containers)

## Quick Start

GPU acceleration is **enabled by default** when GPUs are detected. No
configuration is required for typical use cases.

### Verify GPU Access

```bash
# Check GPU availability
conda activate casa6
python -c "from dsa110_contimg.utils.gpu_utils import get_gpu_config; print(get_gpu_config())"

# Expected output:
# GPUConfig(enabled=True, backend=<GPUBackend.CUDA: 'cuda'>, ...gpus=[GPUInfo(...)])
```

### Test Docker GPU Access

```bash
docker run --rm --gpus all wsclean-everybeam:0.7.4 nvidia-smi
```

## Configuration Options

### Environment Variables

GPU settings can be configured via environment variables in
`/data/dsa110-contimg/ops/systemd/contimg.env`:

| Variable                       | Default  | Description                                     |
| ------------------------------ | -------- | ----------------------------------------------- |
| `PIPELINE_GPU_ENABLED`         | `true`   | Enable GPU acceleration                         |
| `PIPELINE_GPU_DEVICES`         | (all)    | Comma-separated device IDs (e.g., "0,1")        |
| `PIPELINE_GPU_GRIDDER`         | `idg`    | WSClean gridder: `idg`, `wgridder`, `wstacking` |
| `PIPELINE_GPU_IDG_MODE`        | `hybrid` | IDG mode: `cpu`, `gpu`, or `hybrid`             |
| `PIPELINE_GPU_MEMORY_FRACTION` | `0.9`    | Max fraction of GPU memory to use               |

### IDG Modes Explained

- **`gpu`**: All operations on GPU. Fastest but uses most memory.
- **`cpu`**: All operations on CPU. Slowest but minimal GPU memory.
- **`hybrid`** (default): GPU for compute, CPU for I/O. Best balance of speed
  and memory usage.

### ImagingConfig Options

When using the Python API, GPU settings are in `ImagingConfig`:

```python
from dsa110_contimg.pipeline.config import ImagingConfig

imaging_config = ImagingConfig(
    gpu_enabled=True,       # Enable GPU acceleration
    gridder="idg",          # Use IDG gridder
    gpu_idg_mode="hybrid",  # Hybrid mode for best balance
    gpu_device_ids=[0, 1],  # Use both GPUs (None = all)
)
```

## Python API

### Auto-Detection

```python
from dsa110_contimg.utils.gpu_utils import get_gpu_config, is_gpu_available

# Quick check
if is_gpu_available():
    print("GPU acceleration available!")

# Full configuration
config = get_gpu_config()
print(f"GPUs: {len(config.gpus)}, Memory: {config.total_gpu_memory_gb:.1f} GB")
```

### Building Docker Commands

```python
from dsa110_contimg.utils.gpu_utils import build_docker_command, get_gpu_config

gpu_config = get_gpu_config()
cmd = build_docker_command(
    image="wsclean-everybeam:0.7.4",
    command=["wsclean", "-size", "5040", "5040", ...],
    gpu_config=gpu_config,
)
# cmd includes --gpus all when GPUs are available
```

### WSClean GPU Arguments

```python
from dsa110_contimg.utils.gpu_utils import build_wsclean_gpu_args, get_gpu_config

gpu_config = get_gpu_config()
args = build_wsclean_gpu_args(gpu_config)
# Returns ["-gridder", "idg", "-idg-mode", "hybrid"] with GPU
# Returns ["-gridder", "wgridder"] without GPU
```

### Environment Configuration

```python
from dsa110_contimg.utils.gpu_utils import get_gpu_env_config

# Load config from environment variables
config = get_gpu_env_config()
```

## Execution Modes

GPU acceleration works consistently across all execution modes:

### CLI Mode

```bash
# GPU auto-detected, uses IDG gridder if available
python -m dsa110_contimg.pipeline.cli run --stages imaging ...
```

### Streaming Mode

The streaming converter automatically uses GPU acceleration when available:

```bash
# GPU settings from environment
sudo systemctl start contimg-stream.service
```

### ABSURD Workflow Mode

GPU configuration is inherited from environment:

```bash
# Set GPU env vars in contimg.env, then:
sudo systemctl restart absurd-worker.service
```

### Long-Running Container Mode

For the `WSCleanContainer` class (NFS hang workaround):

```python
from dsa110_contimg.imaging.docker_utils import WSCleanContainer
from dsa110_contimg.utils.gpu_utils import get_gpu_config

gpu_config = get_gpu_config()
with WSCleanContainer(gpu_config=gpu_config) as container:
    container.wsclean(["-gridder", "idg", "-idg-mode", "gpu", ...])
```

## Performance Expectations

With GPU acceleration (2x RTX 2080 Ti):

| Operation          | CPU-only | GPU (hybrid) | Speedup |
| ------------------ | -------- | ------------ | ------- |
| 5040×5040 image    | ~8 min   | ~2 min       | 4x      |
| Widefield gridding | ~15 min  | ~4 min       | 3-4x    |
| Multi-scale clean  | ~25 min  | ~8 min       | 3x      |

**Note**: Actual speedup depends on image size, spectral configuration, and
clean depth.

## Troubleshooting

### GPUs Not Detected

```bash
# Check nvidia-smi works
nvidia-smi

# Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:11.1.1-base-ubuntu18.04 nvidia-smi

# Clear cached detection
python -c "from dsa110_contimg.utils.gpu_utils import clear_gpu_cache; clear_gpu_cache()"
```

### Docker GPU Not Working

```bash
# Verify nvidia-container-toolkit installed
dpkg -l | grep nvidia-container

# Reconfigure Docker runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Memory Errors

If you see CUDA out-of-memory errors:

1. Reduce IDG mode from `gpu` to `hybrid`
2. Reduce image size
3. Use single GPU: `PIPELINE_GPU_DEVICES=0`

### Disable GPU Acceleration

```bash
# Disable via environment
export PIPELINE_GPU_ENABLED=false
python -m dsa110_contimg.pipeline.cli run ...

# Or permanently in contimg.env
echo "PIPELINE_GPU_ENABLED=false" >> /data/dsa110-contimg/ops/systemd/contimg.env
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Pipeline Execution                      │
│  (CLI / Streaming / ABSURD)                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    gpu_utils Module                          │
│  - detect_gpus()           - get_gpu_config()               │
│  - build_docker_command()  - build_wsclean_gpu_args()       │
└──────────────────────────┬──────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│ cli_imaging │   │docker_utils │   │   config    │
│  run_wsclean│   │WSCleanCont. │   │ImagingConfig│
└──────┬──────┘   └──────┬──────┘   └─────────────┘
       │                 │
       ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                Docker with --gpus all                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     wsclean-everybeam:0.7.4                         │    │
│  │     WSClean 3.6 + IDG GPU gridder                   │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    GPU Hardware                              │
│  GPU 0: RTX 2080 Ti (11 GB)    GPU 1: RTX 2080 Ti (11 GB)   │
└─────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [WSClean Documentation](https://wsclean.readthedocs.io/)
- [IDG Gridder](https://gitlab.com/astron-idg/idg)
- [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)

