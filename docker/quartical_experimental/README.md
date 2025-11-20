# CubiCal Docker Environment

## Purpose

Isolates CubiCal/Montblanc installation in a Docker container to avoid:

- Compatibility issues with Ubuntu 18.x
- Conflicts with existing CASA environment
- System-wide package pollution

## Prerequisites

- Docker installed and running
- NVIDIA Docker runtime (nvidia-docker2) for GPU support
- Docker Compose (optional, for easier management)

## Setup

### 1. Install NVIDIA Docker Runtime

```bash
# Add NVIDIA Docker repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install nvidia-docker2
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker
sudo systemctl restart docker
```

### 2. Build Docker Image

```bash
cd /data/dsa110-contimg/docker/cubical_experimental

# Build the image
docker build -t dsa110-cubical:experimental -f Dockerfile ../..
```

### 3. Run Container

#### Option A: Using Docker Compose (Recommended)

```bash
cd /data/dsa110-contimg/docker/cubical_experimental
docker-compose up -d
docker-compose exec cubical bash
```

#### Option B: Using Docker Directly

```bash
docker run -it --rm \
  --gpus all \
  -v /scratch:/scratch:ro \
  -v /data:/data:ro \
  -v /scratch/calibration_test:/workspace/output:rw \
  -v /data/dsa110-contimg/src/dsa110_contimg/calibration/cubical_experimental:/workspace/cubical_experimental:ro \
  dsa110-cubical:experimental \
  bash
```

## Usage

### Inside Container

```bash
# Activate conda environment
conda activate cubical

# Test GPU access
python -c "import cupy; print(cupy.cuda.runtime.getDeviceCount())"

# Run CubiCal calibration
python -m cubical_experimental.cubical_cli \
  --ms /scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms \
  --field 0 \
  --output-dir /workspace/output/cubical
```

### From Host (One-liner)

```bash
docker run -it --rm --gpus all \
  -v /scratch:/scratch:ro \
  -v /scratch/calibration_test:/workspace/output:rw \
  -v /data/dsa110-contimg/src/dsa110_contimg/calibration/cubical_experimental:/workspace/cubical_experimental:ro \
  dsa110-cubical:experimental \
  bash -c "conda activate cubical && python -m cubical_experimental.cubical_cli --ms /scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms --field 0 --output-dir /workspace/output/cubical"
```

## Benefits

✓ Isolated environment (no conflicts with host) ✓ Clean Ubuntu 20.04 base
(better compatibility) ✓ GPU access via NVIDIA runtime ✓ Easy to rebuild/clean
up ✓ Can run alongside existing CASA pipeline

## Troubleshooting

### GPU Not Available

```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.1-base nvidia-smi

# If fails, install nvidia-docker2 (see Prerequisites)
```

### Build Fails on python-casacore

```bash
# May need to build python-casacore manually
# Or use pre-built conda package
```

### Permission Issues

```bash
# Ensure output directory is writable
chmod 777 /scratch/calibration_test
```

## Development Workflow

1. Edit code on host:
   `/data/dsa110-contimg/src/dsa110_contimg/calibration/cubical_experimental/`
2. Code is mounted into container (read-only)
3. Test in container
4. Results saved to `/scratch/calibration_test/` (accessible from host)
