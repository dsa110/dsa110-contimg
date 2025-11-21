# CARTA Port Allocation

## Port Assignment

CARTA integration follows the DSA-110 port allocation strategy as documented in
`docs/operations/port_organization_recommendations.md`.

### Assigned Ports

| Port     | Service        | Range                             | Rationale                                      |
| -------- | -------------- | --------------------------------- | ---------------------------------------------- |
| **9002** | CARTA Backend  | 9000-9099 (External Integrations) | WebSocket endpoint for CARTA backend           |
| **9003** | CARTA Frontend | 9000-9099 (External Integrations) | HTTP endpoint for CARTA frontend (iframe mode) |

### Port Allocation Strategy Compliance

**Range:** 9000-9099 - External Integrations

- CARTA is an external tool integration
- Fits within the designated range for external services
- Avoids conflicts with core application services (8000-8099)
- Avoids conflicts with development servers (5000-5199)
- Avoids conflicts with dashboard services (3200-3299)

### Previous Port Issues (Resolved)

**Port 3000:**

- **Issue:** Conflict with Grafana (Docker container `docker-grafana-1`)
- **Resolution:** Moved CARTA frontend to port 9003

**Port 3002:**

- **Issue:** In 3000-3099 range (Frontend Services), but CARTA is external
  integration
- **Resolution:** Moved CARTA backend to port 9002 (External Integrations range)

### Configuration

Environment variables:

```bash
# CARTA Backend (WebSocket)
VITE_CARTA_BACKEND_URL=http://localhost:9002

# CARTA Frontend (HTTP, for iframe mode)
VITE_CARTA_FRONTEND_URL=http://localhost:9003
```

### Docker Deployment

When deploying CARTA backend via Docker, map container port to host port:

```bash
# CARTA backend container uses internal port 3002
# Map to host port 9002 (per allocation strategy)
docker run -d \
  --name carta-backend \
  -p 9002:3002 \
  -v /stage/dsa110-contimg:/data:ro \
  cartavis/carta-backend:latest
```

### References

- Port Allocation Strategy:
  `docs/operations/port_organization_recommendations.md`
- Port Audit Report: `docs/operations/port_audit_report.md`
- CARTA Integration Guide: `docs/how-to/carta_integration_guide.md`
