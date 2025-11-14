# PM2 Process Respawning Issue

**Date:** 2025-01-27  
**Root Cause:** PM2 (Process Manager) is automatically restarting Vite processes

---

## Problem

Vite processes keep respawning even after being killed because **PM2 is managing
them**.

### Evidence

```bash
$ ps aux | grep pm2
ubuntu   3060697  PM2 v6.0.13: God Daemon

$ ps -p 4015074 -o pid,ppid,cmd
  PID    PPID CMD
4015074 3060697 npm run dev  # Parent is PM2!
```

**Process Hierarchy:**

```
PM2 (PID 3060697)
  └─ npm run dev (PID 4015074)
      └─ sh -c bash scripts/start-dev-safe.sh || vite (PID 4015145)
          └─ node vite (PID 4015364, port 5174)
```

**What happens:**

1. You kill the Vite process
2. PM2 detects the process died
3. PM2 automatically restarts it
4. New Vite process appears on a different port

---

## Solution

### Option 1: Stop PM2 Processes (Recommended)

```bash
# List PM2 processes
pm2 list

# Stop all PM2 processes
pm2 stop all

# Delete all PM2 processes (prevents auto-restart)
pm2 delete all

# Then kill Vite processes normally
./scripts/kill-vite-thoroughly.sh
```

### Option 2: Stop Specific PM2 Process

```bash
# Find the process name
pm2 list

# Stop specific process
pm2 stop <process-name>

# Delete specific process
pm2 delete <process-name>
```

### Option 3: Use Updated Cleanup Script

The `kill-vite-thoroughly.sh` script now:

1. Checks for PM2-managed processes
2. Prompts to stop PM2 processes
3. Then kills Vite processes

```bash
./scripts/kill-vite-thoroughly.sh
# Will prompt: "Stop PM2 processes now? (y/n)"
```

---

## Prevention

### Don't Use PM2 for Development

**For development:**

- Use `npm run dev` directly
- Use `./scripts/manage-services.sh start dashboard`
- Don't use PM2 for dev servers

**For production:**

- PM2 is fine for production
- But use separate PM2 configs
- Don't mix dev and production processes

### Check Before Starting

```bash
# Check if PM2 is managing anything
pm2 list

# If PM2 processes exist, stop them first
pm2 stop all
pm2 delete all
```

---

## PM2 Commands Reference

```bash
# List all processes
pm2 list

# Stop all processes
pm2 stop all

# Stop specific process
pm2 stop <id|name>

# Delete all processes
pm2 delete all

# Delete specific process
pm2 delete <id|name>

# Show process info
pm2 describe <id|name>

# Show logs
pm2 logs

# Save current process list
pm2 save

# Restore saved processes
pm2 resurrect
```

---

## Updated Cleanup Script

The `kill-vite-thoroughly.sh` script now includes PM2 detection:

1. **Step 0:** Check for PM2-managed processes
2. **Step 1:** Find all Vite processes
3. **Step 2:** Find parent npm processes
4. **Step 3:** Find process groups
5. **Step 4:** Find wrapper scripts
6. **Step 5:** Kill in correct order
7. **Step 5:** Force kill remaining
8. **Step 6:** Verify cleanup

**Usage:**

```bash
./scripts/kill-vite-thoroughly.sh
```

---

## Why PM2 Was Running

PM2 might have been started:

1. Manually: `pm2 start npm --name "frontend" -- run dev`
2. By a script: Some startup script uses PM2
3. By systemd: PM2 service auto-starts
4. By previous session: Left running from before

**Check:**

```bash
# Check if PM2 service is enabled
systemctl status pm2

# Check PM2 startup script
pm2 startup

# Check saved processes
pm2 list
```

---

## Best Practices

### Development

✅ **DO:**

- Use `npm run dev` directly
- Use `./scripts/manage-services.sh start dashboard`
- Use the safe startup script

❌ **DON'T:**

- Use PM2 for development
- Mix PM2 and direct npm processes
- Leave PM2 processes running

### Production

✅ **DO:**

- Use PM2 for production
- Use separate PM2 configs
- Monitor PM2 processes

❌ **DON'T:**

- Run dev and production together
- Use same PM2 instance for both

---

## Status

✅ **PM2 Detection** - Added to cleanup script  
✅ **PM2 Handling** - Prompts to stop PM2 processes  
✅ **Documentation** - Complete

---

**See Also:**

- `scripts/kill-vite-thoroughly.sh` - Updated cleanup script
- `docs/operations/vite_respawning_fix.md` - General respawning fix
