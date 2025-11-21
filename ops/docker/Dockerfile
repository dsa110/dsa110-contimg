# Multi-purpose image for streaming worker and API
FROM mambaorg/micromamba:1.5.9-focal

ARG MAMBA_DOCKERFILE_ACTIVATE=1
COPY ops/docker/environment.yml /tmp/environment.yml
RUN micromamba create -y -n casa6 -f /tmp/environment.yml && \
    micromamba clean -a -y

SHELL ["/bin/bash", "-lc"]
ENV PATH=/opt/conda/envs/casa6/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HDF5_USE_FILE_LOCKING=FALSE \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    PYTHONPATH=/app/src

WORKDIR /app
# Copy only minimal files required at runtime; code is volume-mounted by compose
COPY backend/src /app/src
COPY scripts /app/scripts
COPY ops /app/ops

# Sanity check
RUN python -c "import sys; print(sys.version)" && python -c "import casatasks, pyuvdata; print('CASA/pyuvdata OK')"

CMD ["/bin/bash"]

