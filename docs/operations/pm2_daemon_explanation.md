# PM2 Daemon Explanation

**Date:** 2025-01-27  
**What:** PM2 is managing the frontend dev server

---

## What PM2 Is

**PM2** (Process Manager 2) is a production process manager for Node.js
applications. It provides:

- **Auto-restart** - Automatically restarts processes if they crash
- **Monitoring** - Tracks CPU, memory, uptime
- **Logging** - Centralized log management
- **Cluster mode** - Can run multiple instances
- **Startup scripts** - Can auto-start on system boot

---

## What PM2 Is Managing

Based on the PM2 dump file (`/home/ubuntu/.pm2/dump.pm2`), PM2 is managing:

**Process Name:** `frontend-dev`  
**Command:** `npm run dev`  
**Working Directory:** `/data/dsa110-contimg/frontend`  
**Status:** `online` (auto-restart enabled)  
**Started:** November 10, 2024

### Configuration

```json
{
  "name": "frontend-dev",
  "exec_mode": "fork_mode",
  "autorestart": true, // ← This is why it keeps respawning!
  "watch": false,
  "pm_exec_path": "/opt/miniforge/envs/casa6/bin/npm",
  "args": ["run", "dev"],
  "pm_cwd": "/data/dsa110-contimg/frontend"
}
```

**Key Settings:**

- `autorestart: true` - Automatically restarts when killed
- `autostart: true` - Starts automatically when PM2 starts
- `watch: false` - Not watching files for changes

---

## Why It Was Set Up

PM2 was likely set up to:

1. **Keep dev server running** - Auto-restart if it crashes
2. **Survive terminal disconnects** - Keep running after SSH session ends
3. **Production-like environment** - Test in production-like setup
4. **Convenience** - Don't need to manually start dev server

---

## The Problem

PM2's auto-restart behavior is causing issues:

1. **Processes respawn** - When you kill Vite, PM2 restarts it
2. **Port conflicts** - Multiple instances on different ports
3. **Development confusion** - Hard to know which process is "real"
4. **Not ideal for dev** - PM2 is better suited for production

### Evidence from Logs

The PM2 log shows repeated restarts:

```
2025-11-13T14:26:21: App [frontend-dev:0] exited with code [0] via signal [SIGINT]
2025-11-13T14:26:21: App [frontend-dev:0] starting in -fork mode-
2025-11-13T14:26:21: App [frontend-dev:0] online
```

Every time the process is killed, PM2 immediately restarts it.

---

## When PM2 Is Appropriate

### ✅ Good For Production

- Production deployments
- Long-running services
- Services that need to survive crashes
- Services that need monitoring

### ❌ Not Ideal For Development

- Development servers (better to run directly)
- Testing/debugging (harder to control)
- Quick iterations (auto-restart gets in the way)
- Local development (adds complexity)

---

## How It Was Started

PM2 was likely started with:

```bash
# From /data/dsa110-contimg/frontend
pm2 start npm --name "frontend-dev" -- run dev

# Or with a config file
pm2 start ecosystem.config.js
```

The process has been running since **November 10, 2024** (over 2 months!).

---

## What To Do

### Option 1: Stop PM2 Management (Recommended for Dev)

```bash
# Find pm2 command
find ~ -name pm2 2>/dev/null
# Or use: /opt/miniforge/envs/casa6/bin/pm2

# Stop and delete the process
pm2 stop frontend-dev
pm2 delete frontend-dev

# Or stop all
pm2 stop all
pm2 delete all
```

### Option 2: Kill PM2 Daemon

```bash
# Kill PM2 daemon (stops all PM2-managed processes)
sudo kill 3060697
```

### Option 3: Keep PM2 But Disable Auto-Restart

```bash
# Disable auto-restart for this process
pm2 stop frontend-dev
pm2 delete frontend-dev

# If you want to use PM2 later, start without auto-restart
pm2 start npm --name "frontend-dev" -- run dev --no-autorestart
```

---

## Recommendation

**For Development:**

- ❌ Don't use PM2 for dev servers
- ✅ Run `npm run dev` directly
- ✅ Use `./scripts/manage-services.sh start dashboard`
- ✅ Use the safe startup script

**For Production:**

- ✅ PM2 is fine
- ✅ Use separate PM2 configs
- ✅ Don't mix dev and production

---

## Summary

**What PM2 is doing:**

- Managing `frontend-dev` process
- Running `npm run dev` in frontend directory
- Auto-restarting when killed (causing respawning)

**Why it's a problem:**

- Auto-restart conflicts with manual process management
- Creates duplicate instances
- Not ideal for development workflow

**Solution:**

- Stop PM2 management for dev servers
- Use direct `npm run dev` or service management scripts
- Keep PM2 for production only

---

**The cleanup script will handle this automatically** - it detects PM2 and
offers to stop it before cleaning up processes.
