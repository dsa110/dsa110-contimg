# Port Usage and Assignment Audit Report

**Date:** 2025-01-27  
**Project:** DSA-110 Continuum Imaging Pipeline  
**Audit Scope:** All port assignments across the pipeline infrastructure

---

## Executive Summary

This audit identifies all port assignments across the DSA-110 pipeline,
including:

- Primary services (API, frontend, dashboard)
- Development servers
- Docker containers
- Documentation servers
- External dependencies (Redis, databases)
- Browser MCP services
- Monitoring and observability tools

**Key Findings:**

- 15+ distinct ports identified
- Some port conflicts documented
- Multiple configuration sources need consolidation
- Port ranges reserved for dynamic allocation

---

## Port Assignments by Service

### Primary Application Services

#### Port 8000: Backend API (FastAPI)

- **Service:** DSA-110 API Server
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `ops/systemd/contimg.env`: `CONTIMG_API_PORT=8000`
  - `docker-compose.yml`: `"8000:8000"`
  - `scripts/manage-services.sh`: `API_PORT="${CONTIMG_API_PORT:-8000}"`
  - `src/dsa110_contimg/api/__init__.py`: uvicorn command `--port 8000`
- **Status:** Primary port for API
- **CORS Origins:** Configured in `src/dsa110_contimg/api/routes.py` (lines
  284-301)
- **Health Check:** `http://localhost:8000/api/status`
- **Notes:**
  - Default port, configurable via `CONTIMG_API_PORT` environment variable
  - Used in both Docker and native deployments

#### Port 8010: Alternative API Port

- **Service:** Alternative backend API (fallback)
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `README.md`: Mentioned as alternative port
  - `docs/operations/port-management.md`: Listed as reserved
- **Status:** Reserved but not actively used
- **Notes:** Documented as alternative if port 8000 is unavailable

#### Port 5173: Frontend Development Server (Vite)

- **Service:** React/Vite development server
- **Protocol:** HTTP/HTTPS, WebSocket (for HMR)
- **Configuration Sources:**
  - `frontend/vite.config.ts`: `server.port: 5173`
  - `docker-compose.yml`: `"5174:5173"` (host:container mapping for dev
    container)
  - `scripts/manage-services.sh`: Not explicitly configured (uses Vite default)
- **Status:** Primary development port
- **API Proxy:** Proxies `/api/*` to `http://127.0.0.1:8000`
- **WebSocket:** Enabled for Hot Module Replacement (HMR)
- **Notes:**
  - Default Vite port
  - Multiple instances detected in environment analysis (potential conflict)
  - Docker dev container maps to host port 5174 to avoid conflicts

#### Port 5174: Frontend Dev Container (Host Mapping)

- **Service:** Docker containerized frontend dev server
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `docker-compose.yml`: `"5174:5173"` (host:container)
- **Status:** Docker-specific port mapping
- **Notes:** Used to avoid conflict with local dev server on 5173

#### Port 3000: Production Dashboard (Static Serve)

- **Service:** Production React dashboard (served via `serve`)
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `docker-compose.yml`: `"3000:3000"` (dashboard service)
  - `docs/operations/port-management.md`: Listed as reserved
  - `scripts/manage-services.sh`: Not used (uses 3210 range instead)
- **Status:** Used in Docker Compose for production dashboard
- **Notes:**
  - Currently in use by Grafana (Docker container `docker-grafana-1`) -
    **CONFLICT**
  - Not related to DSA-110 dashboard per environment analysis
  - Production dashboard uses `serve -s /app/build -l 3000`

#### Port 3210: Dashboard Service (Script-Managed)

- **Service:** Dashboard served via `manage-services.sh`
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `scripts/manage-services.sh`:
    `DASHBOARD_PORT="${CONTIMG_DASHBOARD_PORT:-3210}"`
  - `scripts/manage-services.sh`: Fallback range `3210-3220` (lines 47-55)
- **Status:** Default for script-managed dashboard
- **Notes:**
  - Script automatically finds free port in range 3210-3220 if 3210 is occupied
  - Used when running dashboard via `manage-services.sh` script

### Documentation and Development Tools

#### Port 8001: MkDocs Documentation Server

- **Service:** MkDocs development server
- **Protocol:** HTTP/HTTPS
- **Configuration Sources:**
  - `mkdocs.yml`: `dev_addr: 127.0.0.1:8001`
  - `scripts/manage-services.sh`: `DOCS_PORT="${CONTIMG_DOCS_PORT:-8001}"`
- **Status:** Active documentation server port
- **Notes:** Used for local documentation development and preview

### Docker and Container Services

#### Port 8080: Pipeline Service (Docker)

- **Service:** DSA-110 Pipeline (Docker container)
- **Protocol:** HTTP/HTTPS (assumed)
- **Configuration Sources:**
  - Environment analysis report: Docker container `dsa110-pipeline`
- **Status:** In use
- **Notes:** Related to pipeline, not dashboard API

### Browser MCP and Development Tools

#### Port 3111: Browser MCP HTTP Server

- **Service:** Browser MCP server (HTTP endpoint)
- **Protocol:** HTTP (JSON-RPC)
- **Configuration Sources:**
  - `docs/concepts/browser_mcp_chrome_remote_desktop_architecture.md`: Port 3111
  - `.cursor/mcp.json`: Configurable in MCP configuration
- **Status:** Used for Cursor IDE integration
- **Notes:**
  - Receives MCP protocol requests from Cursor
  - Streamable HTTP transport
  - Process:
    `/opt/miniforge/envs/casa6/bin/node dist/index.js --http --port 3111`

#### Port 9009: Browser MCP WebSocket Server

- **Service:** Browser MCP WebSocket server
- **Protocol:** WebSocket
- **Configuration Sources:**
  - `docs/concepts/browser_mcp_chrome_remote_desktop_architecture.md`: Port 9009
    (hardcoded)
  - Browser MCP extension: Hardcoded in extension background script
- **Status:** Critical - must be port 9009
- **Notes:**
  - **CRITICAL:** Port 9009 is hardcoded in Browser MCP extension
  - Server MUST listen on 9009, not configurable
  - Used for browser extension connection
  - Connection: `ws://localhost:9009`

#### Port 9222: Chrome Remote Debugging

- **Service:** Chrome DevTools Protocol
- **Protocol:** HTTP/WebSocket
- **Configuration Sources:**
  - `scripts/test_with_chrome.sh`: `--remote-debugging-port=9222`
- **Status:** Used for browser automation testing
- **Notes:** Chrome DevTools Protocol for remote debugging

### Optional/External Services

#### Port 6379: Redis (Optional)

- **Service:** Redis cache backend
- **Protocol:** Redis protocol
- **Configuration Sources:**
  - `src/dsa110_contimg/pipeline/caching.py`: Default `port: int = 6379`
  - Environment variable: `REDIS_PORT=6379` (default)
  - `docs/dev/implementation_summary.md`: `export REDIS_PORT=6379`
- **Status:** Optional dependency
- **Notes:**
  - Only used if Redis backend is enabled
  - Default Redis port
  - Configurable via `REDIS_HOST` and `REDIS_PORT` environment variables

### Reserved/Unused Ports

#### Port 8111

- **Status:** Available (not configured)
- **Notes:** Mentioned in environment analysis as available

#### Port 9090

- **Status:** Available (not configured)
- **Notes:** Mentioned in environment analysis as available

---

## Port Ranges

### Dynamic Port Allocation Ranges

#### Dashboard Port Range: 3210-3220

- **Purpose:** Fallback ports for dashboard service
- **Configuration:** `scripts/manage-services.sh` (line 47)
- **Usage:** Automatically finds first free port in this range if default 3210
  is occupied
- **Candidates:** `3210 3211 3212 3213 3214 3215 3216 3217 3218 3219 3220`

#### CORS Allowed Origins (Multiple Ports)

- **Configuration:** `src/dsa110_contimg/api/routes.py` (lines 284-301)
- **Ports Allowed:**
  - `5173` (frontend dev)
  - `5174` (docker dev)
  - `3000`, `3001`, `3002`, `3210` (various dashboard configs)
- **Notes:** Regex pattern also allows any port on localhost/127.0.0.1/lxd110h17

---

## Configuration Sources Summary

### Environment Variables

- `CONTIMG_API_PORT` → Port 8000 (default)
- `CONTIMG_DASHBOARD_PORT` → Port 3210 (default)
- `CONTIMG_DOCS_PORT` → Port 8001 (default)
- `REDIS_HOST` → localhost (default)
- `REDIS_PORT` → 6379 (default)

### Configuration Files

1. **`ops/systemd/contimg.env`**: API port (8000)
2. **`frontend/vite.config.ts`**: Frontend dev port (5173)
3. **`docker-compose.yml`**: Container port mappings
4. **`mkdocs.yml`**: Docs server port (8001)
5. **`scripts/manage-services.sh`**: Service management ports
6. **`src/dsa110_contimg/api/routes.py`**: CORS allowed origins

---

## Port Conflicts and Issues

### Identified Conflicts

1. **Port 3000: Grafana vs Dashboard**
   - **Issue:** Port 3000 is used by Grafana (Docker container)
   - **Impact:** Production dashboard in Docker Compose may conflict
   - **Resolution:**
     - Docker Compose dashboard service uses 3000
     - Script-managed dashboard uses 3210 range
     - Grafana is external service (not part of DSA-110)

2. **Port 5173: Multiple Vite Instances**
   - **Issue:** Multiple Vite processes detected on port 5173
   - **Impact:** Potential resource waste, unclear which instance is active
   - **Resolution:**
     - Docker dev container uses port 5174 on host
     - Should consolidate local dev instances

### Potential Issues

1. **Port Documentation Inconsistency**
   - `docs/operations/port-management.md` lists port 3000 as reserved for
     dashboard
   - Actual usage shows Grafana on 3000, dashboard uses 3210 range
   - Documentation needs update

2. **Hardcoded Ports in Code**
   - Browser MCP WebSocket port 9009 is hardcoded in extension
   - Some test scripts hardcode ports (e.g., `localhost:8000`, `localhost:5173`)
   - Consider making more ports configurable

3. **CORS Configuration Complexity**
   - Multiple hardcoded origins in `routes.py`
   - Regex pattern provides flexibility but may be too permissive
   - Consider environment-based CORS configuration

---

## Recommendations

### Immediate Actions

1. **Update Port Documentation**
   - Update `docs/operations/port-management.md` to reflect actual usage
   - Document Grafana conflict on port 3000
   - Clarify port 3210 range usage

2. **Consolidate Frontend Instances**
   - Investigate why multiple Vite instances are running
   - Ensure only one dev server instance per environment

3. **Standardize Port Configuration**
   - Create single source of truth for port assignments
   - Consider `config/ports.yaml` or similar centralized config

### Long-Term Improvements

1. **Environment-Based Port Configuration**
   - Use environment variables consistently across all services
   - Provide `.env.example` with all port assignments
   - Document port requirements in README

2. **Port Conflict Detection**
   - Add port conflict checks to startup scripts
   - Provide clear error messages when ports are in use
   - Auto-fallback to alternative ports where appropriate

3. **Service Discovery**
   - Consider service discovery for dynamic port allocation
   - Use consistent naming for service endpoints
   - Document service dependencies

4. **Monitoring and Observability**
   - Add port usage monitoring
   - Track port conflicts in logs
   - Alert on unexpected port usage

---

## Port Assignment Matrix

| Port | Service               | Protocol  | Configurable   | Status    | Notes                        |
| ---- | --------------------- | --------- | -------------- | --------- | ---------------------------- |
| 8000 | Backend API           | HTTP      | Yes (env)      | Active    | Primary API port             |
| 8010 | Alternative API       | HTTP      | Yes            | Reserved  | Fallback port                |
| 5173 | Frontend Dev          | HTTP/WS   | No (hardcoded) | Active    | Vite default                 |
| 5174 | Frontend Dev (Docker) | HTTP/WS   | No             | Active    | Host mapping                 |
| 3000 | Dashboard (Docker)    | HTTP      | No             | Conflict  | Used by Grafana              |
| 3210 | Dashboard (Script)    | HTTP      | Yes (env)      | Active    | Default, auto-fallback range |
| 8001 | MkDocs                | HTTP      | Yes (env)      | Active    | Documentation server         |
| 8080 | Pipeline (Docker)     | HTTP      | Unknown        | Active    | External service             |
| 3111 | Browser MCP HTTP      | HTTP      | Yes            | Active    | MCP server                   |
| 9009 | Browser MCP WS        | WebSocket | No (hardcoded) | Active    | Extension requirement        |
| 9222 | Chrome Debugging      | HTTP/WS   | Yes            | Optional  | Testing only                 |
| 6379 | Redis                 | Redis     | Yes (env)      | Optional  | Cache backend                |
| 8111 | Unused                | -         | -              | Available | Not configured               |
| 9090 | Unused                | -         | -              | Available | Not configured               |

---

## Testing and Validation

### Port Availability Checks

```bash
# Check all DSA-110 ports
for port in 8000 8010 5173 5174 3000 3210 8001 3111 9009 6379; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Port $port: IN USE"
        lsof -i :$port
    else
        echo "Port $port: FREE"
    fi
done
```

### Service Health Checks

```bash
# API
curl http://localhost:8000/api/status

# Frontend Dev
curl http://localhost:5173

# Dashboard
curl http://localhost:3210

# Docs
curl http://localhost:8001

# Browser MCP
curl http://localhost:3111/mcp
```

---

## Related Documentation

- `docs/operations/port-management.md` - Port management guide
- `docs/development/ENVIRONMENT_ANALYSIS_REPORT.md` - Environment analysis
- `docs/concepts/browser_mcp_chrome_remote_desktop_architecture.md` - MCP
  architecture
- `scripts/manage-services.sh` - Service management script

---

**Report Generated:** 2025-01-27  
**Next Review:** When port assignments change or conflicts are reported
