# DSA-110 Continuum Imaging Pipeline Dockerfile
# Multi-stage build for optimized production image

# Stage 1: Base image with system dependencies
FROM ubuntu:22.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    unzip \
    libfftw3-dev \
    libcfitsio-dev \
    libhdf5-dev \
    libblas-dev \
    liblapack-dev \
    libgsl-dev \
    libgfortran5 \
    libgomp1 \
    libopenmpi-dev \
    openmpi-bin \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Python environment
FROM base as python-env

    # Install Python 3.11
    RUN apt-get update && apt-get install -y \
        software-properties-common \
        && add-apt-repository ppa:deadsnakes/ppa \
        && apt-get update && apt-get install -y \
        python3.11 \
        python3.11-dev \
        python3.11-distutils \
        python3-pip \
        && rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# Install pip and upgrade
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11
RUN python -m pip install --upgrade pip setuptools wheel

# Stage 3: CASA installation (simplified - skip for now)
FROM python-env as casa-env

# Set CASA environment variables
ENV CASA_ROOT=/opt/casa
ENV PATH=$CASA_ROOT/bin:$PATH
ENV LD_LIBRARY_PATH=$CASA_ROOT/lib:$LD_LIBRARY_PATH

# Create CASA directory (will be populated later)
RUN mkdir -p $CASA_ROOT

# Stage 4: Application dependencies
FROM casa-env as app-deps

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Verify critical packages are installed
RUN python -c "import psutil, numpy, astropy; print('Critical packages verified')"

# Stage 5: Application
FROM app-deps as app

# Create non-root user
RUN groupadd -r dsa110 && useradd -r -g dsa110 dsa110

# Create application directories
RUN mkdir -p /app/data /app/logs /app/config /app/output && \
    chown -R dsa110:dsa110 /app

# Copy application code
COPY . /app/

# Verify all critical imports work
RUN python -c "import sys; sys.path.insert(0, '/app'); from core.utils.health_monitoring import HealthMonitor; from core.utils.monitoring_dashboard import MonitoringDashboard; print('All critical imports successful')"

# Set ownership
RUN chown -R dsa110:dsa110 /app

# Switch to non-root user
USER dsa110

# Set working directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/data/hdf5 /app/data/ms /app/data/images /app/data/mosaics /app/data/photometry

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Default command
CMD ["python", "-m", "core.main"]

# Stage 6: Production image (minimal)
FROM ubuntu:22.04 as production

    # Install minimal runtime dependencies
    RUN apt-get update && apt-get install -y \
        python3.10 \
        python3-pip \
        python3.10-dev \
        python3.10-distutils \
        libfftw3-3 \
        libgsl27 \
        libgfortran5 \
        libgomp1 \
        && rm -rf /var/lib/apt/lists/*

# Install Python packages for Python 3.10
COPY requirements.txt /tmp/requirements.txt
RUN python3.10 -m pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application from app stage
COPY --from=app /app /app
COPY --from=app /opt/casa /opt/casa

# Set environment variables
ENV PATH=/opt/casa/bin:/app:$PATH
ENV LD_LIBRARY_PATH=/opt/casa/lib:$LD_LIBRARY_PATH
ENV PYTHONPATH=/app

# Create symlink for python command
RUN ln -sf /usr/bin/python3.10 /usr/bin/python

# Create non-root user
RUN groupadd -r dsa110 && useradd -r -g dsa110 dsa110

# Set ownership
RUN chown -R dsa110:dsa110 /app

# Switch to non-root user
USER dsa110

# Set working directory
WORKDIR /app

# Expose ports
EXPOSE 8080 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Default command
CMD ["python3", "-m", "core.main"]
