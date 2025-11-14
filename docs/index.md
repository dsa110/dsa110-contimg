# DSA-110 Continuum Imaging Pipeline

Welcome. This pipeline turns incoming UVH5 subband data into calibrated,
quick-look continuum images and exposes a monitoring API.

!!! info "Package Information" This documentation is for **dsa110-contimg**
version **0.1.0**.

    DSA-110 Continuum Imaging Pipeline

This documentation is organized to help you understand and use the pipeline
effectively.

## Getting Started

- **[Documentation Guide](DOCUMENTATION_QUICK_REFERENCE.md)**: Guide to
  documentation organization and location.
- **[Quick Start Guide](how-to/quickstart.md)**: Get up and running quickly.
- **[Mosaic Quickstart](how-to/mosaic_quickstart.md)**: Plan and build a basic
  sky mosaic.
- **[Dashboard Guide](how-to/dashboard.md)**: Development, deployment, testing

## Documentation Sections

- **[Concepts](concepts/index.md)**: Understand the high-level architecture and
  design.
- **[Tutorials](tutorials/)**: Follow step-by-step guides for common tasks.
- **[How-To Guides](how-to/)**: Find instructions for specific procedures.
- **[Reference](reference/)**: API documentation and technical references.
- **[Operations](operations/)**: Deployment and operational procedures.
- **Authoring Guide**:
  [Documentation Quick Reference](DOCUMENTATION_QUICK_REFERENCE.md)

## Key Features

### Streaming

- **[Streaming Guide](how-to/streaming.md)**: Control, deploy, troubleshoot, and
  run standalone conversions
- **[Streaming API Reference](reference/streaming-api.md)**: Complete API
  documentation
- **[Streaming Architecture](concepts/streaming-architecture.md)**: System
  architecture and design

### Dashboard

- **[Dashboard Guide](how-to/dashboard.md)**: Quick start, development,
  deployment, and testing
- **[Dashboard API Reference](reference/dashboard_backend_api.md)**: Complete
  API documentation
- **[Control Panel Guide](how-to/control-panel-quickstart.md)**: Using the
  control panel
- **[QA Visualization Quick Start](QA_VISUALIZATION_QUICK_START.md)**: FITS
  viewing, CASA browsing, QA notebooks
- **[QA Visualization Usage Guide](QA_VISUALIZATION_USAGE.md)**: Full usage and
  integration examples

### Pipeline Operations

- **[Docker Deployment](operations/deploy-docker.md)**: Deploy with Docker
- **[Systemd Deployment](operations/deploy-systemd.md)**: Deploy as system
  service
- **[CASA Log Daemon](operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md)**:
Automated log file management and monitoring
<!-- Streaming Converter doc consolidated into Streaming Guide -->
