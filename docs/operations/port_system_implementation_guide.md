# Port Organization System - Implementation Guide

**Quick Start Guide** for implementing the improved port organization system.

---

## Quick Start (5 Minutes)

### Step 1: Create Port Configuration

```bash
# Copy example configuration
cp config/ports.yaml.example config/ports.yaml

# Edit if needed (usually not necessary)
# vim config/ports.yaml
```

### Step 2: Use in Scripts

**Before:**

```bash
API_PORT="${CONTIMG_API_PORT:-8000}"
```

**After:**

```bash
# Option 1: Use existing env vars (backward compatible)
API_PORT="${CONTIMG_API_PORT:-8000}"

# Option 2: Use port manager (future)
API_PORT=$(python3 -c "from dsa110_contimg.config.ports import PortManager; pm = PortManager(); print(pm.get_port('api'))")
```

### Step 3: Update Docker Compose

```yaml
services:
  api:
    ports:
      - "${CONTIMG_API_PORT:-8000}:8000"
```

---

## Implementation Phases

### Phase 1: Minimal Implementation (Recommended First Step)

**Goal:** Create centralized port configuration without breaking existing code.

1. **Create `config/ports.yaml`** (copy from example)
2. **Update `ops/systemd/contimg.env`** with all port variables
3. **Update documentation** to reference new system

**Time:** 15 minutes  
**Risk:** Low (backward compatible)

### Phase 2: Port Manager Module

**Goal:** Create Python module for programmatic port access.

1. **Create `src/dsa110_contimg/config/ports.py`**
2. **Add to requirements** (if using PyYAML)
3. **Update scripts** to use PortManager

**Time:** 1-2 hours  
**Risk:** Medium (requires testing)

### Phase 3: Conflict Detection

**Goal:** Add automatic port conflict detection.

1. **Enhance PortManager** with conflict checking
2. **Update startup scripts** to check conflicts
3. **Add port validation** to service management

**Time:** 2-3 hours  
**Risk:** Medium (requires careful testing)

### Phase 4: Full Migration

**Goal:** Remove all hardcoded ports.

1. **Find all hardcoded ports** (grep for port numbers)
2. **Replace with PortManager** calls
3. **Update tests** to use new system

**Time:** 4-6 hours  
**Risk:** High (requires comprehensive testing)

---

## Recommended Approach

**Start with Phase 1** - it provides immediate benefits with minimal risk:

1. ✅ Centralized documentation
2. ✅ Clear port assignments
3. ✅ Environment variable consistency
4. ✅ No code changes required

**Then gradually implement Phases 2-4** as needed.

---

## Port Range Quick Reference

```
8000-8099  → Core Application Services
5000-5199  → Development Servers
3200-3299  → Dashboard Services
9000-9099  → External Integrations
6000-6099  → Optional Services
```

---

## Common Tasks

### Check Port Availability

```bash
# Manual check
lsof -i :8000

# Using port manager (after Phase 2)
python3 -c "from dsa110_contimg.config.ports import PortManager; pm = PortManager(); print('Available' if not pm._check_conflict(8000, 'test') else 'In Use')"
```

### List All Ports

```bash
# After Phase 2
python3 -c "from dsa110_contimg.config.ports import PortManager; import json; pm = PortManager(); print(json.dumps(pm.list_ports(), indent=2))"
```

### Validate Configuration

```bash
# After Phase 2
python3 -c "from dsa110_contimg.config.ports import PortManager; pm = PortManager(); results = pm.validate_all(); print('All ports valid' if all(results.values()) else 'Conflicts detected')"
```

---

## Troubleshooting

### Port Conflict Detected

1. **Check what's using the port:**

   ```bash
   lsof -i :8000
   ```

2. **Kill conflicting process (if safe):**

   ```bash
   kill <PID>
   ```

3. **Or use alternative port:**
   ```bash
   export CONTIMG_API_PORT=8001
   ```

### Configuration Not Found

1. **Check file exists:**

   ```bash
   ls config/ports.yaml
   ```

2. **Copy example:**
   ```bash
   cp config/ports.yaml.example config/ports.yaml
   ```

### Environment Variable Not Working

1. **Check variable is set:**

   ```bash
   echo $CONTIMG_API_PORT
   ```

2. **Source environment file:**
   ```bash
   source ops/systemd/contimg.env
   ```

---

## Next Steps

1. Review `docs/operations/port_organization_recommendations.md` for full
   details
2. Start with Phase 1 (minimal implementation)
3. Gradually implement additional phases as needed
4. Update documentation as you go

---

**See Also:**

- `docs/operations/port_audit_report.md` - Current port audit
- `docs/operations/port_organization_recommendations.md` - Full recommendations
- `config/ports.yaml.example` - Example configuration
