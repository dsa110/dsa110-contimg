# Port Organization System Recommendations

**Date:** 2025-01-27  
**Based on:** Port Audit Report (`port_audit_report.md`)

---

## Executive Summary

This document proposes an improved port organization system to address:

- Port conflicts and inconsistencies
- Hardcoded ports scattered across codebase
- Lack of centralized configuration
- Documentation gaps
- Multiple service instances

**Key Principles:**

1. **Centralized Configuration** - Single source of truth
2. **Port Ranges by Service Type** - Logical grouping
3. **Environment-Based** - Easy per-environment configuration
4. **Conflict Detection** - Automatic port conflict resolution
5. **Documentation** - Self-documenting configuration

---

## Proposed Port Allocation Strategy

### Port Range Allocation

```
┌─────────────────────────────────────────────────────────────┐
│ Port Ranges by Service Type                                │
├─────────────────────────────────────────────────────────────┤
│ 8000-8099  │ Core Application Services                      │
│ 8100-8199  │ Alternative/Backup Services                  │
│ 8200-8299  │ Development Tools                              │
│ 9000-9099  │ External Integrations (MCP, Browser)          │
│ 3000-3099  │ Frontend Services (Legacy/Production)        │
│ 5000-5199  │ Development Servers (Vite, etc.)             │
│ 6000-6099  │ Optional Services (Redis, etc.)              │
│ 3200-3299  │ Dashboard Services (Script-managed)         │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Port Assignments

#### Core Application Services (8000-8099)

| Port     | Service     | Purpose                         | Configurable              |
| -------- | ----------- | ------------------------------- | ------------------------- |
| **8000** | Backend API | Primary FastAPI server          | `CONTIMG_API_PORT`        |
| **8001** | MkDocs      | Documentation server            | `CONTIMG_DOCS_PORT`       |
| **8002** | API Metrics | Prometheus metrics endpoint     | `CONTIMG_METRICS_PORT`    |
| **8003** | API Health  | Dedicated health check endpoint | `CONTIMG_HEALTH_PORT`     |
| **8010** | API Backup  | Alternative API port            | `CONTIMG_API_BACKUP_PORT` |

**Rationale:**

- Keep core services in 8000 range for easy identification
- Reserve 8002-8009 for future monitoring/observability
- 8010+ for alternative/backup instances

#### Development Servers (5000-5199)

| Port     | Service               | Purpose                  | Configurable                    |
| -------- | --------------------- | ------------------------ | ------------------------------- |
| **5173** | Frontend Dev (Vite)   | Primary dev server       | `CONTIMG_FRONTEND_DEV_PORT`     |
| **5174** | Frontend Dev (Docker) | Docker dev container     | Auto (host mapping)             |
| **5100** | Frontend Dev (Alt)    | Alternative dev instance | `CONTIMG_FRONTEND_DEV_ALT_PORT` |

**Rationale:**

- Vite default (5173) is well-known, keep it
- Reserve 5100-5199 for development servers
- Clear separation from production ports

#### Dashboard Services (3200-3299)

| Port          | Service            | Purpose                     | Configurable                    |
| ------------- | ------------------ | --------------------------- | ------------------------------- |
| **3210**      | Dashboard (Script) | Script-managed dashboard    | `CONTIMG_DASHBOARD_PORT`        |
| **3211-3220** | Dashboard Fallback | Auto-selected if 3210 busy  | Auto                            |
| **3000**      | Dashboard (Docker) | Production Docker dashboard | `CONTIMG_DASHBOARD_DOCKER_PORT` |

**Rationale:**

- Keep 3210 range for script-managed services
- Reserve 3000 for Docker production (resolve Grafana conflict)
- Clear fallback range

#### External Integrations (9000-9099)

| Port     | Service          | Purpose               | Configurable                |
| -------- | ---------------- | --------------------- | --------------------------- |
| **9009** | Browser MCP WS   | WebSocket (hardcoded) | No (extension requirement)  |
| **3111** | Browser MCP HTTP | HTTP endpoint         | `CONTIMG_MCP_HTTP_PORT`     |
| **9222** | Chrome Debugging | DevTools Protocol     | `CONTIMG_CHROME_DEBUG_PORT` |

**Rationale:**

- Keep 9009 for MCP (hardcoded requirement)
- Move 3111 to 9000 range for consistency
- Group all browser/dev tools together

#### Optional Services (6000-6099)

| Port     | Service   | Purpose                    | Configurable            |
| -------- | --------- | -------------------------- | ----------------------- |
| **6379** | Redis     | Cache backend              | `REDIS_PORT` (standard) |
| **6000** | Redis Alt | Alternative Redis instance | `REDIS_ALT_PORT`        |

**Rationale:**

- Keep 6379 (Redis standard)
- Reserve 6000-6099 for optional services

---

## Implementation Plan

### Phase 1: Centralized Configuration

#### 1.1 Create Port Configuration File

**File:** `config/ports.yaml`

```yaml
# DSA-110 Port Configuration
# Single source of truth for all port assignments

ports:
  # Core Application Services (8000-8099)
  api:
    default: 8000
    env_var: CONTIMG_API_PORT
    description: "Backend FastAPI server"
    range: [8000, 8009]

  docs:
    default: 8001
    env_var: CONTIMG_DOCS_PORT
    description: "MkDocs documentation server"
    range: [8001, 8001]

  metrics:
    default: 8002
    env_var: CONTIMG_METRICS_PORT
    description: "Prometheus metrics endpoint"
    range: [8002, 8002]
    optional: true

  # Development Servers (5000-5199)
  frontend_dev:
    default: 5173
    env_var: CONTIMG_FRONTEND_DEV_PORT
    description: "Vite development server"
    range: [5173, 5173]

  # Dashboard Services (3200-3299)
  dashboard:
    default: 3210
    env_var: CONTIMG_DASHBOARD_PORT
    description: "Script-managed dashboard"
    range: [3210, 3220] # Auto-fallback range

  dashboard_docker:
    default: 3000
    env_var: CONTIMG_DASHBOARD_DOCKER_PORT
    description: "Docker production dashboard"
    range: [3000, 3000]
    conflict_check: true # Warn if Grafana detected

  # External Integrations (9000-9099)
  mcp_http:
    default: 3111
    env_var: CONTIMG_MCP_HTTP_PORT
    description: "Browser MCP HTTP server"
    range: [3111, 3111]

  mcp_ws:
    default: 9009
    env_var: null # Hardcoded in extension
    description: "Browser MCP WebSocket (hardcoded)"
    range: [9009, 9009]
    immutable: true

  chrome_debug:
    default: 9222
    env_var: CONTIMG_CHROME_DEBUG_PORT
    description: "Chrome DevTools Protocol"
    range: [9222, 9222]
    optional: true

  # Optional Services (6000-6099)
  redis:
    default: 6379
    env_var: REDIS_PORT
    description: "Redis cache backend"
    range: [6379, 6379]
    optional: true

# Port conflict detection
conflict_detection:
  enabled: true
  check_on_startup: true
  auto_resolve: true # Use fallback ranges
  warn_on_conflict: true

# Reserved ports (external services)
reserved:
  - port: 3000
    service: "Grafana (external)"
    note: "Check before using dashboard_docker"
  - port: 8080
    service: "Pipeline (external Docker)"
    note: "External service, not managed"
```

#### 1.2 Create Port Configuration Module

**File:** `src/dsa110_contimg/config/ports.py`

```python
"""Centralized port configuration management."""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PortConfig:
    """Port configuration for a service."""
    name: str
    default: int
    env_var: Optional[str]
    description: str
    range: Tuple[int, int]
    optional: bool = False
    immutable: bool = False
    conflict_check: bool = False


class PortManager:
    """Manages port assignments and conflict detection."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "ports.yaml"
        self._config = self._load_config()
        self._ports = self._parse_ports()

    def _load_config(self) -> dict:
        """Load port configuration from YAML."""
        if not self.config_path.exists():
            return self._default_config()
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def get_port(self, service: str, check_conflict: bool = True) -> int:
        """Get port for a service, respecting environment variables and conflicts."""
        if service not in self._ports:
            raise ValueError(f"Unknown service: {service}")

        config = self._ports[service]

        # Check environment variable first
        port = config.default
        if config.env_var:
            port = int(os.getenv(config.env_var, config.default))

        # Validate port is in range
        if not (config.range[0] <= port <= config.range[1]):
            raise ValueError(
                f"Port {port} for {service} outside allowed range {config.range}"
            )

        # Check for conflicts if enabled
        if check_conflict and config.conflict_check:
            if self._check_conflict(port, service):
                if config.range[0] != config.range[1]:
                    # Try fallback range
                    port = self._find_free_port_in_range(config.range)
                else:
                    raise RuntimeError(f"Port {port} conflict detected for {service}")

        return port

    def _check_conflict(self, port: int, service: str) -> bool:
        """Check if port is in use."""
        # Implementation using lsof or socket binding
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('', port))
            sock.close()
            return False
        except OSError:
            return True

    def _find_free_port_in_range(self, port_range: Tuple[int, int]) -> int:
        """Find first free port in range."""
        for port in range(port_range[0], port_range[1] + 1):
            if not self._check_conflict(port, "auto"):
                return port
        raise RuntimeError(f"No free ports in range {port_range}")

    def list_ports(self) -> Dict[str, int]:
        """List all configured ports with current values."""
        return {name: self.get_port(name, check_conflict=False)
                for name in self._ports.keys()}

    def validate_all(self) -> Dict[str, bool]:
        """Validate all ports are available."""
        results = {}
        for service in self._ports:
            try:
                port = self.get_port(service, check_conflict=True)
                results[service] = True
            except Exception as e:
                results[service] = False
        return results
```

### Phase 2: Update Configuration Files

#### 2.1 Update Environment File

**File:** `ops/systemd/contimg.env`

```bash
# Port Configuration
# All ports configurable via environment variables
# See config/ports.yaml for port ranges and defaults

CONTIMG_API_PORT=8000
CONTIMG_DOCS_PORT=8001
CONTIMG_DASHBOARD_PORT=3210
CONTIMG_DASHBOARD_DOCKER_PORT=3000
CONTIMG_FRONTEND_DEV_PORT=5173
CONTIMG_MCP_HTTP_PORT=3111
CONTIMG_CHROME_DEBUG_PORT=9222

# Optional Services
REDIS_PORT=6379
```

#### 2.2 Update Service Management Script

**File:** `scripts/manage-services.sh`

```bash
# Load port configuration
source "$PROJECT_DIR/config/ports.sh"  # Generated from ports.yaml

# Or use Python port manager
API_PORT=$(python3 -c "
from dsa110_contimg.config.ports import PortManager
pm = PortManager()
print(pm.get_port('api'))
")
```

#### 2.3 Update Docker Compose

**File:** `docker-compose.yml`

```yaml
services:
  api:
    ports:
      - "${CONTIMG_API_PORT:-8000}:8000"
    environment:
      - CONTIMG_API_PORT=${CONTIMG_API_PORT:-8000}

  dashboard:
    ports:
      - "${CONTIMG_DASHBOARD_DOCKER_PORT:-3000}:3000"
    environment:
      - CONTIMG_DASHBOARD_DOCKER_PORT=${CONTIMG_DASHBOARD_DOCKER_PORT:-3000}
```

### Phase 3: Port Conflict Detection

#### 3.1 Create Port Check Utility

**File:** `scripts/check-ports.sh`

```bash
#!/bin/bash
# Port conflict detection and reporting

source "$(dirname "$0")/../config/ports.sh"

check_all_ports() {
    echo "Checking DSA-110 port assignments..."
    echo ""

    for service in api docs dashboard frontend_dev mcp_http; do
        port=$(get_port "$service")
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo "✓ Port $port ($service): IN USE"
            lsof -i :$port | head -2
        else
            echo "○ Port $port ($service): FREE"
        fi
    done
}

check_conflicts() {
    echo "Checking for port conflicts..."
    # Implementation
}
```

### Phase 4: Documentation Updates

#### 4.1 Update Port Management Docs

- Update `docs/operations/port-management.md` with new system
- Reference `config/ports.yaml` as source of truth
- Document port ranges and allocation strategy

#### 4.2 Create Port Migration Guide

- Guide for migrating from old to new system
- Environment variable mapping
- Docker Compose updates

---

## Benefits of New System

### 1. Centralized Configuration

- **Single source of truth:** `config/ports.yaml`
- **Easy updates:** Change once, applies everywhere
- **Version controlled:** Port changes tracked in git

### 2. Environment Flexibility

- **Per-environment configs:** `.env.development`, `.env.production`
- **Easy overrides:** Environment variables take precedence
- **Docker-friendly:** Works with Docker Compose env files

### 3. Conflict Prevention

- **Automatic detection:** Port conflicts detected at startup
- **Auto-resolution:** Falls back to available ports in range
- **Clear warnings:** Users informed of conflicts

### 4. Better Documentation

- **Self-documenting:** Port purposes in config file
- **Auto-generated docs:** Scripts can generate port tables
- **Clear ranges:** Easy to see what ports are reserved

### 5. Developer Experience

- **Consistent API:** Same way to get ports everywhere
- **Type safety:** Python module provides type hints
- **IDE support:** Autocomplete for port names

---

## Migration Strategy

### Step 1: Create New Configuration (Non-Breaking)

1. Create `config/ports.yaml`
2. Create `src/dsa110_contimg/config/ports.py`
3. Keep existing env vars working (backward compatible)

### Step 2: Update Scripts Gradually

1. Update `manage-services.sh` to use new system
2. Update Docker Compose files
3. Update startup scripts

### Step 3: Update Documentation

1. Update port management docs
2. Create migration guide
3. Update README with new system

### Step 4: Remove Hardcoded Ports

1. Replace hardcoded ports in code
2. Use PortManager everywhere
3. Remove old port constants

---

## Example Usage

### Python Code

```python
from dsa110_contimg.config.ports import PortManager

pm = PortManager()

# Get API port (respects CONTIMG_API_PORT env var)
api_port = pm.get_port('api')

# Get port with conflict checking
dashboard_port = pm.get_port('dashboard', check_conflict=True)

# List all ports
all_ports = pm.list_ports()
```

### Shell Scripts

```bash
# Source generated port config
source config/ports.sh

# Use port variables
uvicorn dsa110_contimg.api:app --port $CONTIMG_API_PORT
```

### Docker Compose

```yaml
services:
  api:
    ports:
      - "${CONTIMG_API_PORT:-8000}:8000"
```

---

## Port Range Rationale

### Why These Ranges?

1. **8000-8099 (Core Services)**
   - Standard HTTP port range
   - Easy to remember
   - Leaves room for expansion

2. **5000-5199 (Development)**
   - Separated from production
   - Vite default (5173) fits naturally
   - Clear dev/prod distinction

3. **3200-3299 (Dashboard)**
   - Already in use
   - Sufficient range for fallbacks
   - Distinct from other services

4. **9000-9099 (External)**
   - High port numbers = less likely conflicts
   - Groups browser/dev tools
   - MCP requirement (9009) fits

5. **6000-6099 (Optional)**
   - Standard Redis port (6379) fits
   - Clear optional service range
   - Easy to disable if not needed

---

## Conflict Resolution Strategy

### Automatic Resolution

1. **Check primary port** (e.g., 8000)
2. **If conflict detected:**
   - Check if service has fallback range
   - Try ports in range sequentially
   - Use first available port
   - Log warning with actual port used

### Manual Resolution

1. **Detect conflict** at startup
2. **Report conflict** with details:
   - What service is using the port
   - PID and process name
   - Suggested actions
3. **Provide options:**
   - Kill conflicting process
   - Use alternative port
   - Change configuration

---

## Future Enhancements

1. **Port Reservation System**
   - Reserve ports for specific services
   - Prevent accidental conflicts
   - System-level port locking

2. **Port Monitoring**
   - Track port usage over time
   - Alert on unexpected changes
   - Port usage analytics

3. **Service Discovery**
   - Automatic service detection
   - Dynamic port allocation
   - Health check integration

4. **Multi-Environment Support**
   - Different ports per environment
   - Environment-specific configs
   - Staging/production separation

---

## Conclusion

This port organization system provides:

- **Clarity:** Clear port allocation strategy
- **Flexibility:** Easy configuration and overrides
- **Reliability:** Conflict detection and resolution
- **Maintainability:** Centralized configuration
- **Documentation:** Self-documenting system

**Next Steps:**

1. Review and approve port ranges
2. Implement Phase 1 (centralized config)
3. Gradually migrate existing code
4. Update documentation

---

**Related Documents:**

- `docs/operations/port_audit_report.md` - Current port audit
- `docs/operations/port-management.md` - Port management guide
- `docs/operations/PORT_ASSIGNMENTS_QUICK_REFERENCE.md` - Quick reference
