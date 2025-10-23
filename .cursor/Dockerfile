FROM mambaorg/micromamba:1.5.9-focal

ARG MAMBA_DOCKERFILE_ACTIVATE=1

# Create the same environment used by ops/docker/Dockerfile
COPY ops/docker/environment.yml /tmp/environment.yml
RUN micromamba create -y -n contimg -f /tmp/environment.yml && \
    micromamba clean -a -y

SHELL ["/bin/bash", "-lc"]
ENV PATH=/opt/conda/envs/contimg/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HDF5_USE_FILE_LOCKING=FALSE \
    OMP_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    PYTHONPATH=/app/src

# Background agents do not copy source; agents clone/mount code later
USER mambauser
WORKDIR /home/mambauser

CMD ["bash", "-lc", "sleep infinity"]

