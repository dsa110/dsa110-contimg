# Frontend Server Port Mismatch Investigation

**Date:** 2025-11-15  
**Status:** Identified - SSH port forwarding using old port

---

## Problem Summary

SSH is repeatedly attempting to connect to port **5173** (old frontend port),
but the frontend dev server is running on port **3210** (new port). This causes
connection failures logged in system logs.

## Error Evidence

From system logs (`journalctl`):

```
sshd[2989295]: error: connect_to localhost port 5173: failed.
```

This error repeats continuously, indicating an active SSH port forwarding
session trying to connect to the old port.

## Root Cause

1. **Frontend server migrated:** Port changed from 5173 → 3210 (per
   `operations/frontend_dev_port_migration.md`)
2. **SSH configuration outdated:** Client machine has SSH port forwarding
   configured for old port 5173
3. **Documentation outdated:** Some docs still reference port 5173

## Current Status

- **Frontend server:** Running correctly on port 3210 (PID 721538)
- **Server response:** HTTP 200 OK
- **API proxy:** Working correctly
- **SSH forwarding:** Attempting to connect to non-existent port 5173

## Solution

### For SSH Port Forwarding

Update your SSH configuration on your **local machine** (not on lxd110h17):

#### Option 1: Update SSH Command

**Old:**

```bash
ssh -L 8000:localhost:8000 -L 5173:localhost:5173 h17
```

**New:**

```bash
ssh -L 8000:localhost:8000 -L 3210:localhost:3210 h17
```

#### Option 2: Update SSH Config File

Edit `~/.ssh/config` on your local machine:

**Old:**

```
Host h17
    LocalForward 8000 localhost:8000
    LocalForward 5173 localhost:5173
```

**New:**

```
Host h17
    LocalForward 8000 localhost:8000
    LocalForward 3210 localhost:3210
```

Then reconnect:

```bash
ssh h17
```

### Access URLs

After updating SSH port forwarding:

- **Backend API:** `http://localhost:8000`
- **Frontend dev server:** `http://localhost:3210` (was `http://localhost:5173`)

## Verification

1. **Check if port forwarding is working:**

   ```bash
   # On your local machine
   curl http://localhost:3210
   # Should return HTML (not "connection refused")
   ```

2. **Check server status on remote:**

   ```bash
   # On lxd110h17
   curl http://localhost:3210
   lsof -i :3210
   ```

3. **Verify no more errors:**
   ```bash
   # On lxd110h17
   journalctl --since "5 minutes ago" | grep "5173" | tail -5
   # Should show no new errors after fixing SSH config
   ```

## Documentation Updates Needed

The following files still reference port 5173 and should be updated:

1. `docs/how-to/remote-access-tools.md` - Line 59, 64
2. `docs/development/DEVELOPMENT_SETUP.md` - Lines 81-84, 103, 115

## Related Documentation

- `operations/frontend_dev_port_migration.md` - Port migration details
- `operations/frontend_dev_fix_summary.md` - Previous fixes
- `config/ports.yaml` - Current port configuration

---

**Next Steps:**

1. Update SSH port forwarding on local machine
2. Update documentation to reflect port 3210
3. Verify errors stop appearing in logs
