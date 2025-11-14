# Automatic and Proactive Duplicate Prevention

**Date:** 2025-01-27  
**Status:** ✅ Implemented

---

## Overview

The system now automatically prevents duplicate service instances through:

1. **Proactive checks** before starting services
2. **Automatic cleanup** of duplicates
3. **Service locking** to prevent race conditions
4. **Integration** into all startup scripts

---

## How It Works

### 1. Proactive Prevention Script

**File:** `scripts/prevent-duplicate-services.sh`

**What it does:**

- Checks for duplicate instances before starting
- Automatically cleans up duplicates (if enabled)
- Prevents starting if service already running
- Can be called for specific services or all

**Usage:**

```bash
# Check and clean up before starting frontend
./scripts/prevent-duplicate-services.sh frontend

# Check and clean up before starting API
./scripts/prevent-duplicate-services.sh api

# Check all services
./scripts/prevent-duplicate-services.sh all
```

**Auto-cleanup:**

- Enabled by default (`AUTO_CLEANUP_DUPLICATES=1`)
- Set `AUTO_CLEANUP_DUPLICATES=0` to disable (will error instead)

### 2. Service Locking

**File:** `scripts/service-lock.sh`

**What it does:**

- File-based locking to prevent race conditions
- Ensures only one instance can start at a time
- Automatically removes stale locks
- Prevents simultaneous startups

**Usage:**

```bash
# Acquire lock before starting
./scripts/service-lock.sh frontend-dev acquire

# Release lock when done
./scripts/service-lock.sh frontend-dev release

# Check if locked
./scripts/service-lock.sh frontend-dev check
```

### 3. Safe Startup Scripts

**File:** `frontend/scripts/start-dev-safe.sh`

**What it does:**

- Replaces direct `npm run dev` calls
- Automatically runs duplicate prevention
- Acquires service lock
- Verifies port availability
- Releases lock on exit

**Usage:**

```bash
# Instead of: npm run dev
cd frontend
./scripts/start-dev-safe.sh
```

### 4. Service Management Integration

**File:** `scripts/manage-services.sh`

**What it does:**

- Automatically calls prevention script before starting
- Integrated into `start_api()` and `start_dashboard()`
- No manual intervention needed

**Usage:**

```bash
# Automatically prevents duplicates
./scripts/manage-services.sh start api
./scripts/manage-services.sh start dashboard
```

---

## Automatic Prevention Flow

### When Starting a Service

```
1. User runs: ./scripts/manage-services.sh start dashboard
   │
   ├─> Calls: prevent-duplicate-services.sh dashboard
   │   │
   │   ├─> Checks for duplicate Vite instances
   │   ├─> If found: Auto-cleans (kills npm processes)
   │   └─> If service already running: Exits (skip start)
   │
   ├─> Acquires service lock (prevents race conditions)
   │
   ├─> Verifies port is free
   │
   └─> Starts service
```

### Prevention Layers

1. **Pre-start Check** - `prevent-duplicate-services.sh`
   - Runs before any service starts
   - Automatically cleans duplicates
   - Prevents starting if already running

2. **Service Lock** - `service-lock.sh`
   - File-based locking
   - Prevents simultaneous startups
   - Removes stale locks automatically

3. **Port Verification** - Built into startup
   - Checks port availability
   - Fails fast if port in use

4. **Process Management** - Integrated checks
   - Service management scripts check before starting
   - Safe startup scripts include all checks

---

## Configuration

### Environment Variables

```bash
# Enable/disable auto-cleanup (default: 1)
export AUTO_CLEANUP_DUPLICATES=1  # Auto-clean duplicates
export AUTO_CLEANUP_DUPLICATES=0  # Error if duplicates found
```

### Lock Directory

```bash
# Default: /var/run/dsa110/locks
# Can be overridden
export DSA110_LOCK_DIR="/custom/path/locks"
```

---

## Usage Examples

### Starting Services (Automatic Prevention)

```bash
# API - automatically prevents duplicates
./scripts/manage-services.sh start api

# Dashboard - automatically prevents duplicates
./scripts/manage-services.sh start dashboard

# Frontend - use safe startup script
cd frontend && ./scripts/start-dev-safe.sh
```

### Manual Prevention Check

```bash
# Check and clean up before manual start
./scripts/prevent-duplicate-services.sh frontend

# Then start normally
cd frontend && npm run dev
```

### Disable Auto-Cleanup

```bash
# Error instead of auto-cleaning
AUTO_CLEANUP_DUPLICATES=0 ./scripts/prevent-duplicate-services.sh frontend
```

---

## Integration Points

### 1. Service Management Script

**File:** `scripts/manage-services.sh`

**Changes:**

- `start_api()` calls prevention before starting
- `start_dashboard()` calls prevention before starting
- Automatic, no user action needed

### 2. Frontend Startup

**File:** `frontend/scripts/start-dev-safe.sh`

**Replaces:** Direct `npm run dev` calls

**Benefits:**

- All checks built-in
- Safe to use anywhere
- Prevents duplicates automatically

### 3. CI/CD Integration

Can be added to CI workflows:

```yaml
# .github/workflows/test.yml
- name: Prevent duplicate services
  run: ./scripts/prevent-duplicate-services.sh all
```

---

## Prevention Strategies

### Strategy 1: Pre-Start Checks (Implemented)

- ✅ Check before starting
- ✅ Auto-clean if duplicates found
- ✅ Fail if cleanup disabled and duplicates exist

### Strategy 2: Service Locking (Implemented)

- ✅ File-based locks
- ✅ Prevents race conditions
- ✅ Auto-removes stale locks

### Strategy 3: Port Reservation (Future)

- ⏳ System-level port reservation
- ⏳ Port locking mechanism
- ⏳ Reserved port tracking

### Strategy 4: Process Monitoring (Future)

- ⏳ Monitor for new instances
- ⏳ Auto-kill duplicates
- ⏳ Alert on conflicts

---

## Benefits

✅ **Automatic** - No manual intervention needed  
✅ **Proactive** - Prevents issues before they occur  
✅ **Safe** - Multiple layers of protection  
✅ **Integrated** - Works with existing scripts  
✅ **Configurable** - Can disable auto-cleanup if needed

---

## Troubleshooting

### Lock File Stuck

```bash
# Check lock status
./scripts/service-lock.sh frontend-dev check

# Manually remove stale lock
rm /var/run/dsa110/locks/frontend-dev.lock
```

### Auto-Cleanup Not Working

```bash
# Check if script exists
ls -la scripts/prevent-duplicate-services.sh

# Run manually with verbose output
bash -x scripts/prevent-duplicate-services.sh frontend
```

### Service Still Starting Duplicates

```bash
# Check if prevention is being called
grep -n "prevent-duplicate-services" scripts/manage-services.sh

# Verify service management script is being used
./scripts/manage-services.sh start dashboard
```

---

## Migration Guide

### For Developers

**Old way:**

```bash
cd frontend && npm run dev
```

**New way (recommended):**

```bash
cd frontend && ./scripts/start-dev-safe.sh
```

**Or use service management:**

```bash
./scripts/manage-services.sh start dashboard
```

### For Scripts

**Update scripts that start services:**

```bash
# Before
npm run dev &

# After
./scripts/prevent-duplicate-services.sh frontend
./frontend/scripts/start-dev-safe.sh &
```

---

## Status

✅ **Prevention Script** - Implemented and tested  
✅ **Service Locking** - Implemented  
✅ **Safe Startup Script** - Created  
✅ **Service Management Integration** - Updated  
⏳ **Port Reservation** - Future enhancement  
⏳ **Process Monitoring** - Future enhancement

---

**See Also:**

- `scripts/prevent-duplicate-services.sh` - Prevention script
- `scripts/service-lock.sh` - Locking mechanism
- `frontend/scripts/start-dev-safe.sh` - Safe startup
- `docs/operations/port_duplicate_vite_explanation.md` - Root cause analysis
