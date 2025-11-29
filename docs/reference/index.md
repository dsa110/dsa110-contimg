# API Reference Index

**Last Updated:** November 29, 2025

This index organizes all API documentation for the DSA-110 Continuum Imaging
Pipeline.

---

## Quick Links

| Document                                      | Description                           |
| --------------------------------------------- | ------------------------------------- |
| [API Overview](api.md)                        | Core REST API (images, sources, jobs) |
| [Endpoint List](api-endpoints.md)             | Complete verified endpoint listing    |
| [Dashboard Backend](dashboard_backend_api.md) | Dashboard-specific endpoints          |
| [Pipeline API](pipeline-api.md)               | Pipeline execution and monitoring     |
| [Validation API](validation_api.md)           | QA and validation endpoints           |
| [Streaming API](../guides/streaming/api.md)   | Streaming service control             |

---

## Base URLs

| Service       | URL                              | Description         |
| ------------- | -------------------------------- | ------------------- |
| Main API      | `http://localhost:8000/api`      | Core REST endpoints |
| Dashboard API | `http://localhost:8010/api`      | Dashboard backend   |
| Swagger UI    | `http://localhost:8000/api/docs` | Interactive docs    |

---

## Authentication

The API uses IP-based access control. See [security.md](security.md) for
details.

---

## Endpoint Categories

### Core Data

- **Images** - `/api/images/*` - Image artifacts and metadata
- **Sources** - `/api/sources/*` - Source catalogs
- **MS** - `/api/ms/*` - Measurement sets
- **Data** - `/api/data/*` - Generic data access

### Pipeline Operations

- **Jobs** - `/api/jobs/*` - Pipeline job management
- **Batch** - `/api/batch/*` - Batch processing
- **Pipeline** - `/api/pipeline/*` - Workflow status

### Streaming

- **Streaming** - `/api/streaming/*` - Converter service control
- **Queue** - `/api/queue/*` - Processing queue

### Quality Assurance

- **QA** - `/api/qa/*` - Quality metrics
- **Validation** - `/api/qa/images/*/catalog-validation` - Validation
- **Alerts** - `/api/alerts/*` - Quality alerts

### Monitoring

- **Health** - `/api/health` - Service health
- **Cache** - `/api/cache/*` - Cache statistics
- **Disk Usage** - `/api/disk-usage/*` - Storage metrics

### Visualization

- **CARTA** - `/api/visualization/carta/*` - CARTA control

---

## API Reference Files

### [api.md](api.md)

Core REST API documentation covering:

- Health check
- Images (list, detail, header, download)
- Sources (list, cross-match)
- Jobs (status, submit)
- Calibration tables

### [api-endpoints.md](api-endpoints.md)

Auto-generated verified endpoint listing organized by category. Use this as the
complete reference for available endpoints.

### [dashboard_backend_api.md](dashboard_backend_api.md)

Dashboard-specific endpoints including:

- WebSocket/SSE real-time updates
- Pipeline status
- Job management

### [pipeline-api.md](pipeline-api.md)

Pipeline execution and monitoring:

- Workflow status
- Stage metrics
- Active executions
- Performance summary

### [validation_api.md](validation_api.md)

Quality assurance and validation:

- Catalog validation (astrometry, flux, completeness)
- Photometry validation
- Variability detection
- Database consistency checks

### [Streaming API](../guides/streaming/api.md)

Streaming service control (located in streaming guide):

- Service status and health
- Start/stop/restart
- Configuration
- Queue metrics

---

## Related Documentation

- [CLI Reference](cli.md) - Command-line interface
- [Database Schema](database_schema.md) - Database structure
- [Security](security.md) - Access control
