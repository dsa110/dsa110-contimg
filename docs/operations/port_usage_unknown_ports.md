# Unknown Port Usage Analysis

**Date:** 2025-01-27  
**Ports Identified:** 5176, 33307, 37982

---

## Port Analysis

### Port 5176: Vite Dev Server (Duplicate Instance)

**Status:** ⚠️ **Duplicate Frontend Dev Server**  
**Process:** `node /data/dsa110-contimg/frontend/node_modules/.bin/vite (1772875)`  
**Origin:**
Auto Forwarded  
**Issue:** Multiple Vite instances running

**Analysis:**

- Port 5173 is the primary frontend dev server (standard Vite port)
- Port 5176 is a duplicate/secondary Vite instance
- Likely started accidentally or from a different terminal/session

**Recommendation:**

1. **Kill duplicate instance:**

   ```bash
   kill 1772875
   # Or find and kill all Vite processes
   pkill -f "vite.*5176"
   ```

2. **Prevent duplicates:**
   - Check for existing Vite process before starting
   - Use port manager to detect conflicts
   - Add to startup validation

3. **Document in port system:**
   - Add as "frontend_dev_alt" with range 5174-5179
   - Mark as "avoid duplicates" in config

---

### Port 33307: VS Code Extension Host

**Status:** ℹ️ **VS Code Extension Port**  
**Process:** `Code Extension Host (1165206)`  
**Origin:** User Forwarded  
**Purpose:** VS Code remote development/port forwarding

**Analysis:**

- VS Code automatically forwards ports for remote development
- This is a dynamic port assigned by VS Code
- Not part of DSA-110 pipeline configuration
- Safe to ignore in port management

**Recommendation:**

- **No action needed** - This is VS Code infrastructure
- Add to "excluded ports" in validation scripts
- Document as "external tool" in port audit

---

### Port 37982: VS Code Extension Host

**Status:** ℹ️ **VS Code Extension Port**  
**Process:** `Code Extension Host (1165206)`  
**Origin:** User Forwarded  
**Purpose:** VS Code remote development/port forwarding

**Analysis:**

- Same as port 33307 - VS Code extension host
- Dynamic port assigned by VS Code
- Not part of DSA-110 pipeline
- Safe to ignore

**Recommendation:**

- **No action needed** - This is VS Code infrastructure
- Add to "excluded ports" in validation scripts
- Document as "external tool" in port audit

---

## Summary

| Port      | Service        | Action Required                | Priority |
| --------- | -------------- | ------------------------------ | -------- |
| **5176**  | Duplicate Vite | Kill duplicate, prevent future | High     |
| **33307** | VS Code        | None (external tool)           | None     |
| **37982** | VS Code        | None (external tool)           | None     |

---

## Immediate Actions

### 1. Kill Duplicate Vite Instance

```bash
# Find all Vite processes
ps aux | grep vite

# Kill specific process
kill 1772875

# Or kill all Vite processes on non-standard ports
pkill -f "vite.*517[4-9]"
```

### 2. Update Port Configuration

Add to `config/ports.yaml`:

```yaml
ports:
  # ... existing ports ...

  frontend_dev_alt:
    default: 5174
    env_var: CONTIMG_FRONTEND_DEV_ALT_PORT
    description: "Alternative frontend dev server (avoid duplicates)"
    range: [5174, 5179]
    optional: true
    conflict_check: true
```

### 3. Update Validation Scripts

Add VS Code ports to exclusion list in `scripts/validate-port-config.py`:

```python
# External tools (not managed by port system)
EXTERNAL_TOOL_PORTS = {
    33307,  # VS Code Extension Host
    37982,  # VS Code Extension Host
    # Add other VS Code dynamic ports as needed
}
```

### 4. Add Duplicate Detection

Update `scripts/check-ports.sh` to detect duplicate Vite instances:

```bash
# Check for duplicate Vite instances
vite_count=$(ps aux | grep -c "vite.*517[0-9]")
if [ "$vite_count" -gt 1 ]; then
    echo "⚠️  Warning: Multiple Vite instances detected"
    ps aux | grep "vite.*517[0-9]"
fi
```

---

## Prevention Strategies

### 1. Port Conflict Detection

Enhance port manager to detect duplicate services:

```python
def detect_duplicate_services(self) -> Dict[str, List[int]]:
    """Detect duplicate service instances."""
    duplicates = {}
    # Check for multiple Vite instances
    # Check for multiple API instances
    return duplicates
```

### 2. Startup Validation

Add to `scripts/manage-services.sh`:

```bash
# Before starting frontend, check for existing instances
if pgrep -f "vite.*5173" > /dev/null; then
    echo "Warning: Vite instance already running on 5173"
    read -p "Kill existing instance? (y/n) " -n 1 -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pkill -f "vite.*5173"
    fi
fi
```

### 3. Process Management

Create `scripts/cleanup-duplicate-services.sh`:

```bash
#!/bin/bash
# Clean up duplicate service instances

# Find duplicate Vite instances
vite_pids=$(pgrep -f "vite.*517[0-9]" | sort -u)
vite_count=$(echo "$vite_pids" | wc -l)

if [ "$vite_count" -gt 1 ]; then
    echo "Found $vite_count Vite instances, keeping oldest, killing others"
    # Keep first PID, kill rest
    # Implementation...
fi
```

---

## Updated Port Organization

### Port Ranges (Updated)

- **8000-8099**: Core Application Services
- **5000-5199**: Development Servers
  - **5173**: Primary frontend dev (Vite)
  - **5174-5179**: Alternative/fallback frontend dev (avoid duplicates)
- **3200-3299**: Dashboard Services
- **9000-9099**: External Integrations
- **6000-6099**: Optional Services
- **30000-39999**: External Tools (VS Code, etc.) - Excluded from validation

---

## Documentation Updates Needed

1. **Port Audit Report** - Add VS Code ports as external tools
2. **Port Quick Reference** - Note duplicate detection
3. **Development Guide** - Warn about duplicate Vite instances
4. **Troubleshooting Guide** - Add section on duplicate services

---

## Next Steps

1. ✅ Kill duplicate Vite instance (port 5176)
2. ✅ Update port configuration to include frontend_dev_alt
3. ✅ Add VS Code ports to exclusion list
4. ✅ Add duplicate detection to validation scripts
5. ✅ Update documentation

---

**See Also:**

- `docs/operations/port_audit_report.md` - Full port audit
- `docs/operations/port_organization_recommendations.md` - Port system docs
