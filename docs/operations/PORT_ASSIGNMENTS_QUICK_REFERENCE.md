# Port Assignments Quick Reference

**Last Updated:** 2025-01-27

## Primary Services

| Port     | Service             | Default | Configurable             |
| -------- | ------------------- | ------- | ------------------------ |
| **8000** | Backend API         | ✓       | `CONTIMG_API_PORT`       |
| **5173** | Frontend Dev (Vite) | ✓       | No (hardcoded)           |
| **3210** | Dashboard (Script)  | ✓       | `CONTIMG_DASHBOARD_PORT` |
| **8001** | MkDocs Docs         | ✓       | `CONTIMG_DOCS_PORT`      |

## Docker Services

| Port     | Service               | Notes                  |
| -------- | --------------------- | ---------------------- |
| **3000** | Dashboard (Docker)    | Conflicts with Grafana |
| **5174** | Frontend Dev (Docker) | Host mapping for 5173  |

## Development Tools

| Port     | Service          | Notes                  |
| -------- | ---------------- | ---------------------- |
| **3111** | Browser MCP HTTP | MCP server             |
| **9009** | Browser MCP WS   | Hardcoded in extension |
| **9222** | Chrome Debugging | Testing only           |

## Optional Services

| Port     | Service | Configurable |
| -------- | ------- | ------------ |
| **6379** | Redis   | `REDIS_PORT` |

## Reserved Ranges

- **3210-3220**: Dashboard fallback ports (auto-selected if 3210 busy)

## Common Commands

```bash
# Check port usage
lsof -i :8000

# Start services
./scripts/manage-services.sh start all

# Check status
./scripts/manage-services.sh status
```

## Full Documentation

See `docs/operations/port_audit_report.md` for complete audit details.
