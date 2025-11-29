# DSA-110 Backend Documentation

This directory contains documentation for the DSA-110 Continuum Imaging Pipeline
backend.

## Contents

| Document                   | Description                           |
| -------------------------- | ------------------------------------- |
| [api.md](api.md)           | REST API endpoint reference           |
| [security.md](security.md) | IP-based access control configuration |

## Quick Links

- **API Docs (Interactive):** http://localhost:8000/api/docs
- **OpenAPI Spec:** http://localhost:8000/api/openapi.json
- **Health Check:** http://localhost:8000/api/health

## Getting Started

```bash
# Start the API
cd /data/dsa110-contimg/backend
python -m uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000

# Run tests
bash test_api_endpoints.sh
```
