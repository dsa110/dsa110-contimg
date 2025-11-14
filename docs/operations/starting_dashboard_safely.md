# Starting Dashboard Safely - Exactly One Instance

**Date:** 2025-01-27  
**Status:** ✅ Automatic duplicate prevention enabled

---

## Recommended Methods

### Method 1: Service Management Script (Recommended)

**Best for:** Production-like usage, automatic port management

```bash
./scripts/manage-services.sh start dashboard
```

**What it does:**

1. ✅ Automatically checks for duplicates
2. ✅ Cleans up any existing duplicates
3. ✅ Acquires service lock (prevents race conditions)
4. ✅ Verifies port availability
5. ✅ Starts exactly one instance

**Features:**

- Automatic duplicate prevention
- Port conflict detection
- Process management
- Logging to `logs/dashboard.log`

---

### Method 2: Safe Startup Script

**Best for:** Direct control, development workflow

```bash
cd frontend
./scripts/start-dev-safe.sh
```

**What it does:**

1. ✅ Checks for duplicates
2. ✅ Cleans up if needed
3. ✅ Acquires service lock
4. ✅ Verifies port 5173 is free
5. ✅ Starts npm run dev

**Features:**

- All safety checks built-in
- Prevents duplicates automatically
- Releases lock on exit (Ctrl+C)

---

### Method 3: npm run dev (Now Safe!)

**Best for:** Quick start, familiar workflow

```bash
cd frontend
npm run dev
```

**What it does:**

- Now uses `start-dev-safe.sh` automatically
- All safety checks included
- Prevents duplicates

**Note:** This was updated to use the safe startup script automatically.

---

## What Happens Automatically

All methods now include:

1. **Duplicate Prevention**
   - Checks for existing Vite instances
   - Auto-cleans duplicates (kills parent npm processes)
   - Prevents starting if already running

2. **Service Locking**
   - File-based locks prevent race conditions
   - Ensures only one instance can start at a time
   - Auto-removes stale locks

3. **Port Verification**
   - Checks port 5173 is available
   - Fails fast if port in use
   - Prevents conflicts

4. **Process Management**
   - Kills parent npm processes (not just Vite)
   - Handles process groups
   - Verifies cleanup

---

## Verification

After starting, verify only one instance:

```bash
# Check for duplicates
./scripts/check-duplicate-services.sh

# Check port usage
lsof -i :5173

# Check processes
ps aux | grep -E "vite|npm.*dev" | grep -v grep
```

**Expected output:**

- ✅ One Vite process on port 5173
- ✅ One npm process (parent of Vite)
- ✅ No duplicates

---

## Troubleshooting

### "Service already running"

If you see:

```
Service already running - skipping start
```

**This means:**

- ✅ Duplicate prevention worked!
- ✅ An instance is already running
- ✅ No need to start another

**To restart:**

```bash
# Stop first
./scripts/manage-services.sh stop dashboard

# Then start
./scripts/manage-services.sh start dashboard
```

### "Port already in use"

If you see:

```
Port 5173 is already in use
```

**Solution:**

```bash
# Clean up duplicates
./scripts/kill-vite-thoroughly.sh

# Then start
./scripts/manage-services.sh start dashboard
```

### "Could not acquire lock"

If you see:

```
ERROR: Could not acquire lock
```

**Solution:**

```bash
# Remove stale lock
rm /var/run/dsa110/locks/dashboard-dev.lock

# Then start
./scripts/manage-services.sh start dashboard
```

---

## Quick Reference

### Start Dashboard

```bash
# Recommended
./scripts/manage-services.sh start dashboard

# Or direct
cd frontend && npm run dev
```

### Stop Dashboard

```bash
./scripts/manage-services.sh stop dashboard

# Or kill manually
pkill -f "npm run dev"
```

### Check Status

```bash
./scripts/check-duplicate-services.sh
```

### Clean Up Duplicates

```bash
./scripts/kill-vite-thoroughly.sh
```

---

## Best Practices

### ✅ DO

- Use service management script for production-like usage
- Use `npm run dev` for quick development
- Check for duplicates before starting: `./scripts/check-duplicate-services.sh`
- Stop before starting: `./scripts/manage-services.sh stop dashboard` then
  `start`

### ❌ DON'T

- Start multiple instances manually
- Use PM2 for dev servers
- Kill processes without stopping properly
- Start without checking for duplicates

---

## Summary

**To start exactly one instance:**

```bash
./scripts/manage-services.sh start dashboard
```

**That's it!** The system automatically:

- ✅ Prevents duplicates
- ✅ Handles conflicts
- ✅ Manages processes
- ✅ Ensures exactly one instance

---

**See Also:**

- `scripts/manage-services.sh` - Service management
- `frontend/scripts/start-dev-safe.sh` - Safe startup
- `scripts/prevent-duplicate-services.sh` - Prevention
- `docs/operations/automatic_duplicate_prevention.md` - Full details
