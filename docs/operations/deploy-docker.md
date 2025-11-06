# Deploy with Docker Compose

- Copy `.env`: `cp ops/docker/.env.example ops/docker/.env`; edit absolute paths and UID/GID
- Build: `make compose-build`
- Up: `make compose-up`
- Logs: `make compose-logs SERVICE=stream`
- Optional scheduler: `make compose-up-scheduler`

## Environment (.env)
- Paths: `REPO_ROOT`, `CONTIMG_INPUT_DIR`, `CONTIMG_OUTPUT_DIR`, `CONTIMG_SCRATCH_DIR`, `CONTIMG_STATE_DIR`
- DBs: `CONTIMG_QUEUE_DB`, `CONTIMG_REGISTRY_DB`, `CONTIMG_PRODUCTS_DB`
- Service: `CONTIMG_API_PORT`, `CONTIMG_LOG_LEVEL`, `CONTIMG_EXPECTED_SUBBANDS`, `CONTIMG_CHUNK_MINUTES`, `CONTIMG_MONITOR_INTERVAL`
- User mapping: `UID`, `GID`
- Optional: `HDF5_USE_FILE_LOCKING=FALSE`, `OMP_NUM_THREADS`, `MKL_NUM_THREADS`
