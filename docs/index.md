# DSA-110 Continuum Imaging Pipeline

Welcome. This pipeline turns incoming UVH5 subband data into calibrated, quick-look continuum images and exposes a monitoring API.

This documentation is organized to help you understand and use the pipeline effectively.

## Getting Started

- **[Documentation Guide](DOCUMENTATION_QUICK_REFERENCE.md)**: Guide to documentation organization and location.
- **[Quick Start Guide](how-to/quickstart.md)**: Get up and running quickly.
- **[Mosaic Quickstart](how-to/mosaic_quickstart.md)**: Plan and build a basic sky mosaic.
- **[Dashboard Development](how-to/dashboard-development.md)**: Set up the development environment.

## Documentation Sections

- **[Concepts](concepts/index.md)**: Understand the high-level architecture and design.
- **[Tutorials](tutorials/)**: Follow step-by-step guides for common tasks.
- **[How-To Guides](how-to/)**: Find instructions for specific procedures.
- **[Reference](reference/)**: API documentation and technical references.
- **[Operations](operations/)**: Deployment and operational procedures.

## Key Features

### Streaming Service Control
- **[Streaming Control Guide](how-to/streaming-control.md)**: Control the streaming service via dashboard
- **[Streaming Troubleshooting Guide](how-to/streaming-troubleshooting.md)**: Comprehensive troubleshooting procedures
- **[Streaming API Reference](reference/streaming-api.md)**: Complete API documentation
- **[Streaming Architecture](concepts/streaming-architecture.md)**: System architecture and design

### Dashboard
- **[Dashboard API Reference](reference/dashboard_backend_api.md)**: Complete API documentation
- **[Control Panel Guide](how-to/control-panel-quickstart.md)**: Using the control panel
- **[Sky View](SKYVIEW_IMPLEMENTATION_PLAN.md)**: Image viewing and analysis

### Pipeline Operations
- **[Docker Deployment](operations/deploy-docker.md)**: Deploy with Docker
- **[Systemd Deployment](operations/deploy-systemd.md)**: Deploy as system service
- **[CASA Log Daemon](operations/CASA_LOG_DAEMON_PROTECTION_SUMMARY.md)**: Automated log file management and monitoring
- **[Streaming Converter](how-to/streaming_converter_guide.md)**: Streaming converter architecture
