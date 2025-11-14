# Port Organization System - Enforcement

**Status:** ✅ **ENFORCED**  
**Date:** 2025-01-27

---

## Enforcement Status

The port organization system is now **enforced** across the pipeline. All new
code must use the centralized port configuration system.

---

## What's Enforced

### 1. Centralized Configuration

- **Required:** `config/ports.yaml` must exist
- **Location:** `/data/dsa110-contimg/config/ports.yaml`
- **Fallback:** Default configuration if file missing (backward compatible)

### 2. Port Manager Module

- **Module:** `src/dsa110_contimg/config/ports.py`
- **Usage:** All new code should use `PortManager` or `get_port()` function
- **Backward Compatible:** Environment variables still work

### 3. Validation Scripts

- **`scripts/check-ports.sh`** - Check port availability and conflicts
- **`scripts/validate-port-config.py`** - Validate configuration and detect
  hardcoded ports

### 4. Service Management

- **`scripts/manage-services.sh`** - Updated to use port manager when available
- **Fallback:** Still uses environment variables if port manager unavailable

---

## How to Use

### Getting a Port in Python

```python
from dsa110_contimg.config.ports import get_port

# Get API port (respects CONTIMG_API_PORT env var)
api_port = get_port('api')

# Get port with conflict checking
dashboard_port = get_port('dashboard', check_conflict=True)
```

### Getting a Port in Shell Scripts

```bash
# Option 1: Use environment variable (still works)
export CONTIMG_API_PORT=8000

# Option 2: Use port manager (if available)
API_PORT=$(python3 -c "from dsa110_contimg.config.ports import get_port; print(get_port('api'))")
```

### Checking Ports

```bash
# Check all ports
./scripts/check-ports.sh

# Validate configuration
./scripts/validate-port-config.py
```

---

## Validation

### Pre-Commit Hook (Optional)

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
./.pre-commit-port-check.sh
```

Or use in CI:

```yaml
# .gitlab-ci.yml or similar
validate_ports:
  script:
    - ./scripts/validate-port-config.py
```

### Manual Validation

```bash
# Check port configuration
./scripts/check-ports.sh

# Validate no hardcoded ports
./scripts/validate-port-config.py
```

---

## Allowed Exceptions

These ports are **allowed** to be hardcoded (they're in the exception list):

- **9009** - Browser MCP WebSocket (hardcoded in extension)
- **6379** - Redis standard port
- **9222** - Chrome DevTools Protocol

All other ports should use the port manager or environment variables.

---

## Migration Status

### ✅ Completed

- [x] Port configuration file created (`config/ports.yaml`)
- [x] Port manager module implemented (`src/dsa110_contimg/config/ports.py`)
- [x] Service management script updated
- [x] Validation scripts created
- [x] Environment file updated with all port variables
- [x] Documentation created

### 🔄 In Progress

- [ ] Update all hardcoded ports in codebase (gradual migration)
- [ ] Add pre-commit hook to repository
- [ ] Update CI/CD to validate ports

### 📋 Future

- [ ] Remove all hardcoded ports
- [ ] Add port conflict detection to startup
- [ ] Port usage monitoring

---

## Enforcement Rules

1. **New Code:** Must use `PortManager` or environment variables
2. **Existing Code:** Gradually migrate to port manager
3. **Configuration:** `config/ports.yaml` is the source of truth
4. **Validation:** Run `validate-port-config.py` before committing
5. **Documentation:** Update port docs when adding new services

---

## Troubleshooting

### Port Manager Not Found

```bash
# Check if module exists
ls src/dsa110_contimg/config/ports.py

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### Configuration File Missing

```bash
# Create from example
cp config/ports.yaml.example config/ports.yaml
```

### Port Conflicts

```bash
# Check what's using a port
lsof -i :8000

# Use alternative port
export CONTIMG_API_PORT=8001
```

---

## Related Documents

- `docs/operations/port_organization_recommendations.md` - Full recommendations
- `docs/operations/port_audit_report.md` - Port audit
- `docs/operations/PORT_ASSIGNMENTS_QUICK_REFERENCE.md` - Quick reference
- `config/ports.yaml.example` - Example configuration

---

**Last Updated:** 2025-01-27
