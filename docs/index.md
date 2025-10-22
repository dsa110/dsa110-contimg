# DSA-110 Continuum Imaging Pipeline

Welcome. This pipeline turns incoming UVH5 subband data into calibrated, quick-look continuum images and exposes a monitoring API.

- Stream: ingest → convert → calibrate/apply → image
- Data stores: queue (ingest), calibration registry, products (images + index)
- Deploy: systemd (worker) or Docker Compose (worker + API)

Get started fast in the Quick Start.

- [Quick Start](quickstart.md)
- [Pipeline Visuals](pipeline.md)
- [Quick-Look Pipeline (sub-minute)](quicklook.md)
- [CLI Reference](reference/cli.md)
