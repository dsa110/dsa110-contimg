# Dockerfile for CubiCal Experimental Calibration
# Isolates CubiCal/Montblanc from host system to avoid compatibility issues

FROM ubuntu:20.04

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
# Note: We use conda for Python 3.11.13, so system Python is not required
# System Python 3.8 (default in Ubuntu 20.04) is sufficient for system tools
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    build-essential \
    libboost-all-dev \
    libcfitsio-dev \
    wcslib-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda for better Python package management
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh && \
    /opt/conda/bin/conda clean -afy

ENV PATH=/opt/conda/bin:$PATH

# Accept conda Terms of Service and create environment for CubiCal
RUN conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    conda create -n cubical python=3.10.13 -y && \
    conda clean -afy

# Activate conda environment in shell
SHELL ["conda", "run", "-n", "cubical", "/bin/bash", "-c"]

# Install CUDA toolkit (for GPU support)
RUN conda install -n cubical -c conda-forge \
    cudatoolkit=11.1 \
    cupy \
    numpy \
    scipy \
    -y && \
    conda clean -afy

# Install python-casacore (required for CubiCal)
# Try conda first, then pip as fallback
RUN conda install -n cubical -c conda-forge \
    python-casacore \
    -y || (pip install --no-cache-dir python-casacore || echo "python-casacore installation may need manual handling")

# Install additional build dependencies for CubiCal
RUN pip install --no-cache-dir \
    setuptools \
    wheel \
    cython \
    numpy \
    scipy

# Install CubiCal with Montblanc support
# Use explicit pip in conda environment
RUN /opt/conda/envs/cubical/bin/pip install --no-cache-dir \
    "cubical[lsm-support]@git+https://github.com/ratt-ru/CubiCal.git@1.4.0" || \
    echo "CubiCal installation failed - may need additional dependencies"

# Install additional dependencies
RUN pip install --no-cache-dir \
    astropy \
    matplotlib \
    h5py

# Set working directory
WORKDIR /workspace

# Copy CubiCal experimental module
COPY src/dsa110_contimg/calibration/cubical_experimental /workspace/cubical_experimental

# Default command
CMD ["/bin/bash"]
