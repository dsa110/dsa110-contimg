# Tutorial: End-to-End Streaming

This walks through running the streaming worker + API and verifying outputs.

- Start services (Docker): `make compose-up`
- Tail logs: `make compose-logs SERVICE=stream`
- Verify MS tiles appear in `${CONTIMG_OUTPUT_DIR}`
- Confirm products DB has entries in `images` and `ms_index`
- Visit API `/api/status`

Tips
- Set `PIPELINE_POINTING_DEC_DEG` and `VLA_CALIBRATOR_CSV` to enable calibrator matching
- Use `make compose-up-scheduler` to enable nightly mosaic/housekeeping
