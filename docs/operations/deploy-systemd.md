# Deploy with systemd

- Edit `ops/systemd/contimg.env`
- Install units: copy to `/etc/systemd/system/`, daemon-reload
- Enable services: `contimg-stream.service`, `contimg-api.service`
- Logs: `journalctl -u contimg-stream -f`

## Environment keys (contimg.env)
- `CONTIMG_INPUT_DIR`, `CONTIMG_OUTPUT_DIR`, `CONTIMG_SCRATCH_DIR`
- `CONTIMG_QUEUE_DB`, `CONTIMG_REGISTRY_DB`, `CONTIMG_PRODUCTS_DB`, `CONTIMG_STATE_DIR`
- `CONTIMG_LOG_LEVEL`, `CONTIMG_EXPECTED_SUBBANDS`, `CONTIMG_CHUNK_MINUTES`, `CONTIMG_MONITOR_INTERVAL`
- Pipeline identity: `PIPELINE_TELESCOPE_NAME` (default `DSA_110`)
- Optional: `CASACORE_DATA` (Measures overlay) when an observatory name must resolve via casacore

Unit example: see `ops/systemd/contimg-stream.service` for full ExecStart and resource limits.
