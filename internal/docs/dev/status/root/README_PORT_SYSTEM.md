# Port Organization System

**Status:** ✅ **ENFORCED**

The DSA-110 pipeline uses a centralized port organization system to manage all
port assignments.

## Quick Start

### Check Ports

```bash
./scripts/check-ports.sh
```

### Get a Port in Python

```python
from dsa110_contimg.config.ports import get_port

api_port = get_port('api')  # Respects CONTIMG_API_PORT env var
```

### Get a Port in Shell

```bash
# Use environment variable (recommended)
export CONTIMG_API_PORT=8000

# Or use port manager
API_PORT=$(python3 -c "from dsa110_contimg.config.ports import get_port; print(get_port('api'))")
```

## Port Ranges

- **8000-8099**: Core Application Services
- **5000-5199**: Development Servers
- **3200-3299**: Dashboard Services
- **9000-9099**: External Integrations
- **6000-6099**: Optional Services

## Configuration

- **Config File:** `config/ports.yaml`
- **Port Manager:** `src/dsa110_contimg/config/ports.py`
- **Environment:** `ops/systemd/contimg.env`

## Documentation

See `docs/operations/` for complete documentation:

- `port_organization_recommendations.md` - Full recommendations
- `PORT_SYSTEM_ENFORCEMENT.md` - Enforcement details
- `PORT_ASSIGNMENTS_QUICK_REFERENCE.md` - Quick reference
