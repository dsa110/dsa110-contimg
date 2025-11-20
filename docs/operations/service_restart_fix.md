# Service Restart Fix - Process Tree Killing

## Problem

The `manage-services.sh` script's `restart` command was failing because:

1. `lsof -ti:8000` only returns the **child process** (uvicorn)
2. The **parent process** (conda/bash wrapper) was still alive
3. When the child was killed, the parent would immediately respawn it
4. The new `start` command would fail with "Address already in use"

## Root Cause

When using `conda run -n casa6 ... uvicorn ...`, the process tree looks like:

```
bash (parent, PID 1859238)
  └─ /tmp/tmpXXXXXX (conda wrapper script)
      └─ uvicorn (child, PID 1860090) ← listening on port 8000
```

Killing only the uvicorn process left the parent alive, which would respawn it.

## Solution

Updated `kill_port()` function in `scripts/manage-services.sh` to:

1. For each PID on the port, find its parent process (`ppid`)
2. Check if parent is a conda/bash/tmp wrapper
3. Kill the **parent first**, then the child
4. Use graceful kill (SIGTERM) first, then force kill (SIGKILL) if needed
5. Retry up to 5 times with 2-second delays

## Code Changes

```bash
# Old: Only killed the child
sudo kill $pids 2>/dev/null || kill $pids 2>/dev/null

# New: Kill parent and child
for pid in $pids; do
    local ppid=$(ps -o ppid= -p $pid 2>/dev/null | tr -d ' ')
    if [ -n "$ppid" ] && [ "$ppid" != "1" ]; then
        local parent_cmd=$(ps -o cmd= -p $ppid 2>/dev/null)
        if [[ "$parent_cmd" =~ (conda|bash|tmp) ]]; then
            sudo kill $ppid 2>/dev/null || kill $ppid 2>/dev/null
        fi
    fi
    sudo kill $pid 2>/dev/null || kill $pid 2>/dev/null
done
```

## Verification

```bash
# Test restart
./scripts/manage-services.sh restart api

# Check port
lsof -i :8000

# Verify API responds
curl http://localhost:8000/api/ms
```

## Additional Cleanup

Removed old systemd override that had incorrect uvicorn path:

```bash
sudo rm -rf /etc/systemd/system/contimg-api.service.d/
sudo systemctl daemon-reload
```

## Result

✓ `restart api` now works reliably without manual intervention ✓ No more
"Address already in use" errors ✓ Port is properly freed before new process
starts
