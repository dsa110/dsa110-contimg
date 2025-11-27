# Operations Documentation

This directory contains operational guides for running and maintaining the
DSA-110 continuum imaging pipeline.

## Contents

### Service Management

- **[API Server Configuration](api_server.md)** - API server setup, auto-reload
  behavior, and configuration options
- **[API Restart Guide](service_restart_fix.md)** - How to restart the API
  service and troubleshoot common issues

### CASA Log Management

- **CASA Log Daemon Protection Summary** -
  Quick overview of protection features (start here)
- **CASA Log Daemon Monitoring** - Complete
  monitoring and health check guide
- **CASA Log Daemon Fixes** - Technical details of
  fixes and improvements

### Deployment

- **[Docker Deployment](deploy-docker.md)** - Deploy with Docker
- **[Systemd Deployment](deploy-systemd.md)** - Deploy as system service
- **[Systemd Migration](systemd-migration.md)** - Migration guide

### Other Operations

- **[Port Management](port-management.md)** - Port configuration and management
- **[Refant Quick Reference](refant_quick_reference.md)** - Reference antenna
  selection guide

## Quick Links

- API Docker Compose: `/data/dsa110-contimg/ops/docker/docker-compose.yml`
- API Code: `/data/dsa110-contimg/src/dsa110_contimg/api/routes.py`
- Service Management: `scripts/manage-services.sh`
- Systemd Config: `/data/dsa110-contimg/ops/systemd/contimg.env`
- CASA Log Daemon Setup: `scripts/setup_casa_log_daemon_monitoring.sh`
